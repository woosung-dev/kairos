# Sprint 28 Wave 1 — feedback 제출 단위 + 통합 테스트
import uuid

import pytest
import pytest_asyncio
from fastapi import BackgroundTasks
from httpx import ASGITransport, AsyncClient
from sqlmodel import select
from unittest.mock import AsyncMock

from src.feedback.models import FeedbackEntry
from src.feedback.service import FeedbackService, _format_slack_message


# ── 단위: Slack 메시지 포맷 ──────────────────────────────────────────

class TestFormatSlackMessage:
    def test_with_rating(self):
        msg = _format_slack_message(
            display_name="우성", is_anonymous=False, rating=4, body="좋아요", page_url="/dashboard"
        )
        assert "우성" in msg
        assert "★★★★☆" in msg
        assert "좋아요" in msg
        assert "/dashboard" in msg

    def test_anonymous_hides_name(self):
        msg = _format_slack_message(
            display_name="우성", is_anonymous=True, rating=None, body="버그", page_url=None
        )
        assert "우성" not in msg
        assert "익명" in msg

    def test_no_rating_no_stars(self):
        msg = _format_slack_message(
            display_name="우성", is_anonymous=False, rating=None, body="의견", page_url=None
        )
        assert "★" not in msg
        assert "☆" not in msg


# ── 단위: 서비스 submit (AsyncMock repo + 실 BackgroundTasks) ──────────

class TestFeedbackServiceSubmit:
    @pytest.mark.asyncio
    async def test_submit_saves_and_schedules_notify(self):
        repo = AsyncMock()
        saved = {}

        async def _save(entry: FeedbackEntry):
            saved["entry"] = entry
            return entry

        repo.save = _save
        repo.commit = AsyncMock()

        service = FeedbackService(feedback_repo=repo)
        bt = BackgroundTasks()
        user_id = uuid.uuid4()

        result = await service.submit(
            user_id=user_id,
            body="피드백 본문",
            rating=5,
            is_anonymous=False,
            workspace_id=None,
            page_url="/notes",
            user_agent="pytest-UA",
            display_name="우성",
            background_tasks=bt,
        )

        # 저장 + commit + 백그라운드 알림 1건 예약
        assert saved["entry"].user_id == user_id
        assert saved["entry"].body == "피드백 본문"
        assert saved["entry"].user_agent == "pytest-UA"
        repo.commit.assert_awaited_once()
        assert len(bt.tasks) == 1
        assert result["status"] == "received"
        assert "id" in result and "createdAt" in result


# ── 통합: POST /api/v1/feedback ───────────────────────────────────────

@pytest_asyncio.fixture
async def feedback_client(integration_session, auth_user):
    """feedback API 테스트용 AsyncClient — get_current_user + get_async_session override."""
    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session
    from src.main import app

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_async_session] = lambda: integration_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class TestFeedbackEndpoint:
    @pytest.mark.asyncio
    async def test_submit_minimal_persists(self, feedback_client, auth_user, integration_session):
        resp = await feedback_client.post(
            "/api/v1/feedback",
            json={"body": "최소 피드백"},
            headers={"user-agent": "pytest-agent"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "received"

        rows = (
            await integration_session.exec(
                select(FeedbackEntry).where(FeedbackEntry.user_id == auth_user.id)
            )
        ).all()
        assert len(rows) == 1
        entry = rows[0]
        assert entry.body == "최소 피드백"
        assert entry.workspace_id is None
        assert entry.rating is None
        assert entry.is_anonymous is False
        # user_agent 는 서버에서 헤더 추출
        assert entry.user_agent == "pytest-agent"

    @pytest.mark.asyncio
    async def test_submit_full_with_workspace(
        self, feedback_client, auth_user, personal_ws, integration_session
    ):
        resp = await feedback_client.post(
            "/api/v1/feedback",
            json={
                "body": "별점+익명+워크스페이스",
                "rating": 4,
                "isAnonymous": True,
                "workspaceId": str(personal_ws.id),
                "pageUrl": "/dashboard",
            },
        )
        assert resp.status_code == 201

        entry = (
            await integration_session.exec(
                select(FeedbackEntry).where(FeedbackEntry.workspace_id == personal_ws.id)
            )
        ).one()
        assert entry.rating == 4
        assert entry.is_anonymous is True
        assert entry.page_url == "/dashboard"
        assert entry.user_id == auth_user.id

    @pytest.mark.asyncio
    async def test_empty_body_rejected(self, feedback_client):
        resp = await feedback_client.post("/api/v1/feedback", json={"body": ""})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_rating_out_of_range_rejected(self, feedback_client):
        resp = await feedback_client.post(
            "/api/v1/feedback", json={"body": "ok", "rating": 9}
        )
        assert resp.status_code == 422
