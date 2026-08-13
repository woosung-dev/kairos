# backend/tests/actions/test_actions_service.py
"""ActionItemService 단위 테스트 — create / list / update / _to_dict.

기존 actions 도메인 0 coverage (7 src, 359 LOC). 단일 도메인 CRUD 회귀 가드.
"""
import uuid
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.actions.exceptions import ActionItemNotFoundError
from src.actions.service import ActionItemService


def _make_action(
    item_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    title: str = "AI 모델 마이그레이션",
    priority: str = "medium",
    status: str = "open",
    project_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    due_date: date | None = None,
) -> SimpleNamespace:
    now = datetime(2026, 5, 16, 12, 0, 0)
    return SimpleNamespace(
        id=item_id or uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        meeting_id=None,
        project_id=project_id,
        title=title,
        description="설명",
        assignee_id=assignee_id,
        due_date=due_date,
        priority=priority,
        status=status,
        created_at=now,
        updated_at=now,
    )


class TestCreateActionItem:
    @pytest.mark.asyncio
    async def test_default_priority_medium(self):
        ws_id = uuid.uuid4()
        saved = _make_action(workspace_id=ws_id, title="새 액션", priority="medium")
        repo = AsyncMock()
        repo.save = AsyncMock(return_value=saved)
        repo.commit = AsyncMock()

        service = ActionItemService(repo)
        result = await service.create_action_item(ws_id, "새 액션")

        assert result["priority"] == "medium"
        assert result["title"] == "새 액션"
        repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_optional_fields_forwarded(self):
        from types import SimpleNamespace
        ws_id = uuid.uuid4()
        proj_id = uuid.uuid4()
        assignee = uuid.uuid4()
        due = date(2026, 6, 1)
        saved = _make_action(
            workspace_id=ws_id,
            project_id=proj_id,
            assignee_id=assignee,
            due_date=due,
            priority="high",
        )
        repo = AsyncMock()
        repo.save = AsyncMock(return_value=saved)
        repo.commit = AsyncMock()

        # Codex F-2 + 2차 Minor 1 fail-closed: project_repo / workspace_repo 주입 필수
        project_repo = AsyncMock()
        project_repo.find_by_id = AsyncMock(
            return_value=SimpleNamespace(id=proj_id, workspace_id=ws_id)
        )
        workspace_repo = AsyncMock()
        workspace_repo.find_member = AsyncMock(
            return_value=SimpleNamespace(user_id=assignee, workspace_id=ws_id)
        )

        service = ActionItemService(
            repo=repo,
            project_repo=project_repo,
            workspace_repo=workspace_repo,
        )
        result = await service.create_action_item(
            ws_id,
            "긴급",
            project_id=proj_id,
            assignee_id=assignee,
            due_date=due,
            priority="high",
        )

        assert result["projectId"] == str(proj_id)
        assert result["assigneeId"] == str(assignee)
        assert result["dueDate"] == due.isoformat()
        assert result["priority"] == "high"


class TestListActionItems:
    @pytest.mark.asyncio
    async def test_pagination_metadata(self):
        ws_id = uuid.uuid4()
        items = [_make_action(workspace_id=ws_id) for _ in range(3)]
        repo = AsyncMock()
        repo.find_by_workspace = AsyncMock(return_value=items)
        repo.count_by_workspace = AsyncMock(return_value=42)

        service = ActionItemService(repo)
        result = await service.list_action_items(ws_id, page=2, page_size=10)

        assert result["total"] == 42
        assert result["page"] == 2
        assert result["pageSize"] == 10
        assert result["hasNext"] is True  # 2 * 10 = 20 < 42
        assert len(result["items"]) == 3
        repo.find_by_workspace.assert_awaited_once_with(
            ws_id, status=None, priority=None, project_id=None, offset=10, limit=10,
            requester_user_id=None, requester_role=None,
        )

    @pytest.mark.asyncio
    async def test_filters_forwarded(self):
        ws_id = uuid.uuid4()
        proj_id = uuid.uuid4()
        repo = AsyncMock()
        repo.find_by_workspace = AsyncMock(return_value=[])
        repo.count_by_workspace = AsyncMock(return_value=0)

        service = ActionItemService(repo)
        await service.list_action_items(
            ws_id, status="done", priority="high", project_id=proj_id
        )
        repo.find_by_workspace.assert_awaited_once_with(
            ws_id,
            status="done",
            priority="high",
            project_id=proj_id,
            offset=0,
            limit=20,
            requester_user_id=None,
            requester_role=None,
        )
        # PR-2 c1: count 도 동일 필터 계약 (priority/project_id 미전달 회귀 차단)
        repo.count_by_workspace.assert_awaited_once_with(
            ws_id,
            status="done",
            priority="high",
            project_id=proj_id,
            requester_user_id=None,
            requester_role=None,
        )

    @pytest.mark.asyncio
    async def test_last_page_has_next_false(self):
        ws_id = uuid.uuid4()
        repo = AsyncMock()
        repo.find_by_workspace = AsyncMock(return_value=[])
        repo.count_by_workspace = AsyncMock(return_value=20)
        service = ActionItemService(repo)

        result = await service.list_action_items(ws_id, page=2, page_size=10)
        assert result["hasNext"] is False  # 2 * 10 = 20 < 20 → False


class TestUpdateActionItem:
    @pytest.mark.asyncio
    async def test_partial_update(self):
        existing = _make_action(title="old", priority="low", status="open")
        ws_id = existing.workspace_id
        repo = AsyncMock()
        repo.find_by_id = AsyncMock(return_value=existing)
        repo.save = AsyncMock(side_effect=lambda i: i)
        repo.commit = AsyncMock()

        service = ActionItemService(repo)
        result = await service.update_action_item(
            existing.id, ws_id, title="new", status="done"
        )
        assert result["title"] == "new"
        assert result["status"] == "done"
        # 미지정 필드는 기존 값 유지
        assert result["priority"] == "low"

    @pytest.mark.asyncio
    async def test_none_values_dont_overwrite(self):
        """None 인자는 기존 값을 덮어쓰지 않음 (PATCH 의미)."""
        existing = _make_action(title="유지", priority="high")
        ws_id = existing.workspace_id
        repo = AsyncMock()
        repo.find_by_id = AsyncMock(return_value=existing)
        repo.save = AsyncMock(side_effect=lambda i: i)
        repo.commit = AsyncMock()

        service = ActionItemService(repo)
        result = await service.update_action_item(
            existing.id, ws_id, title=None, priority=None
        )
        assert result["title"] == "유지"
        assert result["priority"] == "high"

    @pytest.mark.asyncio
    async def test_updated_at_refreshed(self):
        """update 후 updated_at 이 변경됨을 확인 (정확한 시간이 아닌 변경 자체)."""
        existing = _make_action()
        ws_id = existing.workspace_id
        original_updated_at = existing.updated_at
        repo = AsyncMock()
        repo.find_by_id = AsyncMock(return_value=existing)
        repo.save = AsyncMock(side_effect=lambda i: i)
        repo.commit = AsyncMock()

        service = ActionItemService(repo)
        await service.update_action_item(existing.id, ws_id, title="t")
        assert existing.updated_at is not original_updated_at

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        repo = AsyncMock()
        repo.find_by_id = AsyncMock(return_value=None)
        service = ActionItemService(repo)

        with pytest.raises(ActionItemNotFoundError):
            await service.update_action_item(uuid.uuid4(), uuid.uuid4(), title="x")


class TestToDict:
    def test_camelcase_mapping(self):
        item = _make_action()
        result = ActionItemService._to_dict(item)  # type: ignore[arg-type]
        for key in (
            "workspaceId",
            "meetingId",
            "projectId",
            "assigneeId",
            "dueDate",
            "createdAt",
            "updatedAt",
        ):
            assert key in result

    def test_null_optional_fields(self):
        item = _make_action(project_id=None, assignee_id=None, due_date=None)
        result = ActionItemService._to_dict(item)  # type: ignore[arg-type]
        assert result["projectId"] is None
        assert result["assigneeId"] is None
        assert result["dueDate"] is None
        assert result["meetingId"] is None

    def test_uuid_stringified(self):
        proj_id = uuid.uuid4()
        item = _make_action(project_id=proj_id)
        result = ActionItemService._to_dict(item)  # type: ignore[arg-type]
        assert result["projectId"] == str(proj_id)

    def test_due_date_isoformat(self):
        item = _make_action(due_date=date(2026, 6, 30))
        result = ActionItemService._to_dict(item)  # type: ignore[arg-type]
        assert result["dueDate"] == "2026-06-30"
