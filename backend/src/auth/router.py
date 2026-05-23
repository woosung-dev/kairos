# Clerk 인증 사용자 정보 조회 + Clerk webhook(Svix 검증) 라우터
"""Auth 라우터 — HTTP 전용."""
from fastapi import APIRouter, Depends

from src.auth.dependencies import get_auth_service, get_current_user
from src.auth.models import User
from src.auth.service import AuthService
from src.auth.svix_verify import verify_svix_signature

router = APIRouter(prefix="/api/v1/users", tags=["auth"])


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """현재 인증된 사용자 정보."""
    return AuthService.to_response(current_user)


@router.post("/sync")
async def sync_user(
    verified_payload: dict = Depends(verify_svix_signature),
    service: AuthService = Depends(get_auth_service),
):
    """Clerk webhook 사용자 동기화.

    Sprint 27b ADR-024 회수 — Svix 서명 검증 강제 (`verify_svix_signature`).
    검증 실패 시 401 (DB write 도달 전 차단).
    """
    data = verified_payload.get("data", {})

    clerk_id = data.get("id", "")
    email = ""
    email_addresses = data.get("email_addresses", [])
    if email_addresses:
        email = email_addresses[0].get("email_address", "")

    display_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    avatar_url = data.get("image_url")

    await service.sync_user(
        clerk_id=clerk_id,
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
    )
    return {"synced": True}
