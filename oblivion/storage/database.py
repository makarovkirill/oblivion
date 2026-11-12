from contextlib import asynccontextmanager
import time
from typing import Any, Dict, List, Optional
import aiosqlite
from ..config import settings
from .models import SCHEMA_SQL

@asynccontextmanager
async def get_db():
    db = await aiosqlite.connect(settings.db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode = WAL")
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
    finally:
        await db.close()

async def init_db() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    async with get_db() as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()

async def get_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    async with get_db() as db:
        async with db.execute("SELECT value FROM system_config WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row["value"] if row else default

async def set_config_value(key: str, value: str) -> None:
    async with get_db() as db:
        await db.execute(
            "INSERT INTO system_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value)
        )
        await db.commit()

async def get_all_config() -> Dict[str, str]:
    async with get_db() as db:
        async with db.execute("SELECT key, value FROM system_config") as cursor:
            rows = await cursor.fetchall()
            return {row["key"]: row["value"] for row in rows}

async def add_audit_log(event_type: str, details: str, severity: str = "INFO") -> None:
    async with get_db() as db:
        await db.execute(
            "INSERT INTO audit_logs (timestamp, event_type, details, severity) VALUES (?, ?, ?, ?)",
            (time.time(), event_type, details, severity)
        )
        await db.commit()

async def get_recent_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            "SELECT id, timestamp, event_type, details, severity FROM audit_logs ORDER BY id DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
