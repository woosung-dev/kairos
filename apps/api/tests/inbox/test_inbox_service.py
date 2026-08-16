# apps/api/tests/inbox/test_inbox_service.py
"""InboxService 단위 테스트 — list / classify / dismiss / _to_dict.

기존 inbox 테스트 부재 (BL-029 backlog 검토 시 발견). 287 LOC 도메인 무 coverage 였음.
크로스 레포지토리 (InboxRepo + ProjectRepo) commit-once 패턴 회귀 가드.
"""
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.inbox.exceptions import InboxItemNotFoundError
from src.inbox.service import InboxService


def _make_inbox_item(
    item_id: uuid.UUID,
    workspace_id: uuid.UUID,
    source_type: str = "meeting",
    is_processed: bool = False,
    ai_suggested_project_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    """InboxItem 형태의 mock 객체. 실제 SQLModel 없이 attr 만."""
    now = datetime(2026, 5, 16, 12, 0, 0)
    return SimpleNamespace(
        id=item_id,
        workspace_id=workspace_id,
        title="테스트 회의",
        summary="요약",
        source_type=source_type,
        source_id=uuid.uuid4(),
        ai_suggested_project_id=ai_suggested_project_id,
        ai_suggested_project_title=(
            "프로젝트 후보" if ai_suggested_project_id else None
        ),
        ai_suggested_tags=["태그1", "태그2"],
        ai_confidence=0.85,
        is_processed=is_processed,
        created_at=now,
        updated_at=now,
    )


def _make_project(
    project_id: uuid.UUID, workspace_id: uuid.UUID | None = None
) -> SimpleNamespace:
    """Codex F-2: workspace_id 명시 — secondary FK 검증에 필요."""
    return SimpleNamespace(
        id=project_id,
        title="프로젝트 X",
        workspace_id=workspace_id or uuid.uuid4(),
    )


class TestListInbox:
    @pytest.mark.asyncio
    async def test_pagination_metadata(self):
        ws_id = uuid.uuid4()
        items = [_make_inbox_item(uuid.uuid4(), ws_id) for _ in range(3)]
        inbox_repo = AsyncMock()
        inbox_repo.find_by_workspace = AsyncMock(return_value=items)
        inbox_repo.count_by_workspace = AsyncMock(return_value=55)
        project_repo = AsyncMock()

        service = InboxService(inbox_repo, project_repo)
        result = await service.list_inbox(ws_id, page=2, page_size=20)

        assert result["total"] == 55
        assert result["page"] == 2
        assert result["pageSize"] == 20
        assert result["hasNext"] is True  # 2 * 20 = 40 < 55
        assert len(result["items"]) == 3
        inbox_repo.find_by_workspace.assert_awaited_once_with(
            ws_id, is_processed=None, offset=20, limit=20
        )

    @pytest.mark.asyncio
    async def test_last_page_has_next_false(self):
        ws_id = uuid.uuid4()
        inbox_repo = AsyncMock()
        inbox_repo.find_by_workspace = AsyncMock(return_value=[])
        inbox_repo.count_by_workspace = AsyncMock(return_value=20)
        service = InboxService(inbox_repo, AsyncMock())

        result = await service.list_inbox(ws_id, page=1, page_size=20)
        assert result["hasNext"] is False  # 1 * 20 = 20 < 20 → False

    @pytest.mark.asyncio
    async def test_is_processed_filter_forwarded(self):
        ws_id = uuid.uuid4()
        inbox_repo = AsyncMock()
        inbox_repo.find_by_workspace = AsyncMock(return_value=[])
        inbox_repo.count_by_workspace = AsyncMock(return_value=0)
        service = InboxService(inbox_repo, AsyncMock())

        await service.list_inbox(ws_id, is_processed=True)
        inbox_repo.find_by_workspace.assert_awaited_once_with(
            ws_id, is_processed=True, offset=0, limit=20
        )


class TestClassify:
    @pytest.mark.asyncio
    async def test_meeting_links_to_projects(self):
        ws_id = uuid.uuid4()
        item_id = uuid.uuid4()
        project_ids = [uuid.uuid4(), uuid.uuid4()]
        item = _make_inbox_item(item_id, ws_id, source_type="meeting")

        inbox_repo = AsyncMock()
        inbox_repo.find_by_id = AsyncMock(return_value=item)
        inbox_repo.save = AsyncMock(return_value=item)
        inbox_repo.commit = AsyncMock()

        project_repo = AsyncMock()
        project_repo.add_meeting_link = AsyncMock()
        # F-2 secondary FK: project 가 같은 workspace 내인지 검증 — 검증 + add_meeting_link 호출
        project_repo.find_by_id = AsyncMock(
            side_effect=[_make_project(pid, ws_id) for pid in project_ids]
        )

        # Sprint 19 PR #1 C13a (Codex 2차 F-1): meeting_repo 주입 — source_id 검증 통과
        from unittest.mock import MagicMock
        mock_meeting = MagicMock()
        mock_meeting.id = item.source_id
        mock_meeting.workspace_id = ws_id
        meeting_repo = AsyncMock()
        meeting_repo.find_by_id = AsyncMock(return_value=mock_meeting)

        service = InboxService(inbox_repo, project_repo, meeting_repo=meeting_repo)
        result = await service.classify(item_id, ws_id, project_ids)

        assert project_repo.add_meeting_link.await_count == 2
        assert len(result["linkedProjects"]) == 2
        assert result["isProcessed"] is True
        inbox_repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_non_meeting_source_no_project_link(self):
        """source_type != 'meeting' 일 때 add_meeting_link 호출 X."""
        ws_id = uuid.uuid4()
        item_id = uuid.uuid4()
        item = _make_inbox_item(item_id, ws_id, source_type="note")

        inbox_repo = AsyncMock()
        inbox_repo.find_by_id = AsyncMock(return_value=item)
        inbox_repo.save = AsyncMock()
        inbox_repo.commit = AsyncMock()

        project_repo = AsyncMock()
        project_repo.add_meeting_link = AsyncMock()
        # F-2 검증: project_id 가 같은 workspace 내인 mock 반환 (검증 통과 후 source_type 분기)
        project_repo.find_by_id = AsyncMock(return_value=_make_project(uuid.uuid4(), ws_id))

        service = InboxService(inbox_repo, project_repo)
        result = await service.classify(item_id, ws_id, [uuid.uuid4()])

        project_repo.add_meeting_link.assert_not_called()
        assert result["linkedProjects"] == []

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        inbox_repo = AsyncMock()
        inbox_repo.find_by_id = AsyncMock(return_value=None)
        service = InboxService(inbox_repo, AsyncMock())

        with pytest.raises(InboxItemNotFoundError):
            await service.classify(uuid.uuid4(), uuid.uuid4(), [])

    @pytest.mark.asyncio
    async def test_commit_called_once_cross_repo(self):
        """ADR: 동일 session 공유 시 service 한 번만 commit."""
        ws_id = uuid.uuid4()
        item = _make_inbox_item(uuid.uuid4(), ws_id)

        inbox_repo = AsyncMock()
        inbox_repo.find_by_id = AsyncMock(return_value=item)
        inbox_repo.save = AsyncMock()
        inbox_repo.commit = AsyncMock()

        project_repo = AsyncMock()
        project_repo.add_meeting_link = AsyncMock()
        # F-2 검증: 같은 workspace 의 project 반환
        project_repo.find_by_id = AsyncMock(return_value=_make_project(uuid.uuid4(), ws_id))
        project_repo.commit = AsyncMock()  # 호출되면 안 됨 — service 가 inbox_repo.commit 만

        # Sprint 19 PR #1 C13a (Codex 2차 F-1): meeting_repo 주입 — source_id 검증 통과
        from unittest.mock import MagicMock
        mock_meeting = MagicMock()
        mock_meeting.workspace_id = ws_id
        meeting_repo = AsyncMock()
        meeting_repo.find_by_id = AsyncMock(return_value=mock_meeting)

        service = InboxService(inbox_repo, project_repo, meeting_repo=meeting_repo)
        await service.classify(item.id, ws_id, [uuid.uuid4()])

        inbox_repo.commit.assert_awaited_once()
        project_repo.commit.assert_not_called()


class TestDismiss:
    @pytest.mark.asyncio
    async def test_marks_processed_and_commits(self):
        ws_id = uuid.uuid4()
        item = _make_inbox_item(uuid.uuid4(), ws_id)
        inbox_repo = AsyncMock()
        inbox_repo.find_by_id = AsyncMock(return_value=item)
        inbox_repo.save = AsyncMock()
        inbox_repo.commit = AsyncMock()
        service = InboxService(inbox_repo, AsyncMock())

        result = await service.dismiss(item.id, ws_id)
        assert result["isProcessed"] is True
        inbox_repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        inbox_repo = AsyncMock()
        inbox_repo.find_by_id = AsyncMock(return_value=None)
        service = InboxService(inbox_repo, AsyncMock())

        with pytest.raises(InboxItemNotFoundError):
            await service.dismiss(uuid.uuid4(), uuid.uuid4())


class TestToDict:
    def test_camelcase_mapping(self):
        item = _make_inbox_item(uuid.uuid4(), uuid.uuid4())
        result = InboxService._to_dict(item)  # type: ignore[arg-type]

        # snake_case → camelCase
        assert "workspaceId" in result
        assert "sourceType" in result
        assert "isProcessed" in result
        assert "aiSuggestedProjectId" in result
        assert "aiSuggestedTags" in result
        assert "createdAt" in result
        assert "updatedAt" in result

    def test_null_ai_suggested_project_id_handled(self):
        item = _make_inbox_item(
            uuid.uuid4(), uuid.uuid4(), ai_suggested_project_id=None
        )
        result = InboxService._to_dict(item)  # type: ignore[arg-type]
        assert result["aiSuggestedProjectId"] is None
        assert result["aiSuggestedProjectTitle"] is None

    def test_uuid_stringified(self):
        item_id = uuid.uuid4()
        item = _make_inbox_item(item_id, uuid.uuid4())
        result = InboxService._to_dict(item)  # type: ignore[arg-type]
        assert result["id"] == str(item_id)
        assert isinstance(result["workspaceId"], str)

    def test_datetime_isoformat(self):
        item = _make_inbox_item(uuid.uuid4(), uuid.uuid4())
        result = InboxService._to_dict(item)  # type: ignore[arg-type]
        assert result["createdAt"].startswith("2026-05-16T")
