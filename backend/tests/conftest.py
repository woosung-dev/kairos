# 통합 테스트용 TestContainers PostgreSQL 픽스처.
"""function-scoped PostgreSQL 컨테이너 + async engine + session 픽스처.

session-scoped async fixture 는 pytest-asyncio 의 event loop scope 문제로
function-scoped 이벤트 루프와 충돌한다. 단순성을 위해 module-scoped 컨테이너 +
function-scoped engine/session 을 사용한다.
"""
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel
from testcontainers.postgres import PostgresContainer

# SQLModel.metadata.create_all 이전에 모든 테이블 모델을 임포트해야 등록됨.
import src.auth.models  # noqa: F401 — users
import src.workspaces.models  # noqa: F401 — workspaces, workspace_members, workspace_invites
import src.projects.models  # noqa: F401 — projects, project_members, meeting_project_links
import src.meetings.models  # noqa: F401 — meetings, transcript_segments, meeting_summaries
import src.actions.models  # noqa: F401 — action_items
import src.notes.models  # noqa: F401 — notes
import src.inbox.models  # noqa: F401 — inbox_items
import src.embeddings.models  # noqa: F401 — embedding_chunks, semantic_caches


@pytest.fixture(scope="module")
def postgres_container():
    """pgvector 확장 포함 PostgreSQL 컨테이너 (module-scoped, 동기)."""
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        yield pg


@pytest_asyncio.fixture
async def integration_session(postgres_container):
    """테스트별 독립 async session — 테스트 종료 시 rollback."""
    url = postgres_container.get_connection_url().replace(
        "psycopg2", "asyncpg"
    )
    engine = create_async_engine(url, echo=False)

    # 스키마 초기화 (첫 실행 시) + pgvector 확장 활성화
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()

    await engine.dispose()
