# backend/src/workspaces/router.py
"""Workspace 라우터 — HTTP 전용."""
import uuid

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.workspaces.dependencies import get_workspace_service
from src.workspaces.schemas import CreateWorkspaceRequest
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
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    return await service.get_workspace(workspace_id)
