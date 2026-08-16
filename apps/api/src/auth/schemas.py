# apps/api/src/auth/schemas.py
"""Auth 스키마."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """사용자 응답.

    ★현재 라우터는 이 모델을 쓰지 않는다 — `GET /users/me` 는 `AuthService.to_response()` 의
      camelCase dict 를 직접 반환한다. 그래서 OpenAPI 계약에도 잡히지 않는다.
      필드를 바꿀 때 `to_response()` 와 어긋나지 않게 같이 본다.
    """

    id: uuid.UUID
    auth_user_id: str | None = None
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


# SyncResponse 는 ADR-031 에서 삭제했다. Clerk webhook(`POST /users/sync`) 응답 스키마였고
# 그 엔드포인트는 Sprint 25 T-SEC-1 로 이미 제거됐다. Better Auth 에는 webhook 개념 자체가 없다.
