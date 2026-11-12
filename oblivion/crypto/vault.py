import base64
import os
from pathlib import Path
from typing import Union
from argon2 import PasswordHasher, Type
from argon2.low_level import hash_secret_raw, Type as LowLevelType
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    type=Type.ID
)

def generate_salt(length: int = 16) -> bytes:
    return os.urandom(length)

def hash_secret(secret: str) -> str:
    return _hasher.hash(secret)

def verify_secret(secret_hash: str, candidate: str) -> bool:
    try:
        return _hasher.verify(secret_hash, candidate)
    except Exception:
        return False

def derive_master_key(password: str, salt: bytes, length: int = 32) -> bytes:
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=length,
        type=LowLevelType.ID
    )

def b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

def b64_decode(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))

def encrypt_bytes(key: bytes, plaintext: bytes) -> bytes:
    if len(key) != 32:
        raise ValueError("AES-256 key must be 32 bytes")
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext

def decrypt_bytes(key: bytes, payload: bytes) -> bytes:
    if len(key) != 32:
        raise ValueError("AES-256 key must be 32 bytes")
    if len(payload) < 28:
        raise ValueError("Invalid AES-GCM payload")
    nonce = payload[:12]
    ciphertext = payload[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)

def encrypt_string(key: bytes, plaintext: str) -> str:
    encrypted = encrypt_bytes(key, plaintext.encode("utf-8"))
    return b64_encode(encrypted)

def decrypt_string(key: bytes, token: str) -> str:
    raw = b64_decode(token)
    decrypted = decrypt_bytes(key, raw)
    return decrypted.decode("utf-8")

def encrypt_file(key: bytes, source_path: Union[str, Path], dest_path: Union[str, Path]) -> None:
    data = Path(source_path).read_bytes()
    encrypted = encrypt_bytes(key, data)
    Path(dest_path).write_bytes(encrypted)

def decrypt_file(key: bytes, source_path: Union[str, Path], dest_path: Union[str, Path]) -> None:
    data = Path(source_path).read_bytes()
    decrypted = decrypt_bytes(key, data)
    Path(dest_path).write_bytes(decrypted)
