# Sprint 24 Wave 2 T-N+2 — composite FK SCN-FK-01~12 매트릭스 회귀 가드.
"""Sprint 21 BL-050 Simple 4 composite FK hardening 회귀 안전망 (12 SCN).

본 파일은 `tests/fixtures/composite_fk.py` 의 12 fixture 를 자동 트리거하는 smoke test.
각 fixture 자체가 setup + assertion 까지 수행하므로 test body 는 단순 pass.

기존 `test_workspace_fk_cross_tenant_block.py` (7 case, service-level 가드 우회) 와
상호 보완 — 본 매트릭스는 4 entity × 3 op (insert/update/query) = 12 SCN 매트릭스를
빠짐없이 커버.

회귀 시 어느 entity / 어느 op 에서 FK 가 무너졌는지 SCN ID 로 즉시 식별 가능.
"""
import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# MeetingProjectLink — SCN-FK-01~03
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scn_fk_01_mpl_insert_blocked(scn_fk_01_mpl_insert_blocked) -> None:
    """SCN-FK-01: MeetingProjectLink (insert) cross-workspace project_id 거부."""


@pytest.mark.asyncio
async def test_scn_fk_02_mpl_update_blocked(scn_fk_02_mpl_update_blocked) -> None:
    """SCN-FK-02: MeetingProjectLink (update) workspace_id mismatch update 차단."""


@pytest.mark.asyncio
async def test_scn_fk_03_mpl_query_valid(scn_fk_03_mpl_query_valid) -> None:
    """SCN-FK-03: MeetingProjectLink (query) 정상 row commit + 조회."""


# ---------------------------------------------------------------------------
# InboxItem — SCN-FK-04~06
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scn_fk_04_inbox_insert_blocked(scn_fk_04_inbox_insert_blocked) -> None:
    """SCN-FK-04: InboxItem (insert) cross-workspace ai_suggested_project_id 거부."""


@pytest.mark.asyncio
async def test_scn_fk_05_inbox_update_blocked(scn_fk_05_inbox_update_blocked) -> None:
    """SCN-FK-05: InboxItem (update) suggested project workspace mismatch update 차단."""


@pytest.mark.asyncio
async def test_scn_fk_06_inbox_nullable_allowed(scn_fk_06_inbox_nullable_allowed) -> None:
    """SCN-FK-06: InboxItem (query) nullable ai_suggested_project_id NULL 허용."""


# ---------------------------------------------------------------------------
# ActionItem — SCN-FK-07~09
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scn_fk_07_action_insert_blocked(scn_fk_07_action_insert_blocked) -> None:
    """SCN-FK-07: ActionItem (insert) cross-workspace project_id 거부."""


@pytest.mark.asyncio
async def test_scn_fk_08_action_update_blocked(scn_fk_08_action_update_blocked) -> None:
    """SCN-FK-08: ActionItem (update) workspace_id mismatch update 차단."""


@pytest.mark.asyncio
async def test_scn_fk_09_action_nullable_allowed(scn_fk_09_action_nullable_allowed) -> None:
    """SCN-FK-09: ActionItem (query) nullable project_id NULL 허용."""


# ---------------------------------------------------------------------------
# EmbeddingChunk — SCN-FK-10~12
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scn_fk_10_embedding_insert_blocked(
    scn_fk_10_embedding_insert_blocked,
) -> None:
    """SCN-FK-10: EmbeddingChunk (insert) cross-workspace project_id 거부."""


@pytest.mark.asyncio
async def test_scn_fk_11_embedding_update_blocked(
    scn_fk_11_embedding_update_blocked,
) -> None:
    """SCN-FK-11: EmbeddingChunk (update) workspace_id mismatch update 차단."""


@pytest.mark.asyncio
async def test_scn_fk_12_embedding_nullable_allowed(
    scn_fk_12_embedding_nullable_allowed,
) -> None:
    """SCN-FK-12: EmbeddingChunk (query) nullable project_id NULL 허용."""
