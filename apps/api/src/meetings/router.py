# apps/api/src/meetings/router.py
"""Meeting 라우터 — HTTP 전용."""
import uuid

from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import Response

from src.auth.rbac import require_member, require_member_fresh, require_viewer
from src.workspaces.models import WorkspaceMember
from src.meetings.dependencies import get_meeting_service, get_pipeline_service
from src.meetings.pipeline_service import MeetingPipelineService
from src.meetings.schemas import (
    CaptureTextRequest,
    CreateMeetingRequest,
    MeetingPromoteIn,
    MeetingPromoteOut,
)
from src.meetings.service import MeetingService

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/meetings", tags=["meetings"])


@router.post("", status_code=202)
async def create_meeting(
    workspace_id: uuid.UUID,
    data: CreateMeetingRequest,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member),
    service: MeetingService = Depends(get_meeting_service),
    pipeline: MeetingPipelineService = Depends(get_pipeline_service),
):
    result = await service.create_meeting(
        workspace_id=workspace_id,
        title=data.title,
        file_key=data.file_key,
        created_by_id=member.user_id,
        recorded_at=data.recorded_at,
    )
    # 백그라운드 파이프라인 실행 — Codex F-1: path workspace_id 동반 전달
    background_tasks.add_task(
        pipeline.process_meeting, uuid.UUID(result["id"]), workspace_id
    )
    return result


@router.post("/capture", status_code=202)
async def capture_text_meeting(
    workspace_id: uuid.UUID,
    data: CaptureTextRequest,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member),
    service: MeetingService = Depends(get_meeting_service),
    pipeline: MeetingPipelineService = Depends(get_pipeline_service),
):
    """텍스트 캡처 — STT 없이 직접 AI 분석. 202 Accepted."""
    result = await service.create_meeting(
        workspace_id=workspace_id,
        title=data.title,
        file_key="",
        created_by_id=member.user_id,
        source="text",
    )
    meeting_id = uuid.UUID(result["id"])
    # Codex F-1: path workspace_id 동반 전달
    background_tasks.add_task(
        pipeline.capture_text, meeting_id, workspace_id, data.transcript_text
    )
    return result


@router.get("")
async def list_meetings(
    workspace_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    project_id: uuid.UUID | None = Query(default=None, alias="projectId"),
    member: WorkspaceMember = Depends(require_viewer),
    service: MeetingService = Depends(get_meeting_service),
):
    return await service.list_meetings(
        workspace_id,
        page,
        page_size,
        project_id,
        requester_user_id=member.user_id,
        requester_role=member.role,
    )


@router.get("/{meeting_id}")
async def get_meeting(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_viewer),
    service: MeetingService = Depends(get_meeting_service),
):
    return await service.get_meeting_detail(
        meeting_id,
        workspace_id,
        requester_user_id=member.user_id,
        requester_role=member.role,
    )


@router.get("/{meeting_id}/export")
async def export_meeting(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    format: str = Query(default="md", pattern="^(md|json)$"),
    member: WorkspaceMember = Depends(require_viewer),
    service: MeetingService = Depends(get_meeting_service),
):
    content, filename, media_type = await service.export_meeting(
        meeting_id,
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


@router.get("/{meeting_id}/status")
async def get_meeting_status(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_viewer),
    service: MeetingService = Depends(get_meeting_service),
):
    return await service.get_meeting_status(
        meeting_id,
        workspace_id,
        requester_user_id=member.user_id,
        requester_role=member.role,
    )


# Sprint 23 D4 Task 2 Step 2.2: meetings promote — I-18 복제 + audit + BG embedding.
@router.post(
    "/{meeting_id}/promote",
    response_model=MeetingPromoteOut,
    status_code=202,
)
async def promote_meeting(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    body: MeetingPromoteIn,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member_fresh),
    service: MeetingService = Depends(get_meeting_service),
) -> MeetingPromoteOut:
    """회의 → team workspace 복제 + audit row + 백그라운드 embedding 복제.

    202 Accepted — BG 흐름에서 EmbeddingChunk 복제 후 ItemPromotionAudit.embedding_status 갱신.
    """
    return await service.promote(
        meeting_id=meeting_id,
        source_workspace_id=workspace_id,
        target_workspace_id=body.target_workspace_id,
        promoted_by_user_id=member.user_id,
        background_tasks=background_tasks,
        requester_role=member.role,
    )
