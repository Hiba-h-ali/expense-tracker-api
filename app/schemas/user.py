from pydantic import BaseModel, Field  # BaseModel: JSON schema + validation; Field: per-field constraints


class CreateUserInput(BaseModel):
    """JSON body for POST /users — what the client sends (includes plaintext password)."""

    username: str = Field(min_length=1, max_length=255)  # Non-empty, bounded length for DB String column
    email: str = Field(min_length=1, max_length=255)  # Kept as str to avoid extra email-validator dependency
    password: str = Field(min_length=8, max_length=255)  # Minimum length rule; never echoed in responses


class UserOutput(BaseModel):
    """JSON body for successful user responses — safe subset of User (no password_hash)."""

    id: int  # Surrogate primary key from SQLite
    username: str  # Public display/login name
    email: str  # Normalised email returned after registration
