# apps/backend/src/embeddings/models.py
"""임베딩 청크 + 시맨틱 캐시 모델."""
import uuid
from datetime import datetime, timedelta

from sqlmodel import JSON, Column, Field, ForeignKeyConstraint, SQLModel, Text

try:
    # Sprint 16 ADR-020: Vector(fp32, 4B) → Halfvec(fp16, 2B) — 저장 50% 절감 (I-20)
    from pgvector.sqlalchemy import HALFVEC
except ImportError:
    HALFVEC = None  # 패키지 미설치 시 fallback


class EmbeddingChunk(SQLModel, table=True):
    """계층적 임베딩 청크. Level 2(문단)가 검색 대상."""

    __tablename__ = "embedding_chunks"
    __table_args__ = (
        # Sprint 21 BL-050 Simple 4: cross-workspace project_id 차단.
        # nullable FK → MATCH SIMPLE NULL row 면제 (workspace-level 임베딩 정상).
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_embedding_chunks_project_workspace",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id", index=True
    )
    source_id: uuid.UUID = Field(nullable=False)
    source_type: str = Field(nullable=False)  # 'meeting' | 'note' | 'action' | 'memory'
    chunk_text: str = Field(sa_column=Column(Text, nullable=False))
    chunk_index: int = Field(default=0)
    chunk_level: int = Field(default=2)  # 0=문서, 1=섹션/화자, 2=문단
    parent_chunk_id: uuid.UUID | None = Field(
        default=None, foreign_key="embedding_chunks.id", index=True
    )
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(HALFVEC(1536)) if HALFVEC else Column(Text),
    )
    metadata_json: dict = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=datetime.utcnow)


def _default_expires_at() -> datetime:
    return datetime.utcnow() + timedelta(days=7)


class SemanticCache(SQLModel, table=True):
    """시맨틱 캐시. 유사 질문 → 캐시 답변 반환."""

    __tablename__ = "semantic_caches"
    __table_args__ = (
        # Sprint 21 BL-050 Simple 4: cross-workspace project_id 차단.
        # nullable FK → MATCH SIMPLE NULL row 면제 (workspace-level 캐시 정상).
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_semantic_caches_project_workspace",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id"
    )
    question: str = Field(sa_column=Column(Text, nullable=False))
    question_embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(HALFVEC(1536)) if HALFVEC else Column(Text),
    )
    answer: str = Field(sa_column=Column(Text, nullable=False))
    sources: list = Field(default_factory=list, sa_type=JSON)
    hit_count: int = Field(default=0)
    # BL-042: 캐시된 sources 중 가장 제한적인 visibility (public < draft < private).
    # find_similar_cache 의 fast path — public 은 visibility 검증 skip 가능.
    max_visibility: str = Field(default="public")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=_default_expires_at)
