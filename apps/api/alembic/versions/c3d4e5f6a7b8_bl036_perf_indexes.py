"""BL-036 hot path 성능 — workspace_members + projects 복합 인덱스 추가

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-16 00:00:00.000000

배경: Sprint 17 QA 에서 sidebar 진입 시 3-6s 지연 관찰. 원인은 BE 측의
hot path 두 군데가 인덱스 없이 sequence scan 으로 처리되던 것.

1. **workspace_members(workspace_id, user_id)** — 모든 보호 라우트의
   require_viewer/member/... RoleChecker 가 매 요청마다 호출. Neon 환경
   RTT 50-100ms 위에 seq scan 더해져 누적 200-400ms 베이스라인.

2. **projects(workspace_id, status)** — sidebar 의 projects?status=active
   list 쿼리. workspace_id FK 만으로는 인덱스 없고 status 필터 항상 동반.

3. **projects(workspace_id, sort_order)** — sidebar 의 ORDER BY sort_order
   처리. composite scan 으로 sort 회피.

PG FK constraint 는 인덱스 자동 생성 안 함 — SQLModel `Field(foreign_key=...)`
도 마찬가지. 명시적 추가 필요.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. workspace_members hot path — RBAC check 매 요청
    op.create_index(
        "idx_workspace_members_ws_user",
        "workspace_members",
        ["workspace_id", "user_id"],
        unique=False,
    )

    # 2. projects(workspace_id, status) — sidebar list
    op.create_index(
        "idx_projects_workspace_status",
        "projects",
        ["workspace_id", "status"],
        unique=False,
    )

    # 3. projects(workspace_id, sort_order) — ORDER BY 처리
    op.create_index(
        "idx_projects_workspace_sort",
        "projects",
        ["workspace_id", "sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_projects_workspace_sort", table_name="projects")
    op.drop_index("idx_projects_workspace_status", table_name="projects")
    op.drop_index("idx_workspace_members_ws_user", table_name="workspace_members")
