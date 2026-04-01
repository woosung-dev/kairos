# backend/src/workspaces/schemas.py
"""Workspace 스키마."""
import uuid

from pydantic import BaseModel


class CreateWorkspaceRequest(BaseModel):
    name: str


class AddMemberRequest(BaseModel):
    email: str


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class WorkspaceDetailResponse(WorkspaceResponse):
    member_count: int = 0


class MemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role: str
