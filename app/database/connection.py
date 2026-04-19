import os

from sqlalchemy import create_engine  # Factory that opens connections to the database URL
from sqlalchemy.orm import sessionmaker  # Produces Session objects bound to our engine
from sqlalchemy.orm import Session  # Type hint for session instances


def _database_url() -> str:
    """Local default is SQLite; Railway/Heroku-style hosts set DATABASE_URL (often Postgres)."""
    url = os.getenv("DATABASE_URL", "sqlite:///./expenses.db").strip()
    if url.startswith("sqlite"):
        return url
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


DATABASE_URL = _database_url()

_engine_kwargs: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {
        "check_same_thread": False,  # SQLite across FastAPI / Starlette threadpool
    }
else:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,  # Every session runs SQL through this engine
    autoflush=False,  # Don’t flush before every query; explicit control
    autocommit=False,  # Use transactions; commit() persists changes
)


def get_db():
    """FastAPI dependency: yield one Session per request, then close it in finally."""
    db = SessionLocal()  # Open a new connection/transaction scope from the pool (SQLite: single file)
    try:
        yield db  # Route handlers receive this via Depends(get_db)
    finally:
        db.close()  # Return connection to pool / release SQLite file handle
