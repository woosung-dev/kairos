# common/visibility.py SSOT 단위 테스트 — decide 매트릭스 + 기존 구현과의 SQL 등가성
"""C1 게이트 2종:
1. decide_project_access 매트릭스 (DB 불필요 — 순수함수).
2. 신규 빌더(apply_*)가 기존 도메인 필터와 compiled SQL 동일함을 증명 —
   C2~C5 사이트 교체가 no-op 임을 소비자 0 시점에 선증명.
3. raw SQL 상수 2종(필터/anti-join)의 코어 술어 토큰 일치 — 인코딩 2계보가
   같은 규칙을 공유함을 기계 강제.
"""
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql
from sqlmodel import select

from src.actions.models import ActionItem
from src.actions.repository import _action_visibility_filter
from src.common.visibility import (
    ALL_CHUNKS_VISIBLE_SQL,
    PROJECT_VISIBILITY_FILTER_SQL,
    Access,
    RequesterContext,
    apply_fk_project_visibility,
    apply_project_visibility,
    decide_project_access,
)
from src.embeddings.repository import EmbeddingRepository
from src.notes.models import Note
from src.notes.repository import _note_visibility_filter
from src.projects.models import Project
from src.projects.repository import ProjectRepository

WID = uuid.UUID("00000000-0000-0000-0000-00000000aaaa")
CREATOR = uuid.UUID("00000000-0000-0000-0000-00000000cccc")
OTHER = uuid.UUID("00000000-0000-0000-0000-00000000dddd")


def _project(visibility: str) -> SimpleNamespace:
    return SimpleNamespace(visibility=visibility, created_by_id=CREATOR)


# ── 1. decide 매트릭스 ─────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("visibility", "user_id", "expected"),
    [
        # public: 누구나 (user 부재 포함)
        ("public", CREATOR, Access.ALLOW),
        ("public", OTHER, Access.ALLOW),
        ("public", None, Access.ALLOW),
        # draft: creator 만
        ("draft", CREATOR, Access.ALLOW),
        ("draft", OTHER, Access.DENY),
        ("draft", None, Access.DENY),
        # private: user 있으면 멤버십 판정 위임, 없으면 DENY
        ("private", CREATOR, Access.NEED_MEMBERSHIP),
        ("private", OTHER, Access.NEED_MEMBERSHIP),
        ("private", None, Access.DENY),
        # unknown 값: fail-closed (D7)
        ("secret", CREATOR, Access.DENY),
        ("", OTHER, Access.DENY),
    ],
)
def test_decide_matrix(visibility: str, user_id, expected: Access) -> None:
    assert decide_project_access(_project(visibility), user_id) is expected


def test_requester_context_properties() -> None:
    assert RequesterContext(OTHER, "admin").is_admin
    assert RequesterContext(OTHER, "owner").is_admin
    assert not RequesterContext(OTHER, "member").is_admin
    assert not RequesterContext(OTHER, "viewer").is_admin
    assert RequesterContext(OTHER, None).is_internal
    assert not RequesterContext(None, "member").is_internal


# ── 2. ORM 빌더 ↔ 기존 필터 compiled SQL 등가성 ───────────────────────────────

def _compile(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


def test_apply_project_visibility_equals_legacy_member_path() -> None:
    base = select(Project).where(Project.workspace_id == WID)
    legacy = ProjectRepository._apply_visibility_filter(base, OTHER, "member")
    new = apply_project_visibility(base, RequesterContext(OTHER, "member"))
    assert _compile(new) == _compile(legacy)


def test_apply_project_visibility_equals_legacy_anonymous_path() -> None:
    base = select(Project).where(Project.workspace_id == WID)
    legacy = ProjectRepository._apply_visibility_filter(base, None, "member")
    new = apply_project_visibility(base, RequesterContext(None, "member"))
    assert _compile(new) == _compile(legacy)


def test_apply_project_visibility_admin_and_role_none_modes() -> None:
    """D1 고정: admin 은 no-op, role=None(+user 有)은 projects 에선 member 분기."""
    base = select(Project).where(Project.workspace_id == WID)
    assert _compile(
        apply_project_visibility(base, RequesterContext(OTHER, "owner"))
    ) == _compile(base)
    legacy = ProjectRepository._apply_visibility_filter(base, OTHER, None)
    new = apply_project_visibility(base, RequesterContext(OTHER, None))
    assert _compile(new) == _compile(legacy)


@pytest.mark.parametrize(
    ("model", "col_name", "legacy_fn"),
    [
        (Note, "project_id", _note_visibility_filter),
        (ActionItem, "project_id", _action_visibility_filter),
    ],
)
def test_apply_fk_project_visibility_equals_legacy(model, col_name, legacy_fn) -> None:
    base = select(model).where(model.workspace_id == WID)
    legacy = legacy_fn(base, OTHER, "member")
    new = apply_fk_project_visibility(
        base, getattr(model, col_name), RequesterContext(OTHER, "member")
    )
    assert _compile(new) == _compile(legacy)
    # 내부호출(role=None) skip 모드 동일
    assert _compile(
        apply_fk_project_visibility(
            base, getattr(model, col_name), RequesterContext(OTHER, None)
        )
    ) == _compile(legacy_fn(base, OTHER, None))


# ── 3. raw SQL 상수 — 기존 사이트와 byte 일치 + 코어 술어 토큰 일치 ───────────

def _norm(sql: str) -> str:
    return " ".join(sql.split())


# 코어 술어의 canonical 토큰 시퀀스 — 규칙 변경 시 이 문자열과 두 상수를 함께 수정.
CORE_PREDICATE_TOKENS = (
    "p.visibility = 'public' "
    "OR (p.visibility = 'draft' AND p.created_by_id = :req_uid) "
    "OR (p.visibility = 'private' AND EXISTS ( "
    "SELECT 1 FROM project_members pm "
    "WHERE pm.project_id = p.id AND pm.user_id = :req_uid "
    "AND EXISTS ( SELECT 1 FROM workspace_members wm "
    "WHERE wm.workspace_id = p.workspace_id AND wm.user_id = :req_uid ) ))"
)


def test_filter_sql_constant_matches_legacy_byte_exact() -> None:
    assert PROJECT_VISIBILITY_FILTER_SQL == EmbeddingRepository._visibility_filter_sql()


def test_core_predicate_identical_across_both_raw_sql_constants() -> None:
    assert CORE_PREDICATE_TOKENS in _norm(PROJECT_VISIBILITY_FILTER_SQL)
    assert CORE_PREDICATE_TOKENS in _norm(ALL_CHUNKS_VISIBLE_SQL)
