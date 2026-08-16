# apps/api/src/auth/schemas.py
"""Auth 스키마."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """사용자 응답."""

    id: uuid.UUID
    clerk_id: str
    display_name: str
    email: str
    avatar_url: str | None = None
    # Sprint 22 OBN-02: 서버 측 영속 onboarding 단계 + 완료 시각 (FE camelCase alias)
    onboarding_step: int = Field(0, alias="onboardingStep")
    onboarded_at: datetime | None = Field(None, alias="onboardedAt")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class SyncResponse(BaseModel):
    """Webhook 동기화 응답."""

    synced: bool = True
