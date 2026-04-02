from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.actions.router import router as actions_router
from src.auth.router import router as auth_router
from src.core.lifespan import lifespan
from src.inbox.router import router as inbox_router
from src.meetings.router import router as meetings_router
from src.projects.router import meeting_project_router, router as projects_router
from src.upload.router import router as upload_router
from src.workspaces.router import router as workspaces_router

app = FastAPI(
    title="Kairos API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
app.include_router(upload_router)


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
