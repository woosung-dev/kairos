# backend/tests/rag/test_pipeline_service.py
"""RagPipelineService 단위 테스트 — visibility 검증 4 시나리오 + admin 우회.

BL-029 refactor 회귀 가드: helper 추출 후에도 동작 등가성 보장.
ADR-014 옵션 A.
"""
import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.rag.pipeline_service import RagPipelineService, _sse_error_done


@pytest.fixture
def workspace_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def project_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def member_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def non_member_id() -> uuid.UUID:
    return uuid.uuid4()


def _make_project(
    project_id: uuid.UUID,
    workspace_id: uuid.UUID,
    visibility: str,
    created_by_id: uuid.UUID,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=project_id,
        workspace_id=workspace_id,
        visibility=visibility,
        created_by_id=created_by_id,
    )


def _make_rag_service() -> AsyncMock:
    """RagService.ask — 통과 시 dummy answer 이벤트 stream 반환."""

    async def fake_ask(**_kwargs):
        yield {"event": "answer", "data": json.dumps({"text": "ok"})}
        yield {"event": "done", "data": json.dumps({"cached": False, "sourceCount": 0})}

    rag_service = AsyncMock()
    rag_service.ask = fake_ask  # AsyncGenerator factory
    return rag_service


class TestSSEErrorDoneHelper:
    """_sse_error_done — 보일러플레이트 통합 helper."""

    def test_returns_error_then_done(self):
        error_event, done_event = _sse_error_done("테스트 메시지")
        assert error_event["event"] == "error"
        assert json.loads(error_event["data"]) == {"message": "테스트 메시지"}
        assert done_event["event"] == "done"
        assert json.loads(done_event["data"]) == {"cached": False, "sourceCount": 0}

    def test_korean_message_no_ascii_escape(self):
        """ensure_ascii=False — 한국어 메시지 raw 유지."""
        error_event, _ = _sse_error_done("권한 없음")
        assert "권한 없음" in error_event["data"]


class TestRagPipelineServiceAsk:
    """RagPipelineService.ask — visibility 검증 시나리오."""

    @pytest.mark.asyncio
    async def test_admin_bypasses_visibility_check(
        self, workspace_id, project_id, non_member_id
    ):
        """admin 역할은 visibility (draft/private) 우회. 단 tenant 검증은 받음.

        Sprint 19 PR #1 C11 (Codex F-2): tenant boundary 는 role 무관 항상 검증.
        visibility 검증 (draft creator / private ProjectMember) 만 admin/owner 우회.
        """
        project_repo = AsyncMock()
        # tenant check 통과 (project 가 본 workspace 소속이라 반환)
        mock_project = MagicMock()
        mock_project.visibility = "private"
        project_repo.find_by_id = AsyncMock(return_value=mock_project)
        project_repo.is_member = AsyncMock(return_value=False)  # 호출되면 안 됨 (visibility 우회)
        rag_service = _make_rag_service()
        pipeline = RagPipelineService(rag_service, project_repo)

        events = []
        async for event in pipeline.ask(
            question="test?",
            workspace_id=workspace_id,
            requester_user_id=non_member_id,
            requester_role="admin",
            project_id=project_id,
        ):
            events.append(event)

        # admin은 visibility 검증 skip → RagService 위임 결과 그대로
        assert events[0]["event"] == "answer"
        # Codex F-2: tenant 검증은 받음 (project_id, workspace_id)
        project_repo.find_by_id.assert_called_with(project_id, workspace_id)
        # visibility 검증 (_check_project_access 의 is_member) 는 우회
        project_repo.is_member.assert_not_called()

    @pytest.mark.asyncio
    async def test_project_not_found_yields_error(
        self, workspace_id, project_id, non_member_id
    ):
        project_repo = AsyncMock()
        project_repo.find_by_id = AsyncMock(return_value=None)
        rag_service = _make_rag_service()
        pipeline = RagPipelineService(rag_service, project_repo)

        events = []
        async for event in pipeline.ask(
            question="test?",
            workspace_id=workspace_id,
            requester_user_id=non_member_id,
            requester_role="member",
            project_id=project_id,
        ):
            events.append(event)

        assert len(events) == 2
        assert events[0]["event"] == "error"
        assert "찾을 수 없" in events[0]["data"]
        assert events[1]["event"] == "done"

    @pytest.mark.asyncio
    async def test_draft_non_creator_denied(
        self, workspace_id, project_id, member_id, non_member_id
    ):
        project_repo = AsyncMock()
        project_repo.find_by_id = AsyncMock(
            return_value=_make_project(
                project_id, workspace_id, visibility="draft", created_by_id=member_id
            )
        )
        rag_service = _make_rag_service()
        pipeline = RagPipelineService(rag_service, project_repo)

        events = []
        async for event in pipeline.ask(
            question="test?",
            workspace_id=workspace_id,
            requester_user_id=non_member_id,
            requester_role="member",
            project_id=project_id,
        ):
            events.append(event)

        assert events[0]["event"] == "error"
        assert "Draft" in events[0]["data"]

    @pytest.mark.asyncio
    async def test_private_non_member_denied(
        self, workspace_id, project_id, member_id, non_member_id
    ):
        project_repo = AsyncMock()
        project_repo.find_by_id = AsyncMock(
            return_value=_make_project(
                project_id, workspace_id, visibility="private", created_by_id=member_id
            )
        )
        project_repo.is_member = AsyncMock(return_value=False)
        rag_service = _make_rag_service()
        pipeline = RagPipelineService(rag_service, project_repo)

        events = []
        async for event in pipeline.ask(
            question="test?",
            workspace_id=workspace_id,
            requester_user_id=non_member_id,
            requester_role="member",
            project_id=project_id,
        ):
            events.append(event)

        assert events[0]["event"] == "error"
        assert "Private" in events[0]["data"]

    @pytest.mark.asyncio
    async def test_private_member_allowed(
        self, workspace_id, project_id, member_id
    ):
        project_repo = AsyncMock()
        project_repo.find_by_id = AsyncMock(
            return_value=_make_project(
                project_id, workspace_id, visibility="private", created_by_id=member_id
            )
        )
        project_repo.is_member = AsyncMock(return_value=True)
        rag_service = _make_rag_service()
        pipeline = RagPipelineService(rag_service, project_repo)

        events = []
        async for event in pipeline.ask(
            question="test?",
            workspace_id=workspace_id,
            requester_user_id=member_id,
            requester_role="member",
            project_id=project_id,
        ):
            events.append(event)

        # private 멤버 → 통과 → RagService 결과
        assert events[0]["event"] == "answer"

    @pytest.mark.asyncio
    async def test_public_anyone_allowed(self, workspace_id, project_id, member_id, non_member_id):
        project_repo = AsyncMock()
        project_repo.find_by_id = AsyncMock(
            return_value=_make_project(
                project_id, workspace_id, visibility="public", created_by_id=member_id
            )
        )
        rag_service = _make_rag_service()
        pipeline = RagPipelineService(rag_service, project_repo)

        events = []
        async for event in pipeline.ask(
            question="test?",
            workspace_id=workspace_id,
            requester_user_id=non_member_id,
            requester_role="member",
            project_id=project_id,
        ):
            events.append(event)

        assert events[0]["event"] == "answer"

    @pytest.mark.asyncio
    async def test_no_project_id_skips_check(self, workspace_id, non_member_id):
        """project_id 없으면 visibility 검증 skip (글로벌 RAG, visibility filter 는 RagService 내부)."""
        project_repo = AsyncMock()
        project_repo.find_by_id = AsyncMock()
        rag_service = _make_rag_service()
        pipeline = RagPipelineService(rag_service, project_repo)

        events = []
        async for event in pipeline.ask(
            question="test?",
            workspace_id=workspace_id,
            requester_user_id=non_member_id,
            requester_role="member",
            project_id=None,
        ):
            events.append(event)

        assert events[0]["event"] == "answer"
        project_repo.find_by_id.assert_not_called()
