# backend/src/meetings/router.py
"""Meeting 라우터 — HTTP 전용."""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from src.auth.dependencies import get_current_user
from src.auth.models import User
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
    current_user: User = Depends(get_current_user),
    service: MeetingService = Depends(get_meeting_service),
    pipeline: MeetingPipelineService = Depends(get_pipeline_service),
):
    result = await service.create_meeting(
        workspace_id=workspace_id,
        title=data.title,
        file_key=data.file_key,
        created_by_id=current_user.id,
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
    current_user: User = Depends(get_current_user),
    service: MeetingService = Depends(get_meeting_service),
):
    return await service.list_meetings(workspace_id, page, page_size)


@router.get("/{meeting_id}")
async def get_meeting(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MeetingService = Depends(get_meeting_service),
):
    return await service.get_meeting_detail(meeting_id)


@router.get("/{meeting_id}/status")
async def get_meeting_status(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MeetingService = Depends(get_meeting_service),
):
    return await service.get_meeting_status(meeting_id)
