# Onboarding 도메인 — Pydantic 스키마 (server-side persistent step tracker)
from datetime import datetime
from enum import IntEnum

from pydantic import BaseModel, ConfigDict, Field


class OnboardingStep(IntEnum):
    """User.onboarding_step lifecycle. Sprint 22 OBN-02."""

    NOT_STARTED = 0
    WORKSPACE_CREATED = 1
    FIRST_PROJECT = 2
    FIRST_MEETING = 3
    FIRST_RAG = 4


class OnboardingResponse(BaseModel):
    """GET /api/v1/users/me/onboarding 응답."""

    model_config = ConfigDict(populate_by_name=True)

    step: int = Field(..., alias="step")
    total_steps: int = Field(4, alias="totalSteps")
    onboarded_at: datetime | None = Field(None, alias="onboardedAt")
    is_completed: bool = Field(False, alias="isCompleted")
