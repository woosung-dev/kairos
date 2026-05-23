# Clerk webhook /api/v1/users/sync 회귀 4 case — Svix 서명 검증 + sync 로직
"""Sprint 27b Task 1.5 — ADR-024 회수 옵션 5단계 §5.

회귀 4 case:
1. 정상 user.created — Svix 서명 OK + AuthService.sync_user(clerk_id=...) 호출
2. 정상 user.updated — Svix 서명 OK + 동일 호출 (service 가 upsert 처리)
3. 잘못된 서명 — 401 INVALID_SIGNATURE + service 미호출 (DB write 차단)
4. stale timestamp (1시간 전) — 401 STALE_TIMESTAMP + service 미호출

Sprint 25 sentinel test `test_auth_sync_disabled.py` 는 본 sprint 에서 삭제 (obsolete).
"""
import base64
import json
import secrets
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from svix.webhooks import Webhook

from src.auth.dependencies import get_auth_service
from src.auth.service import AuthService
from src.common.database import get_async_session
from src.core.config import get_settings
from src.main import app

_TEST_SECRET = "whsec_" + base64.b64encode(secrets.token_bytes(32)).decode()


def _sign_payload(
    payload_dict: dict,
    *,
    age_seconds: int = 0,
) -> tuple[bytes, dict[str, str]]:
    """Svix sign helper — 정상 / stale 변형."""
    wh = Webhook(_TEST_SECRET)
    msg_id = "msg_test_" + secrets.token_hex(8)
    ts_int = int(datetime.now(tz=timezone.utc).timestamp()) - age_seconds
    ts_dt = datetime.fromtimestamp(ts_int, tz=timezone.utc)
    payload_str = json.dumps(payload_dict)
    sig = wh.sign(msg_id, ts_dt, payload_str)
    headers = {
        "svix-id": msg_id,
        "svix-timestamp": str(ts_int),
        "svix-signature": sig,
    }
    return payload_str.encode(), headers


@pytest_asyncio.fixture
async def mock_service():
    """AuthService mock — sync_user 호출 spy."""
    service = AsyncMock(spec=AuthService)
    service.sync_user = AsyncMock(return_value=None)
    return service


@pytest_asyncio.fixture
async def client(mock_service):
    """Test client — Svix secret override + AuthService mock + DB mock."""
    # config override: clerk_webhook_secret 만 test secret 으로 교체.
    # 다른 필드는 get_settings() 기존값 (lru_cache 캐시) 그대로.
    original_settings = get_settings()
    # SecretStr 은 immutable — model_copy 로 새 instance.
    test_settings = original_settings.model_copy(
        update={"clerk_webhook_secret": SecretStr(_TEST_SECRET)}
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_auth_service] = lambda: mock_service
    app.dependency_overrides[get_async_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_user_created_signed_ok(client, mock_service):
    """Case 1 — 정상 user.created payload + 유효 서명 → 200 + sync_user 호출."""
    payload = {
        "type": "user.created",
        "data": {
            "id": "user_clerk_new",
            "email_addresses": [{"email_address": "new@kairos.test"}],
            "first_name": "신규",
            "last_name": "사용자",
        },
    }
    body, headers = _sign_payload(payload)
    response = await client.post("/api/v1/users/sync", content=body, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {"synced": True}
    mock_service.sync_user.assert_awaited_once()
    call_kwargs = mock_service.sync_user.await_args.kwargs
    assert call_kwargs["clerk_id"] == "user_clerk_new"
    assert call_kwargs["email"] == "new@kairos.test"
    assert call_kwargs["display_name"] == "신규 사용자"


@pytest.mark.asyncio
async def test_sync_user_updated_signed_ok(client, mock_service):
    """Case 2 — 정상 user.updated payload + 유효 서명 → 200 + sync_user 호출 (upsert)."""
    payload = {
        "type": "user.updated",
        "data": {
            "id": "user_clerk_existing",
            "email_addresses": [{"email_address": "updated@kairos.test"}],
            "first_name": "갱신",
            "last_name": "사용자",
        },
    }
    body, headers = _sign_payload(payload)
    response = await client.post("/api/v1/users/sync", content=body, headers=headers)
    assert response.status_code == 200
    mock_service.sync_user.assert_awaited_once()
    assert mock_service.sync_user.await_args.kwargs["clerk_id"] == "user_clerk_existing"


@pytest.mark.asyncio
async def test_sync_user_invalid_signature_blocked(client, mock_service):
    """Case 3 — 잘못된 서명 → 401 INVALID_SIGNATURE + DB write 차단 (service 미호출)."""
    payload = {"type": "user.created", "data": {"id": "user_attacker"}}
    body, headers = _sign_payload(payload)
    headers["svix-signature"] = "v1,AAAAbogusAAAA="  # 위조 서명
    response = await client.post("/api/v1/users/sync", content=body, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "INVALID_SIGNATURE"
    mock_service.sync_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_user_stale_timestamp_blocked(client, mock_service):
    """Case 4 — 1시간 전 timestamp → 401 STALE_TIMESTAMP + DB write 차단."""
    payload = {"type": "user.created", "data": {"id": "user_replay"}}
    body, headers = _sign_payload(payload, age_seconds=3600)
    response = await client.post("/api/v1/users/sync", content=body, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "STALE_TIMESTAMP"
    mock_service.sync_user.assert_not_awaited()
