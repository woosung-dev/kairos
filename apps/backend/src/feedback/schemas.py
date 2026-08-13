# 피드백 제출 요청 Pydantic V2 스키마 (camelCase alias)
import uuid

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    rating: int | None = Field(default=None, ge=1, le=5)
    is_anonymous: bool = Field(default=False, alias="isAnonymous")
    # 작성 시점 활성 워크스페이스 (FE 의 activeWorkspaceId, 없을 수 있음)
    workspace_id: uuid.UUID | None = Field(default=None, alias="workspaceId")
    # 작성 페이지 SPA 경로 (서버가 알 수 없으므로 FE 가 전달)
    page_url: str | None = Field(default=None, alias="pageUrl", max_length=2000)

    model_config = {"populate_by_name": True}
