"""BL-042 semantic_caches.max_visibility 컬럼 추가 — cache 누출 검증 fast path

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-16 02:50:00.000000

BL-041 (#54) 의 후속 — find_similar_cache 가 cache hit 시 sources 의 모든
chunk visibility 를 매번 검증하는 비용을 회피하기 위한 fast path 인덱스.

새 컬럼:
- max_visibility (text NOT NULL DEFAULT 'public') — 캐시된 sources 중
  가장 제한적인 visibility (public < draft < private). 캐시 저장 시 계산.
- 인덱스 (workspace_id, max_visibility) — public-only cache 빠른 조회.

read path 동작:
- requester admin/owner : 어떤 max_visibility 든 통과
- requester member/viewer + max_visibility = 'public' : 즉시 hit (검증 skip)
- 그 외 : BL-041 의 _all_chunks_visible 검증 후 hit/miss 결정
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "semantic_caches",
        sa.Column(
            "max_visibility",
            sa.String(),
            nullable=False,
            server_default="public",
        ),
    )
    op.create_index(
        "idx_semantic_caches_ws_max_vis",
        "semantic_caches",
        ["workspace_id", "max_visibility"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_semantic_caches_ws_max_vis", table_name="semantic_caches")
    op.drop_column("semantic_caches", "max_visibility")
