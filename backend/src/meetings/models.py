# backend/src/meetings/models.py
"""Meeting 관련 모델."""
import uuid
from datetime import datetime

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel


class Meeting(SQLModel, table=True):
    __tablename__ = "meetings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    title: str
    file_key: str  # R2 저장 경로
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
    key_decisions: dict = Field(default_factory=list, sa_type=JSON)
    topics: dict = Field(default_factory=list, sa_type=JSON)
