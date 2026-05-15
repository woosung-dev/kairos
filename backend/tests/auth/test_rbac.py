# backend/tests/auth/test_rbac.py
"""RoleChecker 단위 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.auth.rbac import ROLE_LEVEL, RoleChecker
from src.workspaces.models import WorkspaceMember


def test_role_level_ordering():
    """역할 레벨 순서: viewer < member < admin < owner."""
    assert ROLE_LEVEL["viewer"] < ROLE_LEVEL["member"]
    assert ROLE_LEVEL["member"] < ROLE_LEVEL["admin"]
    assert ROLE_LEVEL["admin"] < ROLE_LEVEL["owner"]


def test_invalid_role_raises():
    """존재하지 않는 역할로 RoleChecker 생성 시 ValueError."""
    with pytest.raises(ValueError, match="유효하지 않은 역할"):
        RoleChecker("superadmin")


@pytest.mark.asyncio
async def test_role_checker_allows_sufficient_role():
    """충분한 역할이면 WorkspaceMember를 반환."""
    checker = RoleChecker("member")
    mock_member = MagicMock(spec=WorkspaceMember)
    mock_member.role = "admin"

    with patch("src.auth.rbac.WorkspaceRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.find_member = AsyncMock(return_value=mock_member)
        result = await checker(
            workspace_id=uuid.uuid4(),
            current_user=MagicMock(id=uuid.uuid4()),
            session=AsyncMock(),
        )
    assert result is mock_member


@pytest.mark.asyncio
async def test_role_checker_rejects_insufficient_role():
    """역할이 부족하면 403."""
    checker = RoleChecker("admin")
    mock_member = MagicMock(spec=WorkspaceMember)
    mock_member.role = "member"

    with patch("src.auth.rbac.WorkspaceRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.find_member = AsyncMock(return_value=mock_member)
        with pytest.raises(HTTPException) as exc_info:
            await checker(
                workspace_id=uuid.uuid4(),
                current_user=MagicMock(id=uuid.uuid4()),
                session=AsyncMock(),
            )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_role_checker_rejects_non_member():
    """멤버가 아니면 403."""
    checker = RoleChecker("viewer")

    with patch("src.auth.rbac.WorkspaceRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.find_member = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await checker(
                workspace_id=uuid.uuid4(),
                current_user=MagicMock(id=uuid.uuid4()),
                session=AsyncMock(),
            )
    assert exc_info.value.status_code == 403
