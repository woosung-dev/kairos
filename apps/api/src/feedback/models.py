# 사용자 dogfooding 피드백을 저장하는 SQLModel 테이블
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class FeedbackEntry(SQLModel, table=True):
    __tablename__ = "feedback_entries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # 피드백 작성자 (서버에서 강제 — 클라이언트 입력 신뢰 안 함)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    # 작성 시점 활성 워크스페이스 컨텍스트 (없을 수 있음 — user-level 피드백)
    workspace_id: uuid.UUID | None = Field(
        default=None, foreign_key="workspaces.id", index=True
    )
    # 1-5 별점 (선택)
    rating: int | None = Field(default=None)
    body: str
    # 익명 제출 표시 (그래도 user_id 는 internal 보존)
    is_anonymous: bool = Field(default=False)
    # 컨텍스트 메타 — 작성 페이지 URL + user agent (디버깅/재현용)
    page_url: str | None = Field(default=None)
    user_agent: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
