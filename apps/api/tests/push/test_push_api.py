# PWA PR-2 웹 푸시 API-001~003 (T-PWA-30·31·32·34) — TestContainers 통합
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import func, select

from src.auth.models import User
from src.push.models import PushSubscription
from tests.fixtures.push import (
    TEST_VAPID_SUBJECT,
    generate_vapid_key_pair,
    settings_with_vapid,
    valid_subscription_keys,
)

pytestmark = pytest.mark.integration

BASE = "/api/v1/users/me"
FCM_ENDPOINT = "https://fcm.googleapis.com/fcm/send/device-a"


@pytest_asyncio.fixture
async def other_user(integration_session):
    user = User(
        auth_user_id="test_ba_push_other",
        display_name="다른 사용자",
        email="push_other@kairos.test",
    )
    integration_session.add(user)
    await integration_session.flush()
    return user


@pytest_asyncio.fixture
async def push_client(integration_session, auth_user):
    """get_current_user + get_async_session override — 인증 사용자는 auth_user (테스트에서 교체 가능)."""
    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session
    from src.main import app

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_async_session] = lambda: integration_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def anonymous_client(integration_session):
    """인증 override 없음 — 실제 verify_bearer_token 이 Authorization 헤더를 검사한다."""
    from src.common.database import get_async_session
    from src.main import app

    app.dependency_overrides[get_async_session] = lambda: integration_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _act_as(user: User) -> None:
    from src.auth.dependencies import get_current_user
    from src.main import app

    app.dependency_overrides[get_current_user] = lambda: user


async def _rows(session) -> list[tuple]:
    """ORM identity map 을 거치지 않는 컬럼 조회 (Core upsert 결과를 그대로 본다)."""
    result = await session.execute(
        select(
            PushSubscription.id,
            PushSubscription.user_id,
            PushSubscription.endpoint,
            PushSubscription.p256dh,
            PushSubscription.auth,
            PushSubscription.created_at,
            PushSubscription.updated_at,
        )
    )
    return list(result.all())


# ── T-PWA-30 API-001 config ───────────────────────────────────────────


class TestPushConfig:
    @pytest.mark.asyncio
    async def test_t_pwa_30_enabled_when_all_three_vapid_settings_present(
        self, push_client, monkeypatch
    ):
        """T-PWA-30: VAPID 3개 설정 → isEnabled=true + 87자 공개키."""
        private_key, public_key = generate_vapid_key_pair()
        monkeypatch.setattr(
            "src.push.service.get_settings",
            lambda: settings_with_vapid(
                public_key=public_key, private_key=private_key, subject=TEST_VAPID_SUBJECT
            ),
        )
        resp = await push_client.get(f"{BASE}/push-config")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"isEnabled": True, "vapidPublicKey": public_key}
        assert len(body["vapidPublicKey"]) == 87

    @pytest.mark.asyncio
    @pytest.mark.parametrize("missing", ["public_key", "private_key", "subject"])
    async def test_t_pwa_30_disabled_when_any_vapid_setting_missing(
        self, push_client, monkeypatch, missing
    ):
        """T-PWA-30: 1개라도 없음 → {isEnabled:false, vapidPublicKey:null} 200."""
        private_key, public_key = generate_vapid_key_pair()
        values = {
            "public_key": public_key,
            "private_key": private_key,
            "subject": TEST_VAPID_SUBJECT,
        }
        values[missing] = None
        monkeypatch.setattr(
            "src.push.service.get_settings", lambda: settings_with_vapid(**values)
        )
        resp = await push_client.get(f"{BASE}/push-config")
        assert resp.status_code == 200
        assert resp.json() == {"isEnabled": False, "vapidPublicKey": None}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("GET", f"{BASE}/push-config"),
            ("PUT", f"{BASE}/push-subscriptions"),
            ("DELETE", f"{BASE}/push-subscriptions/{uuid.uuid4()}"),
        ],
    )
    async def test_t_pwa_30_requires_bearer_token(self, anonymous_client, method, path):
        """T-PWA-30 (+API-002·003): 토큰 없음 → 401."""
        kwargs = {}
        if method == "PUT":
            kwargs["json"] = {"endpoint": FCM_ENDPOINT, "keys": valid_subscription_keys()}
        resp = await anonymous_client.request(method, path, **kwargs)
        assert resp.status_code == 401


# ── T-PWA-31 API-002 upsert·rebind ────────────────────────────────────


class TestPushSubscriptionUpsert:
    @pytest.mark.asyncio
    async def test_t_pwa_31_upsert_keeps_id_and_rebinds_to_current_user(
        self, push_client, integration_session, auth_user, other_user
    ):
        """T-PWA-31: 신규 → 같은 사용자 재전송(같은 id·keys/updated_at 갱신) → 다른 사용자(같은 id·rebind) · 행 1."""
        first_keys = valid_subscription_keys()
        resp = await push_client.put(
            f"{BASE}/push-subscriptions",
            json={"endpoint": FCM_ENDPOINT, "keys": first_keys, "expirationTime": None},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == {"id"}
        subscription_id = uuid.UUID(body["id"])

        rows = await _rows(integration_session)
        assert len(rows) == 1
        row_id, user_id, endpoint, p256dh, auth, created_at, first_updated_at = rows[0]
        assert row_id == subscription_id
        assert user_id == auth_user.id
        assert (endpoint, p256dh, auth) == (FCM_ENDPOINT, first_keys["p256dh"], first_keys["auth"])

        # 같은 사용자 · 같은 endpoint · 새 keys → 같은 id, keys·updated_at 갱신
        second_keys = valid_subscription_keys()
        resp = await push_client.put(
            f"{BASE}/push-subscriptions",
            json={"endpoint": FCM_ENDPOINT, "keys": second_keys},
        )
        assert resp.status_code == 200
        assert resp.json() == {"id": str(subscription_id)}
        rows = await _rows(integration_session)
        assert len(rows) == 1
        _, user_id, _, p256dh, auth, created_again, second_updated_at = rows[0]
        assert user_id == auth_user.id
        assert (p256dh, auth) == (second_keys["p256dh"], second_keys["auth"])
        assert created_again == created_at
        assert second_updated_at > first_updated_at

        # 다른 사용자 · 같은 endpoint (같은 기기 계정 전환) → 같은 id, user_id 가 그 사용자로
        _act_as(other_user)
        third_keys = valid_subscription_keys()
        resp = await push_client.put(
            f"{BASE}/push-subscriptions",
            json={"endpoint": FCM_ENDPOINT, "keys": third_keys},
        )
        assert resp.status_code == 200
        assert resp.json() == {"id": str(subscription_id)}
        rows = await _rows(integration_session)
        assert len(rows) == 1
        _, user_id, _, p256dh, _, _, third_updated_at = rows[0]
        assert user_id == other_user.id
        assert p256dh == third_keys["p256dh"]
        assert third_updated_at > second_updated_at

        count = (
            await integration_session.execute(select(func.count()).select_from(PushSubscription))
        ).scalar_one()
        assert count == 1


# ── T-PWA-32 API-002 검증 (SSRF·형식) ──────────────────────────────────

_LONG_PREFIX = "https://fcm.googleapis.com/fcm/send/"


class TestPushSubscriptionValidation:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "endpoint",
        [
            "http://fcm.googleapis.com/fcm/send/x",
            "https://169.254.169.254/",
            "https://10.0.0.1/",
            "https://evil.example/",
            "https://fcm.googleapis.com:8443/",
            "https://u:p@fcm.googleapis.com/",
            _LONG_PREFIX + "x" * (2049 - len(_LONG_PREFIX)),
            # 추가 가드 — allowlist 의미(정확 일치 vs 접미사)와 파서 차이
            "https://[::1]/x",
            "https://evilfcm.googleapis.com/x",
            "https://fcm.googleapis.com.evil.example/x",
            "https://notpush.apple.com/x",
            "https://push.apple.com/x",
            "https://fcm.googleapis.com\\@evil.example/x",
            "https://fcm.googleapis.com/fcm send/x",
            "fcm.googleapis.com/fcm/send/x",
        ],
    )
    async def test_t_pwa_32_rejects_unsafe_endpoint(self, push_client, integration_session, endpoint):
        """T-PWA-32: http · IP 리터럴 · allowlist 밖 · 포트 · userinfo · 길이 2049 → 422, 행 0."""
        resp = await push_client.put(
            f"{BASE}/push-subscriptions",
            json={"endpoint": endpoint, "keys": valid_subscription_keys()},
        )
        assert resp.status_code == 422
        assert await _rows(integration_session) == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "endpoint_json",
        [
            # 허용 호스트 + 비ASCII 경로 — 2048자(=6072바이트 UTF-8)는 btree 인덱스 행 한도를 넘겨 500 이었다
            '"' + _LONG_PREFIX + "한" * (2048 - len(_LONG_PREFIX)) + '"',
            '"https://web.push.apple.com/알림"',
            # JSON lone surrogate — DB 인코딩에서 500 이었다
            '"https://fcm.googleapis.com/fcm/send/\\ud800"',
            # IDN 호스트 — 접미사 allowlist 는 통과하지만 HTTP 클라이언트가 punycode 로 바꿔 다른 호스트가 된다
            '"https://ü.push.apple.com/x"',
        ],
        ids=["non-ascii-path-2048", "non-ascii-path", "lone-surrogate", "idn-host"],
    )
    async def test_t_pwa_32_rejects_non_ascii_endpoint(
        self, push_client, integration_session, endpoint_json
    ):
        """T-PWA-32 (EVAL-P2-1 D1): 비ASCII endpoint → 500 이 아니라 422, 행 0.

        본문은 원문 JSON 으로 보낸다 — httpx `json=` 은 lone surrogate 를 UTF-8 로 인코딩하지 못한다.
        """
        keys = valid_subscription_keys()
        body = (
            '{"endpoint": ' + endpoint_json
            + f', "keys": {{"p256dh": "{keys["p256dh"]}", "auth": "{keys["auth"]}"}}}}'
        )
        resp = await push_client.put(
            f"{BASE}/push-subscriptions",
            content=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422, resp.text
        assert await _rows(integration_session) == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "keys",
        [
            # p256dh 디코드 ≠ 65
            {"p256dh": "BAAA", "auth": "AAAAAAAAAAAAAAAAAAAAAA"},
            # p256dh 65바이트지만 0x04 로 시작하지 않음
            {"p256dh": "Aw" + "A" * 85, "auth": "AAAAAAAAAAAAAAAAAAAAAA"},
            # p256dh base64url 알파벳 밖
            {"p256dh": "B" + "+" * 86, "auth": "AAAAAAAAAAAAAAAAAAAAAA"},
            # auth 디코드 ≠ 16
            {"p256dh": None, "auth": "AAAAAAAAAAAAAAAAAAAA"},
            {"p256dh": None, "auth": "AAAAAAAAAAAAAAAAAAAAAAAA"},
        ],
    )
    async def test_t_pwa_32_rejects_malformed_keys(self, push_client, integration_session, keys):
        """T-PWA-32: p256dh 디코드≠65 · auth 디코드≠16 → 422."""
        body_keys = dict(keys)
        if body_keys["p256dh"] is None:
            body_keys["p256dh"] = valid_subscription_keys()["p256dh"]
        resp = await push_client.put(
            f"{BASE}/push-subscriptions",
            json={"endpoint": FCM_ENDPOINT, "keys": body_keys},
        )
        assert resp.status_code == 422
        assert await _rows(integration_session) == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "endpoint",
        [
            "https://fcm.googleapis.com/fcm/send/x",
            "https://updates.push.services.mozilla.com/wpush/v2/x",
            "https://web.push.apple.com/x",
            # ★allowlist 문자열 검증일 뿐 — Edge(WNS) 실제 endpoint 형식·발송은 미검증 (pwa.md §5.2)
            "https://wns2-par02p.notify.windows.com/w/?token=x",
            "https://android.googleapis.com/gcm/send/x",
            "https://fcm.googleapis.com:443/fcm/send/x",
            "HTTPS://FCM.googleapis.com/fcm/send/x",
            _LONG_PREFIX + "x" * (2048 - len(_LONG_PREFIX)),
        ],
    )
    async def test_t_pwa_32_accepts_known_push_services(self, push_client, endpoint):
        """T-PWA-32: 주요 푸시 서비스 4종 호스트 + 포트 443 + 길이 2048 → 200."""
        resp = await push_client.put(
            f"{BASE}/push-subscriptions",
            json={"endpoint": endpoint, "keys": valid_subscription_keys()},
        )
        assert resp.status_code == 200, resp.text
        uuid.UUID(resp.json()["id"])


# ── T-PWA-34 API-003 삭제 ─────────────────────────────────────────────


class TestPushSubscriptionDelete:
    @pytest.mark.asyncio
    async def test_t_pwa_34_delete_own_other_missing_and_invalid(
        self, push_client, integration_session, auth_user, other_user
    ):
        """T-PWA-34: 본인 id → 204+삭제 · 타인 id → 204+유지 · 없는 id → 204 · UUID 아님 → 422."""
        own = await push_client.put(
            f"{BASE}/push-subscriptions",
            json={"endpoint": FCM_ENDPOINT, "keys": valid_subscription_keys()},
        )
        own_id = own.json()["id"]

        _act_as(other_user)
        others = await push_client.put(
            f"{BASE}/push-subscriptions",
            json={
                "endpoint": "https://fcm.googleapis.com/fcm/send/device-b",
                "keys": valid_subscription_keys(),
            },
        )
        other_id = others.json()["id"]

        _act_as(auth_user)
        # 타인 id → 204 + 행 유지
        resp = await push_client.delete(f"{BASE}/push-subscriptions/{other_id}")
        assert resp.status_code == 204
        assert resp.content == b""
        ids = {str(row[0]) for row in await _rows(integration_session)}
        assert ids == {own_id, other_id}

        # 없는 id → 204
        resp = await push_client.delete(f"{BASE}/push-subscriptions/{uuid.uuid4()}")
        assert resp.status_code == 204

        # 본인 id → 204 + 삭제
        resp = await push_client.delete(f"{BASE}/push-subscriptions/{own_id}")
        assert resp.status_code == 204
        ids = {str(row[0]) for row in await _rows(integration_session)}
        assert ids == {other_id}

        # 같은 id 재삭제 → 여전히 204 (멱등)
        resp = await push_client.delete(f"{BASE}/push-subscriptions/{own_id}")
        assert resp.status_code == 204

        # UUID 아님 → 422
        resp = await push_client.delete(f"{BASE}/push-subscriptions/not-a-uuid")
        assert resp.status_code == 422
