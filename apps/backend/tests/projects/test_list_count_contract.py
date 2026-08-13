# PR-2 c1 회귀 — projects list/count 필터 계약 정합 (tag 누락 버그)
"""count_by_workspace 가 tag 필터를 받지 않으면 태그 필터된 목록의 total/hasNext
가 전체 기준으로 계산돼 pagination 이 틀어진다 (codex 발견 실버그). 실 DB 로
list 길이 == count 를 고정한다."""
import pytest

from src.projects.models import Project
from src.projects.repository import ProjectRepository


@pytest.mark.asyncio
async def test_count_matches_list_for_tag(integration_session, auth_user, team_ws):
    projects = [
        Project(
            title="백엔드 A", workspace_id=team_ws.id, visibility="public",
            created_by_id=auth_user.id, tags=["backend"],
        ),
        Project(
            title="백엔드 B", workspace_id=team_ws.id, visibility="public",
            created_by_id=auth_user.id, tags=["backend", "infra"],
        ),
        Project(
            title="프론트", workspace_id=team_ws.id, visibility="public",
            created_by_id=auth_user.id, tags=["frontend"],
        ),
    ]
    integration_session.add_all(projects)
    await integration_session.flush()

    repo = ProjectRepository(integration_session)
    ctx = {"requester_user_id": auth_user.id, "requester_role": "owner"}

    listed = await repo.find_by_workspace(team_ws.id, tag="backend", **ctx)
    total = await repo.count_by_workspace(team_ws.id, tag="backend", **ctx)
    assert total == len(listed) == 2

    listed_all = await repo.find_by_workspace(team_ws.id, **ctx)
    total_all = await repo.count_by_workspace(team_ws.id, **ctx)
    assert total_all == len(listed_all) == 3
