# backend/src/rag/router.py
"""RAG 엔드포인트 — SSE 스트리밍."""
import uuid

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from src.auth.rbac import require_viewer
from src.workspaces.models import WorkspaceMember
from src.rag.dependencies import get_rag_service
from src.rag.schemas import RagAskRequest
from src.rag.service import RagService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/rag",
    tags=["rag"],
)


@router.post("/ask")
async def ask_rag(
    workspace_id: uuid.UUID,
    data: RagAskRequest,
    member: WorkspaceMember = Depends(require_viewer),
    service: RagService = Depends(get_rag_service),
):
    """RAG 질문 → SSE 스트리밍 답변."""
    project_id = uuid.UUID(data.project_id) if data.project_id else None

    async def event_generator():
        async for event in service.ask(
            question=data.question,
            workspace_id=workspace_id,
            project_id=project_id,
            time_range=data.time_range,
            source_type=data.source_type,
        ):
            yield event

    return EventSourceResponse(event_generator())
