import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.actions.router import router as actions_router
from src.auth.router import router as auth_router
from src.core.config import get_settings
from src.core.lifespan import lifespan
from src.inbox.router import router as inbox_router
from src.meetings.router import router as meetings_router
from src.notes.router import router as notes_router
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

# 허용 Origin 목록 (쉼표 구분 문자열에서 파싱)
ALLOWED_ORIGINS = [o.strip() for o in settings.cors_origins.split(",")]

app = FastAPI(
    title="Kairos API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
async def global_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
    """BE-T4: 5xx 오류 시 CORS 헤더 강제 (exception_handler 레이어)."""
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
app.include_router(notes_router)
app.include_router(rag_router)
app.include_router(upload_router)
app.include_router(member_router)
app.include_router(invite_router)
app.include_router(invite_public_router)


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
