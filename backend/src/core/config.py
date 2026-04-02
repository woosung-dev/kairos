# backend/src/core/config.py
"""앱 설정. 모든 환경변수를 여기서 관리."""
from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Kairos 백엔드 설정. .env 파일 또는 환경변수에서 로드."""

    # 앱
    app_env: str = "development"
    log_level: str = "INFO"

    # CORS (쉼표 구분, 예: "http://localhost:3000,https://kairos.vercel.app")
    cors_origins: str = "http://localhost:3000"

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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


def get_settings() -> Settings:
    """Settings 인스턴스를 반환한다. 모듈 레벨 싱글톤 대신 사용."""
    return Settings()
