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

    # Codex 2차 P2 fix (primary email): Clerk 의 multi-email user 는 index 0 가
    # primary 아님. primary_email_address_id 와 id 매칭하는 row 사용 + fallback index 0.
    email = ""
    email_addresses = data.get("email_addresses", []) or []
    primary_email_id = data.get("primary_email_address_id")
    if email_addresses:
        if primary_email_id:
            primary = next(
                (e for e in email_addresses if e.get("id") == primary_email_id),
                None,
            )
            if primary:
                email = primary.get("email_address", "") or ""
        if not email:
            email = email_addresses[0].get("email_address", "") or ""

    # Codex 2차 P2 fix (nullable name): Clerk payload 가 first_name/last_name=None 보낼 수
    # 있음. `dict.get(k, "")` 는 key 가 있으면서 value=None 일 때 None 반환 → f-string
    # 이 'None None' 으로 변환. `(x or "")` 패턴으로 null 정규화 + 빈 fallback "사용자".
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    display_name = " ".join(p for p in (first, last) if p).strip() or "사용자"
    avatar_url = data.get("image_url")

    await service.sync_user(
        clerk_id=clerk_id,
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
    )
    return {"synced": True}
