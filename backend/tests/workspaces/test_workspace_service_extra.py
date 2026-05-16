# backend/tests/workspaces/test_workspace_service_extra.py
"""WorkspaceService — list / get / update_settings / add_member 단위 테스트.

기존 test_workspace_service.py 는 create_workspace 1 케이스만 다룸. 이 파일은
나머지 4 메서드 (list / get / update_settings / add_member) + 7 분기 검증.
"""
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.common.exceptions import NotFoundError
from src.workspaces.exceptions import (
    MemberAlreadyExistsError,
    PersonalWorkspaceProtected,
    WorkspaceNotFoundError,
)
from src.workspaces.service import WorkspaceService


def _make_workspace(
    ws_id: uuid.UUID | None = None,
    name: str = "우리팀",
    type_: str = "team",
    owner_id: uuid.UUID | None = None,
    inbox_threshold: float = 0.7,
) -> SimpleNamespace:
    now = datetime(2026, 5, 16)
    return SimpleNamespace(
        id=ws_id or uuid.uuid4(),
        name=name,
        owner_id=owner_id or uuid.uuid4(),
        type=type_,
        inbox_threshold=inbox_threshold,
        created_at=now,
        updated_at=now,
    )


def _make_user(user_id: uuid.UUID | None = None, email: str = "u@example.com") -> SimpleNamespace:
    return SimpleNamespace(id=user_id or uuid.uuid4(), email=email)


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def user_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def project_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(repo: AsyncMock, user_repo: AsyncMock, project_repo: AsyncMock) -> WorkspaceService:
    return WorkspaceService(repo=repo, user_repo=user_repo, project_repo=project_repo)


class TestListWorkspaces:
    @pytest.mark.asyncio
    async def test_returns_camelcase_dicts(self, service, repo):
        user_id = uuid.uuid4()
        workspaces = [_make_workspace(name=f"ws-{i}") for i in range(3)]
        repo.find_by_user = AsyncMock(return_value=workspaces)

        result = await service.list_workspaces(user_id)
        assert len(result) == 3
        assert all("ownerId" in r and "createdAt" in r and "type" in r for r in result)

    @pytest.mark.asyncio
    async def test_empty_list(self, service, repo):
        repo.find_by_user = AsyncMock(return_value=[])
        result = await service.list_workspaces(uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_personal_type_preserved(self, service, repo):
        ws = _make_workspace(type_="personal")
        repo.find_by_user = AsyncMock(return_value=[ws])
        result = await service.list_workspaces(uuid.uuid4())
        assert result[0]["type"] == "personal"


class TestGetWorkspace:
    @pytest.mark.asyncio
    async def test_includes_member_count(self, service, repo):
        ws = _make_workspace()
        repo.find_by_id = AsyncMock(return_value=ws)
        repo.get_member_count = AsyncMock(return_value=7)

        result = await service.get_workspace(ws.id)
        assert result["memberCount"] == 7
        assert result["inboxThreshold"] == ws.inbox_threshold

    @pytest.mark.asyncio
    async def test_not_found_raises(self, service, repo):
        repo.find_by_id = AsyncMock(return_value=None)
        with pytest.raises(WorkspaceNotFoundError):
            await service.get_workspace(uuid.uuid4())


class TestUpdateSettings:
    @pytest.mark.asyncio
    async def test_threshold_updated_and_committed(self, service, repo):
        ws = _make_workspace()
        repo.find_by_id = AsyncMock(return_value=ws)
        repo.update_threshold = AsyncMock()
        repo.commit = AsyncMock()

        result = await service.update_settings(ws.id, 0.5)
        assert result == {"inboxThreshold": 0.5}
        repo.update_threshold.assert_awaited_once_with(ws.id, 0.5)
        repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_not_found_raises(self, service, repo):
        repo.find_by_id = AsyncMock(return_value=None)
        with pytest.raises(WorkspaceNotFoundError):
            await service.update_settings(uuid.uuid4(), 0.5)


class TestAddMember:
    @pytest.mark.asyncio
    async def test_happy_path(self, service, repo, user_repo):
        ws = _make_workspace(type_="team")
        target_user = _make_user(email="alice@example.com")
        added = SimpleNamespace(id=uuid.uuid4(), user_id=target_user.id, role="member")

        repo.find_by_id = AsyncMock(return_value=ws)
        user_repo.find_by_email = AsyncMock(return_value=target_user)
        repo.find_member = AsyncMock(return_value=None)
        repo.add_member = AsyncMock(return_value=added)
        repo.commit = AsyncMock()

        result = await service.add_member(ws.id, "alice@example.com")
        assert result["role"] == "member"
        assert result["userId"] == str(target_user.id)
        repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_workspace_not_found(self, service, repo):
        repo.find_by_id = AsyncMock(return_value=None)
        with pytest.raises(WorkspaceNotFoundError):
            await service.add_member(uuid.uuid4(), "x@example.com")

    @pytest.mark.asyncio
    async def test_personal_workspace_protected(self, service, repo):
        """I-19: personal workspace 는 멤버 추가 차단."""
        ws = _make_workspace(type_="personal")
        repo.find_by_id = AsyncMock(return_value=ws)
        with pytest.raises(PersonalWorkspaceProtected):
            await service.add_member(ws.id, "x@example.com")

    @pytest.mark.asyncio
    async def test_user_not_found(self, service, repo, user_repo):
        ws = _make_workspace(type_="team")
        repo.find_by_id = AsyncMock(return_value=ws)
        user_repo.find_by_email = AsyncMock(return_value=None)
        with pytest.raises(NotFoundError):
            await service.add_member(ws.id, "unknown@example.com")

    @pytest.mark.asyncio
    async def test_already_member_raises(self, service, repo, user_repo):
        ws = _make_workspace(type_="team")
        target_user = _make_user()
        existing_member = SimpleNamespace(id=uuid.uuid4())

        repo.find_by_id = AsyncMock(return_value=ws)
        user_repo.find_by_email = AsyncMock(return_value=target_user)
        repo.find_member = AsyncMock(return_value=existing_member)

        with pytest.raises(MemberAlreadyExistsError):
            await service.add_member(ws.id, target_user.email)
