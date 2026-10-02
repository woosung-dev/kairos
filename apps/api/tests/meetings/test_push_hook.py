# 회의 파이프라인 웹 푸시 훅 (PWA PR-2, pwa.md §5.3) — T-PWA-35~42, TestContainers 통합
"""실 DB + 실 Repository 로 파이프라인을 돌리고, 외부 호출(Gemini·R2·STT·임베딩)과 sender 만 가짜로 둔다.

수신자 규칙·멤버십·구독 조회·404/410 정리가 모두 실제 SQL 을 거치므로 mock 이 게이트를 대신하지 않는다.
"""
import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.meetings.models import Meeting, TranscriptSegment
from src.meetings.pipeline_service import MeetingPipelineService
from src.meetings.repository import MeetingRepository
from src.push.models import PushSubscription
from src.push.service import PUSH_PAYLOAD_MAX_BYTES, PushDispatchService
from src.workspaces.models import Workspace, WorkspaceMember
from tests.fixtures.push import (
    TEST_VAPID_SUBJECT,
    FakeSender,
    generate_vapid_key_pair,
    push_loggers_enabled,  # noqa: F401 — pytestmark usefixtures 로 사용
    settings_with_vapid,
    valid_subscription_keys,
)

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("push_loggers_enabled")]

SECRET_TITLE = "극비 인수 협상 회의"
SECRET_SUMMARY = "요약 본문 — 인수가 3억"
SECRET_TRANSCRIPT = "전사 원문 — 인수가는 비밀"

UPLOADER_ENDPOINTS = (
    "https://fcm.googleapis.com/fcm/send/uploader-chrome",
    "https://updates.push.services.mozilla.com/wpush/v2/uploader-firefox",
)
OWNER_ENDPOINT = "https://fcm.googleapis.com/fcm/send/owner-chrome"

PATHS = ["capture_text", "process_meeting"]


class SessionSpy:
    """session_factory 감시 — 세션 열림/닫힘 순서와 현재 열린 세션 수 (T-PWA-41)."""

    def __init__(self, maker: async_sessionmaker[AsyncSession]) -> None:
        self._maker = maker
        self.events: list[tuple[str, int]] = []
        self.open_count = 0
        self._seq = 0

    def __call__(self):
        return self._session()

    @asynccontextmanager
    async def _session(self):
        self._seq += 1
        index = self._seq
        self.open_count += 1
        self.events.append(("open", index))
        try:
            async with self._maker() as session:
                yield session
        finally:
            self.open_count -= 1
            self.events.append(("close", index))

    @property
    def opened(self) -> int:
        return self._seq


@dataclass
class HookEnv:
    maker: async_sessionmaker[AsyncSession]
    spy: SessionSpy
    workspace_id: uuid.UUID
    meeting_id: uuid.UUID
    uploader_id: uuid.UUID
    owner_id: uuid.UUID


@pytest_asyncio.fixture
async def hook_env(integration_session) -> HookEnv:
    """팀 워크스페이스: owner(다른 사람) + 업로더(member). 업로더 구독 2 · owner 구독 1."""
    owner = User(auth_user_id="push_hook_owner", display_name="관리자", email="owner@kairos.test")
    uploader = User(auth_user_id="push_hook_uploader", display_name="업로더", email="uploader@kairos.test")
    integration_session.add_all([owner, uploader])
    await integration_session.flush()

    workspace = Workspace(name="푸시 팀", owner_id=owner.id, type="team")
    integration_session.add(workspace)
    await integration_session.flush()
    integration_session.add_all(
        [
            WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="owner"),
            WorkspaceMember(workspace_id=workspace.id, user_id=uploader.id, role="member"),
        ]
    )
    meeting = Meeting(
        workspace_id=workspace.id,
        title=SECRET_TITLE,
        file_key="uploads/test/audio.mp3",
        created_by_id=uploader.id,
    )
    integration_session.add(meeting)
    for endpoint in UPLOADER_ENDPOINTS:
        keys = valid_subscription_keys()
        integration_session.add(
            PushSubscription(user_id=uploader.id, endpoint=endpoint, p256dh=keys["p256dh"], auth=keys["auth"])
        )
    owner_keys = valid_subscription_keys()
    integration_session.add(
        PushSubscription(user_id=owner.id, endpoint=OWNER_ENDPOINT, p256dh=owner_keys["p256dh"], auth=owner_keys["auth"])
    )
    await integration_session.commit()

    maker = async_sessionmaker(integration_session.bind, class_=AsyncSession, expire_on_commit=False)
    return HookEnv(
        maker=maker,
        spy=SessionSpy(maker),
        workspace_id=workspace.id,
        meeting_id=meeting.id,
        uploader_id=uploader.id,
        owner_id=owner.id,
    )


@pytest.fixture(autouse=True)
def _no_embedding_calls(monkeypatch):
    """임베딩(OpenAI) 호출 차단 — 파이프라인은 비치명적으로 다루지만 네트워크를 타지 않게."""
    embedding = AsyncMock()
    embedding.embed_meeting.return_value = 0
    monkeypatch.setattr(
        "src.meetings.pipeline_service.EmbeddingService", lambda *_args, **_kwargs: embedding
    )


def _use_fake_sender(monkeypatch, sender: FakeSender) -> None:
    monkeypatch.setattr(
        "src.push.service.create_push_dispatcher", lambda: PushDispatchService(sender)
    )


def _pipeline(env: HookEnv, *, analysis_error: Exception | None = None) -> MeetingPipelineService:
    ai = AsyncMock()
    if analysis_error is not None:
        ai.summarize.side_effect = analysis_error
    else:
        ai.summarize.return_value = {"summary": SECRET_SUMMARY, "key_decisions": [], "topics": []}
    ai.extract_actions_and_link.return_value = {
        "actionItems": [],
        "suggestedProject": {"existingProjectId": None, "newProjectTitle": None, "confidence": 0.0},
        "suggestedTags": [],
    }
    r2 = AsyncMock()
    r2.get_download_url.return_value = "https://r2.example.invalid/audio.mp3"
    transcription = AsyncMock()
    transcription.download_audio.return_value = b"audio"
    transcription.transcribe_with_chunking.return_value = (
        [TranscriptSegment(speaker="화자", start_sec=0.0, end_sec=1.0, text=SECRET_TRANSCRIPT)],
        1.0,
    )
    return MeetingPipelineService(
        session_factory=env.spy,
        r2_service=r2,
        transcription_service=transcription,
        ai_service=ai,
    )


async def _run(pipeline: MeetingPipelineService, path: str, meeting_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
    if path == "capture_text":
        await pipeline.capture_text(meeting_id, workspace_id, SECRET_TRANSCRIPT)
    else:
        await pipeline.process_meeting(meeting_id, workspace_id)


async def _meeting_status(env: HookEnv) -> str:
    async with env.maker() as session:
        meeting = (await session.exec(select(Meeting).where(Meeting.id == env.meeting_id))).one()
        return meeting.status


async def _endpoints(env: HookEnv) -> set[str]:
    async with env.maker() as session:
        return set((await session.exec(select(PushSubscription.endpoint))).all())


# ── T-PWA-35 완료 발송 ────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PATHS)
async def test_t_pwa_35_completed_sends_only_to_uploader(hook_env, monkeypatch, path):
    """T-PWA-35: 성공 → sender 호출 대상 = 업로더 구독 2개, 같은 워크스페이스 owner 구독 0 · kind=completed."""
    sender = FakeSender()
    _use_fake_sender(monkeypatch, sender)

    await _run(_pipeline(hook_env), path, hook_env.meeting_id, hook_env.workspace_id)

    assert await _meeting_status(hook_env) == "completed"
    assert len(sender.calls) == 1
    targets, payload = sender.calls[0]
    assert {t.endpoint for t in targets} == set(UPLOADER_ENDPOINTS)
    assert OWNER_ENDPOINT not in {t.endpoint for t in targets}
    assert json.loads(payload)["kind"] == "meeting.completed"


@pytest.mark.asyncio
async def test_t_pwa_35_real_dispatcher_wiring_uses_vapid_settings(hook_env, monkeypatch):
    """T-PWA-35: 실제 create_push_dispatcher 경로 — 설정 VAPID 로 sender 를 만들고 업로더에게 보낸다."""
    private_key, public_key = generate_vapid_key_pair()
    monkeypatch.setattr(
        "src.push.service.get_settings",
        lambda: settings_with_vapid(public_key=public_key, private_key=private_key, subject=TEST_VAPID_SUBJECT),
    )
    sender = FakeSender()
    created: list[dict] = []

    def _sender_factory(**kwargs):
        created.append(kwargs)
        return sender

    monkeypatch.setattr("src.push.service.WebPushSender", _sender_factory)

    await _run(_pipeline(hook_env), "capture_text", hook_env.meeting_id, hook_env.workspace_id)

    assert created == [{"vapid_private_key": private_key, "vapid_subject": TEST_VAPID_SUBJECT}]
    assert len(sender.calls) == 1
    assert {t.endpoint for t in sender.calls[0][0]} == set(UPLOADER_ENDPOINTS)


# ── T-PWA-36 실패 발송 ────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PATHS)
async def test_t_pwa_36_failed_sends_failed_kind_to_uploader(hook_env, monkeypatch, path):
    """T-PWA-36: 분석 예외 주입 → status failed + 업로더에게 kind=meeting.failed."""
    sender = FakeSender()
    _use_fake_sender(monkeypatch, sender)

    await _run(
        _pipeline(hook_env, analysis_error=RuntimeError("analysis failed")),
        path,
        hook_env.meeting_id,
        hook_env.workspace_id,
    )

    assert await _meeting_status(hook_env) == "failed"
    assert len(sender.calls) == 1
    targets, payload = sender.calls[0]
    assert {t.endpoint for t in targets} == set(UPLOADER_ENDPOINTS)
    assert json.loads(payload)["kind"] == "meeting.failed"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PATHS)
async def test_t_pwa_36_failed_status_commit_failure_sends_nothing(hook_env, monkeypatch, path):
    """T-PWA-36: 실패 상태 commit 자체가 실패 → sender 호출 0 (파이프라인 예외 전파도 0)."""
    sender = FakeSender()
    _use_fake_sender(monkeypatch, sender)
    original_update = MeetingRepository.update_status
    original_commit = MeetingRepository.commit
    state = {"failed_pending": False}

    async def _update_status(self, meeting_id, workspace_id, status, error_message=None):
        if status == "failed":
            state["failed_pending"] = True
        await original_update(self, meeting_id, workspace_id, status, error_message=error_message)

    async def _commit(self):
        if state["failed_pending"]:
            raise RuntimeError("db down during failed-status commit")
        await original_commit(self)

    monkeypatch.setattr(MeetingRepository, "update_status", _update_status)
    monkeypatch.setattr(MeetingRepository, "commit", _commit)

    await _run(
        _pipeline(hook_env, analysis_error=RuntimeError("analysis failed")),
        path,
        hook_env.meeting_id,
        hook_env.workspace_id,
    )

    assert state["failed_pending"] is True
    assert await _meeting_status(hook_env) != "failed"
    assert sender.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PATHS)
async def test_t_pwa_36_missing_meeting_early_return_sends_nothing(hook_env, monkeypatch, path):
    """T-PWA-36: `meeting is None` 조기 return → sender 호출 0, 조회 세션도 열지 않는다."""
    sender = FakeSender()
    _use_fake_sender(monkeypatch, sender)

    await _run(_pipeline(hook_env), path, uuid.uuid4(), hook_env.workspace_id)

    assert sender.calls == []
    assert hook_env.spy.opened == 1


# ── T-PWA-37 best-effort ──────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize(
    ("analysis_error", "expected_status"),
    [(None, "completed"), (RuntimeError("analysis failed"), "failed")],
)
@pytest.mark.parametrize(
    "sender_error",
    [RuntimeError(f"boom {UPLOADER_ENDPOINTS[0]}"), asyncio.TimeoutError()],
    ids=["exception", "timeout"],
)
async def test_t_pwa_37_sender_failure_never_changes_meeting_status(
    hook_env, monkeypatch, caplog, path, analysis_error, expected_status, sender_error
):
    """T-PWA-37: sender 예외·타임아웃 → status 그대로 · 예외 전파 0 · warning 1줄 (endpoint 미포함)."""
    sender = FakeSender(exc=sender_error)
    _use_fake_sender(monkeypatch, sender)

    with caplog.at_level(logging.INFO):
        await _run(
            _pipeline(hook_env, analysis_error=analysis_error),
            path,
            hook_env.meeting_id,
            hook_env.workspace_id,
        )

    assert await _meeting_status(hook_env) == expected_status
    assert len(sender.calls) == 1
    warnings = [r for r in caplog.records if r.name.startswith("src.") and r.levelno == logging.WARNING]
    assert len(warnings) == 1, [r.getMessage() for r in warnings]
    assert "push_dispatch_failed" in warnings[0].getMessage()
    assert type(sender_error).__name__ in warnings[0].getMessage()
    assert warnings[0].exc_info is None
    for record in caplog.records:
        message = record.getMessage()
        assert all(endpoint not in message for endpoint in (*UPLOADER_ENDPOINTS, OWNER_ENDPOINT))


# ── T-PWA-38 응답 코드별 정리 ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_t_pwa_38_gone_rows_are_pruned_and_others_kept(hook_env, monkeypatch, integration_session):
    """T-PWA-38: 404·410 → 행 삭제 · 429·500·403·413·201 → 행 유지 · 정리 세션은 그때만 연다."""
    statuses = {
        f"https://fcm.googleapis.com/fcm/send/s{code}": code
        for code in (404, 410, 429, 500, 403, 413, 201)
    }
    for endpoint in statuses:
        keys = valid_subscription_keys()
        integration_session.add(
            PushSubscription(user_id=hook_env.uploader_id, endpoint=endpoint, p256dh=keys["p256dh"], auth=keys["auth"])
        )
    await integration_session.commit()
    sender = FakeSender(status_by_endpoint=statuses)
    _use_fake_sender(monkeypatch, sender)

    await _run(_pipeline(hook_env), "capture_text", hook_env.meeting_id, hook_env.workspace_id)

    remaining = await _endpoints(hook_env)
    gone = {e for e, code in statuses.items() if code in (404, 410)}
    kept = {e for e, code in statuses.items() if code not in (404, 410)}
    assert remaining.isdisjoint(gone)
    assert kept <= remaining
    assert set(UPLOADER_ENDPOINTS) <= remaining
    assert OWNER_ENDPOINT in remaining
    # 파이프라인 · 조회 · 정리
    assert hook_env.spy.opened == 3


@pytest.mark.asyncio
async def test_t_pwa_38_no_gone_response_opens_no_cleanup_session(hook_env, monkeypatch):
    """T-PWA-38: 404·410 이 0건이면 정리 세션을 열지 않는다 (파이프라인 · 조회 2개뿐)."""
    sender = FakeSender(default_status=500)
    _use_fake_sender(monkeypatch, sender)

    await _run(_pipeline(hook_env), "capture_text", hook_env.meeting_id, hook_env.workspace_id)

    assert len(sender.calls) == 1
    assert hook_env.spy.opened == 2
    assert await _endpoints(hook_env) == {*UPLOADER_ENDPOINTS, OWNER_ENDPOINT}


@pytest.mark.asyncio
async def test_t_pwa_38_prune_never_touches_other_users_rows(hook_env, monkeypatch, integration_session):
    """T-PWA-38: 정리 삭제는 `id AND user_id` — 다른 사용자 행 id 가 섞여 와도 지우지 않는다."""
    from src.push.repository import PushRepository

    async with hook_env.maker() as session:
        owner_target = (await PushRepository(session).list_by_user(hook_env.owner_id))[0]
        deleted = await PushRepository(session).delete_by_ids([owner_target.id], hook_env.uploader_id)
        await session.commit()

    assert deleted == 0
    assert OWNER_ENDPOINT in await _endpoints(hook_env)


# ── T-PWA-39 미구성 ───────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PATHS)
async def test_t_pwa_39_unconfigured_vapid_sends_nothing(hook_env, monkeypatch, path):
    """T-PWA-39: VAPID 미설정 → sender 생성·호출 0 · 예외 0 · 조회 세션도 열지 않는다."""
    monkeypatch.setattr(
        "src.push.service.get_settings",
        lambda: settings_with_vapid(public_key=None, private_key=None, subject=None),
    )
    created: list[dict] = []
    monkeypatch.setattr("src.push.service.WebPushSender", lambda **kwargs: created.append(kwargs))

    await _run(_pipeline(hook_env), path, hook_env.meeting_id, hook_env.workspace_id)

    assert await _meeting_status(hook_env) == "completed"
    assert created == []
    assert hook_env.spy.opened == 1


# ── T-PWA-40 비멤버 업로더 ─────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PATHS)
async def test_t_pwa_40_uploader_removed_from_workspace_gets_nothing(
    hook_env, monkeypatch, integration_session, path
):
    """T-PWA-40: 업로더를 워크스페이스에서 제거한 뒤 완료 → sender 호출 0."""
    await integration_session.exec(
        delete(WorkspaceMember).where(
            WorkspaceMember.workspace_id == hook_env.workspace_id,
            WorkspaceMember.user_id == hook_env.uploader_id,
        )
    )
    await integration_session.commit()
    sender = FakeSender()
    _use_fake_sender(monkeypatch, sender)

    await _run(_pipeline(hook_env), path, hook_env.meeting_id, hook_env.workspace_id)

    assert await _meeting_status(hook_env) == "completed"
    assert sender.calls == []


# ── T-PWA-41 commit 이후 시점 + 발송 중 세션 0 ─────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize(
    ("analysis_error", "expected_status"),
    [(None, "completed"), (RuntimeError("analysis failed"), "failed")],
)
async def test_t_pwa_41_send_runs_after_commit_with_zero_open_sessions(
    hook_env, monkeypatch, path, analysis_error, expected_status
):
    """T-PWA-41: 파이프라인 close → 조회 open/close → sender(열린 세션 0, 별도 세션에서 상태 확정 확인) → 정리 open."""
    spy = hook_env.spy
    observed: dict = {}

    async def _on_send() -> None:
        observed["open_sessions"] = spy.open_count
        spy.events.append(("send", 0))
        # spy 밖 별도 세션 — 이 시점에 회의 상태가 이미 commit 돼 있어야 한다
        async with hook_env.maker() as session:
            meeting = (await session.exec(select(Meeting).where(Meeting.id == hook_env.meeting_id))).one()
            observed["status"] = meeting.status

    def _on_return() -> None:
        spy.events.append(("send_return", 0))

    # 410 1건 → 정리 세션이 열리는 경로까지 순서를 본다
    sender = FakeSender(
        status_by_endpoint={UPLOADER_ENDPOINTS[0]: 410},
        on_send=_on_send,
        on_return=_on_return,
    )
    _use_fake_sender(monkeypatch, sender)

    await _run(
        _pipeline(hook_env, analysis_error=analysis_error),
        path,
        hook_env.meeting_id,
        hook_env.workspace_id,
    )

    assert observed == {"open_sessions": 0, "status": expected_status}
    assert spy.events == [
        ("open", 1),  # 파이프라인
        ("close", 1),
        ("open", 2),  # 조회
        ("close", 2),
        ("send", 0),
        ("send_return", 0),
        ("open", 3),  # 404/410 정리
        ("close", 3),
    ]
    assert UPLOADER_ENDPOINTS[0] not in await _endpoints(hook_env)


# ── T-PWA-42 페이로드에 회의 내용 없음 ─────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PATHS)
async def test_t_pwa_42_payload_carries_ids_only(hook_env, monkeypatch, path):
    """T-PWA-42: 페이로드 = {v,kind,meetingId,workspaceId} · 제목·요약·전사 미포함 · ≤ 512B."""
    sender = FakeSender()
    _use_fake_sender(monkeypatch, sender)

    await _run(_pipeline(hook_env), path, hook_env.meeting_id, hook_env.workspace_id)

    _, payload = sender.calls[0]
    assert json.loads(payload) == {
        "v": 1,
        "kind": "meeting.completed",
        "meetingId": str(hook_env.meeting_id),
        "workspaceId": str(hook_env.workspace_id),
    }
    for secret in (SECRET_TITLE, SECRET_SUMMARY, SECRET_TRANSCRIPT, "업로더", "푸시 팀"):
        assert secret not in payload
    assert len(payload.encode("utf-8")) <= PUSH_PAYLOAD_MAX_BYTES
