# backend/tests/test_config.py
"""Settings 로딩 테스트."""
import os
import pytest


def test_settings_loads_from_env(monkeypatch):
    """환경변수에서 Settings를 올바르게 로드하는지 검증."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", "whsec_xxx")
    monkeypatch.setenv("R2_ACCOUNT_ID", "test_account")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test_key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test_secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-xxx")
    monkeypatch.setenv("APP_ENV", "test")

    from src.core.config import Settings

    settings = Settings()
    assert settings.app_env == "test"
    assert settings.r2_bucket_name == "test-bucket"
    # SecretStr 검증
    assert settings.clerk_secret_key.get_secret_value() == "sk_test_xxx"
    assert settings.gemini_api_key.get_secret_value() == "test-gemini-key"


def test_settings_secret_str_not_exposed(monkeypatch):
    """SecretStr이 문자열로 직접 노출되지 않는지 검증."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_secret")
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", "whsec_xxx")
    monkeypatch.setenv("R2_ACCOUNT_ID", "test")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("R2_BUCKET_NAME", "test")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-xxx")

    from src.core.config import Settings

    settings = Settings()
    # str()로 변환 시 SecretStr은 '**********' 출력
    assert "sk_test_secret" not in str(settings.clerk_secret_key)
