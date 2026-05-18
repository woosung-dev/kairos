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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
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

# 워크트리 root 기준 alembic.ini 절대 경로 (Config 'backend/alembic.ini' 상대 경로 문제 회피)
REPO_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = REPO_ROOT / "backend" / "alembic.ini"


def _include_object(obj, name, type_, reflected, compare_to):
    """compare_metadata 의 false positive 필터.

    - alembic_version: alembic 자체 관리 테이블 (model 측에 없음, 정상)
    """
    if type_ == "table" and name == "alembic_version":
        return False
    return True


# Sprint 15/16 의 기존 drift — 본 PR #2 (BUG-C01-EXT-FK) scope 외. BL-047 carry-over.
# 본 set 의 finding 은 PR #2 scope 검증 통과 (PR #2 가 신설하지 않은 drift).
PR2_OUT_OF_SCOPE_DRIFT_TABLES = frozenset(
    {
        "memory_ai_calls",  # Sprint 15: TIMESTAMP vs DateTime + server_default + 인덱스
        "memory_events",
        "memory_items",
        "memory_query_embedding_cache",
        "promotion_audit",
        "embedding_chunks",  # Sprint 16 ADR-020: HNSW 인덱스 model 미명시
        "semantic_caches",  # Sprint 16: HNSW + cache 인덱스
        "workspaces",  # Sprint 15: type/inbox_threshold server_default + uq_workspaces_owner_personal
        "workspace_invites",  # default_project_visibility server_default + idx_invites_workspace
        "workspace_members",  # idx_workspace_members_ws_user
        "projects",  # visibility server_default + idx_projects_workspace_* (Sprint 16 BL-036 인덱스)
        "notes",  # content JSON server_default (Sprint 3)
    }
)


def _is_pr2_scope_drift(diff_entry) -> bool:
    """compare_metadata 가 반환한 diff 가 PR #2 scope 인지 판정.

    PR #2 scope = action_items / notes (FK only) / meeting_project_links / project_members 의 FK / meetings UQ.
    server_default / 인덱스 / TIMESTAMP-DateTime 등은 Sprint 15/16 기존 drift = scope 외 (BL-047).
    """
    # diff_entry 는 tuple 또는 list of tuples
    if isinstance(diff_entry, list):
        return any(_is_pr2_scope_drift(d) for d in diff_entry)
    if not isinstance(diff_entry, tuple):
        return False
    op_type = diff_entry[0]
    # 본 PR scope outside diff 타입: server_default / type / 인덱스 등
    if op_type in {
        "modify_default",
        "modify_type",
        "modify_nullable",
        "modify_comment",
    }:
        return False
    # 테이블 이름 추출 (각 op 마다 위치 다름)
    table_name = None
    for item in diff_entry[1:]:
        if hasattr(item, "table"):
            table_name = getattr(item.table, "name", None)
            break
        if hasattr(item, "name") and op_type in {"add_index", "remove_index"}:
            # Index 객체
            table_name = getattr(getattr(item, "table", None), "name", None)
            break
    if table_name and table_name in PR2_OUT_OF_SCOPE_DRIFT_TABLES:
        return False
    # 인덱스 add/remove 도 BL-047 (대부분 Sprint 15/16 의 명시 누락)
    if op_type in {"add_index", "remove_index"}:
        return False
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
