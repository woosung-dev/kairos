# Memory 서비스 unit tests — 외부 API mock
"""MemoryService unit tests — Gemini/OpenAI/R2 외부 호출은 monkeypatch.

R1 patch §4 — BackgroundTask 분리 architecture의 enqueue 부분만 검증.
실제 distill/embed 호출 검증은 Day 0 spike + 통합 환경에서 별도 e2e로 수행.
"""
import uuid

import pytest
from fastapi import BackgroundTasks

from src.memory import service as memory_service
from src.memory.exceptions import EmptyMemoryError, MemoryNotFoundError
from src.memory.repository import MemoryRepository
from src.memory.service import MemoryService


def _make_service(session) -> MemoryService:
    """테스트용 MemoryService — session_factory는 람다로 컨텍스트 매니저 미사용 분기 회피."""

    class _FakeFactory:
        """async with self._session_factory() as session 컨텍스트를 흉내."""

        def __init__(self, sess):
            self._sess = sess

        def __call__(self):
            return self

        async def __aenter__(self):
            return self._sess

        async def __aexit__(self, *_args):
            return None

    class _FakeR2:
        pass

    return MemoryService(
        repo=MemoryRepository(session),
        session_factory=_FakeFactory(session),
        r2_service=_FakeR2(),
    )


@pytest.mark.asyncio
async def test_capture_text_saves_processing_item(
    integration_session, auth_user, personal_ws, monkeypatch
):
    """capture_text → MemoryItem status=processing 저장 + 202 응답 객체."""

    async def _noop(self, *args, **kwargs):
        return None

    monkeypatch.setattr(
        MemoryService, "_bg_distill_and_embed", _noop
    )

    service = _make_service(integration_session)
    bg = BackgroundTasks()
    result = await service.capture_text(
        user_id=auth_user.id,
        workspace_id=personal_ws.id,
        text="테스트 텍스트",
        background_tasks=bg,
    )
    assert result.status == "processing"
    assert result.distilled_json is None
    assert result.memory_id is not None


@pytest.mark.asyncio
async def test_capture_text_empty_raises(
    integration_session, auth_user, personal_ws
):
    """공백 입력 → EmptyMemoryError."""
    service = _make_service(integration_session)
    bg = BackgroundTasks()
    with pytest.raises(EmptyMemoryError):
        await service.capture_text(
            user_id=auth_user.id,
            workspace_id=personal_ws.id,
            text="   ",
            background_tasks=bg,
        )


@pytest.mark.asyncio
async def test_get_memory_not_found_raises(
    integration_session, auth_user, personal_ws
):
    """존재하지 않는 ID → MemoryNotFoundError."""
    service = _make_service(integration_session)
    with pytest.raises(MemoryNotFoundError):
        await service.get_memory(uuid.uuid4(), personal_ws.id)


@pytest.mark.asyncio
async def test_build_embed_text_uses_distilled_when_present():
    """distilled.title + atomic_notes를 임베딩 입력으로."""
    text = memory_service._build_embed_text(
        {"title": "wedge", "atomic_notes": ["a", "b"]},
        fallback_text="원문",
    )
    assert text == "wedge a b"


@pytest.mark.asyncio
async def test_build_embed_text_falls_back_to_raw():
    """distilled가 비어있으면 fallback_text 사용."""
    text = memory_service._build_embed_text(
        {"title": "", "atomic_notes": []}, fallback_text="원문"
    )
    assert text == "원문"
