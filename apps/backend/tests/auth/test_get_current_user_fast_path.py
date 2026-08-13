# Sprint 27e Post-Merge BUG-QA-1 — get_current_user fast path 회귀 가드.
"""dependencies.py:181-186 fast path — onboarding_step >= 1 사용자는 lazy seed SKIP.

배경 (Sprint 27e QA dynamic verify): dashboard 첫 진입 시 BE 5 endpoint fanout 7.5s.
PERF-r2-4 가 정적 추정한 매 request 3 INSERT + commit hidden cost 의 실측 confirm.

Fix: `user.onboarding_step >= 1` 이면 SELECT 1번만 + early return. workspace/member/onboarding
hook 모두 SKIP. 신규 user / step=0 (lazy seed 미완료) 는 기존 경로 fall-through.

본 test: mock UserRepository 로 onboarding_step 검증 + session.execute 호출 횟수 검증.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_current_user_fast_path_skips_lazy_seed_when_onboarded():
    """onboarding_step >= 1 user 는 lazy seed SQL 호출 0건 (fast path)."""
    from src.auth.dependencies import get_current_user
    from src.auth.models import User
    import uuid

    # Mock: existing user with onboarding_step >= 1
    existing_user = MagicMock(spec=User)
    existing_user.id = uuid.uuid4()
    existing_user.clerk_id = "user_abc"
    existing_user.onboarding_step = 1
    existing_user.display_name = "Test"

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    claims = {"sub": "user_abc"}

    with patch("src.auth.dependencies.UserRepository") as MockRepo:
        repo = AsyncMock()
        repo.find_by_clerk_id = AsyncMock(return_value=existing_user)
        MockRepo.return_value = repo

        result = await get_current_user(claims=claims, session=mock_session)

    # Fast path: session.execute 호출 0건 (lazy seed SQL 미실행)
    assert mock_session.execute.call_count == 0, (
        f"Fast path 위반: session.execute call_count={mock_session.execute.call_count} "
        f"(0 이어야 함 — onboarding_step >= 1 시 lazy seed SKIP)"
    )
    # commit 도 호출 0건
    assert mock_session.commit.call_count == 0
    # 동일 user 반환
    assert result is existing_user
    # find_by_clerk_id 는 1번만 호출 (re-fetch 없음)
    assert repo.find_by_clerk_id.call_count == 1


@pytest.mark.asyncio
async def test_get_current_user_falls_through_when_onboarding_step_zero():
    """onboarding_step=0 (lazy seed 미완료) user 는 기존 lazy seed 경로 fall-through."""
    from src.auth.dependencies import get_current_user
    from src.auth.models import User
    import uuid

    existing_user = MagicMock(spec=User)
    existing_user.id = uuid.uuid4()
    existing_user.clerk_id = "user_xyz"
    existing_user.onboarding_step = 0  # lazy seed 미완료
    existing_user.display_name = "New"

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    claims = {"sub": "user_xyz"}

    with patch("src.auth.dependencies.UserRepository") as MockRepo, \
         patch("src.onboarding.service.OnboardingService"):
        repo = AsyncMock()
        repo.find_by_clerk_id = AsyncMock(return_value=existing_user)
        MockRepo.return_value = repo

        await get_current_user(claims=claims, session=mock_session)

    # Fall-through: workspace + member SQL 호출 (2건 이상)
    assert mock_session.execute.call_count >= 2, (
        f"Fall-through 위반: step=0 시 lazy seed SQL 실행되어야 함 (current count={mock_session.execute.call_count})"
    )


@pytest.mark.asyncio
async def test_get_current_user_new_user_full_seed_path():
    """user 없음 (신규 첫 로그인) → User INSERT + workspace + member 모두 실행."""
    from src.auth.dependencies import get_current_user
    from src.auth.models import User
    import uuid

    created_user = MagicMock(spec=User)
    created_user.id = uuid.uuid4()
    created_user.clerk_id = "user_new"
    created_user.onboarding_step = 0
    created_user.display_name = "Brand New"

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    claims = {"sub": "user_new"}

    with patch("src.auth.dependencies.UserRepository") as MockRepo, \
         patch("src.onboarding.service.OnboardingService"):
        repo = AsyncMock()
        # 첫 find = None, INSERT 후 re-fetch = created_user
        repo.find_by_clerk_id = AsyncMock(side_effect=[None, created_user])
        MockRepo.return_value = repo

        result = await get_current_user(claims=claims, session=mock_session)

    # User INSERT + workspace + member = 3건 이상
    assert mock_session.execute.call_count >= 3
    # find_by_clerk_id 2번 (initial + re-fetch)
    assert repo.find_by_clerk_id.call_count == 2
    assert result is created_user
