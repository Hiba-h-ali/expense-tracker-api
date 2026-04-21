from datetime import datetime  # Type for expense.date / created_at in Pydantic output
from typing import cast  # Satisfy the type checker for SQLAlchemy instance attributes

from fastapi import HTTPException  # 404 when user_id does not exist
from sqlalchemy import select  # SQLAlchemy 2 style SELECT builder
from sqlalchemy.orm import Session  # DB session from get_db dependency

from app.services import ai_service
from app.models.category import Category  # Looked up to ensure category_id is valid
from app.models.expense import Expense  # ORM model for expenses table
from app.schemas.expense import (
    InsertExpenseInput,
    ExpenseOutput,
    UpdateExpenseInput,
)  # API input/output models


def _expense_to_output(expense: Expense) -> ExpenseOutput:
    """Map an Expense ORM instance to the JSON response schema."""
    return ExpenseOutput(
        id=cast(int, expense.id),
        user_id=cast(int, expense.user_id),  # Owner of this expense row
        category_id=cast(int, expense.category_id),  # Canonical category reference
        amount=cast(float, expense.amount),
        description=cast(str | None, expense.description),
        date=cast(datetime, expense.date),
        created_at=cast(datetime, expense.created_at),
    )


def list_expenses(db: Session, user_id: int) -> list[ExpenseOutput]:
    """Return all expenses for one user, newest first."""
    rows = db.scalars(
        select(Expense)  # SELECT * FROM expenses (conceptually)
        .where(Expense.user_id == user_id)  # Restrict to the requested user
        .order_by(Expense.created_at.desc())  # Most recently created first
    ).all()  # Execute query and return a list of Expense instances
    return [_expense_to_output(row) for row in rows]  # Convert each row to API shape


def _get_or_create_uncategorized_category_id(db: Session) -> int:
    uncategorized = db.scalar(
        select(Category).where(Category.name == "uncategorized")
    )
    if uncategorized is None:
        uncategorized = Category(name="uncategorized")
        db.add(uncategorized)
        db.flush()
        db.refresh(uncategorized)
    return cast(int, uncategorized.id)


def _resolve_category_id(db: Session, input: InsertExpenseInput) -> int:
    if input.category_id is not None:
        category = db.get(Category, input.category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return input.category_id

    categories = db.scalars(select(Category)).all()
    if not categories:
        return _get_or_create_uncategorized_category_id(db)

    category_name_to_id = {
        cast(str, category.name).strip().lower(): cast(int, category.id)
        for category in categories
    }
    try:
        predicted_name = ai_service.categorize_expense(
            input.description,
            list(category_name_to_id.keys()),
        ).strip().lower()
    except Exception:
        predicted_name = "uncategorized"
    if predicted_name in category_name_to_id:
        return category_name_to_id[predicted_name]
    return _get_or_create_uncategorized_category_id(db)


def insert_expense(db: Session, input: InsertExpenseInput, user_id: int) -> ExpenseOutput:
    """Create one expense row for the authenticated user."""
    resolved_category_id = _resolve_category_id(db, input)

    expense = Expense(
        user_id=user_id,  # Authenticated user FK
        category_id=resolved_category_id,  # Explicit or AI-resolved category FK
        amount=input.amount,
        description=input.description,
        date=input.date,
    )
    db.add(expense)  # Stage INSERT
    db.commit()  # Persist to SQLite
    db.refresh(expense)  # Fill in DB defaults and generated id on the Python object
    return _expense_to_output(expense)  # Respond with the saved row (including id, timestamps)


def update_expense(
    db: Session,
    expense_id: int,
    input: UpdateExpenseInput,
    user_id: int,
) -> ExpenseOutput:
    expense = db.get(Expense, expense_id)
    if expense is None or cast(int, expense.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Expense not found")

    if input.amount is not None:
        expense.amount = input.amount
    if input.description is not None:
        expense.description = input.description
    if input.date is not None:
        expense.date = input.date

    # If category_id provided, validate it. If null/omitted, infer from description.
    if input.category_id is not None:
        category = db.get(Category, input.category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        expense.category_id = input.category_id
    else:
        inferred_input = InsertExpenseInput(
            amount=cast(float, expense.amount),
            category_id=None,
            description=(
                input.description
                if input.description is not None
                else cast(str | None, expense.description)
            ),
            date=cast(datetime, expense.date),
        )
        expense.category_id = _resolve_category_id(db, inferred_input)

    db.commit()
    db.refresh(expense)
    return _expense_to_output(expense)
