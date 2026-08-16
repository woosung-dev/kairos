# apps/api/src/auth/models.py
"""User 모델."""
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    clerk_id: str = Field(unique=True, index=True)
    display_name: str
    email: str
    avatar_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # Sprint 22 OBN-02: 서버 측 영속 onboarding 단계 (0=NOT_STARTED, 1=WORKSPACE_CREATED, 2=FIRST_PROJECT, 3=FIRST_MEETING, 4=FIRST_RAG)
    onboarding_step: int = Field(
        default=0, sa_column_kwargs={"server_default": "0"}, nullable=False
    )
    onboarded_at: datetime | None = Field(default=None, nullable=True)
