# PR-2 c1 회귀 — actions list/count 필터 계약 정합 (priority/project_id 누락 버그)
"""count_by_workspace 가 find_by_workspace 와 동일 필터를 받지 않으면 필터된
목록의 total/hasNext 가 전체 기준으로 계산돼 pagination 이 틀어진다 (codex 발견
실버그 — priority/project_id 가 count 에 미전달). 실 DB 로 list 길이 == count 를
고정한다."""
import pytest

from src.actions.models import ActionItem
from src.actions.repository import ActionItemRepository
from src.projects.models import Project


@pytest.mark.asyncio
async def test_count_matches_list_for_priority_and_project(
    integration_session, auth_user, team_ws
):
    project = Project(
        title="필터 대상", workspace_id=team_ws.id, visibility="public",
        created_by_id=auth_user.id,
    )
    integration_session.add(project)
    await integration_session.flush()

    items = [
        ActionItem(
            workspace_id=team_ws.id, title="high+proj", priority="high",
            project_id=project.id,
        ),
        ActionItem(
            workspace_id=team_ws.id, title="high only", priority="high",
            project_id=None,
        ),
        ActionItem(
            workspace_id=team_ws.id, title="low+proj", priority="low",
            project_id=project.id,
        ),
    ]
    integration_session.add_all(items)
    await integration_session.flush()

    repo = ActionItemRepository(integration_session)
    ctx = {"requester_user_id": auth_user.id, "requester_role": "owner"}

    for filters in (
        {"priority": "high"},
        {"project_id": project.id},
        {"priority": "high", "project_id": project.id},
    ):
        listed = await repo.find_by_workspace(team_ws.id, **filters, **ctx)
        total = await repo.count_by_workspace(team_ws.id, **filters, **ctx)
        assert total == len(listed), f"count-list 불일치: filters={filters}"

    # 필터별 기대 개수 명시 (list/count 가 같이 틀리는 회귀 차단)
    assert await repo.count_by_workspace(team_ws.id, priority="high", **ctx) == 2
    assert await repo.count_by_workspace(team_ws.id, project_id=project.id, **ctx) == 2
    assert (
        await repo.count_by_workspace(
            team_ws.id, priority="high", project_id=project.id, **ctx
        )
        == 1
    )
