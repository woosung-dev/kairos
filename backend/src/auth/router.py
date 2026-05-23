# Clerk 인증 사용자 정보 조회 + Clerk webhook(Svix 검증) 라우터
"""Auth 라우터 — HTTP 전용."""
from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_auth_service, get_current_user
from src.auth.models import User
from src.auth.service import AuthService
from src.auth.svix_verify import verify_svix_signature

router = APIRouter(prefix="/api/v1/users", tags=["auth"])

# Codex P2-1 (Sprint 27b Wave 1 게이트): Clerk webhook 이 보낼 수 있는 event 중
# 본 endpoint 가 처리하는 것만 화이트리스트. 외 event (user.deleted, organization.*,
# session.* 등) 는 valid Svix 서명이어도 sync_user 호출 차단 → bogus row 회피.
# Clerk 의 재시도 무한루프를 피하려 200 응답 (synced=False) 로 idempotent 종결.
_SUPPORTED_USER_EVENTS = frozenset({"user.created", "user.updated"})


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
    검증 실패 시 401 (DB write 도달 전 차단). Codex P2-1: event_type 화이트리스트.
    """
    event_type = verified_payload.get("type", "")
    if event_type not in _SUPPORTED_USER_EVENTS:
        # 비지원 event — 200 + no-op (Clerk 재시도 회피, DB write 차단).
        return {"synced": False, "reason": f"event_type={event_type or 'missing'}_ignored"}

    data = verified_payload.get("data", {})
    clerk_id = data.get("id", "")
    if not clerk_id:
        # data.id 누락 — invalid Clerk payload. 422 → Clerk dashboard 에서 인지 가능.
        raise HTTPException(status_code=422, detail="MISSING_USER_ID")

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
