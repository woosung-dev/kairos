# Sprint 24 Wave 2 T-AUDIT-VIEW — ItemPromotionAudit 응답 스키마
"""Settings Audit 탭 (admin only) endpoint 응답 스키마.

camelCase alias — FE 와 일관 (admin_router / projects 와 동일 패턴).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditPromotionItem(BaseModel):
    """단일 promote audit row 응답."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    item_type: str = Field(alias="itemType")
    source_item_id: str = Field(alias="sourceItemId")
    new_item_id: str = Field(alias="newItemId")
    source_workspace_id: str = Field(alias="sourceWorkspaceId")
    target_workspace_id: str = Field(alias="targetWorkspaceId")
    promoted_by_user_id: str = Field(alias="promotedByUserId")
    embedding_status: str = Field(alias="embeddingStatus")
    created_at: datetime = Field(alias="createdAt")


class AuditPromotionPage(BaseModel):
    """audit 목록 페이지 응답 — cursor 기반 (more 페이지 있음 여부 + 다음 cursor)."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[AuditPromotionItem]
    next_cursor: str | None = Field(default=None, alias="nextCursor")
