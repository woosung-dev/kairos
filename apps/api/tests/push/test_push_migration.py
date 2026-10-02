# PWA PR-2 마이그레이션 563de342c8ae (T-PWA-43) — 빈 DB upgrade → downgrade -1 → upgrade, 가산형 확인
"""`tests/integration/test_alembic_upgrade.py` 패턴 (Config 절대 경로 + env.py 외부 URL 우선 + to_thread).

검증:
- 단일 head = 이 리비전, down_revision = b3d5f8a1c2e4 (C-20)
- push_subscriptions 의 UNIQUE(endpoint) · FK(user_id → users.id, ON DELETE CASCADE) · index(user_id)
- 기존 테이블 스키마 변경 0 (직전 리비전 스냅샷과 비교)
- downgrade -1 이 테이블을 깨끗이 지우고, 다시 upgrade head 가 성공
- CASCADE 실동작 (사용자 삭제 → 구독 삭제)
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

pytestmark = pytest.mark.integration

APP_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = APP_ROOT / "alembic.ini"

PUSH_REVISION = "563de342c8ae"
PREVIOUS_HEAD = "b3d5f8a1c2e4"
TABLE = "push_subscriptions"


def _snapshot(sync_conn) -> dict[str, dict]:
    """테이블별 컬럼·PK·FK·UNIQUE·index·CHECK 스냅샷 (alembic_version 제외)."""
    inspector = sa.inspect(sync_conn)
    snapshot: dict[str, dict] = {}
    for table in sorted(inspector.get_table_names()):
        if table == "alembic_version":
            continue
        snapshot[table] = {
            "columns": [
                (c["name"], str(c["type"]), c["nullable"], str(c.get("default")))
                for c in inspector.get_columns(table)
            ],
            "pk": inspector.get_pk_constraint(table),
            "fks": sorted(
                (
                    fk["name"],
                    tuple(fk["constrained_columns"]),
                    fk["referred_table"],
                    tuple(fk["referred_columns"]),
                    tuple(sorted((fk.get("options") or {}).items())),
                )
                for fk in inspector.get_foreign_keys(table)
            ),
            "uniques": sorted(
                (u["name"], tuple(u["column_names"]))
                for u in inspector.get_unique_constraints(table)
            ),
            "indexes": sorted(
                (i["name"], tuple(i["column_names"]), bool(i["unique"]))
                for i in inspector.get_indexes(table)
            ),
            "checks": sorted(
                (c["name"], c["sqltext"]) for c in inspector.get_check_constraints(table)
            ),
        }
    return snapshot


def test_t_pwa_43_revision_chain_is_single_head():
    """T-PWA-43: head 는 이 리비전 1개, 직전 head 위에 선다 (병렬 head 없음)."""
    script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    assert script.get_heads() == [PUSH_REVISION]
    assert script.get_revision(PUSH_REVISION).down_revision == PREVIOUS_HEAD


@pytest.mark.asyncio
async def test_t_pwa_43_upgrade_downgrade_upgrade_is_additive():
    """T-PWA-43: 빈 DB upgrade head → downgrade -1 → upgrade head 성공 + 제약 3종 + 기존 테이블 변경 0."""
    with PostgresContainer("pgvector/pgvector:0.8.0-pg17") as pg:
        async_url = pg.get_connection_url().replace("+psycopg2", "+asyncpg")
        engine = create_async_engine(async_url)
        alembic_cfg = Config(str(ALEMBIC_INI))
        alembic_cfg.set_main_option("sqlalchemy.url", async_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

            # 1. 직전 head 까지 → 기존 스키마 스냅샷
            await asyncio.to_thread(command.upgrade, alembic_cfg, PREVIOUS_HEAD)
            async with engine.connect() as conn:
                before = await conn.run_sync(_snapshot)
            assert TABLE not in before

            # 2. head (= 이 리비전)
            await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
            async with engine.connect() as conn:
                after = await conn.run_sync(_snapshot)

            # 기존 테이블은 하나도 바뀌지 않는다 — 새 테이블 1개만 추가
            assert set(after) - set(before) == {TABLE}
            assert {name: after[name] for name in before} == before

            push = after[TABLE]
            assert [c[0] for c in push["columns"]] == [
                "id", "user_id", "endpoint", "p256dh", "auth", "created_at", "updated_at",
            ]
            assert all(nullable is False for _, _, nullable, _ in push["columns"])
            assert push["pk"]["constrained_columns"] == ["id"]
            assert push["uniques"] == [("uq_push_subscriptions_endpoint", ("endpoint",))]
            assert push["fks"] == [
                (
                    "fk_push_subscriptions_user_id_users",
                    ("user_id",),
                    "users",
                    ("id",),
                    (("ondelete", "CASCADE"),),
                )
            ]
            assert ("ix_push_subscriptions_user_id", ("user_id",), False) in push["indexes"]

            # CASCADE 실동작 — 사용자 삭제 시 구독도 사라진다
            user_id, subscription_id = uuid.uuid4(), uuid.uuid4()
            now = datetime.utcnow()
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "INSERT INTO users (id, display_name, email, created_at, updated_at) "
                        "VALUES (:id, 'push', 'push@kairos.test', :now, :now)"
                    ),
                    {"id": user_id, "now": now},
                )
                await conn.execute(
                    sa.text(
                        "INSERT INTO push_subscriptions "
                        "(id, user_id, endpoint, p256dh, auth, created_at, updated_at) "
                        "VALUES (:id, :uid, 'https://fcm.googleapis.com/fcm/send/x', 'p', 'a', :now, :now)"
                    ),
                    {"id": subscription_id, "uid": user_id, "now": now},
                )
                await conn.execute(sa.text("DELETE FROM users WHERE id = :id"), {"id": user_id})
                remaining = (
                    await conn.execute(sa.text("SELECT count(*) FROM push_subscriptions"))
                ).scalar_one()
            assert remaining == 0

            # 3. downgrade -1 → 직전 스키마와 동일
            await asyncio.to_thread(command.downgrade, alembic_cfg, "-1")
            async with engine.connect() as conn:
                downgraded = await conn.run_sync(_snapshot)
            assert downgraded == before

            # 4. 다시 upgrade head
            await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
            async with engine.connect() as conn:
                again = await conn.run_sync(_snapshot)
            assert again == after
        finally:
            await engine.dispose()
