# apps/api/tests/test_config.py
"""Settings 로딩 테스트."""
import os
import pytest


def test_settings_loads_from_env(monkeypatch):
    """환경변수에서 Settings를 올바르게 로드하는지 검증."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
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
    assert settings.gemini_api_key.get_secret_value() == "test-gemini-key"


def test_settings_secret_str_not_exposed(monkeypatch):
    """SecretStr이 문자열로 직접 노출되지 않는지 검증."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("R2_ACCOUNT_ID", "test")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("R2_BUCKET_NAME", "test")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-xxx")

    from src.core.config import Settings

    settings = Settings()
    # str()로 변환 시 SecretStr은 '**********' 출력
    assert "test-gemini-key" not in str(settings.gemini_api_key)


# Sprint 27e BUG-S27e-SEC-4 회귀 가드 — production 환경에서 dev cron token fallback 거부.
def _set_required_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
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
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://auth.example-app.com")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://api.example.com")
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
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://auth.example-app.com")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://api.example.com")

    from src.core.config import Settings

    settings = Settings(_env_file=None)
    assert settings.cron_secret_token.get_secret_value() == "prod-real-secret-xyz-32bytes-long-aaaa"


# Sprint 27e BUG-S27e-SEC-3 회귀 가드 — production 환경에서 dev Better Auth issuer URL 거부.
def test_auth_jwt_issuer_dev_rejected_in_production(monkeypatch):
    """production + dev issuer URL → ValueError."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://api.example.com")
    # dev URL override 안 함 → default 가 dev — validator 가 raise
    monkeypatch.delenv("AUTH_JWT_ISSUER", raising=False)  # loopback 기본값으로 낙하
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")

    from src.core.config import Settings

    with pytest.raises(ValueError, match="AUTH_JWT_ISSUER must not point at loopback"):
        Settings(_env_file=None)


def test_auth_jwt_issuer_prod_url_accepted(monkeypatch):
    """production + 실 production URL → OK."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://auth.example-app.com")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://api.example.com")

    from src.core.config import Settings

    settings = Settings(_env_file=None)
    assert settings.auth_jwt_issuer == "https://auth.example-app.com"


# Sprint 27e Round 2 BUG-S27e-SEC-r2-2 회귀 가드 — staging 환경 우회 + audience None default 거부.
def test_cron_token_dev_fallback_rejected_in_staging(monkeypatch):
    """r2-3: staging 환경에서도 dev fallback token 거부 (Round 1 fix 가 production 만 차단했음)."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://auth.example-app.com")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://api.example.com")
    monkeypatch.delenv("CRON_SECRET_TOKEN", raising=False)

    from src.core.config import Settings

    with pytest.raises(ValueError, match="CRON_SECRET_TOKEN must be set in non-dev"):
        Settings(_env_file=None)


def test_cron_token_short_value_rejected_in_production(monkeypatch):
    """r2-3: 1글자 token 도 production 통과하던 결함 차단 (min 32 byte 강제)."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "x")  # 1 글자 (32 byte 미만)
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://auth.example-app.com")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://api.example.com")

    from src.core.config import Settings

    with pytest.raises(ValueError, match="must be >= 32 bytes"):
        Settings(_env_file=None)


def test_auth_jwt_issuer_dev_rejected_in_staging(monkeypatch):
    """r2-2: staging 환경에서도 dev issuer URL 거부 (Round 1 fix 가 production 만 차단했음)."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://api.example.com")
    monkeypatch.delenv("AUTH_JWT_ISSUER", raising=False)  # loopback 기본값으로 낙하
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")

    from src.core.config import Settings

    with pytest.raises(ValueError, match="AUTH_JWT_ISSUER must not point at loopback"):
        Settings(_env_file=None)


def test_auth_jwt_audience_none_rejected_in_production(monkeypatch):
    """r2-2: audience None default 가 verify_aud: False fallback 으로 audience 검증 영구 skip 차단."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://auth.example-app.com")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")
    monkeypatch.delenv("AUTH_JWT_AUDIENCE", raising=False)

    from src.core.config import Settings

    with pytest.raises(ValueError, match="AUTH_JWT_AUDIENCE must be explicitly set"):
        Settings(_env_file=None)


def test_is_non_dev_env_via_environment_only(monkeypatch):
    """r2-4: ENVIRONMENT=production + APP_ENV=development → validator 가 production 처럼 동작 (OR + lower 일관성)."""
    _set_required_env(monkeypatch)
    # 배포 파이프라인이 ENVIRONMENT 만 production 으로 설정 + APP_ENV 누락 시나리오
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("CRON_SECRET_TOKEN", raising=False)
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://auth.example-app.com")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://api.example.com")

    from src.core.config import Settings

    # _is_non_dev_env 가 environment 도 확인 — dev fallback token 거부
    with pytest.raises(ValueError, match="must be set in non-dev"):
        Settings(_env_file=None)


# Sprint 29 — 프로덕션 아웃티지 fix 회귀 가드.
# 당시 인시던트(2026-06-23~30): APP_ENV=production 인데 dev 인증 인스턴스를 계속 쓰는 모순을
# 27e validator 3종이 부팅 시 잡아내 컨테이너가 crash-loop → prod 백엔드 전면 다운.
# 게이트를 끄면 raise 가 loud warning 으로 바뀌어 부팅이 회복된다.
#
# ADR-031 이후 기본값은 다시 True 다 (`auth_prod_hardening`). Better Auth 는 우리가 발급자를
# 소유하므로 "prod 인데 dev 발급자" 라는 모순 자체가 사라졌고, migrate one-shot 이 config
# 게이트 역할을 해 부팅 차단이 무한 재시작으로 번지지 않는다. 게이트는 비상 탈출구로만 남는다.
def test_prod_hardening_disabled_allows_dev_auth_boot(monkeypatch):
    """게이트 OFF: production + dev issuer/audience/cron 전부라도 raise 없이 부팅(경고만)."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_PROD_HARDENING", "false")
    # dev Better Auth 기본값 그대로 (issuer dev / audience None / cron fallback)
    monkeypatch.delenv("AUTH_JWT_ISSUER", raising=False)  # loopback 기본값으로 낙하
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")
    monkeypatch.delenv("AUTH_JWT_AUDIENCE", raising=False)
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
    assert settings.auth_prod_hardening is False
    assert settings.app_env == "production"
    # 3종 위반 모두 loud warning 으로 기록 (조용한 무력화 금지)
    blob = " ".join(warned)
    assert "AUTH_JWT_ISSUER" in blob
    assert "AUTH_JWT_AUDIENCE" in blob
    assert "CRON_SECRET_TOKEN" in blob


def test_prod_hardening_enabled_by_default_still_raises(monkeypatch):
    """게이트 기본 ON: flag 미설정 시 27e 강제 검증 유지 (dev issuer → raise)."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://api.example.com")
    monkeypatch.delenv("AUTH_JWT_ISSUER", raising=False)  # loopback 기본값으로 낙하
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")
    monkeypatch.delenv("AUTH_PROD_HARDENING", raising=False)

    from src.core.config import Settings

    assert Settings.model_fields["auth_prod_hardening"].default is True
    with pytest.raises(ValueError, match="AUTH_JWT_ISSUER must not point at loopback"):
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
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://auth.example-app.com")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://auth.example-app.com/api/auth/jwks")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://api.example.com")
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


# ── ADR-031 신규 가드 ────────────────────────────────────────────────────────
def test_auth_jwks_url_loopback_rejected_in_production(monkeypatch):
    """JWKS URL 도 issuer 와 같은 loopback 가드를 받는다.

    issuer 만 막고 JWKS 를 놓치면, prod 가 개발자 노트북의 JWKS 를 신뢰하려다 실패하거나
    (도달 불가) 최악의 경우 사내망의 다른 호스트를 신뢰하게 된다.
    """
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://auth.example-app.com")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://api.example.com")
    monkeypatch.setenv("AUTH_JWKS_URL", "http://127.0.0.1:3000/api/auth/jwks")

    from src.core.config import Settings

    with pytest.raises(ValueError, match="AUTH_JWKS_URL must not point at loopback"):
        Settings(_env_file=None)


def test_auth_jwks_url_internal_hostname_accepted_in_production(monkeypatch):
    """compose 내부망 호스트명(`web`)은 loopback 이 아니므로 통과해야 한다.

    prod 구성이 바로 이것이다 — issuer 는 공개 URL, JWKS 는 컨테이너 내부 주소.
    이게 막히면 인증 경로가 Cloudflare Tunnel 왕복으로 되돌아간다.
    """
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRON_SECRET_TOKEN", "prod-real-secret-xyz-32bytes-long-aaaa")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://kairos.example.com")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "https://kairos.example.com")
    monkeypatch.setenv("AUTH_JWKS_URL", "http://web:3000/api/auth/jwks")

    from src.core.config import Settings

    settings = Settings(_env_file=None)
    assert settings.auth_jwks_url == "http://web:3000/api/auth/jwks"
    assert settings.auth_jwt_issuer == "https://kairos.example.com"


def test_empty_auth_jwt_algorithms_rejected(monkeypatch):
    """알고리즘 허용 목록이 비면 부팅을 막는다 (환경 무관).

    빈 목록을 그대로 PyJWT 에 넘기면 alg confusion 의 진입점이 된다.
    """
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_JWT_ALGORITHMS", " , ")

    from src.core.config import Settings

    with pytest.raises(ValueError, match="AUTH_JWT_ALGORITHMS must list at least one"):
        Settings(_env_file=None)


def test_auth_jwt_algorithms_default_is_eddsa(monkeypatch):
    """기본값은 Better Auth jwt 플러그인의 기본 서명 알고리즘과 일치해야 한다."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("AUTH_JWT_ALGORITHMS", raising=False)

    from src.core.config import Settings

    assert Settings(_env_file=None).auth_jwt_algorithms == "EdDSA"
