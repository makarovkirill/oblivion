import asyncio
from email.message import EmailMessage
import smtplib
from typing import Any, Dict, List, Optional, Tuple

def _send_smtp_sync(
    host: str,
    port: int,
    user: str,
    password: str,
    from_addr: str,
    to_addr: str,
    subject: str,
    content: str,
    use_tls: bool = True,
    attachments: Optional[List[Tuple[str, bytes]]] = None
) -> Tuple[bool, str]:
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr or user
        msg["To"] = to_addr
        msg.set_content(content)

        if attachments:
            for filename, file_bytes in attachments:
                msg.add_attachment(
                    file_bytes,
                    maintype="application",
                    subtype="octet-stream",
                    filename=filename
                )

        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=10) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                if use_tls:
                    server.starttls()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        return True, "Success"
    except Exception as exc:
        return False, str(exc)

async def send_email_async(
    config: Dict[str, any],
    to_addr: str,
    subject: str,
    content: str,
    attachments: Optional[List[Tuple[str, bytes]]] = None
) -> Tuple[bool, str]:
    host = config.get("host")
    if not host or not to_addr:
        return False, "SMTP host or recipient missing"
    
    port = int(config.get("port", 587))
    user = config.get("user", "")
    password = config.get("password", "")
    from_addr = config.get("from_addr", user)
    use_tls = str(config.get("use_tls", "1")) in ("1", "true", "True")

    return await asyncio.to_thread(
        _send_smtp_sync,
        host=host,
        port=port,
        user=user,
        password=password,
        from_addr=from_addr,
        to_addr=to_addr,
        subject=subject,
        content=content,
        use_tls=use_tls,
        attachments=attachments
    )
