# Memory HTTP router — POST capture (202) + GET polling
"""Memory router.

patch §4 P-R1:
- POST: text 또는 audio multipart → 202 + {memory_id, status, distilled_json: null}
- GET: 단일 메모 조회 — FE polling endpoint
"""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.memory.dependencies import get_memory_service
from src.memory.exceptions import EmptyMemoryError
from src.memory.schemas import MemoryCreateOut, MemoryDetailOut
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


@router.get("/{memory_id}", response_model=MemoryDetailOut)
async def get_memory(
    workspace_id: uuid.UUID,
    memory_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryDetailOut:
    """단일 메모 조회 — distilled_json / embedding_chunk_id / status 확인."""
    return await service.get_memory(memory_id, workspace_id)
