from fastapi import Depends, FastAPI  # FastAPI app + dependency injection for DB sessions
from sqlalchemy.orm import Session  # Type hint for the db parameter injected by get_db

from app.database.connection import engine, get_db  # SQLite engine + session generator dependency
from app.database.base import Base  # Declarative base whose metadata drives create_all()
import app.models.expense  # noqa: F401 — import side effect registers Expense table on Base.metadata
import app.models.user  # noqa: F401 — import side effect registers User table on Base.metadata
import app.models.category  # noqa: F401 — import side effect registers Category table on Base.metadata
from app.schemas.category import CategoryOutput, CreateCategoryInput  # Category request/response models
from app.schemas.expense import InsertExpenseInput, ExpenseOutput  # Expense request/response models
from app.schemas.user import CreateUserInput, UserOutput  # User registration request/response models
from app.services import category_service, expense_service, user_service  # Business logic kept out of route handlers

app = FastAPI()  # ASGI application instance used by uvicorn

Base.metadata.create_all(bind=engine)  # Create missing tables (SQLite) on startup; does not migrate columns


@app.get("/")
def root():
    """Simple health-style endpoint to confirm the API is up."""
    return {"message": "Expense Tracker API is running"}


@app.get("/users", response_model=list[UserOutput])
def list_users(db: Session = Depends(get_db)) -> list[UserOutput]:
    """Return all users (id, username, email only — no password hashes)."""
    return user_service.list_users(db)


@app.post("/users", response_model=UserOutput, status_code=201)
def create_user(
    input: CreateUserInput, db: Session = Depends(get_db)
) -> UserOutput:
    """Register a user; body validated as CreateUserInput; returns 201 + UserOutput (no password)."""
    return user_service.create_user(db, input)  # Delegate persistence and hashing to the service layer


@app.get("/categories", response_model=list[CategoryOutput])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryOutput]:
    """Return all categories ordered by name."""
    return category_service.list_categories(db)


@app.post("/categories", response_model=CategoryOutput, status_code=201)
def create_category(
    input: CreateCategoryInput, db: Session = Depends(get_db)
) -> CategoryOutput:
    """Create a canonical category row and return it."""
    return category_service.create_category(db, input)


@app.get("/expenses", response_model=list[ExpenseOutput])
def list_expenses(
    user_id: int, db: Session = Depends(get_db)
) -> list[ExpenseOutput]:
    """List expenses for ?user_id=… (required query param until auth provides the user)."""
    return expense_service.list_expenses(db, user_id)


@app.post("/expenses", response_model=ExpenseOutput)
def insert_expense(
    input: InsertExpenseInput, db: Session = Depends(get_db)
) -> ExpenseOutput:
    """Create an expense; body must include user_id plus expense fields."""
    return expense_service.insert_expense(db, input)
