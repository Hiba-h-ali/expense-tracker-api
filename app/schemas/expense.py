from datetime import datetime  # ISO-8601 datetimes in JSON via Pydantic

from pydantic import BaseModel  # Validates and documents expense JSON payloads


class InsertExpenseInput(BaseModel):
    """JSON body for POST /expenses — category_id is optional and can be auto-inferred."""

    amount: float  # Monetary amount (float; use Decimal later if you need exact currency math)
    category_id: int | None = None  # Optional FK to categories.id; resolved by AI when omitted
    description: str | None = None # Free-text details
    date: datetime  # When the expense occurred (client-supplied)


class UpdateExpenseInput(BaseModel):
    """JSON body for updating an expense; omitted fields are left unchanged."""

    amount: float | None = None
    category_id: int | None = None
    description: str | None = None
    date: datetime | None = None


class ExpenseOutput(BaseModel):
    """JSON shape for one expense returned from GET or POST — includes server-generated fields."""

    id: int  # Primary key assigned by the database
    user_id: int  # Foreign key to users.id
    category_id: int  # Foreign key to categories.id
    amount: float
    description: str | None
    date: datetime
    created_at: datetime  # Server timestamp when the row was inserted
