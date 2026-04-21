from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException
from jwt import InvalidTokenError

from config import AuthConfig


def _now_utc() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        100_000,
    ).hex()
    return f"{salt}:{key}"


def verify_password(password: str, stored_password_hash: str) -> bool:
    try:
        salt, expected_key = stored_password_hash.split(":", maxsplit=1)
    except ValueError:
        return False
    computed_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        100_000,
    ).hex()
    return secrets.compare_digest(computed_key, expected_key)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user_id: int, config: AuthConfig) -> str:
    now = _now_utc()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=config.access_token_minutes)).timestamp()),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def create_refresh_token(user_id: int, config: AuthConfig) -> tuple[str, datetime]:
    now = _now_utc()
    expires_at = now + timedelta(days=config.refresh_token_days)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": secrets.token_urlsafe(24),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)
    return token, expires_at


def decode_token(token: str, expected_type: str, config: AuthConfig) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    token_type = payload.get("type")
    if token_type != expected_type:
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload
