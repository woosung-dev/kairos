# Sprint 19 PR #1 BUG-C01-EXT v3 — workspace integrity audit (Codex F-5 신설)
"""single-FK 모델에서 cross-workspace 데이터 무결성 위반 row 탐지.

배경 (Codex F-5 Major):
- find_by_id(id, workspace_id) 시그니처 자체는 alembic 없이 안전 (schema 변경 무).
- 기존 cross-workspace row 가 있으면 fix 후 첫 조회가 None → 의도된 동작.
- 그러나 현재 FK 는 모두 단일 FK 라 DB constraint 가 workspace 일치를 보장하지 못함.
  → action_items.project_id, notes.project_id, meeting_project_links 가 잠재적 mismatch.
- 본 audit 는 mismatch row 0 보장. mismatch 발견 시 composite FK + backfill 은
  Sprint 19 PR #2 (BUG-C01-EXT-FK + alembic) 로 별도 진행.

검증 3건 (TestContainers 빈 DB 이므로 모두 0 row 통과 예상):
1. action_items.project_id ↔ projects.workspace_id 일치
2. notes.project_id ↔ projects.workspace_id 일치
3. meeting_project_links: meeting.workspace_id ↔ project.workspace_id 일치
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_action_items_project_workspace_match(
    integration_session: AsyncSession,
):
    """action_items.project_id 가 다른 workspace 의 project 를 가리키지 않는다."""
    result = await integration_session.execute(text("""
        SELECT a.id, a.workspace_id AS a_ws, p.workspace_id AS p_ws
        FROM action_items a
        JOIN projects p ON p.id = a.project_id
        WHERE a.workspace_id != p.workspace_id
        LIMIT 10
    """))
    mismatched = result.fetchall()
    assert len(mismatched) == 0, (
        f"Codex F-5 audit: action_items 의 {len(mismatched)} 행이 cross-workspace project 참조. "
        f"sample={mismatched[:3]}. composite FK 신설 + backfill 은 Sprint 19 PR #2 "
        f"(BUG-C01-EXT-FK + alembic) 로 분리."
    )


@pytest.mark.asyncio
async def test_notes_project_workspace_match(
    integration_session: AsyncSession,
):
    """notes.project_id 가 다른 workspace 의 project 를 가리키지 않는다."""
    result = await integration_session.execute(text("""
        SELECT n.id, n.workspace_id AS n_ws, p.workspace_id AS p_ws
        FROM notes n
        JOIN projects p ON p.id = n.project_id
        WHERE n.workspace_id != p.workspace_id
        LIMIT 10
    """))
    mismatched = result.fetchall()
    assert len(mismatched) == 0, (
        f"Codex F-5 audit: notes 의 {len(mismatched)} 행이 cross-workspace project 참조. "
        f"sample={mismatched[:3]}. composite FK 는 PR #2 분리."
    )


@pytest.mark.asyncio
async def test_meeting_project_links_workspace_match(
    integration_session: AsyncSession,
):
    """meeting_project_links 에서 meeting.workspace_id ↔ project.workspace_id 일치."""
    result = await integration_session.execute(text("""
        SELECT mpl.meeting_id, mpl.project_id,
               m.workspace_id AS m_ws, p.workspace_id AS p_ws
        FROM meeting_project_links mpl
        JOIN meetings m ON m.id = mpl.meeting_id
        JOIN projects p ON p.id = mpl.project_id
        WHERE m.workspace_id != p.workspace_id
        LIMIT 10
    """))
    mismatched = result.fetchall()
    assert len(mismatched) == 0, (
        f"Codex F-5 audit: meeting_project_links {len(mismatched)} 행이 cross-workspace 링크. "
        f"sample={mismatched[:3]}. MeetingProjectLink workspace 컬럼 + composite FK + backfill 은 "
        f"Sprint 19 PR #2 (BUG-C01-EXT-FK + alembic) 로 별도."
    )


@pytest.mark.asyncio
async def test_project_members_project_workspace_match(
    integration_session: AsyncSession,
):
    """project_members.workspace_id 가 project.workspace_id 와 일치 (Sprint 19 PR #1 C9).

    Codex F-5 cascade: project_members 가 추가된 (Sprint 6 L-6) 도메인 audit.
    composite FK 없으므로 잠재 mismatch 가능. 0 row 보장.
    """
    result = await integration_session.execute(text("""
        SELECT pm.id, pm.workspace_id AS pm_ws, p.workspace_id AS p_ws
        FROM project_members pm
        JOIN projects p ON p.id = pm.project_id
        WHERE pm.workspace_id != p.workspace_id
        LIMIT 10
    """))
    mismatched = result.fetchall()
    assert len(mismatched) == 0, (
        f"Codex F-5 audit (C9 cascade): project_members 의 {len(mismatched)} 행이 "
        f"cross-workspace project 참조. sample={mismatched[:3]}. "
        f"composite FK 는 Sprint 19 PR #2 분리."
    )
