from sqlalchemy import Column, Integer, String  # Column types for the users table
from sqlalchemy.orm import relationship  # Optional ORM navigation User -> expenses

from app.database.base import Base  # Shared metadata registry for create_all()


class User(Base):
    """ORM mapping for table `users` — one row per registered account."""

    __tablename__ = "users"  # Actual SQLite table name

    id = Column(Integer, primary_key=True, index=True)  # Auto-increment integer primary key
    username = Column(String, index=True)  # Display/login name; duplicates allowed (uniqueness is email-only)
    email = Column(String, unique=True, index=True)  # UNIQUE so two users cannot share an email
    password_hash = Column(String)  # Never store plaintext passwords — only a hash string

    expenses = relationship("Expense", back_populates="user")  # user.expenses loads related Expense rows
