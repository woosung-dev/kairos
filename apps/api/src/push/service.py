# 웹 푸시 비즈니스 로직 — 구독 API(PushService) + 세션 없는 발송 단계(PushDispatchService)
"""두 서비스로 나눈 이유: 발송은 DB 세션이 하나도 열려 있지 않은 구간에서 돌아야 한다 (pwa.md §5.3).

- `PushService` — API-001~003. 요청 세션의 Repository 를 쓴다.
- `PushDispatchService` — Repository 를 갖지 않는다. 구독 원시 값(`PushTarget`)을 받아 발송하고
  결과를 성공 / 404·410(정리 대상) / 그 외로 분류만 한다. 조회·정리 세션은 오케스트레이터
  (`meetings/pipeline_service._notify_meeting_finished`)가 앞뒤로 따로 연다.
"""
import json
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

from src.core.config import Settings, get_settings
from src.push.exceptions import PushPayloadTooLargeError
from src.push.repository import PushRepository
from src.push.schemas import (
    PushConfigResponse,
    PushKind,
    PushSubscriptionUpsertRequest,
    PushSubscriptionUpsertResponse,
    PushTarget,
)
from src.push.sender import PushSender, WebPushSender

logger = logging.getLogger(__name__)

PUSH_PAYLOAD_VERSION = 1
# Web Push 페이로드 한도 4KB 대비 여유 (pwa.md §5.4)
PUSH_PAYLOAD_MAX_BYTES = 512
# 구독이 사라졌다는 푸시 서비스 응답 → 행 정리 대상
GONE_STATUS_CODES = frozenset({404, 410})


@dataclass(frozen=True, slots=True)
class VapidConfig:
    public_key: str
    private_key: str = field(repr=False)
    subject: str


def resolve_vapid_config(settings: Settings) -> VapidConfig | None:
    """VAPID 3개 설정이 다 있을 때만 활성 (pwa.md §5.7). 하나라도 없으면 None."""
    if (
        settings.vapid_public_key is None
        or settings.vapid_private_key is None
        or settings.vapid_subject is None
    ):
        return None
    return VapidConfig(
        public_key=settings.vapid_public_key,
        private_key=settings.vapid_private_key.get_secret_value(),
        subject=settings.vapid_subject,
    )


class PushService:
    """API-001~003 — 구독은 사용자 단위 리소스다 (user_id 는 라우터가 get_current_user 로 강제)."""

    def __init__(self, repo: PushRepository) -> None:
        self.repo = repo

    def get_config(self) -> PushConfigResponse:
        config = resolve_vapid_config(get_settings())
        return PushConfigResponse(
            is_enabled=config is not None,
            vapid_public_key=config.public_key if config is not None else None,
        )

    async def upsert_subscription(
        self, user_id: uuid.UUID, data: PushSubscriptionUpsertRequest
    ) -> PushSubscriptionUpsertResponse:
        subscription_id = await self.repo.upsert(
            user_id=user_id,
            endpoint=data.endpoint,
            p256dh=data.keys.p256dh,
            auth=data.keys.auth,
        )
        await self.repo.commit()
        return PushSubscriptionUpsertResponse(id=subscription_id)

    async def delete_subscription(
        self, user_id: uuid.UUID, subscription_id: uuid.UUID
    ) -> None:
        """없거나 남의 구독이어도 조용히 끝난다 — 204 멱등 + 존재 여부 오라클 차단 (API-003)."""
        await self.repo.delete_by_id(subscription_id, user_id)
        await self.repo.commit()


def build_meeting_payload(
    kind: PushKind, meeting_id: uuid.UUID, workspace_id: uuid.UUID
) -> str:
    """`{v, kind, meetingId, workspaceId}` 만 담는다 (pwa.md §5.4, 게이트 ④⑥).

    회의 제목·요약·전사·이름은 넣지 않는다 — 잠금화면은 기기 주인이 아닌 사람도 본다.
    """
    payload = json.dumps(
        {
            "v": PUSH_PAYLOAD_VERSION,
            "kind": kind,
            "meetingId": str(meeting_id),
            "workspaceId": str(workspace_id),
        },
        separators=(",", ":"),
    )
    size = len(payload.encode("utf-8"))
    if size > PUSH_PAYLOAD_MAX_BYTES:
        raise PushPayloadTooLargeError(size, PUSH_PAYLOAD_MAX_BYTES)
    return payload


@dataclass(frozen=True, slots=True)
class DispatchReport:
    sent: int
    failed: int
    # 404·410 을 받은 구독 id — 오케스트레이터가 새 짧은 세션으로 지운다
    gone_ids: tuple[uuid.UUID, ...]


class PushDispatchService:
    """세션 없는 발송 단계 (pwa.md §5.3 step 3). Repository·AsyncSession 을 갖지 않는다."""

    def __init__(self, sender: PushSender) -> None:
        self.sender = sender

    async def dispatch_meeting_finished(
        self,
        targets: Sequence[PushTarget],
        *,
        kind: PushKind,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> DispatchReport:
        payload = build_meeting_payload(kind, meeting_id, workspace_id)
        results = await self.sender.send_all(targets, payload)

        sent = 0
        gone_ids: list[uuid.UUID] = []
        failure_reasons: list[str] = []
        for result in results:
            if result.error_type is None:
                sent += 1
            elif result.status_code in GONE_STATUS_CODES:
                gone_ids.append(result.subscription_id)
            elif result.status_code is not None:
                failure_reasons.append(str(result.status_code))
            else:
                # 상태코드가 없으면(타임아웃·연결 실패) 예외 타입명만 남긴다
                failure_reasons.append(result.error_type)
        if failure_reasons:
            # 재시도 없음 (BL-PWA-6). endpoint·keys·payload 는 로그에 넣지 않는다
            logger.warning(
                "push_send_failed meeting=%s failed=%d reasons=%s",
                meeting_id,
                len(failure_reasons),
                ",".join(sorted(failure_reasons)),
            )
        return DispatchReport(
            sent=sent, failed=len(failure_reasons), gone_ids=tuple(gone_ids)
        )


def create_push_dispatcher() -> PushDispatchService | None:
    """VAPID 미구성이면 None — 호출자는 발송을 건너뛴다 (pwa.md §5.3 step 0)."""
    config = resolve_vapid_config(get_settings())
    if config is None:
        return None
    return PushDispatchService(
        WebPushSender(
            vapid_private_key=config.private_key,
            vapid_subject=config.subject,
        )
    )
