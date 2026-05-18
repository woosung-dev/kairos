# SQLModel AsyncSession Level 3 통일 후 smoke test (BL-053 E1)
"""세션 팩토리가 SQLModel AsyncSession 인스턴스를 생성하고 .exec() 가 동작하는지 검증.

BL-053 (Sprint 20) 의 entry commit (E1) 가 `class_=AsyncSession` 의 AsyncSession 을
sqlmodel.ext.asyncio.session.AsyncSession (SA AsyncSession 의 subclass) 으로 전환한
직후 fail-closed gate. 단일 test fail 시 즉시 stop + commit revert.

Codex 1차 plan review (2026-05-18, REVISE) MINOR-3 finding 수락 반영:
async_sessionmaker(class_=SMAsyncSession) 이 실제 SM 인스턴스를 생성하는지
isinstance assert + .exec() 호출 smoke 로 검증.
"""
import pytest
from sqlalchemy import literal_column
from sqlmodel import select, text
from sqlmodel.ext.asyncio.session import AsyncSession as SMAsyncSession
from testcontainers.postgres import PostgresContainer

from src.common.database import (
    dispose_engine,
    get_session_factory,
    init_engine,
)


@pytest.fixture(scope="module")
def _postgres_smoke_container():
    """smoke 전용 PostgresContainer — pgvector 불필요."""
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.mark.asyncio
async def test_session_factory_creates_sqlmodel_async_session(
    _postgres_smoke_container,
) -> None:
    """async_sessionmaker(class_=AsyncSession) 가 SQLModel AsyncSession 인스턴스를 생성."""
    url = _postgres_smoke_container.get_connection_url().replace(
        "psycopg2", "asyncpg"
    )
    init_engine(url)
    try:
        factory = get_session_factory()
        async with factory() as session:
            # 1. SQLModel AsyncSession 타입 확인 (BL-053 entry 검증)
            assert isinstance(session, SMAsyncSession), (
                f"세션이 SQLModel AsyncSession 이 아닙니다: {type(session).__name__}"
            )

            # 2. raw text 는 execute() 로 (BL-054 manifest G4 — exec 불가)
            raw_result = await session.execute(text("SELECT 1"))
            assert raw_result.scalar_one() == 1

            # 3. typed select 는 exec() 로 (BL-054 manifest G1 선행 검증)
            typed_result = await session.exec(select(literal_column("1")))
            assert typed_result.one() == 1
    finally:
        await dispose_engine()
