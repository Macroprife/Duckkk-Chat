"""Duck Chat — Pydantic models for request/response validation."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=32000)
    model: str = Field("", max_length=200)
    conversation_id: str | None = None
    image: str | None = None


class AuthRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=200)
