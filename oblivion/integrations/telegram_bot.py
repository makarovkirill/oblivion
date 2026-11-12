import asyncio
import logging
import time
from typing import List, Optional, Tuple
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from ..storage.database import get_db, get_config_value, add_audit_log
from ..crypto.vault import verify_secret

logger = logging.getLogger("oblivion.telegram")

class TelegramWorker:
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.polling_task: Optional[asyncio.Task] = None
        self.supervisor_task: Optional[asyncio.Task] = None
        self.is_connected: bool = False
        self.bot_username: Optional[str] = None
        self.watchdog = None
        self._running: bool = False

    def set_watchdog(self, watchdog):
        self.watchdog = watchdog

    async def start(self) -> None:
        self._running = True
        if self.supervisor_task is None or self.supervisor_task.done():
            self.supervisor_task = asyncio.create_task(self._supervise_connection())

    async def _supervise_connection(self) -> None:
        while self._running:
            token = await get_config_value("telegram_bot_token")
            if not token:
                self.is_connected = False
                await asyncio.sleep(5)
                continue

            if not self.is_connected:
                try:
                    self.bot = Bot(token=token)
                    me = await self.bot.get_me()
                    self.bot_username = me.username
                    self.is_connected = True

                    self.dp = Dispatcher()
                    self._register_handlers()

                    self.polling_task = asyncio.create_task(self.dp.start_polling(self.bot, handle_signals=False))
                    await add_audit_log("TELEGRAM_STARTED", f"Telegram Bot @{me.username} online", "INFO")
                except Exception as exc:
                    self.is_connected = False
                    if self.bot:
                        try:
                            await self.bot.session.close()
                        except Exception:
                            pass
                        self.bot = None
                    self.dp = None
                    logger.debug(f"Telegram connection pending network: {exc}")
                    await asyncio.sleep(10)
                    continue

            if self.polling_task and self.polling_task.done():
                self.is_connected = False
                if self.bot:
                    try:
                        await self.bot.session.close()
                    except Exception:
                        pass
                    self.bot = None
                self.dp = None

            await asyncio.sleep(5)

    async def stop(self) -> None:
        self._running = False
        if self.supervisor_task:
            self.supervisor_task.cancel()
            try:
                await self.supervisor_task
            except asyncio.CancelledError:
                pass
            self.supervisor_task = None

        if self.dp and self.polling_task:
            self.dp.stop_polling()
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
            self.polling_task = None

        if self.bot:
            await self.bot.session.close()
            self.bot = None

        self.is_connected = False
        self.bot_username = None

    async def restart(self) -> None:
        await self.stop()
        await self.start()

    def _register_handlers(self) -> None:
        @self.dp.message(Command("start"))
        async def handle_start(message: types.Message):
            lang = await get_config_value("language", "en")
            if lang == "ru":
                text = (
                    "🛡 <b>OBLIVION — Dead Man's Switch</b>\n\n"
                    "Бот активен и подключен к локальной службе.\n\n"
                    "Команды:\n"
                    "/status — Текущее состояние таймера\n"
                    "/checkin — Инструкция по подтверждению активности\n"
                    "/help — Справка по командам\n\n"
                    "Для подтверждения активности отправьте пароль проверки (от 16 символов) в ответ. "
                    "Сообщение с паролем будет <b>немедленно удалено</b> из истории чата."
                )
            else:
                text = (
                    "🛡 <b>OBLIVION — Dead Man's Switch</b>\n\n"
                    "Bot is active and connected to your local instance.\n\n"
                    "Commands:\n"
                    "/status — Current countdown & switch status\n"
                    "/checkin — Check-in instructions\n"
                    "/help — Commands and assistance\n\n"
                    "To confirm activity, send your 16+ character check-in passphrase in reply. "
                    "Your message will be <b>immediately deleted</b> upon receipt for security."
                )
            await message.answer(text, parse_mode="HTML")

        @self.dp.message(Command("status"))
        async def handle_status(message: types.Message):
            if not self.watchdog:
                await message.answer("OBLIVION Engine not initialized.")
                return
            status_info = await self.watchdog.get_detailed_status()
            lang = await get_config_value("language", "en")
            text = self._format_status_message(status_info, lang)
            keyboard = self._build_status_keyboard(lang)
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

        @self.dp.message(Command("checkin"))
        async def handle_checkin_cmd(message: types.Message):
            lang = await get_config_value("language", "en")
            if lang == "ru":
                text = "🔑 Отправьте ваш <b>16+ значный пароль проверки</b> следующим сообщением. Оно будет немедленно удалено из истории чата."
            else:
                text = "🔑 Send your <b>16+ character check-in passphrase</b> as your next message. It will be immediately deleted from chat history."
            await message.answer(text, parse_mode="HTML")

        @self.dp.message(Command("help"))
        async def handle_help_cmd(message: types.Message):
            lang = await get_config_value("language", "en")
            if lang == "ru":
                text = (
                    "ℹ️ <b>Справка OBLIVION</b>\n\n"
                    "• При отсутствии подтверждения включается период ожидания (Grace Period).\n"
                    "• В случае истечения Grace Period система необратимо уничтожит локальные данные или передаст их доверенным лицам по политике Transfer & Wipe.\n"
                    "• Сообщения с паролями проверки стираются ботом мгновенно."
                )
            else:
                text = (
                    "ℹ️ <b>OBLIVION Security Overview</b>\n\n"
                    "• If inactivity expires, OBLIVION enters the Grace Period.\n"
                    "• If the Grace Period elapses without a valid passphrase check-in, the execution engine permanently wipes local data or transmits escrow shares.\n"
                    "• Check-in passphrase messages sent to this bot are purged immediately."
                )
            await message.answer(text, parse_mode="HTML")

        @self.dp.callback_query(F.data == "oblivion_status")
        async def cb_status(query: types.CallbackQuery):
            if not self.watchdog:
                await query.answer("Engine offline.")
                return
            status_info = await self.watchdog.get_detailed_status()
            lang = await get_config_value("language", "en")
            text = self._format_status_message(status_info, lang)
            keyboard = self._build_status_keyboard(lang)
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                pass
            await query.answer()

        @self.dp.callback_query(F.data == "oblivion_checkin_prompt")
        async def cb_checkin_prompt(query: types.CallbackQuery):
            lang = await get_config_value("language", "en")
            prompt = "Отправьте 16+ значный пароль в чат прямо сейчас." if lang == "ru" else "Send your 16+ char passphrase in chat now."
            await query.answer(prompt, show_alert=True)

        @self.dp.message(F.text)
        async def handle_text_message(message: types.Message):
            candidate = message.text.strip()
            chat_id = str(message.chat.id)
            owner_id = await get_config_value("telegram_owner_chat_id")

            if owner_id and chat_id != str(owner_id).strip():
                return

            try:
                await message.delete()
            except Exception as exc:
                logger.warning(f"Could not delete message from chat: {exc}")

            lang = await get_config_value("language", "en")

            now = time.time()
            async with get_db() as db:
                async with db.execute("SELECT failed_attempts, locked_until FROM rate_limit_state WHERE key = 'checkin_passphrase'") as cursor:
                    rl_row = await cursor.fetchone()
                    if rl_row and now < float(rl_row["locked_until"]):
                        rem = max(1, int(float(rl_row["locked_until"]) - now))
                        lock_msg = (
                            f"⏳ <b>OBLIVION: Превышен лимит попыток.</b>\nПовторите попытку через {rem}с."
                            if lang == "ru" else
                            f"⏳ <b>OBLIVION: Rate limit active.</b>\nRetry after {rem}s."
                        )
                        await message.answer(lock_msg, parse_mode="HTML")
                        return

            stored_hash = await get_config_value("passphrase_hash")
            if not stored_hash:
                return

            if verify_secret(stored_hash, candidate):
                async with get_db() as db:
                    await db.execute("DELETE FROM rate_limit_state WHERE key = 'checkin_passphrase'")
                    await db.commit()

                if self.watchdog:
                    await self.watchdog.record_checkin(source="Telegram Bot")
                ok_text = (
                    "✅ <b>OBLIVION: Активность подтверждена!</b>\nТаймер сброшен, отсчет перезапущен."
                    if lang == "ru" else
                    "✅ <b>OBLIVION: Check-In Confirmed!</b>\nTimer successfully reset and restarted."
                )
                await message.answer(ok_text, parse_mode="HTML")
            else:
                async with get_db() as db:
                    async with db.execute("SELECT failed_attempts FROM rate_limit_state WHERE key = 'checkin_passphrase'") as cursor:
                        row = await cursor.fetchone()
                        fails = (row["failed_attempts"] if row else 0) + 1
                    locked_until = now + min(300, 5 * (2 ** (fails - 3))) if fails >= 3 else 0.0
                    await db.execute(
                        """
                        INSERT INTO rate_limit_state (key, failed_attempts, locked_until)
                        VALUES ('checkin_passphrase', ?, ?)
                        ON CONFLICT(key) DO UPDATE SET failed_attempts = excluded.failed_attempts, locked_until = excluded.locked_until
                        """,
                        (fails, locked_until)
                    )
                    await db.commit()

                await add_audit_log("FAILED_CHECKIN", f"Failed Telegram checkin attempt from chat {chat_id} (fails: {fails})", "WARNING")
                fail_text = (
                    "❌ <b>OBLIVION: Неверный пароль проверки.</b>"
                    if lang == "ru" else
                    "❌ <b>OBLIVION: Invalid check-in passphrase.</b>"
                )
                await message.answer(fail_text, parse_mode="HTML")

    def _format_status_message(self, info: dict, lang: str) -> str:
        state = info.get("status", "UNKNOWN")
        remaining_sec = max(0, int(info.get("remaining_seconds", 0)))
        days = remaining_sec // 86400
        hours = (remaining_sec % 86400) // 3600
        mins = (remaining_sec % 3600) // 60
        secs = remaining_sec % 60

        time_str = f"{days}d {hours}h {mins}m {secs}s" if days > 0 else f"{hours}h {mins}m {secs}s"

        if lang == "ru":
            state_ru = {
                "ACTIVE": "🟢 АКТИВЕН",
                "GRACE_PERIOD": "⚠️ GRACE PERIOD",
                "TRIGGERED": "🔴 СРАБОТАЛ"
            }.get(state, state)
            return (
                f"🛡 <b>OBLIVION: Состояние системы</b>\n\n"
                f"Статус: <b>{state_ru}</b>\n"
                f"До дедлайна: <b>{time_str}</b>\n"
                f"Интервал проверки: <b>{info.get('interval_str', '')}</b>\n"
                f"Период ожидания: <b>{info.get('grace_str', '')}</b>\n"
                f"Последний чекин: <b>{info.get('last_checkin_str', '')}</b>"
            )
        else:
            state_en = {
                "ACTIVE": "🟢 ACTIVE",
                "GRACE_PERIOD": "⚠️ GRACE PERIOD",
                "TRIGGERED": "🔴 TRIGGERED"
            }.get(state, state)
            return (
                f"🛡 <b>OBLIVION: System Status</b>\n\n"
                f"State: <b>{state_en}</b>\n"
                f"Time Remaining: <b>{time_str}</b>\n"
                f"Inactivity Interval: <b>{info.get('interval_str', '')}</b>\n"
                f"Grace Period: <b>{info.get('grace_str', '')}</b>\n"
                f"Last Check-In: <b>{info.get('last_checkin_str', '')}</b>"
            )

    def _build_status_keyboard(self, lang: str) -> InlineKeyboardMarkup:
        btn_refresh = "🔄 Обновить" if lang == "ru" else "🔄 Refresh"
        btn_checkin = "🔑 Подтвердить активность" if lang == "ru" else "🔑 Check In"
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=btn_refresh, callback_data="oblivion_status"),
                InlineKeyboardButton(text=btn_checkin, callback_data="oblivion_checkin_prompt")
            ]
        ])

    async def send_grace_alert(self, remaining_sec: int) -> bool:
        if not self.bot or not self.is_connected:
            return False
        owner_id = await get_config_value("telegram_owner_chat_id")
        if not owner_id:
            return False

        lang = await get_config_value("language", "en")
        hours = remaining_sec // 3600
        mins = (remaining_sec % 3600) // 60

        if lang == "ru":
            text = (
                f"🚨 <b>OBLIVION: АКТИВИРОВАН GRACE PERIOD!</b> 🚨\n\n"
                f"Отметка присутствия не была получена вовремя.\n"
                f"До необратимого исполнения протокола осталось: <b>{hours}ч {mins}мин</b>.\n\n"
                f"Отправьте ваш 16+ значный пароль проверки в этот чат прямо сейчас для отмены!"
            )
            btn_text = "🔑 Отправить пароль для отмены"
        else:
            text = (
                f"🚨 <b>OBLIVION: GRACE PERIOD ACTIVATED!</b> 🚨\n\n"
                f"Inactivity threshold exceeded.\n"
                f"Time until irreversible protocol execution: <b>{hours}h {mins}min</b>.\n\n"
                f"Send your 16+ char Check-In Passphrase into this chat immediately to cancel!"
            )
            btn_text = "🔑 Send Passphrase To Cancel"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data="oblivion_checkin_prompt")],
            [InlineKeyboardButton(text="📊 Status", callback_data="oblivion_status")]
        ])

        try:
            await self.bot.send_message(chat_id=int(owner_id), text=text, reply_markup=keyboard, parse_mode="HTML")
            return True
        except Exception as exc:
            logger.error(f"Failed to send grace alert: {exc}")
            return False

    async def send_beneficiary_packet(
        self,
        chat_id: str,
        beneficiary_name: str,
        message_body: str,
        attachments: Optional[List[Tuple[str, bytes]]] = None
    ) -> bool:
        if not self.bot or not self.is_connected:
            return False

        try:
            await self.bot.send_message(
                chat_id=int(chat_id),
                text=message_body,
                parse_mode="HTML"
            )
            if attachments:
                for filename, file_bytes in attachments:
                    doc = BufferedInputFile(file_bytes, filename=filename)
                    await self.bot.send_document(chat_id=int(chat_id), document=doc)
            return True
        except Exception as exc:
            logger.error(f"Failed to send beneficiary packet to {chat_id}: {exc}")
            return False

    @staticmethod
    async def test_ping(token: str, chat_id: str) -> Tuple[bool, str]:
        test_bot = None
        try:
            test_bot = Bot(token=token.strip())
            me = await test_bot.get_me()
            await test_bot.send_message(
                chat_id=int(chat_id.strip()),
                text=(
                    f"✅ <b>OBLIVION Test Ping</b>\n\n"
                    f"Connection established with bot @{me.username}!\n"
                    f"Autonomous monitoring channel is operational."
                ),
                parse_mode="HTML"
            )
            return True, f"Ping sent successfully via @{me.username}"
        except Exception as exc:
            return False, str(exc)
        finally:
            if test_bot:
                await test_bot.session.close()

telegram_worker = TelegramWorker()
