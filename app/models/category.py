from sqlalchemy import Column, Integer, String  # SQL column types for categories
from sqlalchemy.orm import relationship  # ORM relation Category -> Expense

from app.database.base import Base  # Shared SQLAlchemy declarative base


class Category(Base):
    """ORM mapping for table `categories`."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)  # Surrogate key
    name = Column(String, unique=True, index=True)  # One canonical row per category name

    expenses = relationship("Expense", back_populates="category")
