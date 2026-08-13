"""BL-050 Simple 4 — composite FK (action_items.meeting + inbox.suggested + embedding_chunks.project + semantic_caches.project).

Revision ID: cf903ab3dd37
Revises: e5f6g7h8i9ja
Create Date: 2026-05-18

배경:
- Sprint 19 PR #2 (BUG-C01-EXT-FK) 의 후속 hardening.
- 4 entity 의 cross-workspace single-FK 패턴을 composite FK 로 강화.
- 4 entity 모두 nullable → MATCH SIMPLE NULL row 자동 면제.

scope (4 composite FK):
1. action_items (workspace_id, meeting_id) → meetings(workspace_id, id)
2. inbox_items (workspace_id, ai_suggested_project_id) → projects(workspace_id, id)
3. embedding_chunks (workspace_id, project_id) → projects(workspace_id, id)
4. semantic_caches (workspace_id, project_id) → projects(workspace_id, id)

scale trade-off (Sprint 19 PR #2 와 동일):
- dogfooding scale (~수십 row) = 단순 ADD CONSTRAINT ms 단위 lock. 본 revision 단순 패턴.
- production scale (>1만 row) 진입 시 BL-049 NOT VALID + VALIDATE 2단계 권장.
- Cloud Run 컨테이너 startup = 트래픽 받기 전 자연 maintenance window.

preflight 안전성 (D1 audit 4 PASS 기반):
- D1 audit 가 이미 mismatch 0 확인.
- 본 preflight DO $$ 는 production 데이터 mismatch 대비 이중 안전망.
- RAISE EXCEPTION on mismatch > 0 → alembic abort + 명확한 메시지.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'cf903ab3dd37'
down_revision: Union[str, Sequence[str], None] = 'e5f6g7h8i9ja'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """4 entity composite FK 일괄 추가.

    preflight (PR #2 패턴): mismatch row 가 있으면 RAISE EXCEPTION 으로 fail-fast.
    """
    # 0. preflight — 4 mismatch check
    op.execute(
        """
        DO $$
        DECLARE
            cnt_ai_m INT;
            cnt_ib INT;
            cnt_ec INT;
            cnt_sc INT;
        BEGIN
            SELECT COUNT(*) INTO cnt_ai_m FROM action_items a
              JOIN meetings m ON m.id = a.meeting_id
              WHERE a.meeting_id IS NOT NULL AND a.workspace_id != m.workspace_id;
            IF cnt_ai_m > 0 THEN
                RAISE EXCEPTION 'BL-050 preflight: action_items.meeting mismatch=% (composite FK 추가 불가, fix 후 재실행)', cnt_ai_m;
            END IF;

            SELECT COUNT(*) INTO cnt_ib FROM inbox_items i
              JOIN projects p ON p.id = i.ai_suggested_project_id
              WHERE i.ai_suggested_project_id IS NOT NULL AND i.workspace_id != p.workspace_id;
            IF cnt_ib > 0 THEN
                RAISE EXCEPTION 'BL-050 preflight: inbox_items.suggested mismatch=% (composite FK 추가 불가, fix 후 재실행)', cnt_ib;
            END IF;

            SELECT COUNT(*) INTO cnt_ec FROM embedding_chunks ec
              JOIN projects p ON p.id = ec.project_id
              WHERE ec.project_id IS NOT NULL AND ec.workspace_id != p.workspace_id;
            IF cnt_ec > 0 THEN
                RAISE EXCEPTION 'BL-050 preflight: embedding_chunks.project mismatch=% (composite FK 추가 불가, fix 후 재실행)', cnt_ec;
            END IF;

            SELECT COUNT(*) INTO cnt_sc FROM semantic_caches sc
              JOIN projects p ON p.id = sc.project_id
              WHERE sc.project_id IS NOT NULL AND sc.workspace_id != p.workspace_id;
            IF cnt_sc > 0 THEN
                RAISE EXCEPTION 'BL-050 preflight: semantic_caches.project mismatch=% (composite FK 추가 불가, fix 후 재실행)', cnt_sc;
            END IF;
        END $$;
        """
    )

    # 1. action_items meeting composite FK
    op.create_foreign_key(
        "fk_action_items_meeting_workspace",
        "action_items",
        "meetings",
        ["workspace_id", "meeting_id"],
        ["workspace_id", "id"],
    )

    # 2. inbox suggested project composite FK
    op.create_foreign_key(
        "fk_inbox_suggested_project_workspace",
        "inbox_items",
        "projects",
        ["workspace_id", "ai_suggested_project_id"],
        ["workspace_id", "id"],
    )

    # 3. embedding_chunks project composite FK
    op.create_foreign_key(
        "fk_embedding_chunks_project_workspace",
        "embedding_chunks",
        "projects",
        ["workspace_id", "project_id"],
        ["workspace_id", "id"],
    )

    # 4. semantic_caches project composite FK
    op.create_foreign_key(
        "fk_semantic_caches_project_workspace",
        "semantic_caches",
        "projects",
        ["workspace_id", "project_id"],
        ["workspace_id", "id"],
    )


def downgrade() -> None:
    """역순 drop. 데이터 영향 0 (constraint drop 만)."""
    op.drop_constraint("fk_semantic_caches_project_workspace", "semantic_caches", type_="foreignkey")
    op.drop_constraint("fk_embedding_chunks_project_workspace", "embedding_chunks", type_="foreignkey")
    op.drop_constraint("fk_inbox_suggested_project_workspace", "inbox_items", type_="foreignkey")
    op.drop_constraint("fk_action_items_meeting_workspace", "action_items", type_="foreignkey")
