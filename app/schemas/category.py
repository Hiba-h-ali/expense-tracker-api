from pydantic import BaseModel, Field  # Validation and OpenAPI schema definitions


class CreateCategoryInput(BaseModel):
    """JSON body for POST /categories."""

    name: str = Field(min_length=1, max_length=100)


class CategoryOutput(BaseModel):
    """Category representation returned by API endpoints."""

    id: int
    name: str
