# backend/src/projects/router.py
"""Project 라우터 — HTTP 전용."""
import uuid

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.projects.dependencies import get_project_service
from src.projects.schemas import (
    AddMeetingProjectRequest,
    CreateProjectRequest,
    UpdateProjectRequest,
)
from src.projects.service import ProjectService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/projects",
    tags=["projects"],
)

meeting_project_router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/meetings/{meeting_id}/projects",
    tags=["meeting-projects"],
)


# --- Project CRUD ---


@router.get("")
async def list_projects(
    workspace_id: uuid.UUID,
    status: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    return await service.list_projects(workspace_id, status=status, tag=tag, page=page, page_size=page_size)


@router.get("/{project_id}")
async def get_project(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    return await service.get_project(project_id)


@router.post("", status_code=201)
async def create_project(
    workspace_id: uuid.UUID,
    data: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    return await service.create_project(
        workspace_id=workspace_id,
        title=data.title,
        created_by_id=current_user.id,
        description=data.description,
        tags=data.tags,
    )


@router.patch("/{project_id}")
async def update_project(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    data: UpdateProjectRequest,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    return await service.update_project(
        project_id=project_id,
        title=data.title,
        description=data.description,
        status=data.status,
        tags=data.tags,
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    await service.delete_project(project_id)


@router.post("/{project_id}/archive")
async def archive_project(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    return await service.archive_project(project_id)


# --- Meeting-Project Link ---


@meeting_project_router.post("", status_code=201)
async def add_meeting_project(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    data: AddMeetingProjectRequest,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    return await service.add_meeting_project(meeting_id, uuid.UUID(data.project_id))


@meeting_project_router.delete("/{project_id}", status_code=204)
async def remove_meeting_project(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    await service.remove_meeting_project(meeting_id, project_id)
