# backend/src/notes/router.py
"""노트 CRUD 엔드포인트."""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from src.auth.rbac import require_member, require_viewer
from src.workspaces.models import WorkspaceMember
from src.notes.dependencies import get_note_service
from src.notes.schemas import CreateNoteRequest, UpdateNoteRequest
from src.notes.service import NoteService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/notes",
    tags=["notes"],
)


@router.get("")
async def list_notes(
    workspace_id: uuid.UUID,
    project_id: str | None = Query(default=None, alias="projectId"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    member: WorkspaceMember = Depends(require_viewer),
    service: NoteService = Depends(get_note_service),
):
    pid = uuid.UUID(project_id) if project_id else None
    return await service.list_notes(
        workspace_id, project_id=pid, page=page, page_size=page_size
    )


@router.get("/{note_id}")
async def get_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_viewer),
    service: NoteService = Depends(get_note_service),
):
    return await service.get_note(note_id)


@router.post("", status_code=201)
async def create_note(
    workspace_id: uuid.UUID,
    data: CreateNoteRequest,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member),
    service: NoteService = Depends(get_note_service),
):
    pid = uuid.UUID(data.project_id) if data.project_id else None
    result = await service.create_note(
        workspace_id=workspace_id,
        created_by_id=member.user_id,
        title=data.title,
        content=data.content,
        project_id=pid,
    )
    background_tasks.add_task(service.embed_note_async, uuid.UUID(result["id"]))
    return result


@router.patch("/{note_id}")
async def update_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    data: UpdateNoteRequest,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member),
    service: NoteService = Depends(get_note_service),
):
    # project_id sentinel 처리: 필드가 없으면 변경 안 함
    pid = ...  # type: ignore[assignment]
    if data.project_id is not None:
        pid = uuid.UUID(data.project_id) if data.project_id else None

    result = await service.update_note(
        note_id=note_id,
        title=data.title,
        content=data.content,
        project_id=pid,
    )
    if data.content is not None:
        background_tasks.add_task(service.embed_note_async, note_id)
    return result


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_member),
    service: NoteService = Depends(get_note_service),
):
    await service.delete_note(note_id)
