from datetime import UTC, datetime
from typing import cast

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import UserRefreshToken
from app.models.user import User
from app.schemas.auth import LoginInput, MeOutput, TokenPair
from config import AuthConfig


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_me_output(user: User) -> MeOutput:
    return MeOutput(
        id=cast(int, user.id),
        username=cast(str, user.username),
        email=cast(str, user.email),
    )


def authenticate_user(db: Session, input: LoginInput) -> User:
    email = input.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(input.password, cast(str, user.password_hash)):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return user


def issue_token_pair(db: Session, user: User, auth_config: AuthConfig) -> TokenPair:
    user_id = cast(int, user.id)
    access_token = create_access_token(user_id, auth_config)
    refresh_token, refresh_expires_at = create_refresh_token(user_id, auth_config)
    record = UserRefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=refresh_expires_at.replace(tzinfo=None),
        revoked=False,
    )
    db.add(record)
    db.commit()
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
    )


def login(db: Session, input: LoginInput, auth_config: AuthConfig) -> TokenPair:
    user = authenticate_user(db, input)
    return issue_token_pair(db, user, auth_config)


def refresh_access(db: Session, refresh_token: str, auth_config: AuthConfig) -> TokenPair:
    payload = decode_token(refresh_token, expected_type="refresh", config=auth_config)
    user_id = int(payload["sub"])
    token_hash = hash_refresh_token(refresh_token)

    token_row = db.scalar(
        select(UserRefreshToken).where(UserRefreshToken.token_hash == token_hash)
    )
    if token_row is None or cast(bool, token_row.revoked):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    if cast(datetime, token_row.expires_at) <= _utcnow_naive():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    token_row.revoked = True
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    db.flush()
    return issue_token_pair(db, user, auth_config)


def logout(db: Session, refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    row = db.scalar(select(UserRefreshToken).where(UserRefreshToken.token_hash == token_hash))
    if row is not None:
        row.revoked = True
        db.commit()


def me(user: User) -> MeOutput:
    return _to_me_output(user)
