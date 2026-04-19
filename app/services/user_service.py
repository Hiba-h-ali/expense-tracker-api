import hashlib  # Provides PBKDF2-based key derivation for password hashing
import secrets  # Cryptographically strong random salt generation
from typing import cast  # Tells the type checker ORM instance attributes are plain values

from fastapi import HTTPException  # Raised to return HTTP error responses (409 Conflict)
from sqlalchemy import select  # SQLAlchemy 2 style SELECT for listing users
from sqlalchemy.exc import IntegrityError  # Raised when email UNIQUE is violated on INSERT
from sqlalchemy.orm import Session  # Database session passed in from FastAPI Depends(get_db)

from app.models.user import User  # SQLAlchemy ORM model mapped to the users table
from app.schemas.user import CreateUserInput, UserOutput  # Pydantic request/response shapes


def _hash_password(password: str) -> str:
    """Turn a plain password into a stored hash (never store plaintext passwords)."""
    salt = secrets.token_hex(16)  # Random 16-byte salt, hex-encoded, unique per user/password change
    key = hashlib.pbkdf2_hmac(
        "sha256",  # HMAC-SHA256 as the PRF inside PBKDF2
        password.encode("utf-8"),  # Normalise password to bytes
        salt.encode("ascii"),  # Salt must be bytes for pbkdf2_hmac
        100_000,  # Iteration count; slows brute-force attempts
    ).hex()  # Store derived key as readable hex string
    return f"{salt}:{key}"  # Persist salt with hash so we can verify later without a separate salt column


def _user_to_output(user: User) -> UserOutput:
    """Convert a SQLAlchemy User row into an API-safe Pydantic model (no password fields)."""
    return UserOutput(
        id=cast(int, user.id),  # cast: pyright sees Column[int] on class, instance has int
        username=cast(str, user.username),
        email=cast(str, user.email),
    )


def create_user(db: Session, input: CreateUserInput) -> UserOutput:
    """Insert a new user row; 409 if email is already registered (username may repeat)."""
    user = User(
        username=input.username.strip(),  # Remove accidental leading/trailing whitespace
        email=input.email.strip().lower(),  # Normalise email for uniqueness comparisons
        password_hash=_hash_password(input.password),  # Store only the hash, not the raw password
    )
    db.add(user)  # Stage the new row in the session (not yet written to SQLite)
    try:
        db.commit()  # Flush INSERT; fails with IntegrityError if UNIQUE violated
    except IntegrityError:
        db.rollback()  # Discard failed transaction so the session can be reused
        raise HTTPException(
            status_code=409,  # HTTP 409 Conflict — email already in use
            detail="Email already registered",
        )
    db.refresh(user)  # Reload row from DB so server-generated fields (e.g. id) are populated
    return _user_to_output(user)  # Return public fields only


def list_users(db: Session) -> list[UserOutput]:
    """Return every user as API-safe models (no passwords), ordered by id ascending."""
    rows = db.scalars(select(User).order_by(User.id.asc())).all()  # SELECT * FROM users ORDER BY id
    return [_user_to_output(row) for row in rows]  # Map each ORM row to UserOutput
