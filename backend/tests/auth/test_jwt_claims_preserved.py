# Sprint 29 R1 (auth-claim) 회귀 가드 — verify_clerk_token 이 name/email claim 보존.
"""이전엔 result={"sub": ...} 만 남겨 lazy seed 의 claims.get("name"/"email") 이 항상
fallback("사용자"/"")로 동작 → 신규 user 이름/이메일 누락. 이제 claim 이 있으면 보존.
"""
import time
from unittest.mock import MagicMock

import jwt
import pytest


def _setup_env(monkeypatch):
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
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://test-instance.clerk.accounts.dev")


def _mock_jwks(monkeypatch):
    mock_signing_key = MagicMock(key="fake-key")
    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = mock_signing_key
    monkeypatch.setattr(jwt, "PyJWKClient", lambda *a, **kw: mock_jwks)


def _fresh_deps():
    from src.core import config as cfg_mod
    cfg_mod.get_settings.cache_clear()
    from src.auth import dependencies as deps
    deps._jwks_client = None
    deps._JWT_CLAIMS_CACHE.clear()
    return deps


@pytest.mark.asyncio
async def test_verify_clerk_token_preserves_name_email(monkeypatch):
    """name/email claim 이 있으면 result 에 보존돼 lazy seed 가 사용한다."""
    _setup_env(monkeypatch)
    _mock_jwks(monkeypatch)
    deps = _fresh_deps()
    monkeypatch.setattr(
        jwt,
        "decode",
        lambda token, key, **kw: {
            "sub": "user_abc",
            "name": "홍길동",
            "email": "hong@example.com",
            "exp": time.time() + 60,
        },
    )

    result = await deps.verify_clerk_token(authorization="Bearer fake.jwt.token")

    assert result["sub"] == "user_abc"
    assert result["name"] == "홍길동"
    assert result["email"] == "hong@example.com"


@pytest.mark.asyncio
async def test_verify_clerk_token_omits_absent_name_email(monkeypatch):
    """name/email claim 부재 시 result 에 키 없음 — KeyError 없이 caller fallback 유지."""
    _setup_env(monkeypatch)
    _mock_jwks(monkeypatch)
    deps = _fresh_deps()
    monkeypatch.setattr(
        jwt,
        "decode",
        lambda token, key, **kw: {"sub": "user_xyz", "exp": time.time() + 60},
    )

    result = await deps.verify_clerk_token(authorization="Bearer other.jwt.token")

    assert result["sub"] == "user_xyz"
    assert "name" not in result
    assert "email" not in result
