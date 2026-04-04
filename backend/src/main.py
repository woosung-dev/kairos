import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(
    title="Kairos API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
