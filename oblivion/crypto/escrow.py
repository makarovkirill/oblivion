import base64
import json
import os
from typing import List, Tuple, Dict, Any
from .vault import encrypt_bytes, decrypt_bytes, encrypt_string, decrypt_string, b64_encode, b64_decode

EXP = [0] * 512
LOG = [0] * 256

def _init_tables():
    poly = 0x11d
    x = 1
    for i in range(255):
        EXP[i] = x
        EXP[i + 255] = x
        LOG[x] = i
        x = (x << 1)
        if x & 0x100:
            x ^= poly
    LOG[0] = 0

_init_tables()

def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return EXP[(LOG[a] + LOG[b]) % 255]

def _gf_div(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError("Division by zero in GF(256)")
    if a == 0:
        return 0
    return EXP[(LOG[a] - LOG[b] + 255) % 255]

def split_secret(secret: bytes, threshold: int = 2, total_shares: int = 2) -> List[Tuple[int, bytes]]:
    if threshold > total_shares:
        raise ValueError("Threshold cannot exceed total shares")
    if threshold < 2:
        raise ValueError("Threshold must be at least 2")
    if total_shares > 255:
        raise ValueError("Total shares cannot exceed 255")

    shares_data: List[bytearray] = [bytearray() for _ in range(total_shares)]

    for secret_byte in secret:
        coeffs = [secret_byte] + [os.urandom(1)[0] for _ in range(threshold - 1)]
        for i in range(total_shares):
            x = i + 1
            y = 0
            power = 1
            for coeff in coeffs:
                y ^= _gf_mul(coeff, power)
                power = _gf_mul(power, x)
            shares_data[i].append(y)

    return [(i + 1, bytes(shares_data[i])) for i in range(total_shares)]

def combine_shares(shares: List[Tuple[int, bytes]]) -> bytes:
    if not shares:
        raise ValueError("No shares provided")
    
    length = len(shares[0][1])
    for _, share_bytes in shares:
        if len(share_bytes) != length:
            raise ValueError("All shares must match in length")

    secret = bytearray()
    k = len(shares)

    for byte_idx in range(length):
        secret_byte = 0
        for j in range(k):
            xj, yj_bytes = shares[j]
            yj = yj_bytes[byte_idx]
            basis = 1
            for m in range(k):
                if m == j:
                    continue
                xm, _ = shares[m]
                numerator = xm
                denominator = xj ^ xm
                basis = _gf_mul(basis, _gf_div(numerator, denominator))
            secret_byte ^= _gf_mul(yj, basis)
        secret.append(secret_byte)

    return bytes(secret)

def create_split_dek_escrow(dek: bytes) -> Tuple[str, str]:
    shares = split_secret(dek, threshold=2, total_shares=2)
    share1_str = f"OBLIVION-REC-{shares[0][0]}-{b64_encode(shares[0][1])}"
    share2_str = f"OBLIVION-ESC-{shares[1][0]}-{b64_encode(shares[1][1])}"
    return share1_str, share2_str

def parse_share(token: str) -> Tuple[int, bytes]:
    parts = token.strip().split("-")
    if len(parts) >= 4:
        idx = int(parts[2])
        raw = b64_decode(parts[3])
        return idx, raw
    elif ":" in token:
        idx_str, raw_str = token.split(":", 1)
        return int(idx_str), b64_decode(raw_str)
    raise ValueError("Invalid escrow share format")

def combine_escrow_shares(share_a_str: str, share_b_str: str) -> bytes:
    share_a = parse_share(share_a_str)
    share_b = parse_share(share_b_str)
    return combine_shares([share_a, share_b])

def create_recovery_bundle(
    item_title: str,
    encrypted_payload: bytes,
    escrow_share: str,
    instructions: str = ""
) -> bytes:
    bundle_data = {
        "header": "OBLIVION_ENCRYPTED_BUNDLE_V1",
        "title": item_title,
        "escrow_share": escrow_share,
        "instructions": instructions,
        "payload_b64": b64_encode(encrypted_payload)
    }
    return json.dumps(bundle_data, indent=2).encode("utf-8")

def parse_recovery_bundle(bundle_bytes: bytes) -> Dict[str, Any]:
    return json.loads(bundle_bytes.decode("utf-8"))
