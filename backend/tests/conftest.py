# 통합 테스트용 TestContainers PostgreSQL 픽스처.
"""function-scoped PostgreSQL 컨테이너 + async engine + session 픽스처.

session-scoped async fixture 는 pytest-asyncio 의 event loop scope 문제로
function-scoped 이벤트 루프와 충돌한다. 단순성을 위해 module-scoped 컨테이너 +
function-scoped engine/session 을 사용한다.

Sprint 15 Stage 4 T-1 추가 — memory 도메인용 auth_user + memory_client 픽스처.
personal_ws / team_ws / seed_memory 는 R2 이후 (Workspace.type 컬럼 + memory 모듈 신설) 추가.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
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


@pytest_asyncio.fixture
async def auth_user(integration_session):
    """Memory 도메인 테스트용 인증 사용자 — DB에 저장된 User."""
    from src.auth.models import User

    user = User(
        clerk_id="test_clerk_memory_user",
        display_name="메모리 테스터",
        email="memory_test@kairos.test",
    )
    integration_session.add(user)
    await integration_session.flush()
    return user


@pytest_asyncio.fixture
async def memory_client(integration_session, auth_user):
    """Memory API 테스트용 AsyncClient — get_current_user + get_async_session override.

    R2 이후 personal_ws fixture를 함께 의존성 주입 예정.
    """
    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session
    from src.main import app

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_async_session] = lambda: integration_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
