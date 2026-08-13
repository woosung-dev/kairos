# Onboarding 도메인 — GET /api/v1/users/me/onboarding
from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.onboarding.dependencies import get_onboarding_service
from src.onboarding.schemas import OnboardingResponse
from src.onboarding.service import OnboardingService

router = APIRouter(prefix="/api/v1/users/me/onboarding", tags=["onboarding"])


@router.get("", response_model=OnboardingResponse)
async def get_my_onboarding(
    user: User = Depends(get_current_user),
    service: OnboardingService = Depends(get_onboarding_service),
) -> OnboardingResponse:
    """현재 사용자의 onboarding 진행 상태 조회 (Sprint 22 OBN-02)."""
    return await service.get_status(user.id)
