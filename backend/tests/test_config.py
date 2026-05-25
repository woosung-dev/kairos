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


# Sprint 27e BUG-S27e-SEC-4 회귀 가드 — production 환경에서 dev cron token fallback 거부.
def _set_required_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", "whsec_xxx")
    monkeypatch.setenv("R2_ACCOUNT_ID", "test")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("R2_BUCKET_NAME", "test")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-xxx")


def test_cron_token_dev_fallback_rejected_in_production(monkeypatch):
    """BUG-S27e-SEC-4: production + dev fallback token → ValueError."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    # 다른 validator (issuer) 회피 — production URL 명시
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example-app.com")
    monkeypatch.delenv("CRON_SECRET_TOKEN", raising=False)

    from src.core.config import Settings

    # _env_file=None 으로 .env 파일 무시 — process env 만 사용해서 검증.
    with pytest.raises(ValueError, match="CRON_SECRET_TOKEN must be set in production"):
        Settings(_env_file=None)


def test_cron_token_dev_fallback_allowed_in_development(monkeypatch):
    """dev/test 환경에선 fallback 허용 (편의)."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("CRON_SECRET_TOKEN", raising=False)

    from src.core.config import Settings

    settings = Settings(_env_file=None)
    # fallback 적용 — 검증 통과
    assert "CHANGE-ME-IN-PROD" in settings.cron_secret_token.get_secret_value()


def test_cron_token_custom_value_accepted_in_production(monkeypatch):
    """production + 실제 secret 설정 시 OK."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long")
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example-app.com")

    from src.core.config import Settings

    settings = Settings(_env_file=None)
    assert settings.cron_secret_token.get_secret_value() == "prod-real-secret-xyz-32bytes-long"


# Sprint 27e BUG-S27e-SEC-3 회귀 가드 — production 환경에서 dev Clerk issuer URL 거부.
def test_clerk_jwt_issuer_dev_rejected_in_production(monkeypatch):
    """production + dev issuer URL → ValueError."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long")
    # dev URL override 안 함 → default 가 dev — validator 가 raise
    monkeypatch.delenv("CLERK_JWT_ISSUER", raising=False)

    from src.core.config import Settings

    with pytest.raises(ValueError, match="CLERK_JWT_ISSUER must be Clerk Production"):
        Settings(_env_file=None)


def test_clerk_jwt_issuer_prod_url_accepted(monkeypatch):
    """production + 실 production URL → OK."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long")
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example-app.com")

    from src.core.config import Settings

    settings = Settings(_env_file=None)
    assert settings.clerk_jwt_issuer == "https://clerk.example-app.com"
