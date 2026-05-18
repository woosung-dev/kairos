"""Sprint 19 PR #2 BUG-C01-EXT-FK — composite FK 4 entity (DB-level tenant constraint).

Revision ID: e5f6g7h8i9ja
Revises: d4e5f6a7b8c9
Create Date: 2026-05-18

배경:
- PR #1 (#88+#89) 의 service-level cross-workspace 가드 + matrix anchor + real DB + 4 audit 0 row 통과.
- 본 revision = service-level 검증의 defense-in-depth 로 PostgreSQL composite FK 추가.

scope (4 entity):
1. meetings(id, workspace_id) UNIQUE 신설 — composite FK target 선행 조건
   (projects(id, workspace_id) UNIQUE 은 이미 7ebd009f89a4 에서 신설)
2. action_items composite FK (workspace_id, project_id) → projects(workspace_id, id)
3. notes composite FK (nullable project_id, MATCH SIMPLE → IS NULL 시 면제)
4. meeting_project_links workspace_id 컬럼 신설 + backfill + NOT NULL + 단순 FK + 2 composite FK

scale trade-off:
- 현재 dogfooding (~수십 row) = 단순 `ADD CONSTRAINT` ms 단위 lock. 본 revision 단순 패턴 적용.
- production scale (>1만 row) 시점에는 `NOT VALID` + 별도 `VALIDATE CONSTRAINT` 2단계 권장 (BL-045 등재).
- `LOCK TABLE` 미적용 — Cloud Run 컨테이너 startup = 트래픽 받기 전 자연 maintenance window.

backfill 안전성 (PR #1 audit 4 case 0 row 통과 기반):
- meeting_project_links 의 m.workspace_id == p.workspace_id 보장 → workspace_id = m.workspace_id 단순 derive.
- action_items / notes / project_members 의 secondary FK mismatch 0 row 보장.
- staging hard gate (사용자 manual): 4 audit SQL 재실행 후 mismatch 0 + NULL 0 확인 후 머지.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6g7h8i9ja'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """4 entity composite FK 일괄 추가."""
    # 1. meetings(id, workspace_id) UNIQUE — composite FK target 선행
    op.create_unique_constraint(
        "uq_meetings_id_workspace_id", "meetings", ["id", "workspace_id"]
    )

    # 2. action_items composite FK (defense-in-depth, 기존 single-FK 유지)
    op.create_foreign_key(
        "fk_action_items_project_workspace",
        "action_items",
        "projects",
        ["workspace_id", "project_id"],
        ["workspace_id", "id"],
    )

    # 3. notes composite FK (nullable project_id, MATCH SIMPLE)
    op.create_foreign_key(
        "fk_notes_project_workspace",
        "notes",
        "projects",
        ["workspace_id", "project_id"],
        ["workspace_id", "id"],
    )

    # 4. meeting_project_links — workspace_id 신설 (7ebd009f89a4 패턴 그대로)
    op.add_column(
        "meeting_project_links",
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_meeting_project_links_workspace_id"),
        "meeting_project_links",
        ["workspace_id"],
    )
    # backfill: m.workspace_id == p.workspace_id 보장 전제 (audit 0 row PASS)
    op.execute(
        """
        UPDATE meeting_project_links mpl
        SET workspace_id = m.workspace_id
        FROM meetings m
        WHERE m.id = mpl.meeting_id
        """
    )
    op.alter_column("meeting_project_links", "workspace_id", nullable=False)
    op.create_foreign_key(
        "fk_mpl_workspace",
        "meeting_project_links",
        "workspaces",
        ["workspace_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_mpl_project_workspace",
        "meeting_project_links",
        "projects",
        ["workspace_id", "project_id"],
        ["workspace_id", "id"],
    )
    op.create_foreign_key(
        "fk_mpl_meeting_workspace",
        "meeting_project_links",
        "meetings",
        ["workspace_id", "meeting_id"],
        ["workspace_id", "id"],
    )


def downgrade() -> None:
    """역순 drop. mpl.workspace_id 컬럼 drop = 데이터 영구 손실 (개발/test 환경 한정)."""
    op.drop_constraint("fk_mpl_meeting_workspace", "meeting_project_links", type_="foreignkey")
    op.drop_constraint("fk_mpl_project_workspace", "meeting_project_links", type_="foreignkey")
    op.drop_constraint("fk_mpl_workspace", "meeting_project_links", type_="foreignkey")
    op.drop_index(
        op.f("ix_meeting_project_links_workspace_id"),
        table_name="meeting_project_links",
    )
    op.drop_column("meeting_project_links", "workspace_id")

    op.drop_constraint("fk_notes_project_workspace", "notes", type_="foreignkey")
    op.drop_constraint(
        "fk_action_items_project_workspace", "action_items", type_="foreignkey"
    )
    op.drop_constraint("uq_meetings_id_workspace_id", "meetings", type_="unique")
