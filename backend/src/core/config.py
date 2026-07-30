# 앱 환경변수를 pydantic-settings로 관리하는 설정 모듈
import logging
from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

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

    # Sprint 29 — 27e prod 하드닝 validator(issuer/audience/cron) 게이트.
    # 기본 True = 강제 검증 유지(보안 default). prod 가 ADR-022 에 따라 의도적으로 dev Clerk
    # 인스턴스를 유지하는 동안, APP_ENV=production 과 dev Clerk 의 모순으로 부팅이 crash-loop
    # 되어 prod 전체가 다운된 인시던트(2026-06-23~30) 회복용. CLERK_PROD_HARDENING=false 로
    # 명시 opt-out 시 validator 가 raise → loud warning 으로 전환(조용한 무력화 아님).
    # ADR-024 Clerk Production 컷오버 완료 시 이 줄을 제거(=True 복귀)해 하드닝 재무장.
    # 본 field 는 issuer/audience/cron validator 보다 먼저 정의돼야 info.data 에서 보임.
    clerk_prod_hardening: bool = True

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

    # Slack (Sprint 28 Wave 1 — dogfooding 피드백 알림)
    # 미설정 시 send_slack_message 는 no-op (피드백은 DB 에 항상 저장). Sentry SKIP 정책과 정합.
    slack_feedback_webhook_url: str | None = None

    # Integrations (ADR-026 D10 — Google Drive v0, 미구현 상태에서는 모두 선택값)
    integrations_encryption_key: SecretStr | None = None
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: SecretStr | None = None
    google_picker_api_key: SecretStr | None = None

    # DB pool (PERF-r2-5) — 기본값 5+10 유지. PERF-SSE-COMMIT 으로 스트리밍 중
    # 커넥션 점유가 제거돼 상향 필요성은 낮아짐 — 상향 시 Neon max_connections
    # (compute 크기 의존) × Cloud Run 인스턴스 수 곱 초과 금지.
    db_pool_size: int = 5
    db_max_overflow: int = 10

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

    # ADR-026 D10 / ADR-024: Fernet 키는 길이 비교 대신 Fernet() 생성으로 검증한다.
    # `_enforce_or_warn` 은 `clerk_prod_hardening=True`(기본)일 때 `raise` 한다. 현재
    # `deploy.yml` 이 `CLERK_PROD_HARDENING=false` 로 게이팅해 warning 으로 동작하지만,
    # Clerk Production 컷오버 시 그 게이트를 제거하면 integrations 키 검증까지 부팅 차단으로
    # 재무장된다. ADR-024 의 2026-06-30 prod crash-loop 교훈(부팅 차단형 validator 가 prod
    # 전체를 다운시킴)에 따라 integrations 키는 Clerk 하드닝 플래그와 분리해 항상 warning 으로
    # 처리한다.
    @field_validator("integrations_encryption_key")
    @classmethod
    def _validate_integrations_encryption_key(cls, v: SecretStr | None) -> SecretStr | None:
        if v is None:
            return v

        try:
            Fernet(v.get_secret_value().encode())
        except ValueError:
            logger.warning(
                "[CONFIG GUARD · ADR-026] INTEGRATIONS_ENCRYPTION_KEY is invalid; "
                "Fernet key validation failed"
            )
        return v

    # Sprint 27e Round 2 BUG-S27e-SEC-r2-4 — production 판별 분기 통합.
    # main.py 의 _is_production (OR + lower) 와 validator 의 분기 일관성 회복.
    # app_env / environment 둘 중 하나라도 production 이면 prod 판정.
    @staticmethod
    def _is_non_dev_env(app_env: str, environment: str = "development") -> bool:
        """production / staging 등 비-dev 환경 통합 판정 (validator + main.py 공통)."""
        non_dev = {"production", "staging", "stage", "prod"}
        return app_env.lower() in non_dev or environment.lower() in non_dev

    # Sprint 29 — 27e prod 하드닝 위반 처리 게이트.
    @classmethod
    def _enforce_or_warn(cls, info, message: str) -> None:
        """non-dev 보안 위반 처리. clerk_prod_hardening=True(기본)면 raise(27e 강제 검증 유지),
        False(ADR-022 dev Clerk 유지 명시 opt-out)면 loud warning 으로 전환해 부팅 허용.
        조용한 무력화 금지 — opt-out 이어도 위반은 항상 WARNING 로 기록."""
        if info.data.get("clerk_prod_hardening", True):
            raise ValueError(message)
        logger.warning(
            "[CONFIG GUARD · gated by CLERK_PROD_HARDENING=false · ADR-022] %s", message
        )

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
                cls._enforce_or_warn(
                    info,
                    "CRON_SECRET_TOKEN must be set in non-dev (production/staging) "
                    "(dev fallback 'dev-cron-secret-CHANGE-ME-IN-PROD' rejected)",
                )
            elif len(val) < 32:
                cls._enforce_or_warn(
                    info,
                    f"CRON_SECRET_TOKEN must be >= 32 bytes in non-dev (got {len(val)})",
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
            cls._enforce_or_warn(
                info,
                "CLERK_JWT_ISSUER must be Clerk Production instance URL in non-dev "
                "(production/staging). dev issuer 'creative-boxer-79.clerk.accounts.dev' rejected",
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
            cls._enforce_or_warn(
                info,
                "CLERK_JWT_AUDIENCE must be explicitly set in non-dev "
                "(production/staging). implicit aud-skip (None) rejected — "
                "audience 검증 영구 skip 방지",
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """Settings 싱글톤 반환. 앱 전체에서 동일 인스턴스 재사용."""
    return Settings()  # type: ignore[call-arg] — BaseSettings 가 .env / env 에서 값 채움 (false positive)
