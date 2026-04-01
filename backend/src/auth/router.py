# backend/src/auth/router.py
"""Auth 라우터 — HTTP 전용, 10줄 이하."""
from fastapi import APIRouter, Depends, Request

from src.auth.dependencies import get_auth_service, get_current_user
from src.auth.models import User
from src.auth.service import AuthService

router = APIRouter(prefix="/api/v1/users", tags=["auth"])


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """현재 인증된 사용자 정보."""
    return AuthService.to_response(current_user)


@router.post("/sync")
async def sync_user(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """Clerk webhook 사용자 동기화."""
    # TODO: Svix 서명 검증 추가
    body = await request.json()
    data = body.get("data", {})

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
