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
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel, text
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
import src.memory.models  # noqa: F401 — memory_items, memory_ai_calls, memory_events, promotion_audit, memory_query_embedding_cache
import src.common.promote_models  # noqa: F401 — item_promotion_audit (Sprint 23 D4)
import src.feedback.models  # noqa: F401 — feedback_entries (Sprint 28 Wave 1)

# Sprint 24 Wave 2 T-N+2 — composite FK 회귀 안전망 fixture (SCN-FK-01~12 자동화).
# fixture 모듈 import 로 pytest 가 fixture 를 collect (별도 test 호출 없이 future test 에서 활용 가능).
from tests.fixtures.composite_fk import *  # noqa: F401, F403


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

    # 스키마 초기화 + pgvector 확장 활성화.
    # drop_all → create_all로 매 테스트 격리 (이전 테스트 commit 잔여 제거).
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(SQLModel.metadata.drop_all)
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
        auth_user_id="test_ba_memory_user",
        display_name="메모리 테스터",
        email="memory_test@kairos.test",
    )
    integration_session.add(user)
    await integration_session.flush()
    return user


@pytest_asyncio.fixture
async def memory_client(integration_session, auth_user, monkeypatch):
    """Memory API 테스트용 AsyncClient — get_current_user + get_async_session override.

    R1 patch §4 — BackgroundTask 헬퍼(_bg_distill_and_embed, _bg_transcribe_distill_embed)는
    외부 Gemini/OpenAI 호출이 발생하므로 테스트에서 no-op으로 monkeypatch.
    enqueue 동작(202 즉시)만 검증하고, distill/embed 실제 호출은 별도 unit test에서 mock으로.

    R3 patch §6 — recall endpoint의 _call_embedding(OpenAI)도 monkeypatch로 차단.
    vector_search는 항상 None 반환 → keyword fallback 경로 강제 검증.
    """
    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session, get_session_factory
    from src.main import app
    from src.memory import service as memory_service_module
    from src.memory.service import MemoryService

    async def _noop_distill(self, *args, **kwargs):
        return None

    async def _noop_transcribe(self, *args, **kwargs):
        return None

    async def _noop_embed(_text: str):
        # (embedding, total_tokens, elapsed_ms, error) — error 반환으로 vector 경로 우회
        return [], 0, 0, "test-disabled"

    async def _noop_promote_embed(**_kwargs):
        # R6 promote bgtask — 외부 OpenAI 호출 차단 (audit row 검증은 동기 경로에서)
        return None

    monkeypatch.setattr(
        MemoryService, "_bg_distill_and_embed", _noop_distill
    )
    monkeypatch.setattr(
        MemoryService, "_bg_transcribe_distill_embed", _noop_transcribe
    )
    monkeypatch.setattr(memory_service_module, "_call_embedding", _noop_embed)
    monkeypatch.setattr(
        memory_service_module, "_bg_promote_embed", _noop_promote_embed
    )

    # session_factory는 lifespan 미실행이라 None — dummy 주입 (background no-op이므로 실제 미사용)
    def _dummy_factory():
        return None

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_session_factory] = _dummy_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def personal_ws(integration_session, auth_user):
    """Personal workspace fixture — type='personal' + WorkspaceMember(owner)."""
    from src.workspaces.models import Workspace, WorkspaceMember

    ws = Workspace(
        name=f"{auth_user.display_name}의 개인 Kairos",
        owner_id=auth_user.id,
        type="personal",
    )
    integration_session.add(ws)
    await integration_session.flush()
    member = WorkspaceMember(
        workspace_id=ws.id, user_id=auth_user.id, role="owner"
    )
    integration_session.add(member)
    await integration_session.flush()
    return ws


@pytest_asyncio.fixture
async def team_ws(integration_session, auth_user):
    """Team workspace fixture — type='team' + WorkspaceMember(owner)."""
    from src.workspaces.models import Workspace, WorkspaceMember

    ws = Workspace(
        name="테스트 팀",
        owner_id=auth_user.id,
        type="team",
    )
    integration_session.add(ws)
    await integration_session.flush()
    member = WorkspaceMember(
        workspace_id=ws.id, user_id=auth_user.id, role="owner"
    )
    integration_session.add(member)
    await integration_session.flush()
    return ws


@pytest_asyncio.fixture
async def seed_memory(integration_session, auth_user, personal_ws):
    """Recall 테스트용 단일 MemoryItem seed."""
    from src.memory.models import MemoryItem

    item = MemoryItem(
        user_id=auth_user.id,
        workspace_id=personal_ws.id,
        type="text",
        raw_content="Sprint 15 wedge 결정 Recall-first",
        distilled_json={
            "title": "Sprint 15 wedge",
            "atomic_notes": ["Recall-first wedge 채택"],
            "suggested_visibility": "personal",
        },
        status="active",
    )
    integration_session.add(item)
    await integration_session.flush()
    return item


@pytest_asyncio.fixture
async def seed_memories(integration_session, auth_user, personal_ws):
    """Recall ranking 테스트용 5개 MemoryItem seed."""
    from src.memory.models import MemoryItem

    items = []
    for i in range(5):
        m = MemoryItem(
            user_id=auth_user.id,
            workspace_id=personal_ws.id,
            type="text",
            raw_content=f"테스트 메모 {i}",
            distilled_json={
                "title": f"테스트 메모 {i}",
                "atomic_notes": [f"atomic notes content {i}"],
                "suggested_visibility": "personal",
            },
            status="active",
        )
        integration_session.add(m)
        items.append(m)
    await integration_session.flush()
    return items
