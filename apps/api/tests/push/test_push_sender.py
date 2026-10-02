# PWA PR-2 발송 계층 — webpush_async 인자·페이로드 (T-PWA-42) + 결과 분류 (T-PWA-38) + VAPID 왕복 (pwa.md §5.7)
import asyncio
import json
import logging
import time
import uuid

import aiohttp
import http_ece
import pytest
from aiohttp import web
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from pywebpush import WebPushException

from src.push import sender as sender_module
from src.push.exceptions import PushPayloadTooLargeError
from src.push.schemas import PushTarget
from src.push.sender import PUSH_TIMEOUT_SECONDS, PUSH_TTL_SECONDS, SendResult, WebPushSender
from src.push.service import (
    PUSH_PAYLOAD_MAX_BYTES,
    PushDispatchService,
    build_meeting_payload,
    create_push_dispatcher,
)
from tests.fixtures.push import (
    TEST_VAPID_SUBJECT,
    FakeSender,
    b64url,
    b64url_decode,
    generate_subscription_keys,
    generate_vapid_key_pair,
    push_loggers_enabled,  # noqa: F401 — pytestmark usefixtures 로 사용
    settings_with_vapid,
)

pytestmark = pytest.mark.usefixtures("push_loggers_enabled")


def _target(endpoint: str = "https://fcm.googleapis.com/fcm/send/a") -> PushTarget:
    _, p256dh, auth = generate_subscription_keys()
    return PushTarget(id=uuid.uuid4(), endpoint=endpoint, p256dh=p256dh, auth=b64url(auth))


class _FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status
        self.headers: dict[str, str] = {}

    async def text(self) -> str:
        return "push service body https://fcm.googleapis.com/fcm/send/secret"


# ── T-PWA-42 페이로드 ─────────────────────────────────────────────────


class TestMeetingPayload:
    @pytest.mark.parametrize("kind", ["meeting.completed", "meeting.failed"])
    def test_t_pwa_42_payload_has_exactly_four_keys_and_fits_512_bytes(self, kind):
        """T-PWA-42: 키 집합 = {v,kind,meetingId,workspaceId} · 직렬화 ≤ 512B."""
        meeting_id = uuid.uuid4()
        workspace_id = uuid.uuid4()
        payload = build_meeting_payload(kind, meeting_id, workspace_id)

        decoded = json.loads(payload)
        assert set(decoded) == {"v", "kind", "meetingId", "workspaceId"}
        assert decoded == {
            "v": 1,
            "kind": kind,
            "meetingId": str(meeting_id),
            "workspaceId": str(workspace_id),
        }
        assert len(payload.encode("utf-8")) <= PUSH_PAYLOAD_MAX_BYTES

    def test_t_pwa_42_oversized_payload_is_rejected(self, monkeypatch):
        """T-PWA-42 회귀 가드: 페이로드가 상한을 넘으면 발송 전에 예외."""
        monkeypatch.setattr("src.push.service.PUSH_PAYLOAD_MAX_BYTES", 10)
        with pytest.raises(PushPayloadTooLargeError):
            build_meeting_payload("meeting.completed", uuid.uuid4(), uuid.uuid4())

    def test_push_target_repr_hides_endpoint_and_keys(self):
        """로그 금지 가드: PushTarget 을 실수로 찍어도 endpoint·keys 가 나오지 않는다."""
        target = _target("https://fcm.googleapis.com/fcm/send/capability-secret")
        text = repr(target)
        assert "capability-secret" not in text
        assert target.p256dh not in text
        assert target.auth not in text


# ── T-PWA-42 webpush_async 인자 ───────────────────────────────────────


class TestWebPushSenderArguments:
    @pytest.mark.asyncio
    async def test_t_pwa_42_webpush_async_arguments(self, monkeypatch):
        """T-PWA-42: ttl=86400 · timeout=10(None 아님) · Urgency normal · 호출마다 새 vapid_claims dict ·
        aiohttp ClientSession 1개 공유."""
        calls: list[dict] = []

        async def _fake_webpush_async(**kwargs):
            calls.append(kwargs)
            # 실제 라이브러리처럼 claims dict 를 변형한다 (aud·exp 주입)
            kwargs["vapid_claims"]["aud"] = "https://fcm.googleapis.com"
            kwargs["vapid_claims"]["exp"] = int(time.time()) + 3600
            return _FakeResponse(201)

        monkeypatch.setattr(sender_module, "webpush_async", _fake_webpush_async)
        targets = [_target("https://fcm.googleapis.com/fcm/send/a"), _target("https://fcm.googleapis.com/fcm/send/b")]
        payload = build_meeting_payload("meeting.completed", uuid.uuid4(), uuid.uuid4())
        sender = WebPushSender(vapid_private_key="private-key-value", vapid_subject=TEST_VAPID_SUBJECT)

        results = await sender.send_all(targets, payload)

        assert results == [
            SendResult(subscription_id=targets[0].id, status_code=201, error_type=None),
            SendResult(subscription_id=targets[1].id, status_code=201, error_type=None),
        ]
        assert len(calls) == 2
        for call, target in zip(calls, targets, strict=True):
            assert call["ttl"] == PUSH_TTL_SECONDS == 86400
            assert call["timeout"] == PUSH_TIMEOUT_SECONDS == 10
            assert call["timeout"] is not None
            assert call["headers"] == {"Urgency": "normal"}
            assert call["data"] == payload
            assert call["vapid_private_key"] == "private-key-value"
            assert call["vapid_claims"]["sub"] == TEST_VAPID_SUBJECT
            assert call["subscription_info"] == {
                "endpoint": target.endpoint,
                "keys": {"p256dh": target.p256dh, "auth": target.auth},
            }
            assert isinstance(call["aiohttp_session"], aiohttp.ClientSession)
        # 호출마다 서로 다른 dict 객체 (라이브러리 변형이 다음 호출로 새지 않는다)
        assert calls[0]["vapid_claims"] is not calls[1]["vapid_claims"]
        assert calls[0]["headers"] is not calls[1]["headers"]
        # ClientSession 은 한 번의 발송 전체가 1개를 공유
        assert calls[0]["aiohttp_session"] is calls[1]["aiohttp_session"]


# ── T-PWA-38 결과 분류 (실 sender → SendResult → DispatchReport) ─────────


class TestSendResultClassification:
    @pytest.mark.asyncio
    async def test_t_pwa_38_sender_maps_exceptions_to_status_and_type(self, monkeypatch):
        """T-PWA-38: WebPushException → 상태코드, 타임아웃 → None + 타입명, 성공 → 201. 순서 보존."""
        outcomes: dict[str, object] = {
            "https://fcm.googleapis.com/fcm/send/ok": _FakeResponse(201),
            "https://fcm.googleapis.com/fcm/send/gone": WebPushException(
                "Push failed: 410", response=_FakeResponse(410)
            ),
            "https://fcm.googleapis.com/fcm/send/slow": asyncio.TimeoutError(),
            "https://fcm.googleapis.com/fcm/send/rate": WebPushException(
                "Push failed: 429", response=_FakeResponse(429)
            ),
        }

        async def _fake_webpush_async(**kwargs):
            outcome = outcomes[kwargs["subscription_info"]["endpoint"]]
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

        monkeypatch.setattr(sender_module, "webpush_async", _fake_webpush_async)
        targets = [_target(endpoint) for endpoint in outcomes]
        sender = WebPushSender(vapid_private_key="k", vapid_subject=TEST_VAPID_SUBJECT)

        results = await sender.send_all(targets, "{}")

        assert [(r.subscription_id, r.status_code, r.error_type) for r in results] == [
            (targets[0].id, 201, None),
            (targets[1].id, 410, "WebPushException"),
            (targets[2].id, None, "TimeoutError"),
            (targets[3].id, 429, "WebPushException"),
        ]

    @pytest.mark.asyncio
    async def test_t_pwa_38_dispatch_report_splits_gone_from_other_failures(self, caplog):
        """T-PWA-38: 404·410 → gone_ids · 429·500·403·413 → failed · 201 → sent. warning 1줄(endpoint 미포함)."""
        statuses = {
            "https://fcm.googleapis.com/fcm/send/s404": 404,
            "https://fcm.googleapis.com/fcm/send/s410": 410,
            "https://fcm.googleapis.com/fcm/send/s429": 429,
            "https://fcm.googleapis.com/fcm/send/s500": 500,
            "https://fcm.googleapis.com/fcm/send/s403": 403,
            "https://fcm.googleapis.com/fcm/send/s413": 413,
            "https://fcm.googleapis.com/fcm/send/s201": 201,
        }
        targets = [_target(endpoint) for endpoint in statuses]
        dispatcher = PushDispatchService(FakeSender(status_by_endpoint=statuses))

        with caplog.at_level(logging.INFO):
            report = await dispatcher.dispatch_meeting_finished(
                targets, kind="meeting.completed", meeting_id=uuid.uuid4(), workspace_id=uuid.uuid4()
            )

        assert report.sent == 1
        assert report.failed == 4
        assert set(report.gone_ids) == {targets[0].id, targets[1].id}
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "403,413,429,500" in warnings[0].getMessage()
        assert all("fcm.googleapis.com" not in r.getMessage() for r in caplog.records)


# ── T-PWA-39 미구성 ───────────────────────────────────────────────────


class TestDispatcherConfiguration:
    @pytest.mark.parametrize("missing", ["public_key", "private_key", "subject"])
    def test_t_pwa_39_dispatcher_is_none_when_vapid_incomplete(self, monkeypatch, missing):
        """T-PWA-39: VAPID 1개라도 없음 → dispatcher None, sender 생성 0."""
        private_key, public_key = generate_vapid_key_pair()
        values = {"public_key": public_key, "private_key": private_key, "subject": TEST_VAPID_SUBJECT}
        values[missing] = None
        created: list[object] = []
        monkeypatch.setattr("src.push.service.get_settings", lambda: settings_with_vapid(**values))
        monkeypatch.setattr(
            "src.push.service.WebPushSender", lambda **kwargs: created.append(kwargs)
        )

        assert create_push_dispatcher() is None
        assert created == []


# ── pwa.md §5.7 VAPID 왕복 — 설정 키로 서명 → 설정 공개키로 검증 ─────────


def _verify_es256_jwt(token: str, public_key_b64url: str) -> dict:
    """JWT(ES256) 서명을 주어진 공개키로 검증하고 claims 를 돌려준다 (검증 실패 시 InvalidSignature)."""
    header_b64, claims_b64, signature_b64 = token.split(".")
    signature = b64url_decode(signature_b64)
    assert len(signature) == 64
    der = encode_dss_signature(
        int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
    )
    public_key = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(), b64url_decode(public_key_b64url)
    )
    public_key.verify(der, f"{header_b64}.{claims_b64}".encode(), ec.ECDSA(hashes.SHA256()))
    assert json.loads(b64url_decode(header_b64))["alg"] == "ES256"
    return json.loads(b64url_decode(claims_b64))


class TestVapidRoundTrip:
    @pytest.mark.asyncio
    async def test_vapid_raw_key_signs_and_settings_public_key_verifies(self, monkeypatch, caplog):
        """§5.7: raw base64url 32B 개인키(설정) → pywebpush 실발송 → Authorization 서명을 설정 공개키로 검증.

        로컬 aiohttp 서버가 실제 POST 를 받는다 — VAPID 헤더·TTL·Urgency·aes128gcm 본문까지 실측한다.
        """
        from src.core.config import Settings

        private_key, public_key = generate_vapid_key_pair()
        assert (len(private_key), len(public_key)) == (43, 87)

        # 설정 경로 그대로: env → Settings (형식 경고 0) → create_push_dispatcher
        for name, value in {
            "DATABASE_URL": "postgresql://fake:fake@localhost:5432/fake",
            "R2_ACCOUNT_ID": "fake",
            "R2_ACCESS_KEY_ID": "fake",
            "R2_SECRET_ACCESS_KEY": "fake",
            "R2_BUCKET_NAME": "fake",
            "GEMINI_API_KEY": "fake",
            "OPENAI_API_KEY": "fake",
            "VAPID_PUBLIC_KEY": public_key,
            "VAPID_PRIVATE_KEY": private_key,
            "VAPID_SUBJECT": TEST_VAPID_SUBJECT,
        }.items():
            monkeypatch.setenv(name, value)
        with caplog.at_level(logging.WARNING, logger="src.core.config"):
            settings = Settings(_env_file=None)
        assert [r for r in caplog.records if "VAPID" in r.getMessage()] == []
        monkeypatch.setattr("src.push.service.get_settings", lambda: settings)

        captured: dict = {}

        async def _push_endpoint(request: web.Request) -> web.Response:
            captured["headers"] = dict(request.headers)
            captured["body"] = await request.read()
            return web.Response(status=201)

        app = web.Application()
        app.router.add_post("/push/{token}", _push_endpoint)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        try:
            port = site._server.sockets[0].getsockname()[1]  # noqa: SLF001 — 테스트 서버 포트 조회
            receiver, p256dh, auth = generate_subscription_keys()
            target = PushTarget(
                id=uuid.uuid4(),
                endpoint=f"http://127.0.0.1:{port}/push/device",
                p256dh=p256dh,
                auth=b64url(auth),
            )
            meeting_id, workspace_id = uuid.uuid4(), uuid.uuid4()

            dispatcher = create_push_dispatcher()
            assert dispatcher is not None
            report = await dispatcher.dispatch_meeting_finished(
                [target], kind="meeting.completed", meeting_id=meeting_id, workspace_id=workspace_id
            )
        finally:
            await runner.cleanup()

        assert report.sent == 1 and report.failed == 0 and report.gone_ids == ()

        headers = {k.lower(): v for k, v in captured["headers"].items()}
        assert headers["ttl"] == "86400"
        assert headers["urgency"] == "normal"
        assert headers["content-encoding"] == "aes128gcm"

        # Authorization: "vapid t=<jwt>,k=<공개키>" (RFC 8292)
        scheme, params = headers["authorization"].split(" ", 1)
        assert scheme == "vapid"
        parts = dict(item.split("=", 1) for item in params.split(","))
        assert parts["k"] == public_key
        claims = _verify_es256_jwt(parts["t"], public_key)
        assert claims["sub"] == TEST_VAPID_SUBJECT
        assert claims["aud"] == f"http://127.0.0.1:{port}"
        assert claims["exp"] > time.time()

        # 대조군 — 다른 키쌍의 공개키로는 검증이 실패해야 위 검증이 공허하지 않다
        _, unrelated_public_key = generate_vapid_key_pair()
        with pytest.raises(InvalidSignature):
            _verify_es256_jwt(parts["t"], unrelated_public_key)

        # 본문은 수신자 키로만 풀린다 — 풀면 §5.4 페이로드 그대로
        plaintext = http_ece.decrypt(
            captured["body"], private_key=receiver, auth_secret=auth, version="aes128gcm"
        )
        assert json.loads(plaintext) == {
            "v": 1,
            "kind": "meeting.completed",
            "meetingId": str(meeting_id),
            "workspaceId": str(workspace_id),
        }
