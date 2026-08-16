# apps/api/src/notes/router.py
"""노트 CRUD 엔드포인트."""
import uuid

from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import Response

from src.auth.rbac import require_member, require_member_fresh, require_viewer
from src.workspaces.models import WorkspaceMember
from src.notes.dependencies import get_note_pipeline_service, get_note_service
from src.notes.pipeline_service import NotePipelineService
from src.notes.schemas import (
    CreateNoteRequest,
    EmbeddingStatusOut,
    NotePromoteIn,
    NotePromoteOut,
    UpdateNoteRequest,
)
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
        workspace_id,
        project_id=pid,
        page=page,
        page_size=page_size,
        requester_user_id=member.user_id,
        requester_role=member.role,
    )


@router.get("/{note_id}")
async def get_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_viewer),
    service: NoteService = Depends(get_note_service),
):
    return await service.get_note(
        note_id,
        workspace_id,
        requester_user_id=member.user_id,
        requester_role=member.role,
    )


@router.get("/{note_id}/export")
async def export_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    format: str = Query(default="md", pattern="^(md|json)$"),
    member: WorkspaceMember = Depends(require_viewer),
    service: NoteService = Depends(get_note_service),
):
    content, filename, media_type = await service.export_note(
        note_id,
        workspace_id,
        format,
        requester_user_id=member.user_id,
        requester_role=member.role,
    )
    encoded = quote(filename)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.post("", status_code=201)
async def create_note(
    workspace_id: uuid.UUID,
    data: CreateNoteRequest,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member),
    service: NoteService = Depends(get_note_service),
    pipeline: NotePipelineService = Depends(get_note_pipeline_service),
):
    pid = uuid.UUID(data.project_id) if data.project_id else None
    result = await service.create_note(
        workspace_id=workspace_id,
        created_by_id=member.user_id,
        title=data.title,
        content=data.content,
        project_id=pid,
    )
    # embedding 은 orchestrator 경유 (ADR-014 옵션 A 정합) — Codex F-1: workspace_id 동반
    background_tasks.add_task(
        pipeline.embed_note_async, uuid.UUID(result["id"]), workspace_id
    )
    return result


@router.patch("/{note_id}")
async def update_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    data: UpdateNoteRequest,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member_fresh),
    service: NoteService = Depends(get_note_service),
    pipeline: NotePipelineService = Depends(get_note_pipeline_service),
):
    # project_id sentinel 처리: 필드가 없으면 변경 안 함
    pid = ...  # type: ignore[assignment]
    if data.project_id is not None:
        pid = uuid.UUID(data.project_id) if data.project_id else None

    result = await service.update_note(
        note_id=note_id,
        workspace_id=workspace_id,
        title=data.title,
        content=data.content,
        project_id=pid,
        requester_user_id=member.user_id,
        requester_role=member.role,
    )
    # Sprint 29 R1 (notes-stale): project_id 변경 시 EmbeddingChunk.project_id 동기화 +
    # old/new SemanticCache 무효화 (content 미변경 시 embed_note_async 가 실행되지 않아
    # chunk.project_id 가 stale 로 남아 RAG project-scope 필터가 틀리는 문제 해소).
    if data.project_id is not None:
        await pipeline.sync_note_project_id(note_id, workspace_id)
    if data.content is not None:
        background_tasks.add_task(pipeline.embed_note_async, note_id, workspace_id)
    return result


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_member_fresh),
    pipeline: NotePipelineService = Depends(get_note_pipeline_service),
):
    # embedding cleanup 포함 orchestrator 경유 (ADR-014 옵션 A 정합) — Codex H2/옵션 A: workspace_id 필수
    # CAND-A completeness: SOURCE 노트의 project visibility 게이트 (비-멤버 write IDOR 차단)
    await pipeline.delete_note_with_cleanup(
        note_id,
        workspace_id,
        requester_user_id=member.user_id,
        requester_role=member.role,
    )


# Sprint 23 D4 Task 2 Step 2.3: notes promote — I-18 복제 + audit + BG embedding.
# Sprint 24 BL-064: chunk 0 + plain_text BG re-embedding 분기 + status endpoint.
# Sprint 24 Gemini P2 fix: pipeline DI 제거 — wrapper 가 자체 session_factory 로 fresh
# NotePipelineService 인스턴스화 (request-scoped session pool 점유 방지).
@router.post(
    "/{note_id}/promote",
    response_model=NotePromoteOut,
    status_code=202,
)
async def promote_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    body: NotePromoteIn,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member_fresh),
    service: NoteService = Depends(get_note_service),
) -> NotePromoteOut:
    """노트 → team workspace 복제 + audit row + 백그라운드 embedding 복제.

    202 Accepted — BG 흐름에서 EmbeddingChunk 복제 후 ItemPromotionAudit.embedding_status 갱신.
    project_id 는 복제본에서 None (cross-workspace 제약, 사용자가 별도 연결).

    Sprint 24 BL-064: chunk 0 + plain_text 분기 BG embedding 재생성 (wrapper 자체 pipeline).
    """
    return await service.promote(
        note_id=note_id,
        source_workspace_id=workspace_id,
        target_workspace_id=body.target_workspace_id,
        promoted_by_user_id=member.user_id,
        background_tasks=background_tasks,
        requester_role=member.role,
    )


# Sprint 24 BL-064: embedding-status polling endpoint (NEW).
@router.get("/{note_id}/embedding-status", response_model=EmbeddingStatusOut)
async def get_embedding_status(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_viewer),
    service: NoteService = Depends(get_note_service),
) -> EmbeddingStatusOut:
    """target note 의 embedding 진행 상태 polling.

    RBAC: viewer 이상 (read-only).
    응답: audit raw embedding_status (pending/processing/completed/failed/n/a) + 실 chunk count.
    """
    return await service.get_embedding_status(
        workspace_id,
        note_id,
        requester_user_id=member.user_id,
        requester_role=member.role,
    )
