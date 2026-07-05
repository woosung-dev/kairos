# backend/src/workspaces/router.py
"""Workspace 라우터 — HTTP 전용."""
import uuid

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.rbac import require_owner, require_viewer
from src.workspaces.dependencies import get_workspace_service
from src.workspaces.models import WorkspaceMember
from src.workspaces.schemas import CreateWorkspaceRequest, UpdateWorkspaceSettingsRequest
from src.workspaces.service import WorkspaceService

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


@router.post("", status_code=201)
async def create_workspace(
    data: CreateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    return await service.create_workspace(data.name, current_user.id)


@router.get("")
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    return await service.list_workspaces(current_user.id)


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: uuid.UUID,
    # BUG-C01 (Sentinel P0 2026-05-17): require_viewer 누락으로 비멤버가 ws 상세 leak
    # → ws name/owner/memberCount/threshold 노출. Codex 정적 분석 의심 → 실 검증 확정.
    member: WorkspaceMember = Depends(require_viewer),
    service: WorkspaceService = Depends(get_workspace_service),
):
    return await service.get_workspace(workspace_id)


@router.patch("/{workspace_id}/settings")
async def update_workspace_settings(
    workspace_id: uuid.UUID,
    data: UpdateWorkspaceSettingsRequest,
    member: WorkspaceMember = Depends(require_owner),
    service: WorkspaceService = Depends(get_workspace_service),
):
    return await service.update_settings(workspace_id, data.inbox_threshold)


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_owner),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """워크스페이스 영구 삭제 (owner 전용, personal 차단, 산하 데이터 전체 cascade)."""
    await service.delete_workspace(workspace_id)
