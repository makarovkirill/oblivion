import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Tuple
from ..config import settings
from ..storage.database import get_db, get_all_config, add_audit_log
from ..crypto.vault import decrypt_string, decrypt_bytes
from ..crypto.escrow import create_recovery_bundle
from ..crypto.shredder import shred_file, shred_directory, shred_target_paths, shred_database_files
from ..integrations.telegram_bot import telegram_worker
from ..integrations.mailer import send_email_async

logger = logging.getLogger("oblivion.dispatcher")

async def simulate_trigger(master_key: Optional[bytes] = None) -> Dict[str, Any]:
    plan: Dict[str, Any] = {
        "mode": "dry_run",
        "transfers": [],
        "wipes": [],
        "database_target": str(settings.db_path)
    }

    async with get_db() as db:
        async with db.execute("SELECT * FROM vault_items") as cursor:
            items = [dict(r) for r in await cursor.fetchall()]

        async with db.execute("SELECT * FROM trusted_contacts") as cursor:
            contacts = {r["id"]: dict(r) for r in await cursor.fetchall()}

        async with db.execute("SELECT * FROM item_assignments") as cursor:
            assignments = [dict(r) for r in await cursor.fetchall()]

    assignments_by_item: Dict[str, List[str]] = {}
    for a in assignments:
        assignments_by_item.setdefault(a["item_id"], []).append(a["contact_id"])

    for item in items:
        item_id = item["id"]
        policy = item["policy"]
        title = item["title"]
        target_path = item.get("target_path")
        has_attachment = bool(item.get("attachment_path"))

        if policy == "transfer_and_wipe":
            contact_ids = assignments_by_item.get(item_id, [])
            recipients = []
            for cid in contact_ids:
                if cid in contacts:
                    c = contacts[cid]
                    recipients.append({
                        "contact_id": cid,
                        "name": c["name"],
                        "telegram": bool(c.get("telegram_chat_id")),
                        "email": bool(c.get("email"))
                    })
            plan["transfers"].append({
                "item_id": item_id,
                "title": title,
                "recipients": recipients,
                "has_attachment": has_attachment,
                "local_target_to_wipe": target_path,
                "bundle_file": f"oblivion_bundle_{item_id}.enc"
            })
            if target_path:
                plan["wipes"].append({
                    "path": target_path,
                    "reason": f"Transfer & Wipe completion for '{title}'"
                })
        else:
            plan["wipes"].append({
                "item_id": item_id,
                "title": title,
                "path": target_path or "Vault Record Only",
                "reason": "Wipe Only policy (Self-Destruct)"
            })

    if settings.uploads_dir.exists():
        for f in settings.uploads_dir.glob("*"):
            if f.is_file():
                plan["wipes"].append({"path": str(f), "reason": "Encrypted vault attachment shredding"})

    await add_audit_log("DRY_RUN_SIMULATION", f"Dry run simulation completed: {len(plan['transfers'])} transfers, {len(plan['wipes'])} wipes", "INFO")
    return plan

async def execute_trigger(master_key: Optional[bytes] = None) -> Dict[str, Any]:
    config = await get_all_config()
    lang = config.get("language", "en")
    smtp_config = {
        "host": config.get("smtp_host", ""),
        "port": int(config.get("smtp_port", 587)),
        "user": config.get("smtp_user", ""),
        "password": config.get("smtp_password", ""),
        "from_addr": config.get("smtp_from", ""),
        "use_tls": config.get("smtp_use_tls", "1")
    }

    async with get_db() as db:
        async with db.execute("SELECT * FROM vault_items") as cursor:
            items = [dict(r) for r in await cursor.fetchall()]

        async with db.execute("SELECT * FROM trusted_contacts") as cursor:
            contacts = {r["id"]: dict(r) for r in await cursor.fetchall()}

        async with db.execute("SELECT * FROM item_assignments") as cursor:
            assignments = [dict(r) for r in await cursor.fetchall()]

    assignments_map: Dict[str, List[dict]] = {}
    for a in assignments:
        assignments_map.setdefault(a["item_id"], []).append(a)

    delivery_results: List[dict] = []
    wipes_to_perform: List[str] = []

    for item in items:
        item_id = item["id"]
        policy = item["policy"]
        title = item["title"]
        target_path = item.get("target_path")
        attachment_path = item.get("attachment_path")
        orig_filename = item.get("attachment_filename") or "attachment.bin"

        if target_path:
            wipes_to_perform.append(target_path)

        if policy == "transfer_and_wipe":
            item_assigns = assignments_map.get(item_id, [])
            for assign in item_assigns:
                contact_id = assign["contact_id"]
                contact = contacts.get(contact_id)
                if not contact:
                    continue

                escrow_share = assign.get("encrypted_item_share", "")
                if master_key and escrow_share:
                    try:
                        escrow_share = decrypt_string(master_key, escrow_share)
                    except Exception:
                        pass

                raw_payload = item["encrypted_payload"]
                payload_text = raw_payload
                if master_key:
                    try:
                        payload_text = decrypt_string(master_key, raw_payload)
                    except Exception:
                        pass

                attachments: List[Tuple[str, bytes]] = []
                bundle_bytes = create_recovery_bundle(
                    item_title=title,
                    encrypted_payload=raw_payload.encode("utf-8"),
                    escrow_share=escrow_share,
                    instructions=contact.get("public_instructions", "") or ""
                )
                attachments.append((f"oblivion_bundle_{item_id}.enc", bundle_bytes))

                if attachment_path:
                    att_file = Path(attachment_path)
                    if att_file.exists():
                        att_bytes = att_file.read_bytes()
                        if master_key:
                            try:
                                att_bytes = decrypt_bytes(master_key, att_bytes)
                            except Exception:
                                pass
                        attachments.append((orig_filename, att_bytes))

                if lang == "ru":
                    message_body = (
                        f"🕊 <b>OBLIVION: СРАБАТЫВАНИЕ DEAD MAN'S SWITCH</b>\n\n"
                        f"Уважаемый(-ая) {contact['name']},\n"
                        f"Вам переданы зашифрованные данные: <b>{title}</b>.\n\n"
                        f"Содержимое:\n<code>{payload_text}</code>\n\n"
                        f"Фрагмент депонирования (Escrow Share):\n<code>{escrow_share}</code>\n\n"
                        f"Инструкции:\n{contact.get('public_instructions', '') or 'Объедините переданный фрагмент с вашим персональным ключом восстановления.'}\n\n"
                        f"К сообщению прикреплен крипто-пакет: oblivion_bundle_{item_id}.enc"
                    )
                    email_subj = f"OBLIVION Digital Legacy: {title}"
                else:
                    message_body = (
                        f"🕊 <b>OBLIVION: DEAD MAN'S SWITCH TRIGGERED</b>\n\n"
                        f"Dear {contact['name']},\n"
                        f"An autonomous release of encrypted assets has been executed: <b>{title}</b>.\n\n"
                        f"Payload:\n<code>{payload_text}</code>\n\n"
                        f"Split Escrow Share:\n<code>{escrow_share}</code>\n\n"
                        f"Instructions:\n{contact.get('public_instructions', '') or 'Combine this escrow share with your pre-shared recovery key to unlock the payload.'}\n\n"
                        f"Enclosed recovery bundle: oblivion_bundle_{item_id}.enc"
                    )
                    email_subj = f"OBLIVION Notification: {title}"

                tg_ok = False
                if contact.get("telegram_chat_id"):
                    tg_ok = await telegram_worker.send_beneficiary_packet(
                        chat_id=contact["telegram_chat_id"],
                        beneficiary_name=contact["name"],
                        message_body=message_body,
                        attachments=attachments
                    )

                email_ok = False
                if contact.get("email") and smtp_config.get("host"):
                    email_ok, _ = await send_email_async(
                        config=smtp_config,
                        to_addr=contact["email"],
                        subject=email_subj,
                        content=message_body,
                        attachments=attachments
                    )

                delivery_results.append({
                    "item_id": item_id,
                    "contact_id": contact_id,
                    "telegram_success": tg_ok,
                    "email_success": email_ok
                })

    shred_results = shred_target_paths(wipes_to_perform, passes=3)

    if settings.uploads_dir.exists():
        for f in settings.uploads_dir.glob("*"):
            if f.is_file():
                shred_file(f, passes=3)

    await add_audit_log("TRIGGER_EXECUTED", f"OBLIVION trigger executed. Deliveries: {len(delivery_results)}, Wipes: {len(shred_results)}", "DANGER")

    try:
        shred_database_files(settings.db_path, passes=3)
    except Exception as exc:
        logger.error(f"Failed to shred database: {exc}")

    return {
        "status": "TRIGGERED",
        "deliveries": delivery_results,
        "shred_results": shred_results
    }

async def execute_panic_wipe(target_paths: Optional[List[str]] = None) -> Dict[str, Any]:
    all_targets = list(target_paths) if target_paths else []
    try:
        async with get_db() as db:
            async with db.execute("SELECT target_path FROM vault_items WHERE target_path IS NOT NULL") as cursor:
                rows = await cursor.fetchall()
                for r in rows:
                    if r["target_path"]:
                        all_targets.append(r["target_path"])
    except Exception:
        pass

    results = shred_target_paths(all_targets, passes=3)

    if settings.uploads_dir.exists():
        shred_directory(settings.uploads_dir, passes=3)
        settings.uploads_dir.mkdir(parents=True, exist_ok=True)

    if settings.logs_dir.exists():
        shred_directory(settings.logs_dir, passes=3)
        settings.logs_dir.mkdir(parents=True, exist_ok=True)

    try:
        shred_database_files(settings.db_path, passes=3)
    except Exception:
        pass

    return {
        "status": "PANIC_WIPE_COMPLETED",
        "shredded_targets": results
    }
