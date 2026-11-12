from typing import List, Optional
from pydantic import BaseModel, Field

class TestTelegramRequest(BaseModel):
    token: str
    chat_id: str

class TestEmailRequest(BaseModel):
    host: str
    port: int = 587
    user: str = ""
    password: str = ""
    from_addr: str = ""
    target_email: str
    use_tls: bool = True

class InitializeRequest(BaseModel):
    language: str = Field(default="en", pattern="^(en|ru)$")
    master_password: str = Field(min_length=8)
    checkin_passphrase: str = Field(min_length=16)
    uninstall_key: Optional[str] = Field(default="1234", min_length=4, max_length=32)
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_use_tls: Optional[bool] = True
    interval_seconds: int = Field(default=604800, ge=30)
    grace_seconds: int = Field(default=86400, ge=10)

class UnlockRequest(BaseModel):
    password: str

class CheckInRequest(BaseModel):
    passphrase: str = Field(min_length=16)

class ContactCreateRequest(BaseModel):
    name: str
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    public_instructions: Optional[str] = None

class ContactUpdateRequest(BaseModel):
    name: str
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    public_instructions: Optional[str] = None

class UpdateSettingsRequest(BaseModel):
    language: Optional[str] = None
    uninstall_key: Optional[str] = None
    checkin_interval_sec: Optional[int] = Field(None, ge=30)
    grace_period_sec: Optional[int] = Field(None, ge=10)
    telegram_bot_token: Optional[str] = None
    telegram_owner_chat_id: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_use_tls: Optional[bool] = True

class PanicWipeRequest(BaseModel):
    passphrase: str = Field(min_length=16)
