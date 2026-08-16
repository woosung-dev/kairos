# create_project 시 onboarding step=2 hook 검증 (Sprint 22 OBN-02)
import pytest

from src.onboarding.service import OnboardingService
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.repository import WorkspaceRepository


@pytest.mark.asyncio
async def test_create_project_sets_onboarding_step_2(
    integration_session, auth_user, team_ws
):
    """프로젝트 생성 → onboarding step=2 advance."""
    onboarding = OnboardingService(integration_session)
    await onboarding.increment_step(auth_user.id, 1)
    await integration_session.flush()

    repo = ProjectRepository(integration_session)
    ws_repo = WorkspaceRepository(integration_session)
    service = ProjectService(repo, ws_repo=ws_repo)

    await service.create_project(
        workspace_id=team_ws.id,
        title="첫 프로젝트",
        created_by_id=auth_user.id,
    )

    status = await onboarding.get_status(auth_user.id)
    assert status.step == 2


@pytest.mark.asyncio
async def test_create_project_step_2_hook_idempotent(
    integration_session, auth_user, team_ws
):
    """이미 step >= 2 → no regression."""
    onboarding = OnboardingService(integration_session)
    await onboarding.increment_step(auth_user.id, 4)
    await integration_session.flush()

    repo = ProjectRepository(integration_session)
    ws_repo = WorkspaceRepository(integration_session)
    service = ProjectService(repo, ws_repo=ws_repo)

    await service.create_project(
        workspace_id=team_ws.id,
        title="두번째 프로젝트",
        created_by_id=auth_user.id,
    )

    status = await onboarding.get_status(auth_user.id)
    assert status.step == 4  # downgrade 안 됨
