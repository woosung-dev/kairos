# Sprint 23 D4 Task 2 Step 2.2 — Meetings promote 통합 테스트
"""Meetings promote 1-button: Meeting/Summary/Segments 복제 + ItemPromotionAudit + 검증.

I-18 (복제 + tombstone): 원본 Meeting.status 변경 없이 target ws 복제본 신규 + audit.
검증: source != target / target type='team' / promoter 가 target ws 멤버.
4 케이스: success / same_workspace 400 / target_not_member 403 / target_personal 400.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import select


@pytest_asyncio.fixture
async def meetings_client(integration_session, auth_user, monkeypatch):
    """Meetings API 테스트용 AsyncClient — get_current_user + get_async_session + session_factory override.

    BG task 는 외부 OpenAI 호출 없이 EmbeddingChunk 복제만 수행 — 실제 호출 차단 불필요.
    단 session_factory 는 동일 integration_session 재사용 (테스트 격리 위해).
    """
    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session, get_session_factory
    from src.main import app

    # session_factory 는 async context manager 인터페이스 필요 → 같은 session 반환하는 dummy.
    class _DummyFactory:
        def __call__(self):
            return _DummyAsyncCM(integration_session)

    class _DummyAsyncCM:
        def __init__(self, sess):
            self._sess = sess

        async def __aenter__(self):
            return self._sess

        async def __aexit__(self, *_args):
            return False

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_session_factory] = lambda: _DummyFactory()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_meeting(integration_session, auth_user, personal_ws):
    """personal ws 의 Meeting + MeetingSummary + 2 TranscriptSegment + EmbeddingChunk seed.

    Sprint 23 Codex 8차 P2 fix: promote preflight 이 source status='completed' + chunk 0
    case 를 거부 (notes 6차 P2 패턴). fixture 가 임베딩 완료 상태 시뮬레이트.
    """
    from src.embeddings.models import EmbeddingChunk
    from src.meetings.models import Meeting, MeetingSummary, TranscriptSegment

    meeting = Meeting(
        workspace_id=personal_ws.id,
        title="테스트 회의",
        file_key="uploads/test/meeting.mp3",
        source=None,
        status="completed",
        has_transcript=True,
        has_summary=True,
        action_item_count=0,
        created_by_id=auth_user.id,
    )
    integration_session.add(meeting)
    await integration_session.flush()

    summary = MeetingSummary(
        meeting_id=meeting.id,
        summary="요약 내용",
        key_decisions=["결정 1", "결정 2"],
        topics=["주제 1"],
    )
    integration_session.add(summary)

    segments = [
        TranscriptSegment(
            meeting_id=meeting.id,
            speaker="Speaker 1",
            start_sec=0.0,
            end_sec=5.0,
            text="첫 번째 문장",
        ),
        TranscriptSegment(
            meeting_id=meeting.id,
            speaker="Speaker 1",
            start_sec=5.0,
            end_sec=10.0,
            text="두 번째 문장",
        ),
    ]
    for seg in segments:
        integration_session.add(seg)

    # Sprint 23 Codex 8차 P2: 임베딩 완료 상태 시뮬레이트 (chunk 1건, vector 더미 1536d).
    chunk = EmbeddingChunk(
        workspace_id=personal_ws.id,
        project_id=None,
        source_id=meeting.id,
        source_type="meeting",
        chunk_text="첫 번째 문장",
        chunk_index=0,
        chunk_level=1,
        embedding=[0.0] * 1536,
        metadata_json={},
    )
    integration_session.add(chunk)
    await integration_session.flush()
    await integration_session.commit()
    return meeting


@pytest.mark.asyncio
async def test_promote_creates_duplicate_and_audit(
    meetings_client,
    integration_session,
    personal_ws,
    team_ws,
    seed_meeting,
    auth_user,
):
    """personal → team promote → 202 + new Meeting/Summary/Segments 복제 + audit row."""
    from src.common.promote_models import ItemPromotionAudit
    from src.meetings.models import Meeting, MeetingSummary, TranscriptSegment

    response = await meetings_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/meetings/{seed_meeting.id}/promote",
        json={"targetWorkspaceId": str(team_ws.id)},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    new_id = body["newMeetingId"] if "newMeetingId" in body else body["new_meeting_id"]
    audit_id = body["auditId"] if "auditId" in body else body["audit_id"]
    assert uuid.UUID(new_id)
    assert uuid.UUID(audit_id)
    assert body["status"] == "embedding_pending"
    assert new_id != str(seed_meeting.id)

    # 원본 보존 — status 변경 없음
    src_q = select(Meeting).where(Meeting.id == seed_meeting.id)
    src = (await integration_session.execute(src_q)).scalar_one()
    assert src.status == "completed"
    assert src.workspace_id == personal_ws.id

    # 복제본 Meeting (target ws)
    dup_q = select(Meeting).where(
        Meeting.workspace_id == team_ws.id,
        Meeting.id != seed_meeting.id,
    )
    dup = (await integration_session.execute(dup_q)).scalar_one()
    assert dup.title == seed_meeting.title
    assert dup.file_key == seed_meeting.file_key
    assert dup.created_by_id == auth_user.id

    # 복제 Summary
    sum_q = select(MeetingSummary).where(MeetingSummary.meeting_id == dup.id)
    dup_summary = (await integration_session.execute(sum_q)).scalar_one()
    assert dup_summary.summary == "요약 내용"
    assert dup_summary.key_decisions == ["결정 1", "결정 2"]

    # 복제 Segments
    seg_q = select(TranscriptSegment).where(TranscriptSegment.meeting_id == dup.id)
    dup_segments = (await integration_session.execute(seg_q)).scalars().all()
    assert len(list(dup_segments)) == 2

    # ItemPromotionAudit row
    audit_q = select(ItemPromotionAudit).where(
        ItemPromotionAudit.id == uuid.UUID(audit_id)
    )
    audit = (await integration_session.execute(audit_q)).scalar_one()
    assert audit.item_type == "meeting"
    assert audit.source_item_id == seed_meeting.id
    assert audit.new_item_id == dup.id
    assert audit.source_workspace_id == personal_ws.id
    assert audit.target_workspace_id == team_ws.id
    assert audit.promoted_by_user_id == auth_user.id


@pytest.mark.asyncio
async def test_promote_same_workspace_rejected(
    meetings_client, personal_ws, seed_meeting
):
    """source == target → 400 (CannotPromoteToSameWorkspaceError)."""
    response = await meetings_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/meetings/{seed_meeting.id}/promote",
        json={"targetWorkspaceId": str(personal_ws.id)},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_promote_target_not_member_rejected(
    meetings_client, integration_session, personal_ws, seed_meeting
):
    """target ws 가 promoter 의 멤버 아님 → 403 (TargetWorkspaceInvalidError)."""
    from src.auth.models import User
    from src.workspaces.models import Workspace, WorkspaceMember

    # promoter 가 멤버 아닌 별도 team workspace (다른 owner)
    other_owner = User(
        auth_user_id="other_ba",
        display_name="다른 오너",
        email="other@kairos.test",
    )
    integration_session.add(other_owner)
    await integration_session.flush()

    other_team = Workspace(
        name="다른 팀",
        owner_id=other_owner.id,
        type="team",
    )
    integration_session.add(other_team)
    await integration_session.flush()
    # promoter (auth_user) 는 멤버 아님 — other_owner 만 멤버
    integration_session.add(
        WorkspaceMember(
            workspace_id=other_team.id,
            user_id=other_owner.id,
            role="owner",
        )
    )
    await integration_session.flush()
    await integration_session.commit()

    response = await meetings_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/meetings/{seed_meeting.id}/promote",
        json={"targetWorkspaceId": str(other_team.id)},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_promote_target_personal_rejected(
    meetings_client, integration_session, personal_ws, seed_meeting, auth_user
):
    """target ws.type='personal' → 400 (CannotPromoteToPersonalError)."""
    from src.workspaces.models import Workspace, WorkspaceMember

    # auth_user 가 멤버인 두 번째 personal ws (보통 1인 1ws 정책이지만 테스트용)
    other_personal = Workspace(
        name="다른 개인 ws",
        owner_id=auth_user.id,
        type="personal",
    )
    integration_session.add(other_personal)
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(
            workspace_id=other_personal.id,
            user_id=auth_user.id,
            role="owner",
        )
    )
    await integration_session.flush()
    await integration_session.commit()

    response = await meetings_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/meetings/{seed_meeting.id}/promote",
        json={"targetWorkspaceId": str(other_personal.id)},
    )
    assert response.status_code == 400


# ── Sprint 24 Task 2 (BL-063): ActionItem 자동 복제 통합 테스트 ──


@pytest.mark.asyncio
async def test_promote_clones_action_items_with_count(
    meetings_client,
    integration_session,
    personal_ws,
    team_ws,
    seed_meeting,
    auth_user,
):
    """BL-063: Meeting promote 시 source ActionItem 3 rows 자동 복제 + count 갱신.

    Sprint 23 D4 Codex 3차 P3 임시 fix (action_item_count=0) 보강.
    cloned actions 의 status 종류 보존 + Meeting.action_item_count 가 실 row count 와 정합.
    """
    from src.actions.models import ActionItem
    from src.meetings.models import Meeting

    # seed_meeting 에 3 ActionItem (status 다양) 추가 (source 측)
    statuses = ["todo", "done", "in_progress"]
    for s in statuses:
        integration_session.add(
            ActionItem(
                workspace_id=personal_ws.id,
                meeting_id=seed_meeting.id,
                project_id=None,
                title=f"액션 {s}",
                description=None,
                assignee_id=None,
                status=s,
                priority="medium",
            )
        )
    await integration_session.flush()
    await integration_session.commit()

    response = await meetings_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/meetings/{seed_meeting.id}/promote",
        json={"targetWorkspaceId": str(team_ws.id)},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    new_meeting_id = uuid.UUID(
        body["newMeetingId"] if "newMeetingId" in body else body["new_meeting_id"]
    )

    # target 의 ActionItem rows 3개 + status 종류 보존
    target_actions = (
        await integration_session.execute(
            select(ActionItem).where(ActionItem.meeting_id == new_meeting_id)
        )
    ).scalars().all()
    assert len(target_actions) == 3
    assert {a.status for a in target_actions} == set(statuses)
    # composite FK remap — workspace_id 가 target 으로 갱신됐는지 verify
    assert all(a.workspace_id == team_ws.id for a in target_actions)

    # Meeting.action_item_count 가 실 row count 와 정합 (Sprint 23 의 0 reset 보강)
    target_meeting = (
        await integration_session.execute(
            select(Meeting).where(Meeting.id == new_meeting_id)
        )
    ).scalar_one()
    assert target_meeting.action_item_count == 3

    # source 의 ActionItem 은 변경 없이 보존 (I-18 tombstone)
    source_actions = (
        await integration_session.execute(
            select(ActionItem).where(ActionItem.meeting_id == seed_meeting.id)
        )
    ).scalars().all()
    assert len(source_actions) == 3


@pytest.mark.asyncio
async def test_promote_with_zero_action_items_keeps_count_zero(
    meetings_client,
    integration_session,
    personal_ws,
    team_ws,
    seed_meeting,
):
    """BL-063: ActionItem 0 건 promote → action_item_count=0 + ActionItem rows 0.

    회귀 가드 — 기존 Sprint 23 4 case (ActionItem 없음) 동작 보존.
    """
    from src.actions.models import ActionItem
    from src.meetings.models import Meeting

    response = await meetings_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/meetings/{seed_meeting.id}/promote",
        json={"targetWorkspaceId": str(team_ws.id)},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    new_meeting_id = uuid.UUID(
        body["newMeetingId"] if "newMeetingId" in body else body["new_meeting_id"]
    )

    target_actions = (
        await integration_session.execute(
            select(ActionItem).where(ActionItem.meeting_id == new_meeting_id)
        )
    ).scalars().all()
    assert len(target_actions) == 0

    target_meeting = (
        await integration_session.execute(
            select(Meeting).where(Meeting.id == new_meeting_id)
        )
    ).scalar_one()
    assert target_meeting.action_item_count == 0


@pytest.mark.asyncio
async def test_promote_resets_assignee_when_not_target_workspace_member(
    meetings_client,
    integration_session,
    personal_ws,
    team_ws,
    seed_meeting,
    auth_user,
):
    """BL-063: source ActionItem assignee_id 가 target ws 비멤버 → None reset (cross-ws 누출 차단).

    사용자 결정 게이트 #5 — silent reset 정책 (target ws member 가 아니면 assignee_id=None).
    """
    from src.actions.models import ActionItem
    from src.auth.models import User

    # auth_user 는 personal_ws/team_ws 둘 다 멤버.
    # 별도 user X — source ws (personal_ws) 멤버 가정하지 않더라도, 본 테스트의 핵심은
    # target ws (team_ws) 의 멤버가 아닌 user_id 가 assignee 일 때 None reset 여부.
    # → external_user 는 어떤 ws 멤버도 아니어도 됨 (assignee_id 필드는 nullable FK
    #   to users.id 라 user 가 존재만 하면 OK; target ws WorkspaceMember 부재가 핵심).
    external_user = User(
        auth_user_id="external_ba_bl063",
        display_name="외부 사용자",
        email="external_bl063@kairos.test",
    )
    integration_session.add(external_user)
    await integration_session.flush()

    # source meeting 에 ActionItem 2건 추가 — 하나는 external assignee, 하나는 auth_user (target 멤버)
    integration_session.add(
        ActionItem(
            workspace_id=personal_ws.id,
            meeting_id=seed_meeting.id,
            project_id=None,
            title="외부 assignee",
            assignee_id=external_user.id,
            status="todo",
            priority="medium",
        )
    )
    integration_session.add(
        ActionItem(
            workspace_id=personal_ws.id,
            meeting_id=seed_meeting.id,
            project_id=None,
            title="내부 assignee",
            assignee_id=auth_user.id,
            status="todo",
            priority="medium",
        )
    )
    await integration_session.flush()
    await integration_session.commit()

    response = await meetings_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/meetings/{seed_meeting.id}/promote",
        json={"targetWorkspaceId": str(team_ws.id)},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    new_meeting_id = uuid.UUID(
        body["newMeetingId"] if "newMeetingId" in body else body["new_meeting_id"]
    )

    target_actions = (
        await integration_session.execute(
            select(ActionItem)
            .where(ActionItem.meeting_id == new_meeting_id)
            .order_by(ActionItem.title)
        )
    ).scalars().all()
    assert len(target_actions) == 2
    by_title = {a.title: a for a in target_actions}
    # external assignee → None reset
    assert by_title["외부 assignee"].assignee_id is None
    # 내부 assignee (auth_user) — target ws member 이므로 보존
    assert by_title["내부 assignee"].assignee_id == auth_user.id
