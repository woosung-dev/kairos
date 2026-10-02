# 웹 푸시 구독 API (API-001~003) — 사용자 단위, I-13 예외 `/api/v1/users` 안 (pwa.md §5.2, C-16)
import uuid

from fastapi import APIRouter, Depends, Response

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.push.dependencies import get_push_service
from src.push.schemas import (
    PushConfigResponse,
    PushSubscriptionUpsertRequest,
    PushSubscriptionUpsertResponse,
)
from src.push.service import PushService

router = APIRouter(prefix="/api/v1/users/me", tags=["push"])


@router.get("/push-config", response_model=PushConfigResponse)
async def get_push_config(
    _user: User = Depends(get_current_user),
    service: PushService = Depends(get_push_service),
) -> PushConfigResponse:
    """API-001 — VAPID 미설정이어도 200 (isEnabled=false 면 FE 가 알림 탭을 숨긴다)."""
    return service.get_config()


@router.put("/push-subscriptions", response_model=PushSubscriptionUpsertResponse)
async def upsert_push_subscription(
    data: PushSubscriptionUpsertRequest,
    user: User = Depends(get_current_user),
    service: PushService = Depends(get_push_service),
) -> PushSubscriptionUpsertResponse:
    """API-002 — endpoint 단위 upsert. 같은 endpoint 면 id 유지 + 현재 사용자로 rebind."""
    return await service.upsert_subscription(user.id, data)


@router.delete(
    "/push-subscriptions/{subscription_id}",
    status_code=204,
    response_class=Response,
)
async def delete_push_subscription(
    subscription_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PushService = Depends(get_push_service),
) -> Response:
    """API-003 — 본인 것만 지운다. 없거나 남의 것이어도 204 (멱등 + 존재 여부 오라클 차단)."""
    await service.delete_subscription(user.id, subscription_id)
    return Response(status_code=204)
