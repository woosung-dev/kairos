# backend/src/meetings/router.py
"""Meeting 라우터 — HTTP 전용."""
import uuid

from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import Response

from src.auth.rbac import require_member, require_viewer
from src.workspaces.models import WorkspaceMember
from src.meetings.dependencies import get_meeting_service, get_pipeline_service
from src.meetings.pipeline_service import MeetingPipelineService
from src.meetings.schemas import CreateMeetingRequest
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
    # 백그라운드에서 파이프라인 실행
    background_tasks.add_task(pipeline.process_meeting, uuid.UUID(result["id"]))
    return result


@router.get("")
async def list_meetings(
    workspace_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    member: WorkspaceMember = Depends(require_viewer),
    service: MeetingService = Depends(get_meeting_service),
):
    return await service.list_meetings(workspace_id, page, page_size)


@router.get("/{meeting_id}")
async def get_meeting(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_viewer),
    service: MeetingService = Depends(get_meeting_service),
):
    return await service.get_meeting_detail(meeting_id)


@router.get("/{meeting_id}/export")
async def export_meeting(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    format: str = Query(default="md", pattern="^(md|json)$"),
    member: WorkspaceMember = Depends(require_viewer),
    service: MeetingService = Depends(get_meeting_service),
):
    content, filename, media_type = await service.export_meeting(meeting_id, format)
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
    return await service.get_meeting_status(meeting_id)
