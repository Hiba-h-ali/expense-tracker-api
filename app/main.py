from contextlib import asynccontextmanager
import os
import uuid

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
    current_user: User = Depends(get_current_user),
):
    if ces_client is None:
        raise HTTPException(status_code=503, detail="CES client is not configured")
    raw_session = request.session_id or str(uuid.uuid4())
    session_id = f"user-{current_user.id}-{raw_session}"
    response = ces_client.run_session_text(request.text, session_id)
    return ChatResponse(
        messages=ces_client.extract_response_text(response),
        session_id=session_id,
    )