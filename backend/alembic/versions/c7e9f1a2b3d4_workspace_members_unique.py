# BUG-WS-MEMBER-UNIQUE (S28b) — workspace_members (workspace_id, user_id) UNIQUE 제약 신설.
"""workspace_members_unique

Revision ID: c7e9f1a2b3d4
Revises: be0e82ab810c
Create Date: 2026-05-29

2차 정검 P1 (BUG-WS-MEMBER-UNIQUE). workspace_members 에 (workspace_id, user_id)
UNIQUE 제약 부재 → lazy-seed/invite-accept 의 app-level NOT EXISTS 가드가
멀티워커(Cloud Run >1 인스턴스) interleave 에서 backstop 없이 중복 멤버십 row 허용
(Channel A 강제 2-트랜잭션 interleave 테스트로 실증). DB 제약으로 차단.

upgrade: 기존 중복 row dedup(가장 작은 id 보존) → UNIQUE 제약 추가.
dedup 보존 정책: 동일 (workspace_id, user_id) 중복 시 id 최소 row 유지. 실 사용자
0명 + 멀티워커 미발생으로 현 시점 중복 0 예상(dedup 은 no-op 방어).
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e9f1a2b3d4"
down_revision: str | Sequence[str] | None = "be0e82ab810c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Dedup 후 (workspace_id, user_id) UNIQUE 제약 추가."""
    # 1) 중복 row 정리 — 동일 (workspace_id, user_id) 쌍에서 id 최소 row 만 보존.
    op.execute(
        """
        DELETE FROM workspace_members a
        USING workspace_members b
        WHERE a.workspace_id = b.workspace_id
          AND a.user_id = b.user_id
          AND a.id > b.id
        """
    )
    # 2) UNIQUE 제약 추가 (행 수 적은 dev/early-stage DB — 직접 ADD CONSTRAINT 안전).
    op.create_unique_constraint(
        "uq_workspace_member", "workspace_members", ["workspace_id", "user_id"]
    )


def downgrade() -> None:
    """UNIQUE 제약 제거."""
    op.drop_constraint("uq_workspace_member", "workspace_members", type_="unique")
