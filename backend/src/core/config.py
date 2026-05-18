# 앱 환경변수를 pydantic-settings로 관리하는 설정 모듈
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Cloudflare R2
    r2_account_id: SecretStr
    r2_access_key_id: SecretStr
    r2_secret_access_key: SecretStr
    r2_bucket_name: str

    # AI
    gemini_api_key: SecretStr
    openai_api_key: SecretStr

    # Cron (Sprint 15 R-CRON — R2 30일 cleanup endpoint 인증)
    cron_secret_token: SecretStr = SecretStr("dev-cron-secret-CHANGE-ME-IN-PROD")

    # Sentry (Sprint 22 Task 7 — Observability)
    sentry_dsn: SecretStr | None = None
    sentry_traces_sample_rate: float = 0.1
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # 빈 문자열 환경변수 무시
        extra="ignore",         # 선언되지 않은 변수 무시
    )


@lru_cache
def get_settings() -> Settings:
    """Settings 싱글톤 반환. 앱 전체에서 동일 인스턴스 재사용."""
    return Settings()
