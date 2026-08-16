"""sprint15 memory items + workspaces type + 보조 테이블

Revision ID: a1b2c3d4e5f6
Revises: 5f9a2b7ee3a4
Create Date: 2026-05-14 00:00:00.000000

Sprint 15 Stage 4 R2 (patch §5 P-R2 적용):
- workspaces.type 컬럼 (personal | team) + partial unique index
- memory_items 테이블 (raw_content, distilled_json, status enum, FK embedding_chunks)
- promotion_audit 테이블 (R6 1-button promote audit row)
- memory_ai_calls 테이블 (C2 — usage tracking)
- memory_query_embedding_cache (C3 — pgvector 1536d query cache)
- memory_events 테이블 (C7 — DB-backed metrics, Cloud Run stateless)
- backfill SQL: 기존 user 전체에 personal workspace + WorkspaceMember 자동 생성 (A8 fix)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '5f9a2b7ee3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — Sprint 15 Recall-first wedge."""
    # ──────────────────────────────────────────────────────────────
    # 1. workspaces.type 컬럼 — 기본값 'team' (기존 row 호환)
    # ──────────────────────────────────────────────────────────────
    op.add_column(
        "workspaces",
        sa.Column("type", sa.String(), nullable=False, server_default="team"),
    )
    op.create_check_constraint(
        "ck_workspaces_type",
        "workspaces",
        "type IN ('personal', 'team')",
    )
    # personal workspace 는 owner당 1개 — partial unique index
    op.create_index(
        "uq_workspaces_owner_personal",
        "workspaces",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text("type = 'personal'"),
    )

    # ──────────────────────────────────────────────────────────────
    # 2. memory_items — Recall-first wedge 핵심 테이블
    # ──────────────────────────────────────────────────────────────
    op.create_table(
        "memory_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(), nullable=False),  # 'voice' | 'text'
        sa.Column("raw_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("distilled_json", JSONB, nullable=True),
        sa.Column("r2_audio_key", sa.String(), nullable=True),
        sa.Column("embedding_chunk_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="processing",
        ),
        # processing | transcription_pending | embedding_pending |
        # embedding_failed | active | archived
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["embedding_chunk_id"], ["embedding_chunks.id"]),
    )
    op.create_index(
        "ix_memory_items_workspace_created",
        "memory_items",
        ["workspace_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_memory_items_user_created",
        "memory_items",
        ["user_id", sa.text("created_at DESC")],
    )

    # ──────────────────────────────────────────────────────────────
    # 3. promotion_audit — R6 1-button promote audit row
    # ──────────────────────────────────────────────────────────────
    op.create_table(
        "promotion_audit",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("memory_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source_workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_project_id", UUID(as_uuid=True), nullable=True),
        sa.Column("promoted_by_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("promoted_note_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "embedding_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),  # pending | processing | completed | failed
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["memory_id"], ["memory_items.id"]),
        sa.ForeignKeyConstraint(["source_workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["target_workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["target_project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["promoted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["promoted_note_id"], ["notes.id"]),
    )

    # ──────────────────────────────────────────────────────────────
    # 4. backfill — 기존 user 전체에 personal workspace + member (A8 fix)
    # 주의: idempotent (NOT EXISTS 가드). downgrade reversibility 없음.
    # ──────────────────────────────────────────────────────────────
    op.execute(
        """
        INSERT INTO workspaces (id, owner_id, name, type, inbox_threshold, created_at, updated_at)
        SELECT gen_random_uuid(),
               u.id,
               COALESCE(u.display_name, '사용자') || '의 개인 Kairos',
               'personal',
               0.9,
               now(),
               now()
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM workspaces w
            WHERE w.owner_id = u.id AND w.type = 'personal'
        );
        """
    )
    op.execute(
        """
        INSERT INTO workspace_members (id, workspace_id, user_id, role)
        SELECT gen_random_uuid(), w.id, w.owner_id, 'owner'
        FROM workspaces w
        WHERE w.type = 'personal'
        AND NOT EXISTS (
            SELECT 1 FROM workspace_members m
            WHERE m.workspace_id = w.id AND m.user_id = w.owner_id
        );
        """
    )

    # ──────────────────────────────────────────────────────────────
    # 5. memory_ai_calls — C2 usage/latency tracking
    # ──────────────────────────────────────────────────────────────
    op.create_table(
        "memory_ai_calls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("memory_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("call_type", sa.String(), nullable=False),
        # transcription | distill | embedding
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("elapsed_ms", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status", sa.String(), nullable=False, server_default="success"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["memory_id"], ["memory_items.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
    )
    op.create_index(
        "ix_memory_ai_calls_workspace_created",
        "memory_ai_calls",
        ["workspace_id", sa.text("created_at DESC")],
    )

    # ──────────────────────────────────────────────────────────────
    # 6. memory_query_embedding_cache — C3 pgvector 1536d query cache
    # ──────────────────────────────────────────────────────────────
    op.create_table(
        "memory_query_embedding_cache",
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("normalized_query", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint(
            "workspace_id", "normalized_query",
            name="pk_memory_query_embedding_cache",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
    )

    # ──────────────────────────────────────────────────────────────
    # 7. memory_events — C7 DB-backed metrics (Cloud Run stateless 정합)
    # ──────────────────────────────────────────────────────────────
    op.create_table(
        "memory_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        # capture | recall | promote
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("event_metadata", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_memory_events_workspace_type_created",
        "memory_events",
        ["workspace_id", "event_type", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    """Downgrade schema — 역순 drop.

    주의: backfill로 생성된 personal workspace + member row는 자동 삭제하지 않는다.
    데이터 손실 위험 — manual rollback only.
    """
    op.drop_index(
        "ix_memory_events_workspace_type_created", table_name="memory_events"
    )
    op.drop_table("memory_events")

    op.drop_table("memory_query_embedding_cache")

    op.drop_index(
        "ix_memory_ai_calls_workspace_created", table_name="memory_ai_calls"
    )
    op.drop_table("memory_ai_calls")

    op.drop_table("promotion_audit")

    op.drop_index("ix_memory_items_user_created", table_name="memory_items")
    op.drop_index("ix_memory_items_workspace_created", table_name="memory_items")
    op.drop_table("memory_items")

    op.drop_index("uq_workspaces_owner_personal", table_name="workspaces")
    op.drop_constraint("ck_workspaces_type", "workspaces", type_="check")
    op.drop_column("workspaces", "type")
