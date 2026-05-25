# 앱 환경변수를 pydantic-settings로 관리하는 설정 모듈
from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sprint 15 R-CRON 의 dev fallback 토큰 — production 에선 절대 사용 X (validator 가 차단).
_CRON_TOKEN_DEV_FALLBACK = "dev-cron-secret-CHANGE-ME-IN-PROD"


class Settings(BaseSettings):
    """Kairos 백엔드 설정. .env 파일 또는 OS 환경변수에서 로드."""

    # 앱
    app_env: str = "development"
    log_level: str = "INFO"

    # CORS (쉼표 구분, 예: "http://localhost:3000,https://kairos.vercel.app")
    cors_origins: str = "http://localhost:3000"

    # 프론트엔드 URL (초대 링크 등에서 사용)
    frontend_url: str = "http://localhost:3000"

    # DB
    database_url: str

    # Clerk
    clerk_secret_key: SecretStr
    clerk_webhook_secret: SecretStr
    # Sprint 27e BUG-S27e-SEC-3 — JWT issuer/audience 명시 검증 (ADR-024 cutover 직격 결함 fix).
    # default = dev instance — production 은 env 로 override 필수 (validator 가 dev URL 차단).
    clerk_jwt_issuer: str = "https://creative-boxer-79.clerk.accounts.dev"
    # Clerk JWT Templates 에 audience 설정 시 사용 — 미설정이면 None 으로 audience 검증 skip.
    clerk_jwt_audience: str | None = None

    # Cloudflare R2
    r2_account_id: SecretStr
    r2_access_key_id: SecretStr
    r2_secret_access_key: SecretStr
    r2_bucket_name: str

    # AI
    gemini_api_key: SecretStr
    openai_api_key: SecretStr

    # Cron (Sprint 15 R-CRON — R2 30일 cleanup endpoint 인증)
    # Sprint 27e BUG-S27e-SEC-4 — production 환경에서 dev fallback 토큰 사용 금지.
    # default 는 dev/test 편의 — validator 가 production 환경에서만 raise.
    cron_secret_token: SecretStr = SecretStr(_CRON_TOKEN_DEV_FALLBACK)

    # Sentry (Sprint 22 Task 7 — Observability)
    sentry_dsn: SecretStr | None = None
    sentry_traces_sample_rate: float = 0.1
    environment: str = "development"

    # Upload validation (Sprint 25 T-SEC-3 — BUG-SENTINEL-003)
    # 500MB 기본 한도. 음성 4시간 = ~120MB(64kbps mp3) ~ 480MB(128kbps wav) 커버.
    max_upload_bytes: int = 500 * 1024 * 1024
    # 화이트리스트 MIME (쉼표 구분). audio/* + video/* (container 추출) + application/pdf + text/*.
    # F-2A fix (Sprint 25 polish v2, codex 2차): 브라우저가 .mp4/.webm/.mov 파일을
    # video/mp4·video/webm·video/quicktime MIME 으로 전송 (audio/* 가 아님). FE 가
    # source-add-modal 과 new/page 에서 video/* accept → 실 사용자 워크플로우 회복.
    allowed_upload_mimes: str = (
        "audio/mpeg,audio/mp4,audio/x-m4a,audio/wav,audio/x-wav,audio/webm,audio/ogg,"
        "video/mp4,video/webm,video/quicktime,"
        "application/pdf,text/plain,text/markdown"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # 빈 문자열 환경변수 무시
        extra="ignore",         # 선언되지 않은 변수 무시
    )

    # Sprint 27e BUG-S27e-SEC-4 — production 환경에서 dev fallback 토큰 거부.
    @field_validator("cron_secret_token")
    @classmethod
    def _no_default_cron_in_prod(cls, v: SecretStr, info) -> SecretStr:
        app_env = info.data.get("app_env", "development")
        if app_env == "production" and v.get_secret_value() == _CRON_TOKEN_DEV_FALLBACK:
            raise ValueError(
                "CRON_SECRET_TOKEN must be set in production "
                "(dev fallback 'dev-cron-secret-CHANGE-ME-IN-PROD' rejected)"
            )
        return v

    # Sprint 27e BUG-S27e-SEC-3 — production 환경에서 dev Clerk issuer 거부.
    @field_validator("clerk_jwt_issuer")
    @classmethod
    def _no_dev_issuer_in_prod(cls, v: str, info) -> str:
        app_env = info.data.get("app_env", "development")
        if app_env == "production" and "creative-boxer-79.clerk.accounts.dev" in v:
            raise ValueError(
                "CLERK_JWT_ISSUER must be Clerk Production instance URL in production "
                "(dev issuer 'creative-boxer-79.clerk.accounts.dev' rejected)"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """Settings 싱글톤 반환. 앱 전체에서 동일 인스턴스 재사용."""
    return Settings()  # type: ignore[call-arg] — BaseSettings 가 .env / env 에서 값 채움 (false positive)
