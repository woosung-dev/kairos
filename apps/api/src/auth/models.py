# apps/api/src/auth/models.py
"""User 모델."""
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # 외부 인증 공급자의 사용자 ID = Better Auth `auth_user.id` (ADR-031).
    # JWT 의 sub 클레임과 조인되는 유일한 키다.
    auth_user_id: str | None = Field(default=None, unique=True, index=True)
    # ★레거시. ADR-031 컷오버 +7일 뒤 별도 리비전에서 DROP 한다
    #   (`docs/development/migrations.md` 2단계 배포 규약).
    #   그때까지 남겨두는 이유는 둘이다 — ① 롤백 창에서 구 이미지가 이 컬럼을 쓴다
    #   ② 레거시 행이 "누구였는지" 식별해 새 auth_user_id 를 이식할 수 있는 유일한 단서다.
    clerk_id: str | None = Field(default=None, unique=True, index=True)
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
