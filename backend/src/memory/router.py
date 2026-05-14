# Memory HTTP router — POST capture (202) + GET polling + GET recall (R3)
"""Memory router.

patch §4 P-R1:
- POST: text 또는 audio multipart → 202 + {memory_id, status, distilled_json: null}
- GET /{memory_id}: 단일 메모 조회 — FE polling endpoint

patch §6 P-R3:
- GET /recall?q=...: vector search + keyword fallback (Top 3). /{memory_id}보다 먼저 선언하여 UUID 패턴 충돌 회피.
"""
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
)

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.memory.dependencies import get_memory_service
from src.memory.exceptions import EmptyMemoryError
from src.memory.schemas import (
    MemoryCreateOut,
    MemoryDetailOut,
    MemoryMetricsOut,
    MemoryPromoteIn,
    MemoryPromoteOut,
    MemoryRecallOut,
)
from src.memory.service import MemoryService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/memory",
    tags=["memory"],
)


@router.post("", response_model=MemoryCreateOut, status_code=202)
async def capture_memory(
    workspace_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    text: str | None = Form(default=None),
    audio: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryCreateOut:
    """메모 capture — text 또는 audio multipart, 즉시 202 + processing."""
    if text and text.strip():
        return await service.capture_text(
            user_id=user.id,
            workspace_id=workspace_id,
            text=text.strip(),
            background_tasks=background_tasks,
        )
    if audio is not None:
        content = await audio.read()
        return await service.capture_voice(
            user_id=user.id,
            workspace_id=workspace_id,
            audio_bytes=content,
            filename=audio.filename or "voice.audio",
            background_tasks=background_tasks,
        )
    raise EmptyMemoryError()


# 주의: /{memory_id} 보다 먼저 선언해야 'recall' 문자열이 UUID 파싱으로 매칭되지 않음.
@router.get("/recall", response_model=MemoryRecallOut)
async def recall_memory(
    workspace_id: uuid.UUID,
    q: str = Query(..., min_length=2, max_length=200),
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryRecallOut:
    """Recall — vector search + keyword fallback (Top 3, O-A lock-in)."""
    return await service.recall(
        workspace_id=workspace_id, user_id=user.id, query=q, top_k=3
    )


# /metrics도 /{memory_id} 보다 먼저 선언 — UUID 패턴 충돌 회피.
@router.get("/metrics", response_model=MemoryMetricsOut)
async def get_memory_metrics(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryMetricsOut:
    """R7 metrics — memory_events 기반 capture/recall/promote count + recall p50/p95."""
    return await service.get_metrics(workspace_id)


@router.get("/{memory_id}", response_model=MemoryDetailOut)
async def get_memory(
    workspace_id: uuid.UUID,
    memory_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryDetailOut:
    """단일 메모 조회 — distilled_json / embedding_chunk_id / status 확인."""
    return await service.get_memory(memory_id, workspace_id)


@router.post(
    "/{memory_id}/promote", response_model=MemoryPromoteOut, status_code=202
)
async def promote_memory(
    workspace_id: uuid.UUID,
    memory_id: uuid.UUID,
    body: MemoryPromoteIn,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryPromoteOut:
    """R6: memory → team workspace 복제 + audit row + 백그라운드 embedding."""
    return await service.promote(
        memory_id=memory_id,
        source_workspace_id=workspace_id,
        target_workspace_id=body.target_workspace_id,
        promoted_by_user_id=user.id,
        background_tasks=background_tasks,
    )
