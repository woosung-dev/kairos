# T-BE-PERF Top 1 fix: verify_clerk_token in-process TTL cache 검증
"""verify_clerk_token 의 JWT claims 캐시 — hit / miss / TTL 만료 / maxsize 회전."""
import time
from unittest.mock import MagicMock, patch

import pytest

from src.auth import dependencies as deps


@pytest.fixture(autouse=True)
def _reset_cache():
    """매 테스트 격리 — 캐시 초기화."""
    deps._JWT_CLAIMS_CACHE.clear()
    yield
    deps._JWT_CLAIMS_CACHE.clear()


@pytest.mark.asyncio
async def test_jwt_cache_hit_on_second_call(monkeypatch):
    """동일 token 2회 호출 — 두번째는 PyJWKClient + jwt.decode 우회."""
    fake_claims = {"sub": "user_abc"}
    decode_calls = {"n": 0}

    def _fake_decode(*args, **kwargs):
        decode_calls["n"] += 1
        return fake_claims

    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = MagicMock(key="dummy_key")

    monkeypatch.setattr(deps, "_get_jwks_client", lambda: mock_jwks)
    monkeypatch.setattr(deps.jwt, "decode", _fake_decode)

    token = "Bearer dummy.jwt.token"
    r1 = await deps.verify_clerk_token(authorization=token)
    r2 = await deps.verify_clerk_token(authorization=token)
    assert r1 == r2 == {"sub": "user_abc"}
    # 첫 호출만 decode — 두번째는 캐시 hit
    assert decode_calls["n"] == 1
    assert mock_jwks.get_signing_key_from_jwt.call_count == 1


@pytest.mark.asyncio
async def test_jwt_cache_miss_on_different_token(monkeypatch):
    """다른 token 은 캐시 hit 안 됨 — 각각 decode 호출."""
    fake_claims = {"sub": "user_x"}
    decode_calls = {"n": 0}

    def _fake_decode(*args, **kwargs):
        decode_calls["n"] += 1
        return fake_claims

    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = MagicMock(key="dummy_key")

    monkeypatch.setattr(deps, "_get_jwks_client", lambda: mock_jwks)
    monkeypatch.setattr(deps.jwt, "decode", _fake_decode)

    await deps.verify_clerk_token(authorization="Bearer token.A")
    await deps.verify_clerk_token(authorization="Bearer token.B")
    assert decode_calls["n"] == 2


@pytest.mark.asyncio
async def test_jwt_cache_expires(monkeypatch):
    """TTL 만료 후 재검증."""
    decode_calls = {"n": 0}

    def _fake_decode(*args, **kwargs):
        decode_calls["n"] += 1
        return {"sub": "user_y"}

    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = MagicMock(key="dummy_key")
    monkeypatch.setattr(deps, "_get_jwks_client", lambda: mock_jwks)
    monkeypatch.setattr(deps.jwt, "decode", _fake_decode)

    # TTL 0 — 즉시 만료
    monkeypatch.setattr(deps, "_JWT_CACHE_TTL_SEC", 0.0)

    token = "Bearer token.expiring"
    await deps.verify_clerk_token(authorization=token)
    # 한 tick 대기 (epoch 진행 보장)
    time.sleep(0.01)
    await deps.verify_clerk_token(authorization=token)
    # 두 호출 모두 decode 통과 (캐시 만료)
    assert decode_calls["n"] == 2


@pytest.mark.asyncio
async def test_jwt_cache_invalid_token_not_cached(monkeypatch):
    """ExpiredSignatureError / InvalidTokenError 는 401 발생 + 캐시 미저장."""
    from fastapi import HTTPException

    def _fake_decode(*args, **kwargs):
        raise deps.jwt.InvalidTokenError("invalid")

    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = MagicMock(key="dummy_key")
    monkeypatch.setattr(deps, "_get_jwks_client", lambda: mock_jwks)
    monkeypatch.setattr(deps.jwt, "decode", _fake_decode)

    with pytest.raises(HTTPException) as exc_info:
        await deps.verify_clerk_token(authorization="Bearer bad.token")
    assert exc_info.value.status_code == 401
    # 캐시에 아무 것도 저장되지 않아야 함
    assert len(deps._JWT_CLAIMS_CACHE) == 0


@pytest.mark.asyncio
async def test_jwt_cache_maxsize_eviction(monkeypatch):
    """maxsize 초과 시 가장 오래된 entry evict (만료된 것 우선)."""

    def _fake_decode(*args, **kwargs):
        return {"sub": "user_z"}

    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = MagicMock(key="dummy_key")
    monkeypatch.setattr(deps, "_get_jwks_client", lambda: mock_jwks)
    monkeypatch.setattr(deps.jwt, "decode", _fake_decode)

    # maxsize 3 으로 줄여서 회전 확인
    monkeypatch.setattr(deps, "_JWT_CACHE_MAX_SIZE", 3)

    for i in range(5):
        await deps.verify_clerk_token(authorization=f"Bearer tok.{i}")

    assert len(deps._JWT_CLAIMS_CACHE) <= 3
