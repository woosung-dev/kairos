# backend/src/projects/router.py
"""Project 라우터 — HTTP 전용.

Sprint 19 PR #1 C9 (Codex F-1/F-3/F-4/F-6):
모든 service 호출이 workspace_id 명시 전달. cross-tenant → 404 lock-in.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.auth.rbac import (
    require_admin,
    require_member,
    require_member_fresh,
    require_viewer,
)
from src.workspaces.models import WorkspaceMember
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


class AddProjectMemberRequest(BaseModel):
    """ProjectMember 추가 요청 (Sprint 6 L-6)."""
    user_id: str = Field(alias="userId")
    role: str = "member"

    model_config = {"populate_by_name": True}


# --- Project CRUD ---


@router.get("")
async def list_projects(
    workspace_id: uuid.UUID,
    status: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    member: WorkspaceMember = Depends(require_viewer),
    service: ProjectService = Depends(get_project_service),
):
    return await service.list_projects(
        workspace_id,
        requester_user_id=member.user_id,
        requester_role=member.role,
        status=status,
        tag=tag,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}")
async def get_project(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_viewer),
    service: ProjectService = Depends(get_project_service),
):
    return await service.get_project(
        workspace_id=workspace_id,
        project_id=project_id,
        requester_user_id=member.user_id,
        requester_role=member.role,
    )


@router.post("", status_code=201)
async def create_project(
    workspace_id: uuid.UUID,
    data: CreateProjectRequest,
    member: WorkspaceMember = Depends(require_member),
    service: ProjectService = Depends(get_project_service),
):
    return await service.create_project(
        workspace_id=workspace_id,
        title=data.title,
        created_by_id=member.user_id,
        description=data.description,
        # W-5: 미지정 시 초대에서 시드된 멤버 기본 visibility → 없으면 public
        visibility=data.visibility
        or member.default_project_visibility
        or "public",
        tags=data.tags,
    )


@router.patch("/{project_id}")
async def update_project(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    data: UpdateProjectRequest,
    member: WorkspaceMember = Depends(require_member_fresh),
    service: ProjectService = Depends(get_project_service),
):
    # BE-T15: visibility 변경은 admin 이상 강제 (L-7)
    if data.visibility is not None and member.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="visibility 변경은 admin 이상만 가능합니다.")
    return await service.update_project(
        workspace_id=workspace_id,
        project_id=project_id,
        title=data.title,
        description=data.description,
        status=data.status,
        visibility=data.visibility,
        tags=data.tags,
    )


# --- ProjectMember (Sprint 6 L-6, BE-T7) ---


@router.get("/{project_id}/members")
async def list_project_members(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_viewer),
    service: ProjectService = Depends(get_project_service),
):
    """프로젝트 멤버 목록 (viewer 이상)."""
    return await service.list_members(workspace_id, project_id)


@router.post("/{project_id}/members", status_code=201)
async def add_project_member(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    data: AddProjectMemberRequest,
    member: WorkspaceMember = Depends(require_admin),
    service: ProjectService = Depends(get_project_service),
):
    """프로젝트 멤버 추가 (admin 이상). cross-workspace 검증은 service 책임."""
    return await service.add_member(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=uuid.UUID(data.user_id),
        role=data.role,
    )


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_project_member(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_admin),
    service: ProjectService = Depends(get_project_service),
):
    """프로젝트 멤버 제거 (admin 이상)."""
    await service.remove_member(workspace_id, project_id, user_id)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_admin),
    service: ProjectService = Depends(get_project_service),
):
    await service.delete_project(workspace_id, project_id)


@router.post("/{project_id}/archive")
async def archive_project(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_admin),
    service: ProjectService = Depends(get_project_service),
):
    return await service.archive_project(workspace_id, project_id)


# --- Meeting-Project Link ---


@meeting_project_router.post("", status_code=201)
async def add_meeting_project(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    data: AddMeetingProjectRequest,
    member: WorkspaceMember = Depends(require_member),
    service: ProjectService = Depends(get_project_service),
):
    return await service.add_meeting_project(
        workspace_id, meeting_id, uuid.UUID(data.project_id)
    )


@meeting_project_router.delete("/{project_id}", status_code=204)
async def remove_meeting_project(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    project_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_member),
    service: ProjectService = Depends(get_project_service),
):
    await service.remove_meeting_project(workspace_id, meeting_id, project_id)
