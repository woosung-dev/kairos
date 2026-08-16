# Sprint 27e BUG-S27e-SEC-3 회귀 가드 — JWT issuer/audience 명시 검증.
"""auth/dependencies.py:verify_clerk_token 의 JWT 검증 호출 시 issuer + audience 가
명시 전달되는지 검증한다. ADR-024 Clerk Production cutover 직격 결함 fix 의 회귀 가드.

이전: options={"verify_aud": False} + issuer 미전달 → cross-account JWT 통과 risk.
이후: settings.clerk_jwt_issuer 강제 + audience 일치 (settings.clerk_jwt_audience 명시 시).
"""
import time
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import HTTPException


def _setup_env_for_test(monkeypatch):
    """Settings 가 부팅되도록 필수 env 채움."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", "whsec_xxx")
    monkeypatch.setenv("R2_ACCOUNT_ID", "test")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("R2_BUCKET_NAME", "test")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-xxx")
    monkeypatch.setenv("APP_ENV", "test")
    # 본 test 의 핵심 — issuer 명시
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://test-instance.clerk.accounts.dev")


@pytest.mark.asyncio
async def test_verify_clerk_token_passes_issuer_to_jwt_decode(monkeypatch):
    """jwt.decode 호출 시 issuer 인자가 settings.clerk_jwt_issuer 로 전달."""
    _setup_env_for_test(monkeypatch)

    # 격리: lru_cache + JWKS singleton + JWT claim cache reset
    from src.core import config as cfg_mod
    cfg_mod.get_settings.cache_clear()
    from src.auth import dependencies as deps
    deps._jwks_client = None
    deps._JWT_CLAIMS_CACHE.clear()

    # PyJWKClient 와 jwt.decode 를 mock — 실 RSA 검증 우회.
    mock_signing_key = MagicMock(key="fake-key")
    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key
    monkeypatch.setattr(jwt, "PyJWKClient", lambda *a, **kw: mock_jwks)

    decode_calls = {}

    def _mock_decode(token, key, **kwargs):
        decode_calls["kwargs"] = kwargs
        return {"sub": "user_test_123", "exp": time.time() + 60}

    monkeypatch.setattr(jwt, "decode", _mock_decode)

    result = await deps.verify_clerk_token(authorization="Bearer fake.jwt.token")

    assert result["sub"] == "user_test_123"
    assert decode_calls["kwargs"].get("issuer") == "https://test-instance.clerk.accounts.dev"
    assert decode_calls["kwargs"].get("algorithms") == ["RS256"]


@pytest.mark.asyncio
async def test_verify_clerk_token_rejects_wrong_issuer(monkeypatch):
    """jwt.InvalidIssuerError → 401 + '발급자' 메시지."""
    _setup_env_for_test(monkeypatch)
    from src.core import config as cfg_mod
    cfg_mod.get_settings.cache_clear()
    from src.auth import dependencies as deps
    deps._jwks_client = None
    deps._JWT_CLAIMS_CACHE.clear()

    mock_signing_key = MagicMock(key="fake-key")
    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key
    monkeypatch.setattr(jwt, "PyJWKClient", lambda *a, **kw: mock_jwks)

    def _raise_issuer(token, key, **kwargs):
        raise jwt.InvalidIssuerError("Invalid issuer")

    monkeypatch.setattr(jwt, "decode", _raise_issuer)

    with pytest.raises(HTTPException) as exc:
        await deps.verify_clerk_token(authorization="Bearer fake.jwt.token")
    assert exc.value.status_code == 401
    assert "발급자" in exc.value.detail


@pytest.mark.asyncio
async def test_verify_clerk_token_passes_audience_when_configured(monkeypatch):
    """settings.clerk_jwt_audience 가 설정되면 jwt.decode 에 audience 전달."""
    _setup_env_for_test(monkeypatch)
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "kairos-api")

    from src.core import config as cfg_mod
    cfg_mod.get_settings.cache_clear()
    from src.auth import dependencies as deps
    deps._jwks_client = None
    deps._JWT_CLAIMS_CACHE.clear()

    mock_signing_key = MagicMock(key="fake-key")
    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key
    monkeypatch.setattr(jwt, "PyJWKClient", lambda *a, **kw: mock_jwks)

    decode_calls = {}

    def _mock_decode(token, key, **kwargs):
        decode_calls["kwargs"] = kwargs
        return {"sub": "user_aud_test", "exp": time.time() + 60}

    monkeypatch.setattr(jwt, "decode", _mock_decode)

    await deps.verify_clerk_token(authorization="Bearer fake.jwt.token")
    assert decode_calls["kwargs"].get("audience") == "kairos-api"
    # audience 설정 시 verify_aud=False 분기 안 탐
    assert "options" not in decode_calls["kwargs"]


@pytest.mark.asyncio
async def test_verify_clerk_token_skips_aud_when_unset(monkeypatch):
    """settings.clerk_jwt_audience 가 None 이면 verify_aud=False 로 skip — 명시 design."""
    _setup_env_for_test(monkeypatch)
    monkeypatch.delenv("CLERK_JWT_AUDIENCE", raising=False)

    from src.core import config as cfg_mod
    cfg_mod.get_settings.cache_clear()
    from src.auth import dependencies as deps
    deps._jwks_client = None
    deps._JWT_CLAIMS_CACHE.clear()

    mock_signing_key = MagicMock(key="fake-key")
    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key
    monkeypatch.setattr(jwt, "PyJWKClient", lambda *a, **kw: mock_jwks)

    decode_calls = {}

    def _mock_decode(token, key, **kwargs):
        decode_calls["kwargs"] = kwargs
        return {"sub": "user_no_aud", "exp": time.time() + 60}

    monkeypatch.setattr(jwt, "decode", _mock_decode)

    await deps.verify_clerk_token(authorization="Bearer fake.jwt.token")
    assert decode_calls["kwargs"].get("audience") is None or "audience" not in decode_calls["kwargs"]
    assert decode_calls["kwargs"].get("options") == {"verify_aud": False}
