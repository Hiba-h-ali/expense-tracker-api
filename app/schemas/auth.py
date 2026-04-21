from pydantic import BaseModel, Field


class LoginInput(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class RefreshInput(BaseModel):
    refresh_token: str = Field(min_length=20)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MeOutput(BaseModel):
    id: int
    username: str
    email: str
