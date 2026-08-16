# apps/api/src/meetings/models.py
"""Meeting 관련 모델."""
import uuid
from datetime import datetime

from sqlmodel import JSON, Field, SQLModel, UniqueConstraint


class Meeting(SQLModel, table=True):
    __tablename__ = "meetings"
    __table_args__ = (
        # Sprint 19 PR #2 D3: composite FK target 선행 조건 (meeting_project_links 의 (workspace_id, meeting_id))
        UniqueConstraint("id", "workspace_id", name="uq_meetings_id_workspace_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Sprint 28 PERF-2 — index=True (alembic be0e82ab810c, ix_meetings_workspace_id 정합).
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    title: str
    file_key: str  # R2 저장 경로
    source: str | None = None  # None=오디오, "text"=텍스트 캡처
    recorded_at: datetime | None = None
    duration_sec: int | None = None
    status: str = "uploading"  # uploading|transcribing|analyzing|completed|failed
    error_message: str | None = None
    has_transcript: bool = False
    has_summary: bool = False
    action_item_count: int = 0
    created_by_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TranscriptSegment(SQLModel, table=True):
    __tablename__ = "transcript_segments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    meeting_id: uuid.UUID = Field(foreign_key="meetings.id")
    speaker: str = "Speaker"  # Sprint 1: 화자 분리 없음
    start_sec: float
    end_sec: float
    text: str


class MeetingSummary(SQLModel, table=True):
    __tablename__ = "meeting_summaries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    meeting_id: uuid.UUID = Field(foreign_key="meetings.id", unique=True)
    summary: str
    key_decisions: list = Field(default_factory=list, sa_type=JSON)
    topics: list = Field(default_factory=list, sa_type=JSON)
