# Sprint 28c — memory mutation workspace 격리 실증 (BUG-MEMORY-WS-FILTER)
"""memory/repository.py 5 mutation 의 workspace_id WHERE 강제를 실증.

기존 QA 정적 단정(PK-only WHERE → 2-layer 갭)을 cross-workspace mutation 차단
통합테스트로 전환(실증). 로컬 TestContainers PostgreSQL 전용 (프로덕션 Neon 아님).

I-9: Repository update/delete 는 workspace_id WHERE 강제. 호출부(background task)는
이미 workspace_id 검증된 item 을 pre-fetch 하므로 기능 영향 0, 격리 backstop 만 추가.
"""
import uuid

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.memory.models import MemoryItem
from src.memory.repository import MemoryRepository
from src.workspaces.models import Workspace

pytestmark = pytest.mark.integration


async def _make_user(session: AsyncSession, name: str = "유저") -> User:
    user = User(
        clerk_id=f"clerk_{uuid.uuid4().hex}",
        display_name=name,
        email=f"{uuid.uuid4().hex}@kairos.test",
    )
    session.add(user)
    await session.flush()
    return user


async def _make_ws(
    session: AsyncSession, owner_id: uuid.UUID, name: str
) -> Workspace:
    ws = Workspace(name=name, owner_id=owner_id, type="team")
    session.add(ws)
    await session.flush()
    return ws


async def _fetch(session: AsyncSession, memory_id: uuid.UUID) -> MemoryItem:
    return (
        await session.exec(select(MemoryItem).where(MemoryItem.id == memory_id))
    ).one()


async def test_update_mutations_reject_cross_workspace(
    integration_session: AsyncSession,
):
    """타 워크스페이스 id 로 mutation 호출 시 대상 row 불변 (I-9 workspace_id WHERE)."""
    session = integration_session
    repo = MemoryRepository(session)

    owner_a = await _make_user(session, "오너A")
    owner_b = await _make_user(session, "오너B")
    ws_a = await _make_ws(session, owner_a.id, "WS-A")
    ws_b = await _make_ws(session, owner_b.id, "WS-B")
    await session.commit()

    item = MemoryItem(
        user_id=owner_a.id,
        workspace_id=ws_a.id,
        type="text",
        raw_content="원본 메모",
        status="processing",
    )
    session.add(item)
    await session.commit()
    memory_id = item.id

    # 1. update_status — WS-B(타 워크스페이스)로 호출 → 변경 0 (불변)
    await repo.update_status(memory_id, ws_b.id, "active")
    await session.commit()
    after = await _fetch(session, memory_id)
    assert after.status == "processing", "cross-ws update_status 가 row 를 변경하면 안 됨"

    # 2. update_transcript — WS-B 로 호출 → 불변
    await repo.update_transcript(memory_id, ws_b.id, "탈취 시도")
    await session.commit()
    after = await _fetch(session, memory_id)
    assert after.raw_content == "원본 메모"

    # 3. update_distilled — WS-B 로 호출 → 불변
    await repo.update_distilled(memory_id, ws_b.id, {"x": 1}, "embedding_pending")
    await session.commit()
    after = await _fetch(session, memory_id)
    assert after.distilled_json is None
    assert after.status == "processing"

    # 4. 대조군 — 올바른 WS-A 로 호출 → 정상 변경
    await repo.update_status(memory_id, ws_a.id, "active")
    await session.commit()
    after = await _fetch(session, memory_id)
    assert after.status == "active", "올바른 workspace_id 면 mutation 이 적용돼야 함"


async def test_update_embedding_rejects_cross_workspace(
    integration_session: AsyncSession,
):
    """update_embedding 도 workspace_id WHERE 강제."""
    session = integration_session
    repo = MemoryRepository(session)

    owner_a = await _make_user(session, "오너A")
    owner_b = await _make_user(session, "오너B")
    ws_a = await _make_ws(session, owner_a.id, "WS-A")
    ws_b = await _make_ws(session, owner_b.id, "WS-B")
    await session.commit()

    item = MemoryItem(
        user_id=owner_a.id,
        workspace_id=ws_a.id,
        type="text",
        raw_content="원본",
        status="embedding_pending",
    )
    session.add(item)
    await session.commit()
    memory_id = item.id
    chunk_id = uuid.uuid4()

    # 타 WS 로 호출 → 불변 (embedding_chunk_id None 유지, status 유지)
    await repo.update_embedding(memory_id, ws_b.id, chunk_id, "active")
    await session.commit()
    after = await _fetch(session, memory_id)
    assert after.embedding_chunk_id is None
    assert after.status == "embedding_pending"


async def test_clear_r2_audio_key_rejects_cross_workspace(
    integration_session: AsyncSession,
):
    """clear_r2_audio_key 도 workspace_id WHERE 강제 (cron cross-ws 안전)."""
    session = integration_session
    repo = MemoryRepository(session)

    owner_a = await _make_user(session, "오너A")
    owner_b = await _make_user(session, "오너B")
    ws_a = await _make_ws(session, owner_a.id, "WS-A")
    ws_b = await _make_ws(session, owner_b.id, "WS-B")
    await session.commit()

    item = MemoryItem(
        user_id=owner_a.id,
        workspace_id=ws_a.id,
        type="voice",
        raw_content="",
        status="active",
        r2_audio_key="memory/ws-a/audio.wav",
    )
    session.add(item)
    await session.commit()
    memory_id = item.id

    # 타 WS 로 clear → 불변
    await repo.clear_r2_audio_key(memory_id, ws_b.id)
    await session.commit()
    after = await _fetch(session, memory_id)
    assert after.r2_audio_key == "memory/ws-a/audio.wav"

    # 올바른 WS 로 clear → NULL (대조군)
    await repo.clear_r2_audio_key(memory_id, ws_a.id)
    await session.commit()
    after = await _fetch(session, memory_id)
    assert after.r2_audio_key is None
