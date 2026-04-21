from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
import os
import re
import uuid

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_client import CESClient
from app.auth.dependencies import get_current_user
from app.database.base import Base
from app.database.connection import engine
from app.database.connection import get_db
import app.models.category  # noqa: F401
import app.models.expense  # noqa: F401
import app.models.refresh_token  # noqa: F401
import app.models.user  # noqa: F401
from app.models.category import Category
from app.models.expense import Expense
from app.models.user import User
from app.schemas.auth import LoginInput, MeOutput, RefreshInput, TokenPair
from app.schemas.category import CategoryOutput, CreateCategoryInput
from app.schemas.expense import ExpenseOutput, InsertExpenseInput
from app.schemas.user import CreateUserInput, UserOutput
from app.services import auth_service, category_service, expense_service, user_service
from config import AuthConfig, CESConfig

ces_client: CESClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ces_client
    # Safety net: ensure tables exist if migration step was skipped on deploy.
    Base.metadata.create_all(bind=engine)
    try:
        ces_client = CESClient(CESConfig.from_env())
    except ValueError:
        ces_client = None
    yield


app = FastAPI(lifespan=lifespan)

cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    text: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    messages: list[str]
    session_id: str


@app.get("/")
def root():
    return {"message": "Expense Tracker API is running"}


@app.get("/users", response_model=list[UserOutput])
def list_users(db: Session = Depends(get_db)) -> list[UserOutput]:
    return user_service.list_users(db)


@app.post("/users", response_model=UserOutput, status_code=201)
def create_user(input: CreateUserInput, db: Session = Depends(get_db)) -> UserOutput:
    return user_service.create_user(db, input)


@app.post("/auth/register", response_model=UserOutput, status_code=201)
def register(input: CreateUserInput, db: Session = Depends(get_db)) -> UserOutput:
    return user_service.create_user(db, input)


@app.post("/auth/login", response_model=TokenPair)
def login(input: LoginInput, db: Session = Depends(get_db)) -> TokenPair:
    return auth_service.login(db, input, AuthConfig.from_env())


@app.post("/auth/refresh", response_model=TokenPair)
def refresh(input: RefreshInput, db: Session = Depends(get_db)) -> TokenPair:
    return auth_service.refresh_access(db, input.refresh_token, AuthConfig.from_env())


@app.post("/auth/logout", status_code=204)
def logout(input: RefreshInput, db: Session = Depends(get_db)) -> None:
    auth_service.logout(db, input.refresh_token)
    return None


@app.get("/auth/me", response_model=MeOutput)
def me(current_user: User = Depends(get_current_user)) -> MeOutput:
    return auth_service.me(current_user)


@app.get("/categories", response_model=list[CategoryOutput])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryOutput]:
    return category_service.list_categories(db)


@app.post("/categories", response_model=CategoryOutput, status_code=201)
def create_category(
    input: CreateCategoryInput,
    db: Session = Depends(get_db),
) -> CategoryOutput:
    return category_service.create_category(db, input)


@app.get("/expenses", response_model=list[ExpenseOutput])
def list_expenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExpenseOutput]:
    return expense_service.list_expenses(db, current_user.id)


@app.post("/expenses", response_model=ExpenseOutput)
def insert_expense(
    input: InsertExpenseInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseOutput:
    return expense_service.insert_expense(db, input, current_user.id)


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Keep a stable session per user and avoid prefixing repeatedly.
    def _build_session_id(user_id: int, raw_session_id: str | None) -> str:
        user_prefix = f"user-{user_id}-"
        if not raw_session_id:
            return f"{user_prefix}default"
        if raw_session_id.startswith(user_prefix):
            return raw_session_id
        return f"{user_prefix}{raw_session_id}"

    def _build_user_context(user_id: int) -> str:
        expenses = db.execute(
            select(Expense, Category)
            .join(Category, Expense.category_id == Category.id)
            .where(Expense.user_id == user_id)
            .order_by(Expense.date.desc())
            .limit(20)
        ).all()
        if not expenses:
            return (
                "User financial context:\n"
                "- No expenses recorded yet for this user.\n"
                "- Advice should focus on first-budget setup and tracking habits."
            )

        total_spent = 0.0
        by_category: dict[str, float] = {}
        recent_lines: list[str] = []
        for expense, category in expenses:
            amount = float(expense.amount)
            total_spent += amount
            category_name = str(category.name)
            by_category[category_name] = by_category.get(category_name, 0.0) + amount
            recent_lines.append(
                f"- {expense.date.date().isoformat()}: {amount:.2f} on {category_name}"
                + (f" ({expense.description})" if expense.description else "")
            )

        top_categories = sorted(
            by_category.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:5]
        top_categories_lines = "\n".join(
            f"- {name}: {amount:.2f}" for name, amount in top_categories
        )
        recent_expenses_lines = "\n".join(recent_lines[:10])

        return (
            "User financial context:\n"
            f"- Total (last {len(expenses)} expenses): {total_spent:.2f}\n"
            "- Top categories:\n"
            f"{top_categories_lines}\n"
            "- Recent expenses:\n"
            f"{recent_expenses_lines}"
        )

    def _build_local_advice(user_id: int) -> str:
        expenses = db.execute(
            select(Expense, Category)
            .join(Category, Expense.category_id == Category.id)
            .where(Expense.user_id == user_id)
            .order_by(Expense.date.desc())
            .limit(30)
        ).all()
        if not expenses:
            return (
                "I do not see recorded expenses yet. "
                "Add 3-5 expenses over the next day, then ask for advice and I can provide a tailored summary."
            )

        total = 0.0
        category_totals: dict[str, float] = {}
        for expense, category in expenses:
            amount = float(expense.amount)
            total += amount
            category_name = str(category.name)
            category_totals[category_name] = category_totals.get(category_name, 0.0) + amount

        avg = total / len(expenses)
        top_name, top_amount = max(category_totals.items(), key=lambda item: item[1])
        share = (top_amount / total * 100.0) if total > 0 else 0.0
        return (
            f"Based on your latest {len(expenses)} expenses, you spent {total:.2f} total "
            f"(average {avg:.2f} per expense). "
            f"Your top category is {top_name} at {top_amount:.2f} ({share:.0f}% of total). "
            "Advice: set a weekly cap for that category and review each purchase before confirming it."
        )

    def _is_log_expense_intent(text: str) -> bool:
        normalized = text.lower()
        has_action = any(
            word in normalized for word in ("log", "add", "insert", "record", "create")
        )
        has_expense_word = any(
            word in normalized for word in ("expense", "spent", "spend", "paid", "pay")
        )
        return has_action and has_expense_word

    def _parse_amount(text: str) -> float | None:
        # Accept "$100", "100", "1000.50", etc.
        match = re.search(r"(?:\$|usd\s*)?(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
        if not match:
            return None
        try:
            amount = float(match.group(1))
        except ValueError:
            return None
        return amount if amount > 0 else None

    def _parse_date(text: str) -> datetime:
        normalized = text.lower()
        now = datetime.now(UTC)
        if "yesterday" in normalized:
            return (now - timedelta(days=1)).replace(tzinfo=None)
        if "today" in normalized or "now" in normalized:
            return now.replace(tzinfo=None)

        # ISO date support: 2026-04-21
        iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if iso_match:
            try:
                parsed = datetime.strptime(iso_match.group(1), "%Y-%m-%d")
                return parsed
            except ValueError:
                pass
        return now.replace(tzinfo=None)

    def _parse_description(text: str) -> str:
        lowered = text.lower().strip()
        description = lowered
        for marker in (" for ", " on ", " at "):
            if marker in lowered:
                description = lowered.split(marker, 1)[1]
                break
        description = re.sub(r"\b(today|yesterday|now)\b", "", description).strip()
        description = re.sub(r"(?:\$|usd\s*)?\d+(?:\.\d+)?", "", description).strip()
        if not description:
            return "expense from chat"
        return description[:255]

    def _find_category_id_from_text(text: str) -> int | None:
        categories = db.scalars(select(Category)).all()
        normalized = text.lower()
        for category in categories:
            category_name = str(category.name).strip().lower()
            if category_name and category_name in normalized:
                return int(category.id)
        return None

    session_id = _build_session_id(current_user.id, request.session_id)

    if _is_log_expense_intent(request.text):
        amount = _parse_amount(request.text)
        if amount is not None:
            payload = InsertExpenseInput(
                amount=amount,
                category_id=_find_category_id_from_text(request.text),
                description=_parse_description(request.text),
                date=_parse_date(request.text),
            )
            created = expense_service.insert_expense(db, payload, current_user.id)
            category = db.get(Category, created.category_id)
            category_name = str(category.name) if category is not None else "uncategorized"
            return ChatResponse(
                messages=[
                    "Expense logged successfully. "
                    f"Amount: {created.amount:.2f}, category: {category_name}, "
                    f"date: {created.date.isoformat()}."
                ],
                session_id=session_id,
            )
        return ChatResponse(
            messages=[
                "I can log that expense, but I could not find a valid amount. "
                "Please include a number, for example: 'log expense 100 for rent'."
            ],
            session_id=session_id,
        )

    if ces_client is None:
        raise HTTPException(status_code=503, detail="CES client is not configured")

    context_text = _build_user_context(current_user.id)
    prompt = (
        "You are a personal finance assistant.\n"
        "Use the user context below to provide specific, practical advice.\n"
        "Do not claim that you cannot access the user's data because context is provided below.\n"
        "Never reference other users.\n\n"
        f"{context_text}\n\n"
        f"User message:\n{request.text}"
    )
    response = ces_client.run_session_text(prompt, session_id)
    messages = ces_client.extract_response_text(response)
    if not messages:
        messages = [_build_local_advice(current_user.id)]
    else:
        first_message = messages[0].lower()
        if (
            "don't have access" in first_message
            or "do not have access" in first_message
            or "don't have account history" in first_message
            or "do not have account history" in first_message
        ):
            messages = [_build_local_advice(current_user.id)]
    return ChatResponse(
        messages=messages,
        session_id=session_id,
    )