# backend/src/auth/schemas.py
"""Auth 스키마."""
import uuid

from pydantic import BaseModel


class UserResponse(BaseModel):
    """사용자 응답."""

    id: uuid.UUID
    clerk_id: str
    display_name: str
    email: str
    avatar_url: str | None = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class SyncResponse(BaseModel):
    """Webhook 동기화 응답."""

    synced: bool = True
