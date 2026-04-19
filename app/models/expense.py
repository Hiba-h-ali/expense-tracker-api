from datetime import datetime  # Default factory for date / created_at columns

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String  # SQL types for expenses table
from sqlalchemy.orm import relationship  # expense.user / expense.category ORM relationships

from app.database.base import Base  # Same Base as User so FK metadata links tables


class Expense(Base):
    """ORM mapping for table `expenses` — spending records owned by a user."""

    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Must reference existing user
    amount = Column(Float, nullable=False)  # Required monetary value
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)  # FK to categories.id
    description = Column(String, nullable=True)  # Optional notes
    date = Column(DateTime, default=datetime.utcnow)  # When the expense happened (UTC if using utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)  # When this row was inserted

    user = relationship("User", back_populates="expenses")  # Navigate to the parent User without a manual join
    category = relationship("Category", back_populates="expenses")  # Navigate to related category row
