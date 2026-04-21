from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.database.connection import get_db
from app.models.user import User
from config import AuthConfig

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    payload = decode_token(token, expected_type="access", config=AuthConfig.from_env())
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token subject missing")
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
