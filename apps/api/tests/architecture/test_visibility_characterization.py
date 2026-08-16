# visibility SSOT characterization — 리팩토링(C2~C5) 전후 SQL 불변 증명 스냅샷 게이트
"""4개 ORM visibility 필터의 compiled SQL + embeddings raw SQL 2종을
tests/fixtures/visibility/*.sql 스냅샷과 비교한다.

- C0 (본 커밋): 현행 구현의 스냅샷을 고정 — 이후 common/visibility.py 로 구현을
  이동해도 이 테스트가 그린이면 생성 SQL(=쿼리 플랜 입력)이 불변임을 CI 가 증명한다.
- 스냅샷 갱신: 의미 등가가 IDOR 매트릭스로 검증된 경우에만
  `UPDATE_VISIBILITY_SNAPSHOTS=1 uv run pytest tests/architecture/test_visibility_characterization.py`
- 2026-08-01 BL-EXT-CACHE-1 로 `embeddings_all_chunks_visible_sql` 스냅샷을
  의도적으로 갱신한다 (fail-closed 전환).
"""
import os
import pathlib
import uuid

import pytest
from sqlalchemy.dialects import postgresql
from sqlmodel import func, select

from src.actions.models import ActionItem
from src.actions.repository import _action_visibility_filter
from src.embeddings.repository import EmbeddingRepository
from src.meetings.models import Meeting
from src.meetings.repository import _meeting_visibility_filter
from src.notes.models import Note
from src.notes.repository import _note_visibility_filter
from src.projects.models import MeetingProjectLink, Project
from src.projects.repository import ProjectRepository

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "visibility"

WID = uuid.UUID("00000000-0000-0000-0000-00000000aaaa")
UID = uuid.UUID("00000000-0000-0000-0000-00000000bbbb")


def _compile(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


def _projects_member() -> str:
    stmt = select(Project).where(Project.workspace_id == WID)
    return _compile(ProjectRepository._apply_visibility_filter(stmt, UID, "member"))


def _projects_anonymous() -> str:
    stmt = select(Project).where(Project.workspace_id == WID)
    return _compile(ProjectRepository._apply_visibility_filter(stmt, None, "member"))


def _notes_member() -> str:
    stmt = select(Note).where(Note.workspace_id == WID)
    return _compile(_note_visibility_filter(stmt, UID, "member"))


def _actions_member() -> str:
    stmt = select(ActionItem).where(ActionItem.workspace_id == WID)
    return _compile(_action_visibility_filter(stmt, UID, "member"))


def _meetings_member() -> str:
    stmt = select(Meeting).where(Meeting.workspace_id == WID)
    return _compile(_meeting_visibility_filter(stmt, UID, "member"))


def _meetings_member_project_join() -> str:
    stmt = (
        select(Meeting)
        .where(Meeting.workspace_id == WID)
        .join(MeetingProjectLink, MeetingProjectLink.meeting_id == Meeting.id)
        .where(MeetingProjectLink.project_id == UID)
    )
    return _compile(_meeting_visibility_filter(stmt, UID, "member"))


def _notes_count_member() -> str:
    stmt = select(func.count()).select_from(Note).where(Note.workspace_id == WID)
    return _compile(_note_visibility_filter(stmt, UID, "member"))


def _embeddings_filter_sql() -> str:
    return EmbeddingRepository._visibility_filter_sql()


def _embeddings_all_chunks_visible_sql() -> str:
    # C2: 인라인 text() → common/visibility.py 상수 승격. 스냅샷(C0 캡처)과의
    # byte 일치가 이동의 무손실을 증명한다.
    from src.common.visibility import ALL_CHUNKS_VISIBLE_SQL

    return ALL_CHUNKS_VISIBLE_SQL


_CASES = {
    "projects_list_member": _projects_member,
    "projects_list_anonymous": _projects_anonymous,
    "notes_list_member": _notes_member,
    "actions_list_member": _actions_member,
    "meetings_list_member": _meetings_member,
    "meetings_list_member_project_join": _meetings_member_project_join,
    "notes_count_member": _notes_count_member,
    "embeddings_visibility_filter_sql": _embeddings_filter_sql,
    "embeddings_all_chunks_visible_sql": _embeddings_all_chunks_visible_sql,
}


@pytest.mark.parametrize("name", sorted(_CASES))
def test_visibility_sql_matches_snapshot(name: str) -> None:
    actual = _CASES[name]().rstrip() + "\n"
    path = FIXTURES / f"{name}.sql"
    if os.environ.get("UPDATE_VISIBILITY_SNAPSHOTS"):
        path.write_text(actual)
        pytest.skip(f"snapshot updated: {path.name}")
    expected = path.read_text()
    assert actual == expected, (
        f"visibility SQL drift in {name} — 의미 등가가 IDOR 매트릭스로 검증된 변경만 "
        f"UPDATE_VISIBILITY_SNAPSHOTS=1 로 스냅샷을 갱신할 것"
    )


def test_admin_bypass_returns_stmt_unchanged() -> None:
    """admin/owner 는 4개 필터 전부 no-op (필터 미적용) — 우회 경로 고정."""
    base = select(Project).where(Project.workspace_id == WID)
    for role in ("admin", "owner"):
        assert _compile(
            ProjectRepository._apply_visibility_filter(base, UID, role)
        ) == _compile(base)
    for fn, model in (
        (_note_visibility_filter, Note),
        (_action_visibility_filter, ActionItem),
        (_meeting_visibility_filter, Meeting),
    ):
        stmt = select(model).where(model.workspace_id == WID)
        for role in ("admin", "owner"):
            assert _compile(fn(stmt, UID, role)) == _compile(stmt)


def test_internal_skip_semantics_locked() -> None:
    """D1 모드 고정: notes/actions/meetings 는 role=None → 게이트 skip(내부 호출),
    projects 는 user=None → public-only 보수 모드 (skip 아님)."""
    for fn, model in (
        (_note_visibility_filter, Note),
        (_action_visibility_filter, ActionItem),
        (_meeting_visibility_filter, Meeting),
    ):
        stmt = select(model).where(model.workspace_id == WID)
        assert _compile(fn(stmt, UID, None)) == _compile(stmt)
    stmt = select(Project).where(Project.workspace_id == WID)
    filtered = _compile(ProjectRepository._apply_visibility_filter(stmt, None, None))
    assert "visibility" in filtered and filtered != _compile(stmt)
