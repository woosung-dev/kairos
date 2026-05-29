import logging

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.common.database import get_async_session

from src.actions.router import router as actions_router
from src.auth.router import router as auth_router
from src.common.audit_router import router as audit_router
from src.core.config import get_settings
from src.core.lifespan import lifespan
from src.feedback.router import router as feedback_router
from src.inbox.router import router as inbox_router
from src.meetings.router import router as meetings_router
from src.memory.admin_router import admin_router as memory_admin_router
from src.memory.router import router as memory_router
from src.notes.router import router as notes_router
from src.onboarding.router import router as onboarding_router
from src.projects.router import meeting_project_router, router as projects_router
from src.rag.router import router as rag_router
from src.upload.router import router as upload_router
from src.workspaces.invite_router import public_router as invite_public_router
from src.workspaces.invite_router import router as invite_router
from src.workspaces.member_router import router as member_router
from src.workspaces.router import router as workspaces_router

settings = get_settings()

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# Sprint 27e Round 2 BUG-S27e-ARCH-r2-4 — global_exception_handler 의 stack trace logging 진입점.
logger = logging.getLogger(__name__)


def _scrub_pii_hook(event, hint):
    """Sentry before_send PII 스크럽 — transcript / email / password / audio_url 제거."""
    request = event.get("request")
    if request and isinstance(request.get("data"), dict):
        for field in ("transcript", "email", "password", "audio_url"):
            request["data"].pop(field, None)
    if event.get("user"):
        event["user"].pop("email", None)
        event["user"].pop("ip_address", None)
    return event


# Sentry 초기화 (DSN 설정 시에만 활성. dev 환경 기본 비활성)
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        integrations=[FastApiIntegration()],
        send_default_pii=False,
        before_send=_scrub_pii_hook,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        environment=settings.environment,
    )

# 허용 Origin 목록 (쉼표 구분 문자열에서 파싱)
ALLOWED_ORIGINS = [o.strip() for o in settings.cors_origins.split(",")]

# T-SEC-5 (Sprint 25, BL-SNT-CANDIDATE-B): production 환경에서 docs/openapi 노출 차단.
# 공격면 축소 — 스키마 introspection 으로 endpoint enumeration / payload 추론 방지.
# F7 fix (Sprint 25 polish, agy review): app_env 와 environment 두 env var 가
# 공존 (전자=앱 자체, 후자=Sentry). 배포 파이프라인이 ENVIRONMENT=production 만
# 설정해도 docs 차단되도록 OR 분기 + 대소문자 무관.
_is_production = (
    settings.app_env.lower() == "production"
    or settings.environment.lower() == "production"
)

app = FastAPI(
    title="Kairos API",
    version="0.1.0",
    docs_url=None if _is_production else "/api/v1/docs",
    redoc_url=None if _is_production else "/api/v1/redoc",
    openapi_url=None if _is_production else "/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# BUG-S27d-4 fix (Sprint 27d opus follow-up): clickjacking / MIME sniffing / referer leak
# 차단. CORSMiddleware 다음 등록 = 외곽 레이어 → 정상 응답과 exception handler 응답 모두 적용.
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(self), geolocation=()"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)


def _attach_cors(request: Request, response: JSONResponse) -> JSONResponse:
    """CORS 헤더 set-once 패턴 부착.

    - append/merge 금지: 단일 대입만
    - 이미 헤더 있으면 skip
    - null Origin 거부
    - allow_credentials=True → wildcard(*) 금지
    """
    origin = request.headers.get("origin", "")
    if origin and origin != "null" and origin in ALLOWED_ORIGINS:
        if "access-control-allow-origin" not in response.headers:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """BE-T4: 5xx 오류 시 CORS 헤더 강제 (exception_handler 레이어).

    Sprint 27e Round 2 BUG-S27e-ARCH-r2-4 — Sentry SKIP path 의 forensic 보장.
    Sentry DSN 미설정 환경 (dev/staging 또는 cron job) 에서도 stack trace 가
    Cloud Run stdout log 에 영구 보존되어야 incident response 가능.
    """
    logger.exception("global_unhandled_5xx", exc_info=exc, extra={"path": str(request.url.path)})
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )
    return _attach_cors(request, response)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """BE-T11: 4xx 오류 시 CORS 헤더 포함 (set-once 패턴)."""
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
    return _attach_cors(request, response)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """BE-T5(d): 422 RequestValidationError 시 CORS 헤더 포함."""
    response = JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )
    return _attach_cors(request, response)


app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(meetings_router)
app.include_router(projects_router)
app.include_router(meeting_project_router)
app.include_router(actions_router)
app.include_router(inbox_router)
app.include_router(memory_router)
app.include_router(memory_admin_router)
app.include_router(notes_router)
app.include_router(onboarding_router)
app.include_router(rag_router)
app.include_router(upload_router)
app.include_router(member_router)
app.include_router(invite_router)
app.include_router(invite_public_router)
app.include_router(audit_router)
app.include_router(feedback_router)


@app.get("/api/v1/health")
async def health_check():
    """Liveness probe — uvicorn 가 응답하면 OK. DB 검증은 /api/v1/ready."""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/ready")
async def readiness_check(session: AsyncSession = Depends(get_async_session)):
    """Readiness probe — DB connectivity 포함. Cloud Run startup probe 대상.

    BL-034 (asyncpg pool_pre_ping) 효과 검증 동시 가능 — SELECT 1 으로
    실제 pool checkout + ping 확인.
    """
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar_one()
        return {"status": "ready", "db": "ok", "version": "0.1.0"}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": f"error: {type(exc).__name__}"},
        )
