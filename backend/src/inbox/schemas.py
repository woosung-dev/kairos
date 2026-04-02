# backend/src/inbox/schemas.py
"""Inbox Pydantic V2 입출력 스키마."""
from pydantic import BaseModel, Field


class ClassifyInboxRequest(BaseModel):
    """Inbox 아이템을 프로젝트에 연결 확정."""

    project_ids: list[str] = Field(alias="projectIds")
    model_config = {"populate_by_name": True}
