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

    # Sprint 27e Round 2 r2-4 — validator 가 environment 도 참조하므로 field 순서 우선.
    # (Pydantic V2 field_validator 는 정의 순서대로 실행 — environment 가 cron_secret_token
    # 보다 앞에 있어야 info.data 에서 보임.)
    environment: str = "development"

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
    # environment 는 위로 이동 (r2-4 validator 가 참조)

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

    # Sprint 27e Round 2 BUG-S27e-SEC-r2-4 — production 판별 분기 통합.
    # main.py 의 _is_production (OR + lower) 와 validator 의 분기 일관성 회복.
    # app_env / environment 둘 중 하나라도 production 이면 prod 판정.
    @staticmethod
    def _is_non_dev_env(app_env: str, environment: str = "development") -> bool:
        """production / staging 등 비-dev 환경 통합 판정 (validator + main.py 공통)."""
        non_dev = {"production", "staging", "stage", "prod"}
        return app_env.lower() in non_dev or environment.lower() in non_dev

    # Sprint 27e BUG-S27e-SEC-4 + Round 2 r2-3 — non-dev 환경에서 dev fallback + 약한 token 거부.
    # r2-3: staging 우회 (app_env=="production" 단일 비교) 차단 + 32 byte min length 강제.
    @field_validator("cron_secret_token")
    @classmethod
    def _validate_cron_token(cls, v: SecretStr, info) -> SecretStr:
        if cls._is_non_dev_env(
            info.data.get("app_env", "development"),
            info.data.get("environment", "development"),
        ):
            val = v.get_secret_value()
            if val == _CRON_TOKEN_DEV_FALLBACK:
                raise ValueError(
                    "CRON_SECRET_TOKEN must be set in non-dev (production/staging) "
                    "(dev fallback 'dev-cron-secret-CHANGE-ME-IN-PROD' rejected)"
                )
            if len(val) < 32:
                raise ValueError(
                    f"CRON_SECRET_TOKEN must be >= 32 bytes in non-dev (got {len(val)})"
                )
        return v

    # Sprint 27e BUG-S27e-SEC-3 + Round 2 r2-2 — non-dev 환경에서 dev Clerk issuer 거부.
    # r2-2: staging 우회 차단 (validator 가 app_env=="production" 단일 비교 였음).
    # dev issuer hard-code 2 곳 (line 32 default + 본 substring) atomic update 책임 명시.
    @field_validator("clerk_jwt_issuer")
    @classmethod
    def _no_dev_issuer_in_non_dev(cls, v: str, info) -> str:
        if cls._is_non_dev_env(
            info.data.get("app_env", "development"),
            info.data.get("environment", "development"),
        ) and "creative-boxer-79.clerk.accounts.dev" in v:
            raise ValueError(
                "CLERK_JWT_ISSUER must be Clerk Production instance URL in non-dev "
                "(production/staging). dev issuer 'creative-boxer-79.clerk.accounts.dev' rejected"
            )
        return v

    # Sprint 27e Round 2 BUG-S27e-SEC-r2-2 — non-dev 환경에서 audience None default 거부.
    # SEC-3 fix 의 audience 검증 영구 skip 방지 (None → verify_aud: False fallback 차단).
    @field_validator("clerk_jwt_audience")
    @classmethod
    def _require_audience_in_non_dev(cls, v: str | None, info) -> str | None:
        if cls._is_non_dev_env(
            info.data.get("app_env", "development"),
            info.data.get("environment", "development"),
        ) and v is None:
            raise ValueError(
                "CLERK_JWT_AUDIENCE must be explicitly set in non-dev "
                "(production/staging). implicit aud-skip (None) rejected — "
                "audience 검증 영구 skip 방지"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """Settings 싱글톤 반환. 앱 전체에서 동일 인스턴스 재사용."""
    return Settings()  # type: ignore[call-arg] — BaseSettings 가 .env / env 에서 값 채움 (false positive)
