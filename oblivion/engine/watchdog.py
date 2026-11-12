import datetime
import logging
import time
from typing import Any, Dict, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ..storage.database import get_config_value, set_config_value, add_audit_log
from ..integrations.telegram_bot import telegram_worker
from .dispatcher import execute_trigger

logger = logging.getLogger("oblivion.watchdog")

class WatchdogEngine:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._master_key_session: Optional[bytes] = None
        self._last_grace_alert_time: float = 0.0

    def set_session_key(self, key: bytes) -> None:
        self._master_key_session = key

    def get_session_key(self) -> Optional[bytes]:
        return self._master_key_session

    def clear_session_key(self) -> None:
        self._master_key_session = None

    async def start(self) -> None:
        telegram_worker.set_watchdog(self)
        self.scheduler.add_job(self._tick, "interval", seconds=5, id="watchdog_ticker", replace_existing=True)
        self.scheduler.start()

    async def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def record_checkin(self, source: str = "Web Dashboard") -> None:
        now = time.time()
        await set_config_value("last_checkin_timestamp", str(now))
        current_status = await get_config_value("status", "ACTIVE")
        if current_status == "GRACE_PERIOD":
            await set_config_value("status", "ACTIVE")
            await set_config_value("grace_started_timestamp", "0")
            await add_audit_log("GRACE_CANCELLED", f"Grace period cancelled by check-in via {source}", "INFO")
        else:
            await add_audit_log("CHECKIN", f"Activity check-in confirmed via {source}", "INFO")

    async def get_detailed_status(self) -> Dict[str, Any]:
        setup_done = (await get_config_value("setup_completed", "0")) == "1"
        if not setup_done:
            return {
                "setup_completed": False,
                "status": "NOT_CONFIGURED",
                "remaining_seconds": 0,
                "is_locked": False,
                "unlocked_session": bool(self._master_key_session)
            }

        status = await get_config_value("status", "ACTIVE")
        last_checkin = float(await get_config_value("last_checkin_timestamp", "0") or "0")
        interval = int(await get_config_value("checkin_interval_sec", "604800") or "604800")
        grace = int(await get_config_value("grace_period_sec", "86400") or "86400")
        now = time.time()

        deadline = last_checkin + interval
        final_deadline = deadline + grace

        if status == "TRIGGERED":
            remaining = 0
        elif now < deadline:
            remaining = max(0, int(deadline - now))
        elif now < final_deadline:
            remaining = max(0, int(final_deadline - now))
        else:
            remaining = 0

        last_checkin_dt = datetime.datetime.fromtimestamp(last_checkin) if last_checkin > 0 else None
        deadline_dt = datetime.datetime.fromtimestamp(deadline) if last_checkin > 0 else None
        final_deadline_dt = datetime.datetime.fromtimestamp(final_deadline) if last_checkin > 0 else None

        return {
            "setup_completed": True,
            "status": status,
            "remaining_seconds": remaining,
            "interval_seconds": interval,
            "grace_seconds": grace,
            "last_checkin_timestamp": last_checkin,
            "last_checkin_str": last_checkin_dt.strftime("%Y-%m-%d %H:%M:%S") if last_checkin_dt else "-",
            "next_deadline_str": deadline_dt.strftime("%Y-%m-%d %H:%M:%S") if deadline_dt else "-",
            "grace_deadline_str": final_deadline_dt.strftime("%Y-%m-%d %H:%M:%S") if final_deadline_dt else "-",
            "interval_str": self._format_duration(interval),
            "grace_str": self._format_duration(grace),
            "unlocked_session": bool(self._master_key_session),
            "telegram_connected": telegram_worker.is_connected,
            "telegram_username": telegram_worker.bot_username
        }

    def _format_duration(self, seconds: int) -> str:
        if seconds >= 86400:
            days = seconds // 86400
            return f"{days}d"
        elif seconds >= 3600:
            hours = seconds // 3600
            return f"{hours}h"
        elif seconds >= 60:
            minutes = seconds // 60
            return f"{minutes}m"
        return f"{seconds}s"

    async def _tick(self) -> None:
        try:
            setup_done = (await get_config_value("setup_completed", "0")) == "1"
            if not setup_done:
                return

            status = await get_config_value("status", "ACTIVE")
            if status == "TRIGGERED":
                return

            last_checkin = float(await get_config_value("last_checkin_timestamp", "0") or "0")
            if last_checkin <= 0:
                return

            interval = int(await get_config_value("checkin_interval_sec", "604800") or "604800")
            grace = int(await get_config_value("grace_period_sec", "86400") or "86400")
            now = time.time()

            deadline = last_checkin + interval
            final_deadline = deadline + grace

            if status == "ACTIVE":
                if now >= deadline:
                    await set_config_value("status", "GRACE_PERIOD")
                    await set_config_value("grace_started_timestamp", str(now))
                    await add_audit_log("GRACE_ENTERED", f"Inactivity deadline reached. Grace period activated ({grace}s)", "WARNING")
                    rem = max(0, int(final_deadline - now))
                    await telegram_worker.send_grace_alert(rem)
                    self._last_grace_alert_time = now

            elif status == "GRACE_PERIOD":
                if now >= final_deadline:
                    await set_config_value("status", "TRIGGERED")
                    await add_audit_log("TRIGGERED", "OBLIVION grace period expired without check-in. Initiating emergency protocols.", "DANGER")
                    await execute_trigger(self._master_key_session)
                else:
                    rem = max(0, int(final_deadline - now))
                    if now - self._last_grace_alert_time >= 300:
                        await telegram_worker.send_grace_alert(rem)
                        self._last_grace_alert_time = now
        except Exception as exc:
            logger.debug(f"Watchdog tick exception: {exc}")

watchdog = WatchdogEngine()
