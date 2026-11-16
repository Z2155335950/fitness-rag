from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path

from fastapi import Request, Response

from src.config import AUTH_SECRET_PATH


OWNER_COOKIE = "fitness_owner"
OWNER_PATTERN = re.compile(r"^user_[A-Za-z0-9_-]{24,64}$")


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _secret() -> bytes:
    configured = os.getenv("APP_SECRET_KEY", "").strip()
    if configured:
        return configured.encode("utf-8")
    path = Path(AUTH_SECRET_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError:
        value = path.read_bytes()
        if len(value) < 32:
            raise RuntimeError("认证密钥文件无效")
        return value
    with os.fdopen(fd, "wb") as handle:
        value = secrets.token_bytes(48)
        handle.write(value)
    return value


def issue_owner_token(owner_id: str, secret: bytes | None = None) -> str:
    if not OWNER_PATTERN.fullmatch(owner_id):
        raise ValueError("无效的用户身份")
    payload = json.dumps(
        {"v": 1, "uid": owner_id},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    signature = hmac.new(
        secret or _secret(),
        payload,
        hashlib.sha256,
    ).digest()
    return f"{_encode(payload)}.{_encode(signature)}"


def verify_owner_token(
    token: str, secret: bytes | None = None
) -> str | None:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        payload = _decode(encoded_payload)
        signature = _decode(encoded_signature)
    except (ValueError, TypeError, binascii.Error):
        return None
    expected = hmac.new(
        secret or _secret(),
        payload,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    owner_id = data.get("uid")
    if data.get("v") != 1 or not isinstance(owner_id, str):
        return None
    return owner_id if OWNER_PATTERN.fullmatch(owner_id) else None


def current_owner(request: Request, response: Response) -> str:
    owner_id = verify_owner_token(
        request.cookies.get(OWNER_COOKIE, "")
    )
    if owner_id:
        return owner_id
    owner_id = f"user_{secrets.token_urlsafe(24)}"
    response.set_cookie(
        OWNER_COOKIE,
        issue_owner_token(owner_id),
        max_age=365 * 24 * 60 * 60,
        httponly=True,
        secure=os.getenv("APP_COOKIE_SECURE", "false").lower()
        in {"1", "true", "yes"},
        samesite="lax",
        path="/",
    )
    return owner_id
