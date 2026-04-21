from typing import cast

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.expense import Expense
from app.schemas.category import CategoryOutput, CreateCategoryInput


def _category_to_output(category: Category) -> CategoryOutput:
    return CategoryOutput(
        id=cast(int, category.id),
        name=cast(str, category.name),
    )


def list_categories(db: Session) -> list[CategoryOutput]:
    rows = db.scalars(select(Category).order_by(Category.name.asc())).all()
    return [_category_to_output(row) for row in rows]


def create_category(db: Session, input: CreateCategoryInput) -> CategoryOutput:
    category = Category(name=input.name.strip().lower())
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category already exists")
    db.refresh(category)
    return _category_to_output(category)


def delete_category(db: Session, category_id: int) -> None:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    has_expenses = db.scalar(
        select(Expense.id).where(Expense.category_id == category_id).limit(1)
    )
    if has_expenses is not None:
        raise HTTPException(
            status_code=409,
            detail="Category is used by existing expenses and cannot be deleted",
        )

    db.delete(category)
    db.commit()
