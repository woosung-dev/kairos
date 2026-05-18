# create_workspace path onboarding step=1 hook 검증 (Sprint 22 OBN-02)
import pytest

from src.auth.repository import UserRepository
from src.onboarding.service import OnboardingService
from src.projects.repository import ProjectRepository
from src.workspaces.repository import WorkspaceRepository
from src.workspaces.service import WorkspaceService


@pytest.mark.asyncio
async def test_create_team_workspace_sets_onboarding_step_1(
    integration_session, auth_user
):
    """팀 워크스페이스 생성 경로 → onboarding step=1 advance."""
    ws_repo = WorkspaceRepository(integration_session)
    user_repo = UserRepository(integration_session)
    project_repo = ProjectRepository(integration_session)
    service = WorkspaceService(
        repo=ws_repo, user_repo=user_repo, project_repo=project_repo
    )

    onboarding = OnboardingService(integration_session)
    initial = await onboarding.get_status(auth_user.id)
    assert initial.step == 0

    await service.create_workspace(name="테스트 팀", owner_id=auth_user.id)

    after = await onboarding.get_status(auth_user.id)
    assert after.step == 1


@pytest.mark.asyncio
async def test_create_workspace_step_1_hook_is_idempotent(
    integration_session, auth_user
):
    """이미 step >= 1 인 user 가 추가 ws 생성 → no regression."""
    onboarding = OnboardingService(integration_session)
    await onboarding.increment_step(auth_user.id, 3)
    await integration_session.flush()

    ws_repo = WorkspaceRepository(integration_session)
    user_repo = UserRepository(integration_session)
    project_repo = ProjectRepository(integration_session)
    service = WorkspaceService(
        repo=ws_repo, user_repo=user_repo, project_repo=project_repo
    )

    await service.create_workspace(name="두번째 팀", owner_id=auth_user.id)

    status = await onboarding.get_status(auth_user.id)
    assert status.step == 3  # downgrade 안 됨
