import ctypes
import io
import json
import os
import secrets
import subprocess
import time
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from ..config import settings
from ..storage.database import (
    get_db,
    get_config_value,
    set_config_value,
    get_all_config,
    add_audit_log,
    get_recent_audit_logs,
    init_db
)
from ..crypto.vault import (
    generate_salt,
    hash_secret,
    verify_secret,
    derive_master_key,
    encrypt_bytes,
    decrypt_bytes,
    encrypt_string,
    decrypt_string,
    b64_encode,
    b64_decode
)
from ..crypto.escrow import create_split_dek_escrow, create_recovery_bundle
from ..crypto.shredder import shred_file
from ..engine.watchdog import watchdog
from ..engine.dispatcher import simulate_trigger, execute_panic_wipe
from ..integrations.telegram_bot import telegram_worker, TelegramWorker
from ..integrations.mailer import send_email_async
from .schemas import (
    TestTelegramRequest,
    TestEmailRequest,
    InitializeRequest,
    UnlockRequest,
    CheckInRequest,
    ContactCreateRequest,
    ContactUpdateRequest,
    UpdateSettingsRequest,
    PanicWipeRequest
)

api_router = APIRouter(prefix="/api")

def is_running_as_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

_task_cache = None
_task_cache_time = 0.0

def check_scheduled_task() -> dict:
    global _task_cache, _task_cache_time
    now = time.time()
    if _task_cache is not None and (now - _task_cache_time) < 30.0:
        return _task_cache

    if os.name != "nt":
        res = {"registered": False, "status": "non_windows", "details": "Non-Windows OS"}
        _task_cache = res
        _task_cache_time = now
        return res

    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        result = subprocess.run(
            ["schtasks", "/query", "/tn", settings.task_name, "/fo", "LIST", "/v"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=flags
        )
        if result.returncode == 0:
            task_status = "Ready"
            for line in result.stdout.splitlines():
                if "Status:" in line or "Состояние:" in line:
                    task_status = line.split(":", 1)[1].strip()
                    break
            res = {
                "registered": True,
                "status": task_status,
                "task_name": settings.task_name
            }
        else:
            res = {
                "registered": False,
                "status": "not_registered",
                "task_name": settings.task_name
            }
    except Exception as exc:
        res = {
            "registered": False,
            "status": "query_error",
            "error": str(exc),
            "task_name": settings.task_name
        }

    _task_cache = res
    _task_cache_time = now
    return res

def require_unlocked_session() -> bytes:
    key = watchdog.get_session_key()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vault session is locked. Master password required."
        )
    return key

async def check_rate_limit(key: str) -> None:
    now = time.time()
    async with get_db() as db:
        async with db.execute("SELECT failed_attempts, locked_until FROM rate_limit_state WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            if row:
                locked_until = float(row["locked_until"])
                if now < locked_until:
                    retry_after = max(1, int(locked_until - now))
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many failed attempts. Rate limit active. Retry after {retry_after}s."
                    )

async def record_failed_attempt(key: str) -> int:
    now = time.time()
    async with get_db() as db:
        async with db.execute("SELECT failed_attempts FROM rate_limit_state WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            current_fails = (row["failed_attempts"] if row else 0) + 1

        if current_fails >= 3:
            delay = min(300, 5 * (2 ** (current_fails - 3)))
            locked_until = now + delay
        else:
            locked_until = 0.0

        await db.execute(
            """
            INSERT INTO rate_limit_state (key, failed_attempts, locked_until)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET failed_attempts = excluded.failed_attempts, locked_until = excluded.locked_until
            """,
            (key, current_fails, locked_until)
        )
        await db.commit()
        return current_fails

async def reset_rate_limit(key: str) -> None:
    async with get_db() as db:
        await db.execute("DELETE FROM rate_limit_state WHERE key = ?", (key,))
        await db.commit()

# --- SETUP ENDPOINTS ---

@api_router.get("/setup/status")
async def get_setup_status():
    setup_completed = (await get_config_value("setup_completed", "0")) == "1"
    language = await get_config_value("language", "en")
    return {
        "setup_completed": setup_completed,
        "language": language
    }

@api_router.post("/setup/test-telegram")
async def test_telegram(req: TestTelegramRequest):
    if not req.token or not req.chat_id:
        raise HTTPException(status_code=400, detail="Token and chat_id are required")
    success, msg = await TelegramWorker.test_ping(req.token, req.chat_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@api_router.post("/setup/test-email")
async def test_email(req: TestEmailRequest):
    config = {
        "host": req.host,
        "port": req.port,
        "user": req.user,
        "password": req.password,
        "from_addr": req.from_addr or req.user,
        "use_tls": req.use_tls
    }
    success, msg = await send_email_async(
        config=config,
        to_addr=req.target_email,
        subject="OBLIVION: SMTP Notification Test",
        content="This is an automated test verifying the OBLIVION notification dispatch channel."
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": "Email sent successfully"}

@api_router.post("/setup/initialize")
async def initialize_system(req: InitializeRequest):
    is_done = (await get_config_value("setup_completed", "0")) == "1"
    if is_done:
        raise HTTPException(status_code=400, detail="System is already initialized")

    if len(req.checkin_passphrase) < 16:
        raise HTTPException(status_code=400, detail="Check-In Passphrase must be at least 16 characters")

    await init_db()

    master_salt = generate_salt(16)
    master_hash = hash_secret(req.master_password)
    master_key = derive_master_key(req.master_password, master_salt)

    passphrase_salt = generate_salt(16)
    passphrase_hash = hash_secret(req.checkin_passphrase)

    uninstall_pin = (req.uninstall_key or "1234").strip()
    uninstall_pin_hash = hash_secret(uninstall_pin)

    await set_config_value("setup_completed", "1")
    await set_config_value("language", req.language)
    await set_config_value("master_salt", b64_encode(master_salt))
    await set_config_value("master_hash", master_hash)
    await set_config_value("passphrase_salt", b64_encode(passphrase_salt))
    await set_config_value("passphrase_hash", passphrase_hash)
    await set_config_value("uninstall_pin_hash", uninstall_pin_hash)

    await set_config_value("checkin_interval_sec", str(req.interval_seconds))
    await set_config_value("grace_period_sec", str(req.grace_seconds))
    await set_config_value("last_checkin_timestamp", str(time.time()))
    await set_config_value("status", "ACTIVE")

    if req.telegram_token:
        await set_config_value("telegram_bot_token", req.telegram_token.strip())
    if req.telegram_chat_id:
        await set_config_value("telegram_owner_chat_id", req.telegram_chat_id.strip())

    if req.smtp_host:
        await set_config_value("smtp_host", req.smtp_host)
        await set_config_value("smtp_port", str(req.smtp_port or 587))
        await set_config_value("smtp_user", req.smtp_user or "")
        if req.smtp_password:
            await set_config_value("smtp_password", req.smtp_password)
        await set_config_value("smtp_from", req.smtp_from or "")
        await set_config_value("smtp_use_tls", "1" if req.smtp_use_tls else "0")

    watchdog.set_session_key(master_key)
    await add_audit_log("SYSTEM_INITIALIZED", "OBLIVION instance initialized and vault created", "INFO")

    if req.telegram_token:
        await telegram_worker.restart()

    return {"success": True, "message": "Initialization completed"}

# --- AUTH ENDPOINTS ---

@api_router.get("/auth/session")
async def get_session_status():
    return {
        "unlocked": watchdog.get_session_key() is not None
    }

@api_router.post("/auth/unlock")
async def unlock_vault(req: UnlockRequest):
    await check_rate_limit("master_password")
    stored_hash = await get_config_value("master_hash")
    stored_salt_b64 = await get_config_value("master_salt")

    if not stored_hash or not stored_salt_b64:
        raise HTTPException(status_code=400, detail="Vault is not initialized")

    if not verify_secret(stored_hash, req.password):
        fails = await record_failed_attempt("master_password")
        await add_audit_log("FAILED_LOGIN", f"Invalid master password attempt (failed: {fails})", "WARNING")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid master password")

    await reset_rate_limit("master_password")
    salt = b64_decode(stored_salt_b64)
    master_key = derive_master_key(req.password, salt)
    watchdog.set_session_key(master_key)
    await add_audit_log("VAULT_UNLOCKED", "Master password validated, vault session unlocked", "INFO")

    return {"success": True, "message": "Vault unlocked"}

@api_router.post("/auth/lock")
async def lock_vault():
    watchdog.clear_session_key()
    await add_audit_log("VAULT_LOCKED", "Vault session locked", "INFO")
    return {"success": True, "message": "Vault locked"}

# --- STATUS & LOGS ---

@api_router.get("/status")
async def get_system_status():
    detailed = await watchdog.get_detailed_status()
    lang = await get_config_value("language", "en")
    
    return {
        "switch": detailed,
        "windows": {
            "is_admin": is_running_as_admin(),
            "task_scheduler": check_scheduled_task(),
            "platform": os.name
        },
        "telegram": {
            "connected": telegram_worker.is_connected,
            "username": telegram_worker.bot_username
        },
        "language": lang
    }

@api_router.get("/status/logs")
async def get_logs(limit: int = 50):
    logs = await get_recent_audit_logs(limit=limit)
    return {"logs": logs}

# --- CHECK-IN ---

@api_router.post("/checkin")
async def perform_checkin(req: CheckInRequest):
    if len(req.passphrase) < 16:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-in passphrase must be at least 16 characters"
        )

    await check_rate_limit("checkin_passphrase")

    stored_hash = await get_config_value("passphrase_hash")
    if not stored_hash:
        raise HTTPException(status_code=400, detail="System not initialized")

    if not verify_secret(stored_hash, req.passphrase):
        fails = await record_failed_attempt("checkin_passphrase")
        await add_audit_log("FAILED_CHECKIN", f"Failed check-in passphrase attempt from Web Dashboard (failed: {fails})", "WARNING")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid check-in passphrase")

    await reset_rate_limit("checkin_passphrase")
    await watchdog.record_checkin(source="Web Dashboard")
    return {"success": True, "message": "Check-in confirmed. Timer reset."}

# --- VAULT ITEMS ---

@api_router.get("/vault/items")
async def list_vault_items():
    master_key = watchdog.get_session_key()
    async with get_db() as db:
        async with db.execute("SELECT * FROM vault_items ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            items = [dict(r) for r in rows]

        async with db.execute("SELECT item_id, contact_id FROM item_assignments") as cursor:
            assignments = await cursor.fetchall()

    assign_map = {}
    for a in assignments:
        assign_map.setdefault(a["item_id"], []).append(a["contact_id"])

    result = []
    for it in items:
        item_id = it["id"]
        payload_decrypted = None
        if master_key:
            try:
                payload_decrypted = decrypt_string(master_key, it["encrypted_payload"])
            except Exception:
                payload_decrypted = "[Decryption Failed]"

        result.append({
            "id": item_id,
            "title": it["title"],
            "category": it["category"],
            "policy": it["policy"],
            "target_path": it["target_path"],
            "attachment_filename": it["attachment_filename"],
            "has_attachment": bool(it["attachment_path"]),
            "contact_ids": assign_map.get(item_id, []),
            "content": payload_decrypted,
            "created_at": it["created_at"],
            "updated_at": it["updated_at"]
        })

    return {"items": result}

@api_router.post("/vault/items")
async def create_vault_item(
    title: str = Form(...),
    category: str = Form(...),
    content: str = Form(""),
    policy: str = Form("transfer_and_wipe"),
    target_path: Optional[str] = Form(None),
    contact_ids: str = Form("[]"),
    file: Optional[UploadFile] = File(None),
    master_key: bytes = Depends(require_unlocked_session)
):
    item_id = str(uuid.uuid4())
    now = time.time()
    contacts_list = json.loads(contact_ids) if contact_ids else []

    dek = os.urandom(32)
    encrypted_payload_str = encrypt_string(master_key, content)

    attachment_filename = None
    attachment_path_str = None

    if file and file.filename:
        attachment_filename = file.filename
        file_bytes = await file.read()
        encrypted_file_bytes = encrypt_bytes(master_key, file_bytes)
        disk_path = settings.uploads_dir / f"{item_id}.enc"
        disk_path.write_bytes(encrypted_file_bytes)
        attachment_path_str = str(disk_path)

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO vault_items (
                id, title, category, encrypted_payload, policy, target_path,
                attachment_filename, attachment_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id, title, category, encrypted_payload_str, policy,
                target_path.strip() if target_path else None,
                attachment_filename, attachment_path_str, now, now
            )
        )

        for cid in contacts_list:
            share_contact, share_escrow = create_split_dek_escrow(dek)
            enc_escrow = encrypt_string(master_key, share_escrow)
            await db.execute(
                """
                INSERT INTO item_assignments (item_id, contact_id, encrypted_item_share)
                VALUES (?, ?, ?)
                ON CONFLICT(item_id, contact_id) DO UPDATE SET encrypted_item_share = excluded.encrypted_item_share
                """,
                (item_id, cid, enc_escrow)
            )

        await db.commit()

    await add_audit_log("VAULT_ITEM_CREATED", f"Vault item created: {title} ({policy})", "INFO")
    return {"success": True, "item_id": item_id}

@api_router.delete("/vault/items/{item_id}")
async def delete_vault_item(item_id: str, master_key: bytes = Depends(require_unlocked_session)):
    async with get_db() as db:
        async with db.execute("SELECT attachment_path, title FROM vault_items WHERE id = ?", (item_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Item not found")
            attachment_path = row["attachment_path"]
            title = row["title"]

        if attachment_path:
            shred_file(attachment_path, passes=3)

        await db.execute("DELETE FROM item_assignments WHERE item_id = ?", (item_id,))
        await db.execute("DELETE FROM vault_items WHERE id = ?", (item_id,))
        await db.commit()

    await add_audit_log("VAULT_ITEM_DELETED", f"Vault item deleted: {title}", "INFO")
    return {"success": True, "message": "Item deleted"}

@api_router.get("/vault/items/{item_id}/attachment")
async def download_attachment(item_id: str, master_key: bytes = Depends(require_unlocked_session)):
    async with get_db() as db:
        async with db.execute("SELECT attachment_filename, attachment_path FROM vault_items WHERE id = ?", (item_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or not row["attachment_path"]:
                raise HTTPException(status_code=404, detail="Attachment not found")
            orig_name = row["attachment_filename"] or "attachment.bin"
            file_path = Path(row["attachment_path"])

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File on disk missing")

    raw_encrypted = file_path.read_bytes()
    decrypted_bytes = decrypt_bytes(master_key, raw_encrypted)

    return StreamingResponse(
        io.BytesIO(decrypted_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{orig_name}"'}
    )

@api_router.get("/vault/items/{item_id}/bundle")
async def download_bundle(item_id: str, master_key: bytes = Depends(require_unlocked_session)):
    async with get_db() as db:
        async with db.execute("SELECT title, encrypted_payload FROM vault_items WHERE id = ?", (item_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Item not found")
            title = row["title"]
            payload = row["encrypted_payload"]

        async with db.execute("SELECT encrypted_item_share FROM item_assignments WHERE item_id = ? LIMIT 1", (item_id,)) as cursor:
            assign_row = await cursor.fetchone()
            escrow_share = ""
            if assign_row:
                try:
                    escrow_share = decrypt_string(master_key, assign_row["encrypted_item_share"])
                except Exception:
                    pass

    bundle_bytes = create_recovery_bundle(
        item_title=title,
        encrypted_payload=payload.encode("utf-8"),
        escrow_share=escrow_share,
        instructions="OBLIVION Offline Recovery Package"
    )

    filename = f"oblivion_bundle_{item_id}.enc"
    return StreamingResponse(
        io.BytesIO(bundle_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# --- CONTACTS ---

@api_router.get("/contacts")
async def list_contacts():
    async with get_db() as db:
        async with db.execute("""
            SELECT c.*, COUNT(a.item_id) as assigned_items_count
            FROM trusted_contacts c
            LEFT JOIN item_assignments a ON c.id = a.contact_id
            GROUP BY c.id
            ORDER BY c.created_at ASC
        """) as cursor:
            rows = await cursor.fetchall()
            return {"contacts": [dict(r) for r in rows]}

@api_router.post("/contacts")
async def create_contact(req: ContactCreateRequest, master_key: bytes = Depends(require_unlocked_session)):
    contact_id = str(uuid.uuid4())
    now = time.time()
    recovery_token = f"OBLIVION-REC-{secrets.token_hex(16).upper()}"
    token_hash = hash_secret(recovery_token)

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO trusted_contacts (
                id, name, email, telegram_chat_id, recovery_token_hash,
                public_instructions, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contact_id, req.name, req.email, req.telegram_chat_id,
                token_hash, req.public_instructions, now
            )
        )
        await db.commit()

    await add_audit_log("CONTACT_CREATED", f"Trusted contact added: {req.name}", "INFO")
    return {
        "success": True,
        "contact_id": contact_id,
        "recovery_token": recovery_token
    }

@api_router.put("/contacts/{contact_id}")
async def update_contact(contact_id: str, req: ContactUpdateRequest, master_key: bytes = Depends(require_unlocked_session)):
    async with get_db() as db:
        await db.execute(
            """
            UPDATE trusted_contacts
            SET name = ?, email = ?, telegram_chat_id = ?, public_instructions = ?
            WHERE id = ?
            """,
            (req.name, req.email, req.telegram_chat_id, req.public_instructions, contact_id)
        )
        await db.commit()

    await add_audit_log("CONTACT_UPDATED", f"Trusted contact updated: {req.name}", "INFO")
    return {"success": True}

@api_router.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: str, master_key: bytes = Depends(require_unlocked_session)):
    async with get_db() as db:
        await db.execute("DELETE FROM item_assignments WHERE contact_id = ?", (contact_id,))
        await db.execute("DELETE FROM trusted_contacts WHERE id = ?", (contact_id,))
        await db.commit()

    await add_audit_log("CONTACT_DELETED", f"Trusted contact deleted: {contact_id}", "INFO")
    return {"success": True}

# --- SETTINGS & EMERGENCY ---

@api_router.get("/settings")
async def get_settings_endpoint(master_key: bytes = Depends(require_unlocked_session)):
    all_cfg = await get_all_config()
    token = all_cfg.get("telegram_bot_token", "")
    masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else ("***" if token else "")

    return {
        "language": all_cfg.get("language", "en"),
        "checkin_interval_sec": int(all_cfg.get("checkin_interval_sec", "604800")),
        "grace_period_sec": int(all_cfg.get("grace_period_sec", "86400")),
        "telegram_bot_token_masked": masked_token,
        "has_telegram_token": bool(token),
        "telegram_owner_chat_id": all_cfg.get("telegram_owner_chat_id", ""),
        "smtp_host": all_cfg.get("smtp_host", ""),
        "smtp_port": int(all_cfg.get("smtp_port", "587")),
        "smtp_user": all_cfg.get("smtp_user", ""),
        "smtp_from": all_cfg.get("smtp_from", ""),
        "smtp_use_tls": all_cfg.get("smtp_use_tls", "1") == "1"
    }

@api_router.post("/settings")
async def update_settings_endpoint(req: UpdateSettingsRequest, master_key: bytes = Depends(require_unlocked_session)):
    restart_bot = False

    if req.language in ("en", "ru"):
        await set_config_value("language", req.language)
    if req.uninstall_key is not None and len(req.uninstall_key.strip()) >= 4:
        await set_config_value("uninstall_pin_hash", hash_secret(req.uninstall_key.strip()))
    if req.checkin_interval_sec is not None:
        await set_config_value("checkin_interval_sec", str(req.checkin_interval_sec))
    if req.grace_period_sec is not None:
        await set_config_value("grace_period_sec", str(req.grace_period_sec))

    if req.telegram_bot_token is not None:
        current_token = await get_config_value("telegram_bot_token", "")
        if req.telegram_bot_token.strip() != current_token:
            await set_config_value("telegram_bot_token", req.telegram_bot_token.strip())
            restart_bot = True

    if req.telegram_owner_chat_id is not None:
        await set_config_value("telegram_owner_chat_id", req.telegram_owner_chat_id.strip())

    if req.smtp_host is not None:
        await set_config_value("smtp_host", req.smtp_host)
    if req.smtp_port is not None:
        await set_config_value("smtp_port", str(req.smtp_port))
    if req.smtp_user is not None:
        await set_config_value("smtp_user", req.smtp_user)
    if req.smtp_password is not None and req.smtp_password.strip():
        await set_config_value("smtp_password", req.smtp_password.strip())
    if req.smtp_from is not None:
        await set_config_value("smtp_from", req.smtp_from)
    if req.smtp_use_tls is not None:
        await set_config_value("smtp_use_tls", "1" if req.smtp_use_tls else "0")

    if restart_bot:
        await telegram_worker.restart()

    await add_audit_log("SETTINGS_UPDATED", "OBLIVION settings updated", "INFO")
    return {"success": True, "message": "Settings updated"}

@api_router.post("/settings/simulate")
async def trigger_simulation_endpoint(master_key: bytes = Depends(require_unlocked_session)):
    plan = await simulate_trigger(master_key)
    return {"success": True, "plan": plan}

@api_router.post("/settings/panic-wipe")
async def panic_wipe_endpoint(req: PanicWipeRequest):
    if len(req.passphrase) < 16:
        raise HTTPException(status_code=400, detail="Check-in passphrase must be at least 16 characters")

    await check_rate_limit("checkin_passphrase")

    stored_hash = await get_config_value("passphrase_hash")
    if not stored_hash or not verify_secret(stored_hash, req.passphrase):
        fails = await record_failed_attempt("checkin_passphrase")
        await add_audit_log("FAILED_PANIC_WIPE", f"Invalid passphrase submitted for Panic Wipe (failed: {fails})", "DANGER")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid passphrase")

    await reset_rate_limit("checkin_passphrase")
    result = await execute_panic_wipe()
    return {"success": True, "result": result}
