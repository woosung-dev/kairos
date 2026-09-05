# apps/api/tests/workspaces/test_settings_service.py
"""WorkspaceService.update_settings 단위 테스트 — 부분 갱신 + 응답 조립."""
import uuid
from unittest.mock import AsyncMock

import pytest

from src.workspaces.exceptions import WorkspaceNotFoundError
from src.workspaces.models import Workspace
from src.workspaces.service import WorkspaceService


def _make_service(workspace: Workspace | None) -> tuple[WorkspaceService, AsyncMock]:
    repo = AsyncMock()
    repo.find_by_id.return_value = workspace
    return WorkspaceService(repo=repo, project_repo=AsyncMock()), repo


@pytest.mark.asyncio
async def test_update_settings_name_only_keeps_threshold():
    """이름만 바꾸면 repo 에 name 만 넘기고, 응답 threshold 는 기존 row 값."""
    workspace_id = uuid.uuid4()
    workspace = Workspace(
        id=workspace_id, name="옛 이름", owner_id=uuid.uuid4(), inbox_threshold=0.8
    )
    service, repo = _make_service(workspace)

    result = await service.update_settings(workspace_id, name="새 이름")

    repo.update_settings.assert_awaited_once_with(
        workspace_id, inbox_threshold=None, name="새 이름"
    )
    assert result == {"inboxThreshold": 0.8, "name": "새 이름"}
    assert repo.commit.await_count == 1


@pytest.mark.asyncio
async def test_update_settings_threshold_only_keeps_name():
    """임계값만 바꾸면 응답 name 은 기존 row 값."""
    workspace_id = uuid.uuid4()
    workspace = Workspace(
        id=workspace_id, name="우리팀", owner_id=uuid.uuid4(), inbox_threshold=0.9
    )
    service, repo = _make_service(workspace)

    result = await service.update_settings(workspace_id, inbox_threshold=0.7)

    repo.update_settings.assert_awaited_once_with(
        workspace_id, inbox_threshold=0.7, name=None
    )
    assert result == {"inboxThreshold": 0.7, "name": "우리팀"}


@pytest.mark.asyncio
async def test_update_settings_missing_workspace_raises():
    """없는 워크스페이스 → WorkspaceNotFoundError, 쓰기·commit 없음."""
    service, repo = _make_service(None)

    with pytest.raises(WorkspaceNotFoundError):
        await service.update_settings(uuid.uuid4(), name="x")

    repo.update_settings.assert_not_awaited()
    repo.commit.assert_not_awaited()
