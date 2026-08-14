# Sprint 28 BUG-S28-SEC-3 회귀 가드 — JWT 검증 실패 forensic logging.
"""JWT 실패는 stdout 로그에만 남는다 (ADR-028 로 Sentry 제거 — docker logs 가 유일한 관측 경로).

4 except 분기 모두 logger.warning + error_type extra 를 검증한다.
"""
import logging
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException


@pytest.fixture
def capture_logs(caplog):
    caplog.set_level(logging.WARNING, logger="src.auth.jwt_failure")
    return caplog


@pytest.mark.asyncio
async def test_jwt_expired_signature_logs_warning(capture_logs):
    """ExpiredSignatureError → logger.warning('jwt_expired')."""
    from src.auth.dependencies import verify_clerk_token

    with patch("src.auth.dependencies._jwt_cache_get", return_value=None), \
         patch("src.auth.dependencies._get_jwks_client") as mock_jwks:
        mock_jwks.return_value.get_signing_key_from_jwt.side_effect = jwt.ExpiredSignatureError()
        with pytest.raises(HTTPException) as exc:
            await verify_clerk_token(authorization="Bearer fake.fake.fake")
        assert exc.value.status_code == 401

    assert any(
        "jwt_expired" in r.message and r.levelname == "WARNING"
        for r in capture_logs.records
    ), f"Expected jwt_expired warning, got: {[r.message for r in capture_logs.records]}"


@pytest.mark.asyncio
async def test_jwt_invalid_issuer_logs_warning(capture_logs):
    """InvalidIssuerError → logger.warning('jwt_invalid_issuer')."""
    from src.auth.dependencies import verify_clerk_token

    with patch("src.auth.dependencies._jwt_cache_get", return_value=None), \
         patch("src.auth.dependencies._get_jwks_client") as mock_jwks:
        mock_jwks.return_value.get_signing_key_from_jwt.side_effect = jwt.InvalidIssuerError()
        with pytest.raises(HTTPException) as exc:
            await verify_clerk_token(authorization="Bearer fake.fake.fake")
        assert exc.value.status_code == 401
        assert "발급자" in exc.value.detail

    assert any("jwt_invalid_issuer" in r.message for r in capture_logs.records)


@pytest.mark.asyncio
async def test_jwt_invalid_audience_logs_warning(capture_logs):
    """InvalidAudienceError → logger.warning('jwt_invalid_audience')."""
    from src.auth.dependencies import verify_clerk_token

    with patch("src.auth.dependencies._jwt_cache_get", return_value=None), \
         patch("src.auth.dependencies._get_jwks_client") as mock_jwks:
        mock_jwks.return_value.get_signing_key_from_jwt.side_effect = jwt.InvalidAudienceError()
        with pytest.raises(HTTPException) as exc:
            await verify_clerk_token(authorization="Bearer fake.fake.fake")
        assert exc.value.status_code == 401

    assert any("jwt_invalid_audience" in r.message for r in capture_logs.records)


@pytest.mark.asyncio
async def test_jwt_unexpected_error_logs_warning(capture_logs):
    """generic Exception → logger.warning('jwt_verify_unexpected_error') + error_type."""
    from src.auth.dependencies import verify_clerk_token

    with patch("src.auth.dependencies._jwt_cache_get", return_value=None), \
         patch("src.auth.dependencies._get_jwks_client") as mock_jwks:
        mock_jwks.return_value.get_signing_key_from_jwt.side_effect = RuntimeError("unexpected")
        with pytest.raises(HTTPException) as exc:
            await verify_clerk_token(authorization="Bearer fake.fake.fake")
        assert exc.value.status_code == 401

    matched = [
        r for r in capture_logs.records
        if "jwt_verify_unexpected_error" in r.message and getattr(r, "error_type", None) == "RuntimeError"
    ]
    assert matched, f"Expected jwt_verify_unexpected_error + error_type=RuntimeError, got: {[(r.message, getattr(r, 'error_type', None)) for r in capture_logs.records]}"
