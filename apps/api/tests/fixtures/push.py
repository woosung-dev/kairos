# 웹 푸시 테스트 공용 헬퍼 — 운영과 같은 형식의 키 생성 + 가짜 sender (PWA PR-2)
import base64
import logging
import os
from collections.abc import Awaitable, Callable, Sequence

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import SecretStr

from src.core.config import Settings, get_settings
from src.push.schemas import PushTarget
from src.push.sender import SendResult

TEST_VAPID_SUBJECT = "mailto:ops@kairos.test"

# 웹 푸시 경로가 로그를 남기는 모듈 로거
PUSH_LOGGER_NAMES = ("src.core.config", "src.push.service", "src.meetings.pipeline_service")


@pytest.fixture
def push_loggers_enabled(monkeypatch):
    """suite 순서와 무관하게 push 로그가 caplog 에 잡히게 한다.

    alembic env.py 의 `fileConfig` (disable_existing_loggers 기본 True) 가 alembic 을 도는 테스트
    이후 기존 `src.*` 로거를 disabled 로 만든다 → caplog 가 비어 "경고 0건" 단언이 공허해진다.
    `tests/rag/test_rag_service.py` 의 명시 복구와 같은 처리, monkeypatch 가 원상 복구한다.
    """
    for name in PUSH_LOGGER_NAMES:
        monkeypatch.setattr(logging.getLogger(name), "disabled", False)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def generate_vapid_key_pair() -> tuple[str, str]:
    """(개인키, 공개키) — push/CONTEXT.md §7 생성 명령과 같은 형식.

    개인키 = raw P-256 base64url 32바이트(43자), 공개키 = uncompressed point base64url(87자).
    """
    key = ec.generate_private_key(ec.SECP256R1())
    private_raw = key.private_numbers().private_value.to_bytes(32, "big")
    public_raw = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return b64url(private_raw), b64url(public_raw)


def generate_subscription_keys() -> tuple[ec.EllipticCurvePrivateKey, str, bytes]:
    """브라우저 쪽 구독 키 — (수신자 개인키, p256dh base64url, auth 16바이트)."""
    receiver = ec.generate_private_key(ec.SECP256R1())
    p256dh = b64url(
        receiver.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
    )
    return receiver, p256dh, os.urandom(16)


def valid_subscription_keys() -> dict[str, str]:
    """API-002 요청 본문의 `keys` — 검증을 통과하는 실제 P-256 공개키 + 16바이트 auth."""
    _, p256dh, auth = generate_subscription_keys()
    return {"p256dh": p256dh, "auth": b64url(auth)}


def settings_with_vapid(
    *,
    public_key: str | None,
    private_key: str | None,
    subject: str | None,
) -> Settings:
    """현재 Settings 에 VAPID 3필드만 바꾼 사본 (get_settings 캐시는 건드리지 않는다)."""
    return get_settings().model_copy(
        update={
            "vapid_public_key": public_key,
            "vapid_private_key": SecretStr(private_key) if private_key is not None else None,
            "vapid_subject": subject,
        }
    )


class FakeSender:
    """`PushSender` 가짜 — 호출을 기록하고 endpoint 별 상태코드를 돌려준다.

    `on_send` 는 발송 시작 시점(결과 반환 전)에, `on_return` 은 결과를 돌려주기 직전에 불린다.
    """

    def __init__(
        self,
        *,
        status_by_endpoint: dict[str, int] | None = None,
        default_status: int = 201,
        exc: BaseException | None = None,
        on_send: Callable[[], Awaitable[None]] | None = None,
        on_return: Callable[[], None] | None = None,
    ) -> None:
        self.calls: list[tuple[list[PushTarget], str]] = []
        self._status_by_endpoint = status_by_endpoint or {}
        self._default_status = default_status
        self._exc = exc
        self._on_send = on_send
        self._on_return = on_return

    async def send_all(
        self, targets: Sequence[PushTarget], payload: str
    ) -> list[SendResult]:
        self.calls.append((list(targets), payload))
        if self._on_send is not None:
            await self._on_send()
        if self._exc is not None:
            raise self._exc
        results = []
        for target in targets:
            status = self._status_by_endpoint.get(target.endpoint, self._default_status)
            is_ok = 200 <= status <= 202
            results.append(
                SendResult(
                    subscription_id=target.id,
                    status_code=status,
                    error_type=None if is_ok else "WebPushException",
                )
            )
        if self._on_return is not None:
            self._on_return()
        return results
