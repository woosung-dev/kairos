# Sprint 19 PR #2 — SQLModel.metadata vs alembic head schema drift detection.
"""alembic 의 autogenerate diff 알고리즘으로 schema drift 검출.

Codex v2 F-3 fix: pgvector/pgvector:pg16 image + Config 절대 경로 + env.py 외부 URL 우선.
Codex v2 F-4 fix: alembic.compare_metadata 사용 — column order / referred columns / UQ / nullable / indexes 전수 비교.

본 test 의 의미:
- D7 (project_members) 처럼 alembic 변경 없이 model __table_args__ 만 sync 한 경우 schema drift 위험.
- 신규 entity 추가 시 alembic revision 누락 즉시 catch.
- SQLModel.create_all (테스트용 conftest fixture) 과 alembic upgrade head (운영) 의 일관성 보장.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, text
from testcontainers.postgres import PostgresContainer

# 모든 model 을 metadata 에 등록
import src.auth.models  # noqa: F401
import src.workspaces.models  # noqa: F401
import src.projects.models  # noqa: F401
import src.meetings.models  # noqa: F401
import src.actions.models  # noqa: F401
import src.notes.models  # noqa: F401
import src.inbox.models  # noqa: F401
import src.embeddings.models  # noqa: F401
import src.memory.models  # noqa: F401

pytestmark = pytest.mark.integration

# 앱 루트 기준 alembic.ini 절대 경로 (Config 의 상대 경로 문제 회피).
# ★앱 디렉터리명을 문자열로 적지 않는다 — ADR-030 rename 때 `"backend"` 하드코딩이 이 테스트를 깼다.
APP_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = APP_ROOT / "alembic.ini"


def _include_object(obj, name, type_, reflected, compare_to):
    """compare_metadata 의 false positive 필터.

    - alembic_version: alembic 자체 관리 테이블 (model 측에 없음, 정상)
    """
    if type_ == "table" and name == "alembic_version":
        return False
    return True


# PR #2 (BUG-C01-EXT-FK) 가 신설/관리하는 constraint name allowlist.
# Codex v2 F-1 fix: 테이블 단위 exclude 대신 constraint name allowlist 로 false-negative 차단.
# 본 set 에 포함된 constraint 의 drift 는 절대 필터링 안 됨 (반드시 검출).
PR2_MANAGED_CONSTRAINTS = frozenset(
    {
        # PR #2 (BUG-C01-EXT-FK) composite FK 4 entity (D2 alembic + D4~D7 model)
        "fk_action_items_project_workspace",
        "fk_notes_project_workspace",
        "fk_mpl_project_workspace",
        "fk_mpl_meeting_workspace",
        "fk_mpl_workspace",
        "fk_project_members_project_workspace",
        # PR #2 UQ target (D3 meetings + D3a projects)
        "uq_meetings_id_workspace_id",
        "uq_projects_id_workspace_id",
        # PR #2 meeting_project_links workspace_id 컬럼 + 인덱스
        "ix_meeting_project_links_workspace_id",
        # Sprint 21 BL-050 Simple 4 composite FK (Codex 1차 MAJOR-1 수락)
        # 이름은 PR2_MANAGED_CONSTRAINTS 유지 (rename = surgical change 위반);
        # 본 set 의 의도는 "drift gate 의 catch allowlist" — generic.
        "fk_action_items_meeting_workspace",
        "fk_inbox_suggested_project_workspace",
        "fk_embedding_chunks_project_workspace",
        "fk_semantic_caches_project_workspace",
    }
)

# PR #2 managed columns — nullable 변화 catch.
PR2_MANAGED_COLUMNS = frozenset(
    {
        ("meeting_project_links", "workspace_id"),  # D6: NOT NULL 강제
        # Sprint 22 OBN-02 (server-side User onboarding tracker)
        ("users", "onboarding_step"),
        ("users", "onboarded_at"),
    }
)


def _diff_constraint_name(diff_entry) -> str | None:
    """diff_entry 에서 constraint/index name 추출 (op 별 위치 다름)."""
    if not isinstance(diff_entry, tuple) or len(diff_entry) < 2:
        return None
    # 각 op 의 payload 위치 다름 — 모든 항목 순회하며 name 속성 탐색
    for item in diff_entry[1:]:
        if hasattr(item, "name") and item.name:
            return str(item.name)
    return None


def _diff_column_key(diff_entry) -> tuple[str, str] | None:
    """diff_entry 가 column 변경이면 (table_name, column_name) 반환."""
    if not isinstance(diff_entry, tuple) or len(diff_entry) < 4:
        return None
    op_type = diff_entry[0]
    if op_type not in {"modify_nullable", "modify_type", "modify_default", "add_column", "remove_column"}:
        return None
    # modify_* 의 schema layout: (op, schema, table_name, column_name, ...)
    # PR #2 시점: alembic 1.13 — modify_nullable 의 경우 (op, schema, table_name, col_name, ...)
    if len(diff_entry) >= 4 and isinstance(diff_entry[2], str) and isinstance(diff_entry[3], str):
        return (diff_entry[2], diff_entry[3])
    return None


def _is_pr2_scope_drift(diff_entry) -> bool:
    """compare_metadata 가 반환한 diff 가 PR #2 scope 인지 판정.

    Codex v2 F-1: PR #2 managed constraint 와 column 의 drift 는 절대 필터링 안 됨.
    Sprint 15/16 의 기존 drift (PR #2 가 신설/수정하지 않은 constraint) 는 BL-047 carry-over.
    """
    if isinstance(diff_entry, list):
        return any(_is_pr2_scope_drift(d) for d in diff_entry)
    if not isinstance(diff_entry, tuple):
        return False

    # 1. PR #2 managed constraint 가 관련된 drift → 반드시 catch (filter X)
    name = _diff_constraint_name(diff_entry)
    if name and name in PR2_MANAGED_CONSTRAINTS:
        return True

    # 2. PR #2 managed column (mpl.workspace_id) 의 nullable/type drift → 반드시 catch
    col_key = _diff_column_key(diff_entry)
    if col_key and col_key in PR2_MANAGED_COLUMNS:
        return True

    op_type = diff_entry[0]

    # 3. 그 외 server_default / type / 인덱스 / column nullable / 다른 FK 추가/제거 등 =
    #    Sprint 15/16 의 기존 drift (BL-047 carry-over). filter 됨.
    if op_type in {
        "modify_default",
        "modify_type",
        "modify_nullable",
        "modify_comment",
        "add_index",
        "remove_index",
    }:
        return False
    # add_fk / remove_fk 도 managed constraint 가 아니면 BL-047 영역
    if op_type in {"add_fk", "remove_fk", "add_constraint", "remove_constraint"}:
        return False

    # 보수적으로 그 외 op 는 catch
    return True


def _do_compare(sync_conn):
    """async connection 의 run_sync 콜백 — sync API 인 compare_metadata 호출."""
    mc = MigrationContext.configure(
        sync_conn,
        opts={
            "compare_type": True,
            "compare_server_default": True,
            "include_object": _include_object,
        },
    )
    return compare_metadata(mc, SQLModel.metadata)


@pytest.mark.asyncio
async def test_alembic_upgrade_matches_sqlmodel_metadata():
    """빈 DB 에 alembic upgrade head → SQLModel.metadata 와 schema diff = 0."""
    # pgvector 확장 필수 (기존 migration b2c3d4e5f6a7 의 HNSW + halfvec)
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        sync_url = pg.get_connection_url()  # postgresql+psycopg2://...
        async_url = sync_url.replace("+psycopg2", "+asyncpg")

        engine = create_async_engine(async_url)

        try:
            # 1. pgvector 확장 활성화 (alembic 이전에)
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

            # 2. alembic upgrade head (env.py 가 외부 URL 우선 → 본 URL 사용)
            # 본 test 자체가 async 라 env.py 의 asyncio.run() 이 running loop 충돌 → to_thread 격리
            alembic_cfg = Config(str(ALEMBIC_INI))
            alembic_cfg.set_main_option("sqlalchemy.url", async_url)
            await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

            # 3. compare_metadata — alembic autogenerate diff 알고리즘 (sync API → run_sync)
            async with engine.connect() as conn:
                diff = await conn.run_sync(_do_compare)
        finally:
            await engine.dispose()

        # 4. drift = PR #2 scope 안의 diff 가 0 이어야 함.
        # Sprint 15/16 의 기존 drift (BL-047) 는 _is_pr2_scope_drift 에서 필터.
        actionable = [d for d in diff if d and _is_pr2_scope_drift(d)]
        assert not actionable, (
            "PR #2 scope schema drift detected (alembic.compare_metadata):\n"
            + "\n".join(repr(d) for d in actionable)
        )
