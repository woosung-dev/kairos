# 인증 사용자 정보 조회 라우터 (ADR-031 — Better Auth JWT. webhook/sync endpoint 는 없다)
"""Auth 라우터 — HTTP 전용, 10줄 이하."""
from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.service import AuthService

router = APIRouter(prefix="/api/v1/users", tags=["auth"])


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """현재 인증된 사용자 정보."""
    return AuthService.to_response(current_user)
