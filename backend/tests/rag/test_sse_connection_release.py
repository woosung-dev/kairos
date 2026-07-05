# PERF-SSE-COMMIT 회귀 가드 — RAG 스트리밍 중 DB 커넥션이 pool 에 반납되는지 검증
"""검색 read 트랜잭션이 열린 채로 Gemini 스트리밍(수 초)에 진입하면 동시 스트림
수만큼 커넥션이 잠겨 pool(15) 고갈 → 전체 API 블로킹. ask() 가 스트리밍 진입 전에
commit 으로 트랜잭션을 닫아 스트리밍 중 checkedout=0 이어야 한다.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.embeddings.models import EmbeddingChunk
from src.embeddings.repository import EmbeddingRepository
from src.rag.service import RagService
from src.workspaces.models import Workspace, WorkspaceMember


def _make_vec(dim: int = 1536) -> list[float]:
    return [0.001 + (i * 0.0001) for i in range(dim)]


@pytest_asyncio.fixture
async def sse_engine(postgres_container):
    """pool 상태 관찰이 필요해 engine 을 직접 보유하는 fixture."""
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(url, echo=False, pool_size=5, max_overflow=0)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


class _FakeEmbeddingService:
    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [_make_vec() for _ in texts]


class _PoolProbeAIService:
    """스트리밍 토큰 사이에서 pool checkedout 수를 기록하는 가짜 Gemini."""

    def __init__(self, engine) -> None:
        self._engine = engine
        self.checkedout_during_stream: list[int] = []

    async def stream_rag_answer(self, question: str, sources_text: str):
        yield "스트리밍 "
        self.checkedout_during_stream.append(self._engine.pool.checkedout())
        yield "중간 "
        self.checkedout_during_stream.append(self._engine.pool.checkedout())
        yield "답변"


@pytest.mark.asyncio
async def test_connection_released_before_streaming(sse_engine):
    """스트리밍 토큰 사이 시점에 pool checkedout == 0 (커넥션 반납 완료)."""
    # 시드는 별도 session 으로 — 서비스 session 의 pool 상태를 오염시키지 않음
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    async with AsyncSession(sse_engine, expire_on_commit=False) as seed:
        user = User(
            id=user_id,
            clerk_id=f"clerk_sse_{user_id}",
            display_name="sse",
            email=f"sse_{user_id}@perf.test",
        )
        seed.add(user)
        seed.add(Workspace(id=ws_id, name="perf", owner_id=user_id, type="team"))
        await seed.flush()
        seed.add(
            WorkspaceMember(workspace_id=ws_id, user_id=user_id, role="owner")
        )
        seed.add(
            EmbeddingChunk(
                workspace_id=ws_id,
                source_id=uuid.uuid4(),
                source_type="note",
                chunk_text="스트리밍 성능 테스트 노트",
                chunk_index=0,
                chunk_level=2,
                embedding=_make_vec(),
            )
        )
        await seed.commit()

    async with AsyncSession(sse_engine, expire_on_commit=False) as session:
        probe = _PoolProbeAIService(sse_engine)
        service = RagService(
            embedding_repo=EmbeddingRepository(session),
            embedding_service=_FakeEmbeddingService(),
            ai_service=probe,
        )

        events = [
            e
            async for e in service.ask(
                question="스트리밍 성능",
                workspace_id=ws_id,
                requester_user_id=user_id,
                requester_role="owner",
            )
        ]

    event_names = [e["event"] for e in events]
    assert "answer" in event_names, f"answer 이벤트 부재: {event_names}"
    assert "done" in event_names, f"done 이벤트 부재: {event_names}"

    assert probe.checkedout_during_stream, "스트리밍 probe 미실행 — fused 빈 결과?"
    assert all(n == 0 for n in probe.checkedout_during_stream), (
        "스트리밍 중 DB 커넥션이 pool 에 반납되지 않음 (PERF-SSE-COMMIT 회귀): "
        f"checkedout={probe.checkedout_during_stream}"
    )
