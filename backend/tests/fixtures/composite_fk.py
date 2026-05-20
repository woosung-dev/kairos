# Sprint 24 Wave 2 T-N+2 — composite FK 회귀 안전망 fixture (SCN-FK-01~12 자동화).
"""Sprint 21 BL-050 Simple 4 composite FK hardening 의 회귀 가드.

검증 대상 (4 entity × 3 op = 12 SCN):

| SCN ID  | Entity              | Op      | 검증 내용                                         |
|---------|---------------------|---------|--------------------------------------------------|
| SCN-FK-01 | MeetingProjectLink | insert  | cross-workspace project_id insert 차단           |
| SCN-FK-02 | MeetingProjectLink | update  | workspace_id 변경으로 mismatch 만드는 update 차단 |
| SCN-FK-03 | MeetingProjectLink | query   | 정상 row (same workspace) commit + 조회 가능     |
| SCN-FK-04 | InboxItem          | insert  | cross-workspace ai_suggested_project_id 차단     |
| SCN-FK-05 | InboxItem          | update  | suggested project workspace mismatch update 차단 |
| SCN-FK-06 | InboxItem          | query   | nullable ai_suggested_project_id NULL 허용       |
| SCN-FK-07 | ActionItem         | insert  | cross-workspace project_id insert 차단           |
| SCN-FK-08 | ActionItem         | update  | workspace_id 변경으로 mismatch 만드는 update 차단 |
| SCN-FK-09 | ActionItem         | query   | nullable project_id NULL row 허용                |
| SCN-FK-10 | EmbeddingChunk     | insert  | cross-workspace project_id insert 차단           |
| SCN-FK-11 | EmbeddingChunk     | update  | workspace_id 변경으로 mismatch 만드는 update 차단 |
| SCN-FK-12 | EmbeddingChunk     | query   | nullable project_id NULL row 허용                |

fixture 가 자동으로 12 SCN 을 검증하여 Sprint 21 composite FK 의 회귀를 차단한다.
기존 `test_workspace_fk_cross_tenant_block.py` 는 service-level 가드 우회 시나리오 (7 case);
본 fixture 는 12 SCN 매트릭스를 빠짐없이 커버하는 회귀 안전망.

설계: 각 fixture 는 (seed, assert) tuple 을 제공 — fixture 자체가 assertion 까지 수행하며
세션 rollback 으로 격리. integration_session fixture 위에서 동작.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.actions.models import ActionItem
from src.auth.models import User
from src.embeddings.models import EmbeddingChunk
from src.inbox.models import InboxItem
from src.meetings.models import Meeting
from src.projects.models import MeetingProjectLink, Project
from src.workspaces.models import Workspace


@dataclass
class TwoWorkspaceSeed:
    """공통 seed: 2 workspace + 2 project + meeting (ws_a only)."""

    user: User
    ws_a: Workspace
    ws_b: Workspace
    project_a: Project
    project_b: Project
    meeting_a: Meeting
    meeting_b: Meeting


@pytest_asyncio.fixture
async def two_workspaces_seed(integration_session: AsyncSession) -> TwoWorkspaceSeed:
    """2-workspace seed — composite FK 시나리오 공통 fixture."""
    suffix = uuid.uuid4().hex[:8]
    user = User(
        clerk_id=f"clerk_compfk_{suffix}",
        display_name="CompFK Tester",
        email=f"compfk_{suffix}@k.test",
    )
    integration_session.add(user)
    await integration_session.flush()

    ws_a = Workspace(name=f"WS A {suffix}", owner_id=user.id)
    ws_b = Workspace(name=f"WS B {suffix}", owner_id=user.id)
    integration_session.add_all([ws_a, ws_b])
    await integration_session.flush()

    project_a = Project(workspace_id=ws_a.id, title="P A", created_by_id=user.id)
    project_b = Project(workspace_id=ws_b.id, title="P B", created_by_id=user.id)
    meeting_a = Meeting(
        workspace_id=ws_a.id,
        title="M A",
        file_key=f"k_a_{suffix}",
        created_by_id=user.id,
    )
    meeting_b = Meeting(
        workspace_id=ws_b.id,
        title="M B",
        file_key=f"k_b_{suffix}",
        created_by_id=user.id,
    )
    integration_session.add_all([project_a, project_b, meeting_a, meeting_b])
    await integration_session.flush()
    await integration_session.commit()

    return TwoWorkspaceSeed(
        user=user,
        ws_a=ws_a,
        ws_b=ws_b,
        project_a=project_a,
        project_b=project_b,
        meeting_a=meeting_a,
        meeting_b=meeting_b,
    )


async def _expect_integrity_error(session: AsyncSession) -> None:
    """commit 이 IntegrityError 를 던지는지 검증 + rollback."""
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


# ---------------------------------------------------------------------------
# SCN-FK-01~03: MeetingProjectLink
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def scn_fk_01_mpl_insert_blocked(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-01: MeetingProjectLink (insert) cross-workspace project_id 거부."""
    s = two_workspaces_seed
    bad = MeetingProjectLink(
        workspace_id=s.ws_a.id,
        meeting_id=s.meeting_a.id,
        project_id=s.project_b.id,  # cross-workspace
    )
    integration_session.add(bad)
    await _expect_integrity_error(integration_session)


@pytest_asyncio.fixture
async def scn_fk_02_mpl_update_blocked(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-02: MeetingProjectLink (update) workspace_id 변경으로 mismatch 만드는 update 차단."""
    s = two_workspaces_seed
    # 정상 row 먼저 commit
    link = MeetingProjectLink(
        workspace_id=s.ws_a.id,
        meeting_id=s.meeting_a.id,
        project_id=s.project_a.id,
    )
    integration_session.add(link)
    await integration_session.commit()

    # workspace_id 만 ws_b 로 변경 → meeting_id/project_id 가 ws_a 의 row 이므로 composite FK 위반
    link.workspace_id = s.ws_b.id
    integration_session.add(link)
    await _expect_integrity_error(integration_session)


@pytest_asyncio.fixture
async def scn_fk_03_mpl_query_valid(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-03: MeetingProjectLink (query) 정상 row commit + 조회 가능."""
    s = two_workspaces_seed
    link = MeetingProjectLink(
        workspace_id=s.ws_a.id,
        meeting_id=s.meeting_a.id,
        project_id=s.project_a.id,
    )
    integration_session.add(link)
    await integration_session.commit()

    result = await integration_session.exec(
        select(MeetingProjectLink).where(MeetingProjectLink.id == link.id)
    )
    fetched = result.one()
    assert fetched.workspace_id == s.ws_a.id
    assert fetched.project_id == s.project_a.id
    assert fetched.meeting_id == s.meeting_a.id


# ---------------------------------------------------------------------------
# SCN-FK-04~06: InboxItem
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def scn_fk_04_inbox_insert_blocked(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-04: InboxItem (insert) cross-workspace ai_suggested_project_id 거부."""
    s = two_workspaces_seed
    bad = InboxItem(
        workspace_id=s.ws_a.id,
        title="X",
        source_type="meeting",
        source_id=s.meeting_a.id,
        ai_suggested_project_id=s.project_b.id,  # cross-workspace
    )
    integration_session.add(bad)
    await _expect_integrity_error(integration_session)


@pytest_asyncio.fixture
async def scn_fk_05_inbox_update_blocked(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-05: InboxItem (update) suggested project workspace mismatch update 차단."""
    s = two_workspaces_seed
    item = InboxItem(
        workspace_id=s.ws_a.id,
        title="Y",
        source_type="meeting",
        source_id=s.meeting_a.id,
        ai_suggested_project_id=s.project_a.id,  # same workspace OK
    )
    integration_session.add(item)
    await integration_session.commit()

    # 동일 workspace 유지하면서 cross-workspace project_b 로 update → composite FK 위반
    item.ai_suggested_project_id = s.project_b.id
    integration_session.add(item)
    await _expect_integrity_error(integration_session)


@pytest_asyncio.fixture
async def scn_fk_06_inbox_nullable_allowed(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-06: InboxItem (query) nullable ai_suggested_project_id NULL 허용 (MATCH SIMPLE)."""
    s = two_workspaces_seed
    item = InboxItem(
        workspace_id=s.ws_a.id,
        title="Free Inbox",
        source_type="meeting",
        source_id=s.meeting_a.id,
        ai_suggested_project_id=None,
    )
    integration_session.add(item)
    await integration_session.commit()
    assert item.id is not None

    result = await integration_session.exec(
        select(InboxItem).where(InboxItem.id == item.id)
    )
    fetched = result.one()
    assert fetched.ai_suggested_project_id is None


# ---------------------------------------------------------------------------
# SCN-FK-07~09: ActionItem
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def scn_fk_07_action_insert_blocked(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-07: ActionItem (insert) cross-workspace project_id 거부."""
    s = two_workspaces_seed
    bad = ActionItem(
        workspace_id=s.ws_a.id,
        project_id=s.project_b.id,  # cross-workspace
        title="X action",
    )
    integration_session.add(bad)
    await _expect_integrity_error(integration_session)


@pytest_asyncio.fixture
async def scn_fk_08_action_update_blocked(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-08: ActionItem (update) workspace_id 변경으로 mismatch 만드는 update 차단."""
    s = two_workspaces_seed
    item = ActionItem(
        workspace_id=s.ws_a.id,
        project_id=s.project_a.id,
        title="Y action",
    )
    integration_session.add(item)
    await integration_session.commit()

    # workspace_id 만 ws_b 로 변경 → project_id 가 ws_a 의 project 이므로 composite FK 위반
    item.workspace_id = s.ws_b.id
    integration_session.add(item)
    await _expect_integrity_error(integration_session)


@pytest_asyncio.fixture
async def scn_fk_09_action_nullable_allowed(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-09: ActionItem (query) nullable project_id NULL 허용 (MATCH SIMPLE)."""
    s = two_workspaces_seed
    item = ActionItem(
        workspace_id=s.ws_a.id,
        project_id=None,
        title="Standalone",
    )
    integration_session.add(item)
    await integration_session.commit()
    assert item.id is not None

    result = await integration_session.exec(
        select(ActionItem).where(ActionItem.id == item.id)
    )
    fetched = result.one()
    assert fetched.project_id is None


# ---------------------------------------------------------------------------
# SCN-FK-10~12: EmbeddingChunk
# ---------------------------------------------------------------------------


def _make_chunk(workspace_id: uuid.UUID, project_id: uuid.UUID | None) -> EmbeddingChunk:
    return EmbeddingChunk(
        workspace_id=workspace_id,
        project_id=project_id,
        source_id=uuid.uuid4(),
        source_type="meeting",
        chunk_text="t",
        chunk_index=0,
        chunk_level=2,
    )


@pytest_asyncio.fixture
async def scn_fk_10_embedding_insert_blocked(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-10: EmbeddingChunk (insert) cross-workspace project_id 거부."""
    s = two_workspaces_seed
    bad = _make_chunk(s.ws_a.id, s.project_b.id)  # cross-workspace
    integration_session.add(bad)
    await _expect_integrity_error(integration_session)


@pytest_asyncio.fixture
async def scn_fk_11_embedding_update_blocked(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-11: EmbeddingChunk (update) workspace_id 변경으로 mismatch 만드는 update 차단."""
    s = two_workspaces_seed
    chunk = _make_chunk(s.ws_a.id, s.project_a.id)
    integration_session.add(chunk)
    await integration_session.commit()

    # workspace_id 만 ws_b 로 변경 → project_id 가 ws_a 의 project 이므로 composite FK 위반
    chunk.workspace_id = s.ws_b.id
    integration_session.add(chunk)
    await _expect_integrity_error(integration_session)


@pytest_asyncio.fixture
async def scn_fk_12_embedding_nullable_allowed(
    integration_session: AsyncSession, two_workspaces_seed: TwoWorkspaceSeed
) -> None:
    """SCN-FK-12: EmbeddingChunk (query) nullable project_id NULL 허용 (MATCH SIMPLE)."""
    s = two_workspaces_seed
    chunk = _make_chunk(s.ws_a.id, None)
    integration_session.add(chunk)
    await integration_session.commit()
    assert chunk.id is not None

    result = await integration_session.exec(
        select(EmbeddingChunk).where(EmbeddingChunk.id == chunk.id)
    )
    fetched = result.one()
    assert fetched.project_id is None
