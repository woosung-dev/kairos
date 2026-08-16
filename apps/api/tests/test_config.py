# apps/api/tests/test_config.py
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
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://api.example.com")
    monkeypatch.delenv("CRON_SECRET_TOKEN", raising=False)

    from src.core.config import Settings

    # _env_file=None 으로 .env 파일 무시 — process env 만 사용해서 검증.
    with pytest.raises(ValueError, match="CRON_SECRET_TOKEN must be set in non-dev"):
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
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example-app.com")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://api.example.com")

    from src.core.config import Settings

    settings = Settings(_env_file=None)
    assert settings.cron_secret_token.get_secret_value() == "prod-real-secret-xyz-32bytes-long-aaaa"


# Sprint 27e BUG-S27e-SEC-3 회귀 가드 — production 환경에서 dev Clerk issuer URL 거부.
def test_clerk_jwt_issuer_dev_rejected_in_production(monkeypatch):
    """production + dev issuer URL → ValueError."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://api.example.com")
    # dev URL override 안 함 → default 가 dev — validator 가 raise
    monkeypatch.delenv("CLERK_JWT_ISSUER", raising=False)

    from src.core.config import Settings

    with pytest.raises(ValueError, match="CLERK_JWT_ISSUER must be Clerk Production"):
        Settings(_env_file=None)


def test_clerk_jwt_issuer_prod_url_accepted(monkeypatch):
    """production + 실 production URL → OK."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example-app.com")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://api.example.com")

    from src.core.config import Settings

    settings = Settings(_env_file=None)
    assert settings.clerk_jwt_issuer == "https://clerk.example-app.com"


# Sprint 27e Round 2 BUG-S27e-SEC-r2-2 회귀 가드 — staging 환경 우회 + audience None default 거부.
def test_cron_token_dev_fallback_rejected_in_staging(monkeypatch):
    """r2-3: staging 환경에서도 dev fallback token 거부 (Round 1 fix 가 production 만 차단했음)."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example-app.com")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://api.example.com")
    monkeypatch.delenv("CRON_SECRET_TOKEN", raising=False)

    from src.core.config import Settings

    with pytest.raises(ValueError, match="CRON_SECRET_TOKEN must be set in non-dev"):
        Settings(_env_file=None)


def test_cron_token_short_value_rejected_in_production(monkeypatch):
    """r2-3: 1글자 token 도 production 통과하던 결함 차단 (min 32 byte 강제)."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "x")  # 1 글자 (32 byte 미만)
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example-app.com")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://api.example.com")

    from src.core.config import Settings

    with pytest.raises(ValueError, match="must be >= 32 bytes"):
        Settings(_env_file=None)


def test_clerk_jwt_issuer_dev_rejected_in_staging(monkeypatch):
    """r2-2: staging 환경에서도 dev issuer URL 거부 (Round 1 fix 가 production 만 차단했음)."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://api.example.com")
    monkeypatch.delenv("CLERK_JWT_ISSUER", raising=False)

    from src.core.config import Settings

    with pytest.raises(ValueError, match="must be Clerk Production"):
        Settings(_env_file=None)


def test_clerk_jwt_audience_none_rejected_in_production(monkeypatch):
    """r2-2: audience None default 가 verify_aud: False fallback 으로 audience 검증 영구 skip 차단."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example-app.com")
    monkeypatch.delenv("CLERK_JWT_AUDIENCE", raising=False)

    from src.core.config import Settings

    with pytest.raises(ValueError, match="CLERK_JWT_AUDIENCE must be explicitly set"):
        Settings(_env_file=None)


def test_is_non_dev_env_via_environment_only(monkeypatch):
    """r2-4: ENVIRONMENT=production + APP_ENV=development → validator 가 production 처럼 동작 (OR + lower 일관성)."""
    _set_required_env(monkeypatch)
    # 배포 파이프라인이 ENVIRONMENT 만 production 으로 설정 + APP_ENV 누락 시나리오
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("CRON_SECRET_TOKEN", raising=False)
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example-app.com")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://api.example.com")

    from src.core.config import Settings

    # _is_non_dev_env 가 environment 도 확인 — dev fallback token 거부
    with pytest.raises(ValueError, match="must be set in non-dev"):
        Settings(_env_file=None)


# Sprint 29 — 프로덕션 아웃티지 fix 회귀 가드.
# APP_ENV=production + dev Clerk 인스턴스 유지(ADR-022) 조합이 27e validator 3종을
# 부팅 시 crash-loop 시켜 prod 백엔드 전체가 다운된 인시던트 (2026-06-23~30).
# CLERK_PROD_HARDENING 게이트(기본 ON)로 raise → loud warning 전환, dev Clerk 부팅 회복.
def test_prod_hardening_disabled_allows_dev_clerk_boot(monkeypatch):
    """게이트 OFF: production + dev issuer/audience/cron 전부라도 raise 없이 부팅(경고만)."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CLERK_PROD_HARDENING", "false")
    # dev Clerk 기본값 그대로 (issuer dev / audience None / cron fallback)
    monkeypatch.delenv("CLERK_JWT_ISSUER", raising=False)
    monkeypatch.delenv("CLERK_JWT_AUDIENCE", raising=False)
    monkeypatch.delenv("CRON_SECRET_TOKEN", raising=False)

    # logger.warning 직접 스파이 — 전역 logging 설정에 의존 않는 isolation-proof 검증.
    import src.core.config as config_mod

    warned: list[str] = []
    monkeypatch.setattr(
        config_mod.logger,
        "warning",
        lambda msg, *args: warned.append(msg % args if args else msg),
    )

    settings = config_mod.Settings(_env_file=None)  # raise 없이 부팅
    assert settings.clerk_prod_hardening is False
    assert settings.app_env == "production"
    # 3종 위반 모두 loud warning 으로 기록 (조용한 무력화 금지)
    blob = " ".join(warned)
    assert "CLERK_JWT_ISSUER" in blob
    assert "CLERK_JWT_AUDIENCE" in blob
    assert "CRON_SECRET_TOKEN" in blob


def test_prod_hardening_enabled_by_default_still_raises(monkeypatch):
    """게이트 기본 ON: flag 미설정 시 27e 강제 검증 유지 (dev issuer → raise)."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://api.example.com")
    monkeypatch.delenv("CLERK_JWT_ISSUER", raising=False)
    monkeypatch.delenv("CLERK_PROD_HARDENING", raising=False)

    from src.core.config import Settings

    assert Settings.model_fields["clerk_prod_hardening"].default is True
    with pytest.raises(ValueError, match="CLERK_JWT_ISSUER must be Clerk Production"):
        Settings(_env_file=None)


def test_google_oauth_redirect_uri_default_is_quiet_in_development(
    monkeypatch,
):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("GOOGLE_OAUTH_REDIRECT_URI", raising=False)

    import src.core.config as config_mod

    warned: list[str] = []
    monkeypatch.setattr(
        config_mod.logger,
        "warning",
        lambda msg, *args: warned.append(msg % args if args else msg),
    )
    config_mod.Settings(_env_file=None)

    assert not any("GOOGLE_OAUTH_REDIRECT_URI" in message for message in warned)


def test_google_oauth_redirect_uri_empty_warns_in_non_dev(
    monkeypatch,
):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example-app.com")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://api.example.com")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "")

    import src.core.config as config_mod

    warned: list[str] = []
    monkeypatch.setattr(
        config_mod.logger,
        "warning",
        lambda msg, *args: warned.append(msg % args if args else msg),
    )
    settings = config_mod.Settings(_env_file=None)

    assert settings.google_oauth_redirect_uri.startswith("http://localhost:8000/")
    assert any("GOOGLE_OAUTH_REDIRECT_URI is using the localhost fallback" in message for message in warned)
