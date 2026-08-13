# apps/backend/tests/workspaces/test_workspace_service.py
"""WorkspaceService 단위 테스트 — 템플릿 프로젝트 시딩 검증."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.workspaces.models import Workspace
from src.workspaces.service import WorkspaceService
from src.workspaces.templates import DEFAULT_TEMPLATE_PROJECTS


@pytest.mark.asyncio
async def test_create_workspace_seeds_template_projects():
    """신규 워크스페이스 생성 시 기본 템플릿 프로젝트 3개가 시딩된다."""
    owner_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    workspace_repo = AsyncMock()
    saved_workspace = Workspace(
        id=workspace_id,
        name="우리팀",
        owner_id=owner_id,
    )
    saved_workspace.created_at = datetime(2026, 4, 22)
    saved_workspace.updated_at = datetime(2026, 4, 22)
    workspace_repo.save.return_value = saved_workspace

    project_repo = AsyncMock()
    project_repo.save.side_effect = lambda p: p  # 저장 객체 그대로 반환

    service = WorkspaceService(
        repo=workspace_repo,
        project_repo=project_repo,
    )

    result = await service.create_workspace(name="우리팀", owner_id=owner_id)

    # 응답 검증
    assert result["id"] == str(workspace_id)
    assert result["name"] == "우리팀"

    # 멤버 추가 1회 호출
    assert workspace_repo.add_member.await_count == 1

    # 템플릿 프로젝트가 3개 시딩됨
    assert project_repo.save.await_count == len(DEFAULT_TEMPLATE_PROJECTS)

    # 시딩된 프로젝트들이 워크스페이스와 owner에 연결됨 + sort_order 보존
    saved_projects = [call.args[0] for call in project_repo.save.await_args_list]
    titles = [p.title for p in saved_projects]
    expected_titles = [t.title for t in DEFAULT_TEMPLATE_PROJECTS]
    assert titles == expected_titles

    for project, template in zip(saved_projects, DEFAULT_TEMPLATE_PROJECTS):
        assert project.workspace_id == workspace_id
        assert project.created_by_id == owner_id
        assert project.sort_order == template.sort_order
        assert project.tags == list(template.tags)
        assert project.description == template.description

    # 트랜잭션은 WorkspaceRepository에서 한 번만 commit
    assert workspace_repo.commit.await_count == 1
