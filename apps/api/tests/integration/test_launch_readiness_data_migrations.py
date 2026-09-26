# 2026-09-27 실사용 준비 Gate 0 — 데이터 마이그레이션 2종 (a9c4e2f7b1d0 · b3d5f8a1c2e4) 행 단위 검증
"""스키마 드리프트(test_alembic_upgrade.py)만으로는 backfill·정제 UPDATE 가 맞는 행을 건드리는지 모른다.
직전 리비전에 행을 심고 head 로 올려 결과를 본다.

- a9c4e2f7b1d0: 원본 작성자가 직접 올린 promote 사본만 is_shared=true (E2-05). 남이 올린 사본·원본이
  사라진 사본·형식이 깨진 metadata 는 작성자 전용으로 남고, 마이그레이션은 멈추지 않는다.
- b3d5f8a1c2e4: 실패 회의의 원문 error_message(서명 URL 포함)를 일반 문구로 바꾼다. NULL 은 그대로.
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlmodel import text
from testcontainers.postgres import PostgresContainer

pytestmark = pytest.mark.integration

APP_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = APP_ROOT / "alembic.ini"
BEFORE = "c1a7e0b5d3f2"
SCRUB = "회의 처리 중 오류가 발생했습니다. 다시 시도하거나 관리자에게 문의하세요."


async def _insert(conn: AsyncConnection, table: str, values: dict) -> None:
    """NOT NULL·기본값 없는 컬럼은 타입별 더미로 채운다 (테이블 전 컬럼을 테스트에 적지 않기 위해)."""
    rows = (await conn.execute(text(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = :t AND is_nullable = 'NO' AND column_default IS NULL"
    ), {"t": table})).all()
    dummy = {
        "uuid": lambda: uuid.uuid4(), "text": lambda: "x", "character varying": lambda: "x",
        "integer": lambda: 0, "bigint": lambda: 0, "boolean": lambda: False,
        "double precision": lambda: 0.0,
    }
    vals = dict(values)
    exprs: dict[str, str] = {}
    for name, dtype in rows:
        if name in vals:
            continue
        if dtype.startswith("timestamp"):
            exprs[name] = "now()"
        elif dtype in ("json", "jsonb"):
            exprs[name] = "CAST('{}' AS jsonb)"
        else:
            vals[name] = dummy[dtype]()
    for name, v in list(vals.items()):
        if isinstance(v, str) and v.startswith("SQL:"):
            exprs[name] = v[4:]
            del vals[name]
    cols = [*vals, *exprs]
    placeholders = [f":{c}" for c in vals] + list(exprs.values())
    await conn.execute(
        text(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"),
        vals,
    )


async def _pairs(conn: AsyncConnection, sql: str) -> dict[uuid.UUID, object]:
    return {row[0]: row[1] for row in (await conn.execute(text(sql))).all()}


def _jsonb(payload: str | None) -> str:
    return "SQL:NULL" if payload is None else f"SQL:CAST('{payload}' AS jsonb)"


@pytest.mark.asyncio
async def test_is_shared_backfill_and_error_scrub():
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        url = pg.get_connection_url().replace("+psycopg2", "+asyncpg")
        engine = create_async_engine(url)
        cfg = Config(str(ALEMBIC_INI))
        cfg.set_main_option("sqlalchemy.url", url)
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await asyncio.to_thread(command.upgrade, cfg, BEFORE)

            author, other = uuid.uuid4(), uuid.uuid4()
            ws = uuid.uuid4()
            src, own_copy, foreign_copy, orphan_copy = (uuid.uuid4() for _ in range(4))
            meet = {k: uuid.uuid4() for k in ("raw", "null")}
            async with engine.begin() as conn:
                for uid in (author, other):
                    await _insert(conn, "users", {"id": uid})
                await _insert(conn, "workspaces", {"id": ws, "owner_id": author, "name": "w"})
                for mid, uid in (
                    (src, author), (own_copy, author), (foreign_copy, other), (orphan_copy, author),
                ):
                    await _insert(conn, "memory_items", {
                        "id": mid, "user_id": uid, "workspace_id": ws, "type": "text",
                        "raw_content": "r", "status": "active",
                    })
                events = [
                    (author, f'{{"source_memory_id": "{src}", "new_memory_id": "{own_copy}"}}'),
                    # 수정 전에는 남의 메모도 올릴 수 있었다 — 그 사본은 공유로 확정하지 않는다
                    (other, f'{{"source_memory_id": "{src}", "new_memory_id": "{foreign_copy}"}}'),
                    # 원본이 사라진 사본
                    (author, f'{{"source_memory_id": "{uuid.uuid4()}", "new_memory_id": "{orphan_copy}"}}'),
                    # 형식이 깨진 metadata 는 건너뛴다 (마이그레이션이 멈추면 안 된다)
                    (author, None), (author, '"scalar"'), (author, "[1, 2]"),
                    (author, '{"source_memory_id": "not-a-uuid", "new_memory_id": 12345}'),
                ]
                for uid, meta in events:
                    await _insert(conn, "memory_events", {
                        "workspace_id": ws, "user_id": uid, "event_type": "promote",
                        "event_metadata": _jsonb(meta),
                    })
                for key, err in (
                    ("raw", "AccessDenied https://acc.r2.cloudflarestorage.com/b/k?X-Amz-Credential=AKIA"),
                    ("null", None),
                ):
                    await _insert(conn, "meetings", {
                        "id": meet[key], "workspace_id": ws, "title": "t", "file_key": "k",
                        "status": "failed", "created_by_id": author,
                        "error_message": err if err is not None else "SQL:NULL",
                    })

            await asyncio.to_thread(command.upgrade, cfg, "head")

            async with engine.connect() as conn:
                shared = await _pairs(conn, "SELECT id, is_shared FROM memory_items")
                errors = await _pairs(conn, "SELECT id, error_message FROM meetings")
            assert shared == {src: False, own_copy: True, foreign_copy: False, orphan_copy: False}
            assert errors[meet["raw"]] == SCRUB
            assert errors[meet["null"]] is None

            # downgrade → 재upgrade 가 같은 결과 (컬럼 drop 후 backfill 재실행)
            await asyncio.to_thread(command.downgrade, cfg, BEFORE)
            await asyncio.to_thread(command.upgrade, cfg, "head")
            async with engine.connect() as conn:
                again = await _pairs(conn, "SELECT id, is_shared FROM memory_items")
            assert again == shared
        finally:
            await engine.dispose()
