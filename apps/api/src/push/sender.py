# pywebpush 2.5.0 `webpush_async` 얇은 래퍼 — 테스트에서 가짜로 교체한다 (pwa.md §5.3 "모듈 배치")
"""DB 를 모르는 발송 계층. 결과 분류(성공·404/410·그 외)는 service.py 가 한다.

로그를 남기지 않는다 — endpoint·keys·payload 원문이 새는 경로를 만들지 않기 위해서다.
예외 원문(`WebPushException.__str__` 은 푸시 서비스 응답 본문을 담는다)도 밖으로 내보내지 않고
상태코드와 예외 타입명만 `SendResult` 로 돌려준다.
"""
import asyncio
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, cast

import aiohttp
from pywebpush import WebPushException, webpush_async

from src.push.schemas import PushTarget

# ttl 기본값 0 = 기기가 오프라인이면 푸시 서비스가 즉시 폐기한다 → 하루 보관
PUSH_TTL_SECONDS = 86400
# ★반드시 명시. 미지정이면 webpush_async 가 timeout=None 을 aiohttp 까지 그대로 넘겨
#   ClientTimeout(total=None) = 무제한 대기가 된다 (pwa.md §5.3 기본값 함정, R-8)
PUSH_TIMEOUT_SECONDS = 10


@dataclass(frozen=True, slots=True)
class SendResult:
    """구독 1건의 발송 결과 — 상태코드와 예외 타입명만 담는다 (원문 없음)."""

    subscription_id: uuid.UUID
    # 푸시 서비스 HTTP 상태. 응답 자체가 없으면(타임아웃·연결 실패) None
    status_code: int | None
    # 실패 시 예외 타입명, 성공이면 None
    error_type: str | None


class PushSender(Protocol):
    """service.py 가 의존하는 발송 인터페이스 (테스트 가짜와 실구현이 공유)."""

    async def send_all(
        self, targets: Sequence[PushTarget], payload: str
    ) -> list[SendResult]: ...


class WebPushSender:
    """VAPID 서명 + aes128gcm 암호화 + POST 를 pywebpush 에 맡긴다."""

    def __init__(self, *, vapid_private_key: str, vapid_subject: str) -> None:
        self._vapid_private_key = vapid_private_key
        self._vapid_subject = vapid_subject

    async def send_all(
        self, targets: Sequence[PushTarget], payload: str
    ) -> list[SendResult]:
        """aiohttp ClientSession 1개를 구독 전체가 공유하고 gather 로 동시에 보낸다.

        개별 실패는 예외로 올리지 않고 `SendResult` 로 돌려준다 (return_exceptions=True).
        """
        async with aiohttp.ClientSession() as http:
            outcomes = await asyncio.gather(
                *(self._send_one(http, target, payload) for target in targets),
                return_exceptions=True,
            )
        return [
            _to_result(target, outcome)
            for target, outcome in zip(targets, outcomes, strict=True)
        ]

    async def _send_one(
        self, http: aiohttp.ClientSession, target: PushTarget, payload: str
    ) -> int:
        response = await webpush_async(
            subscription_info={
                "endpoint": target.endpoint,
                "keys": {"p256dh": target.p256dh, "auth": target.auth},
            },
            data=payload,
            vapid_private_key=self._vapid_private_key,
            # 라이브러리가 이 dict 에 aud·exp 를 주입해 변형한다 → 호출마다 새 dict
            vapid_claims={"sub": self._vapid_subject},
            ttl=PUSH_TTL_SECONDS,
            timeout=PUSH_TIMEOUT_SECONDS,
            headers={"Urgency": "normal"},
            aiohttp_session=http,
        )
        # curl=False 라 항상 ClientResponse 다 (str 반환은 curl=True 전용). >202 는 예외로 온다
        return cast(aiohttp.ClientResponse, response).status


def _to_result(target: PushTarget, outcome: int | BaseException) -> SendResult:
    if isinstance(outcome, BaseException):
        status = outcome.status_code if isinstance(outcome, WebPushException) else None
        return SendResult(
            subscription_id=target.id,
            status_code=status,
            error_type=type(outcome).__name__,
        )
    return SendResult(subscription_id=target.id, status_code=outcome, error_type=None)
