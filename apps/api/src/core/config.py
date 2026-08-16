# 앱 환경변수를 pydantic-settings로 관리하는 설정 모듈
import logging
from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Sprint 15 R-CRON 의 dev fallback 토큰 — production 에선 절대 사용 X (validator 가 차단).
_CRON_TOKEN_DEV_FALLBACK = "dev-cron-secret-CHANGE-ME-IN-PROD"
_GOOGLE_OAUTH_REDIRECT_URI_DEV_FALLBACK = (
    "http://localhost:8000/api/v1/integrations/google-drive/callback"
)


class Settings(BaseSettings):
    """Kairos 백엔드 설정. .env 파일 또는 OS 환경변수에서 로드."""

    # 앱
    app_env: str = "development"
    log_level: str = "INFO"

    # Sprint 27e Round 2 r2-4 — validator 가 environment 도 참조하므로 field 순서 우선.
    # (Pydantic V2 field_validator 는 정의 순서대로 실행 — environment 가 cron_secret_token
    # 보다 앞에 있어야 info.data 에서 보임.)
    environment: str = "development"

    # prod 하드닝 validator(issuer/audience/cron) 게이트.
    #
    # ADR-031 로 **재무장**했다. 2026-06-23~30 인시던트는 dev Clerk 인스턴스로 prod 를 운영하는
    # 모순 때문에 부팅이 막힌 것이었고, ADR-024 컷오버가 계속 미뤄지면서 CLERK_PROD_HARDENING=false
    # 가 prod .env 에 상수로 박혀 있었다. Better Auth 는 우리가 발급자를 소유하므로 그 모순 자체가
    # 없어졌다 — 더 이상 끌 이유가 없다.
    #
    # 그때의 진짜 사고는 "부팅 차단"이 아니라 `api` 의 `restart: unless-stopped` 와 결합한
    # **무한 재시작 루프**였다. 지금은 `migrate` one-shot 이 alembic/env.py:59 에서 get_settings()
    # 를 먼저 호출하고 `api` 가 `depends_on: {migrate: service_completed_successfully}` 로
    # 게이트되므로, config 가 잘못되면 migrate 가 죽고 api 는 아예 재생성되지 않는다.
    # 부팅 차단형 validator 가 prod 를 다운시키는 경로가 구조적으로 막혀 있다.
    #
    # 본 field 는 issuer/audience/cron validator 보다 먼저 정의돼야 info.data 에서 보인다.
    auth_prod_hardening: bool = True

    # CORS (쉼표 구분, 예: "http://localhost:3000,https://kairos.vercel.app")
    cors_origins: str = "http://localhost:3000"

    # 프론트엔드 URL (초대 링크 등에서 사용)
    frontend_url: str = "http://localhost:3000"

    # DB
    database_url: str

    # 인증 (ADR-031 — Better Auth 가 Next.js 에서 발급, 백엔드는 JWKS 로 서명만 검증)
    #
    # ★issuer 와 JWKS URL 을 분리한다. 이전에는 dependencies.py 가
    #   `issuer + "/.well-known/jwks.json"` 으로 조립해 둘이 하드 결합돼 있었다.
    #   분리하면 prod 에서 issuer 는 공개 URL(토큰 claim 과 일치해야 함)로 두고 JWKS 는
    #   compose 내부망(`http://web:3000/api/auth/jwks`)에서 가져올 수 있다 —
    #   Cloudflare Tunnel 왕복과 외부 egress 가 인증 경로에서 빠진다.
    #
    # default 는 로컬 dev 값이고 non-dev 에서는 validator 가 localhost 를 거부한다.
    auth_jwt_issuer: str = "http://localhost:3000"
    auth_jwks_url: str = "http://localhost:3000/api/auth/jwks"
    # Better Auth 기본 audience = baseURL. non-dev 에서는 명시 필수 (validator 가 None 거부).
    auth_jwt_audience: str | None = None
    # Better Auth jwt 플러그인 기본 서명 알고리즘은 EdDSA(Ed25519)다.
    # 쉼표 구분 문자열 — 헤더의 alg 를 절대 신뢰하지 않기 위해 허용 목록을 명시한다.
    auth_jwt_algorithms: str = "EdDSA"

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

    # Sentry 는 ADR-028 로 제거됐다 (DSN 이 한 번도 설정된 적 없어 비활성 상태로만 존재).
    # environment 는 유지 — docs 차단 판정(_is_production)과 r2-4 validator 가 참조한다.

    # Slack (Sprint 28 Wave 1 — dogfooding 피드백 알림)
    # 미설정 시 send_slack_message 는 no-op (피드백은 DB 에 항상 저장).
    slack_feedback_webhook_url: str | None = None

    # Integrations (ADR-026 D10 — Google Drive v0, 미구현 상태에서는 모두 선택값)
    integrations_encryption_key: SecretStr | None = None
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: SecretStr | None = None
    google_oauth_redirect_uri: str = Field(
        default=_GOOGLE_OAUTH_REDIRECT_URI_DEV_FALLBACK,
        validate_default=True,
    )
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

    # ADR-026 D10: Fernet 키는 길이 비교 대신 Fernet() 생성으로 검증한다.
    # `_enforce_or_warn` 은 `auth_prod_hardening=True`(기본)일 때 `raise` 하는데,
    # integrations 키는 그 플래그와 분리해 **항상 warn_only** 로 둔다 — Drive 연동은
    # 선택 기능이라 키가 없거나 깨졌다고 앱 전체 부팅을 막을 이유가 없다.
    # (2026-06-30 prod crash-loop 교훈: 부팅 차단형 validator 의 반경을 좁게 유지한다.)
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
    def _enforce_or_warn(cls, info, message: str, *, warn_only: bool = False) -> None:
        """non-dev 보안 위반 처리. auth_prod_hardening=True(기본)면 raise,
        False(명시 opt-out)면 loud warning 으로 전환해 부팅 허용.
        warn_only는 R6상 부팅을 막지 않아야 하는 설정 경고에 사용한다. 조용한 무력화 금지 —
        opt-out·warn_only 모두 위반은 항상 WARNING 로 기록."""
        if not warn_only and info.data.get("auth_prod_hardening", True):
            raise ValueError(message)
        if warn_only:
            logger.warning("[CONFIG GUARD · ADR-026 · startup allowed] %s", message)
            return
        logger.warning(
            "[CONFIG GUARD · gated by AUTH_PROD_HARDENING=false · ADR-031] %s", message
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

    # non-dev 환경에서 로컬 dev 발급자/JWKS 주소 거부 (ADR-031 — 27e SEC-3 가드 승계).
    # 이전 판정 기준은 Clerk dev 인스턴스 호스트명 substring 이었다. Better Auth 는 발급자가
    # 곧 우리 FE 의 baseURL 이므로, dev 를 가르는 신호는 loopback 주소다.
    @staticmethod
    def _is_loopback_url(v: str) -> bool:
        lowered = v.lower()
        return "localhost" in lowered or "127.0.0.1" in lowered or "[::1]" in lowered

    @field_validator("auth_jwt_issuer", "auth_jwks_url")
    @classmethod
    def _no_loopback_auth_url_in_non_dev(cls, v: str, info) -> str:
        if (
            cls._is_non_dev_env(
                info.data.get("app_env", "development"),
                info.data.get("environment", "development"),
            )
            and cls._is_loopback_url(v)
        ):
            cls._enforce_or_warn(
                info,
                f"{(info.field_name or 'auth url').upper()} must not point at loopback in "
                f"non-dev (production/staging). got: {v}",
            )
        return v

    # non-dev 환경에서 audience None default 거부 (27e SEC-r2-2 승계).
    # None 이면 PyJWT 가 audience 검증을 통째로 skip 하므로, 그 상태가 prod 에 굳는 것을 막는다.
    @field_validator("auth_jwt_audience")
    @classmethod
    def _require_audience_in_non_dev(cls, v: str | None, info) -> str | None:
        if cls._is_non_dev_env(
            info.data.get("app_env", "development"),
            info.data.get("environment", "development"),
        ) and v is None:
            cls._enforce_or_warn(
                info,
                "AUTH_JWT_AUDIENCE must be explicitly set in non-dev "
                "(production/staging). implicit aud-skip (None) rejected — "
                "audience 검증 영구 skip 방지",
            )
        return v

    # 헤더의 alg 를 신뢰하지 않기 위한 허용 목록. 빈 값은 PyJWT 가 모든 알고리즘을 허용하는
    # alg confusion 진입점이 되므로 비어 있으면 부팅을 막는다 (환경 무관).
    @field_validator("auth_jwt_algorithms")
    @classmethod
    def _require_non_empty_algorithms(cls, v: str) -> str:
        if not [item.strip() for item in v.split(",") if item.strip()]:
            raise ValueError("AUTH_JWT_ALGORITHMS must list at least one algorithm")
        return v

    @field_validator("google_oauth_redirect_uri")
    @classmethod
    def _warn_google_oauth_redirect_uri_in_non_dev(cls, v: str, info) -> str:
        if cls._is_non_dev_env(
            info.data.get("app_env", "development"),
            info.data.get("environment", "development"),
        ) and (not v or v == _GOOGLE_OAUTH_REDIRECT_URI_DEV_FALLBACK):
            cls._enforce_or_warn(
                info,
                "GOOGLE_OAUTH_REDIRECT_URI is using the localhost fallback in non-dev; "
                "set the deployed Google OAuth callback URI",
                warn_only=True,
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """Settings 싱글톤 반환. 앱 전체에서 동일 인스턴스 재사용."""
    return Settings()  # type: ignore[call-arg] — BaseSettings 가 .env / env 에서 값 채움 (false positive)
