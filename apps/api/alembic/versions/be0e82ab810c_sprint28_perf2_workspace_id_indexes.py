# Sprint 28 PERF-2 — meetings / actions / inbox workspace_id 인덱스 신설.
"""sprint28_perf2_workspace_id_indexes

Revision ID: be0e82ab810c
Revises: 9dd1a3b80431
Create Date: 2026-05-26 00:29:50.655835

Sprint 27e Round 1 BUG-S27e-PERF-2 carry — 3 entity workspace_id FK 가
SQLModel `Field(foreign_key=...)` 만 명시, `index=True` 누락. Round B 측정
dashboard fanout 의 각 endpoint 1.5-2.5s 중 일부 = workspace_id WHERE seq scan
(rows 적은 dev 환경에서도 RTT 영향). 외부 5명 dogfooding 시 row 누적 후 직선 증가.

notes/models.py:22 만 `index=True` 정합 — 나머지 3 entity 균일 적용.

production 안전: `CREATE INDEX CONCURRENTLY` 명시 (ACCESS EXCLUSIVE lock 회피).
alembic 의 ddl autocommit_block + CONCURRENTLY 사용은 apps/backend/AGENTS.md §9 정합 패턴.
"""
from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "be0e82ab810c"
down_revision: str | Sequence[str] | None = "9dd1a3b80431"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# CONCURRENTLY 강제 — production 데이터 누적 시 ACCESS EXCLUSIVE 회피.
# alembic 의 transaction context 안 CONCURRENTLY 사용 불가 → autocommit_block.
def upgrade() -> None:
    """Upgrade schema — workspace_id 인덱스 3건 (CONCURRENTLY)."""
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_meetings_workspace_id ON meetings (workspace_id)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_action_items_workspace_id ON action_items (workspace_id)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_inbox_items_workspace_id ON inbox_items (workspace_id)"
        )


def downgrade() -> None:
    """Downgrade schema — 3 인덱스 drop."""
    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_inbox_items_workspace_id"
        )
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_action_items_workspace_id"
        )
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_meetings_workspace_id"
        )
