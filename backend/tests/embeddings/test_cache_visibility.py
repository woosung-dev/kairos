# BL-041 + BL-042 통합 — semantic cache visibility 누출 차단 regression
"""ISSUE-040 후속 fix 의 통합 검증.

시나리오:
1. admin 이 private project 의 chunks 를 sources 로 cache 저장 → max_visibility='private'
2. 비-ProjectMember member 가 동일 question 으로 find_similar_cache 호출 → cache miss
3. ProjectMember 매핑된 member 가 호출 → cache hit
4. owner 가 호출 → 항상 hit (admin/owner 우회)
5. max_visibility='public' cache 는 fast path — 모든 사용자 hit
"""
import uuid

import pytest

from src.auth.models import User
from src.embeddings.models import EmbeddingChunk, SemanticCache
from src.embeddings.repository import EmbeddingRepository
from src.projects.models import Project, ProjectMember


def _make_vec(seed: int, dim: int = 1536) -> list[float]:
    base = 0.001 * (seed + 1)
    return [base + (i * 0.0001) for i in range(dim)]


@pytest.mark.asyncio
async def test_compute_max_visibility_picks_most_restrictive(
    integration_session, auth_user, team_ws
):
    """sources 중 가장 제한적인 visibility 가 max_visibility 로 계산됨."""
    p_public = Project(
        title="P", workspace_id=team_ws.id, visibility="public",
        created_by_id=auth_user.id,
    )
    p_private = Project(
        title="PR", workspace_id=team_ws.id, visibility="private",
        created_by_id=auth_user.id,
    )
    integration_session.add_all([p_public, p_private])
    await integration_session.flush()

    ws = team_ws.id
    c_public = EmbeddingChunk(
        workspace_id=ws, project_id=p_public.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="public chunk", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=1),
    )
    c_private = EmbeddingChunk(
        workspace_id=ws, project_id=p_private.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="private chunk", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=2),
    )
    integration_session.add_all([c_public, c_private])
    await integration_session.flush()

    repo = EmbeddingRepository(integration_session)
    # public + private 섞으면 max = private
    mixed = await repo.compute_max_visibility([str(c_public.id), str(c_private.id)])
    assert mixed == "private"
    # public only
    only_pub = await repo.compute_max_visibility([str(c_public.id)])
    assert only_pub == "public"
    # 빈 list
    empty = await repo.compute_max_visibility([])
    assert empty == "public"


@pytest.mark.asyncio
async def test_cache_hit_visibility_member_without_mapping(
    integration_session, auth_user, team_ws
):
    """member (ProjectMember 미매핑) 가 private 포함 cache 조회 → miss."""
    p_private = Project(
        title="PR", workspace_id=team_ws.id, visibility="private",
        created_by_id=auth_user.id,
    )
    integration_session.add(p_private)
    await integration_session.flush()

    c_priv = EmbeddingChunk(
        workspace_id=team_ws.id, project_id=p_private.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="secret", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=10),
    )
    integration_session.add(c_priv)
    await integration_session.flush()

    other = User(
        clerk_id="cache_vis_other_member",
        display_name="비매핑 멤버",
        email="cache_vis_other@kairos.test",
    )
    integration_session.add(other)
    await integration_session.flush()

    cache = SemanticCache(
        workspace_id=team_ws.id,
        question="private question?",
        question_embedding=_make_vec(seed=10),
        answer="비공개 답변",
        sources=[{"id": str(c_priv.id), "text": "secret"}],
        max_visibility="private",
    )
    integration_session.add(cache)
    await integration_session.commit()

    repo = EmbeddingRepository(integration_session)
    # member, 매핑 없음 → miss
    hit = await repo.find_similar_cache(
        question_embedding=_make_vec(seed=10),
        workspace_id=team_ws.id,
        requester_user_id=other.id,
        requester_role="member",
        threshold=0.90,
    )
    assert hit is None


@pytest.mark.asyncio
async def test_cache_hit_visibility_member_with_mapping(
    integration_session, auth_user, team_ws
):
    """member 가 ProjectMember 매핑되어 있으면 private cache hit."""
    p_private = Project(
        title="PR2", workspace_id=team_ws.id, visibility="private",
        created_by_id=auth_user.id,
    )
    integration_session.add(p_private)
    await integration_session.flush()

    c_priv = EmbeddingChunk(
        workspace_id=team_ws.id, project_id=p_private.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="mapped secret", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=20),
    )
    integration_session.add(c_priv)
    await integration_session.flush()

    mapped = User(
        clerk_id="cache_vis_mapped_member",
        display_name="매핑 멤버",
        email="cache_vis_mapped@kairos.test",
    )
    integration_session.add(mapped)
    await integration_session.flush()
    integration_session.add(
        ProjectMember(
            project_id=p_private.id,
            user_id=mapped.id,
            workspace_id=team_ws.id,
            role="member",
        )
    )
    await integration_session.flush()

    cache = SemanticCache(
        workspace_id=team_ws.id,
        question="mapped private?",
        question_embedding=_make_vec(seed=20),
        answer="매핑 멤버용 답변",
        sources=[{"id": str(c_priv.id), "text": "mapped secret"}],
        max_visibility="private",
    )
    integration_session.add(cache)
    await integration_session.commit()

    repo = EmbeddingRepository(integration_session)
    hit = await repo.find_similar_cache(
        question_embedding=_make_vec(seed=20),
        workspace_id=team_ws.id,
        requester_user_id=mapped.id,
        requester_role="member",
        threshold=0.90,
    )
    assert hit is not None
    assert hit["answer"] == "매핑 멤버용 답변"


@pytest.mark.asyncio
async def test_cache_hit_public_fast_path_skips_check(
    integration_session, auth_user, team_ws
):
    """max_visibility='public' cache 는 fast path — 모든 사용자 hit."""
    p_public = Project(
        title="PP", workspace_id=team_ws.id, visibility="public",
        created_by_id=auth_user.id,
    )
    integration_session.add(p_public)
    await integration_session.flush()

    c_pub = EmbeddingChunk(
        workspace_id=team_ws.id, project_id=p_public.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="open", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=30),
    )
    integration_session.add(c_pub)
    await integration_session.flush()

    cache = SemanticCache(
        workspace_id=team_ws.id,
        question="public question?",
        question_embedding=_make_vec(seed=30),
        answer="공개 답변",
        sources=[{"id": str(c_pub.id), "text": "open"}],
        max_visibility="public",
    )
    integration_session.add(cache)
    await integration_session.commit()

    other = User(
        clerk_id="cache_vis_random_viewer",
        display_name="랜덤 viewer",
        email="cache_vis_random@kairos.test",
    )
    integration_session.add(other)
    await integration_session.commit()

    repo = EmbeddingRepository(integration_session)
    hit = await repo.find_similar_cache(
        question_embedding=_make_vec(seed=30),
        workspace_id=team_ws.id,
        requester_user_id=other.id,
        requester_role="viewer",
        threshold=0.90,
    )
    assert hit is not None
    assert hit["answer"] == "공개 답변"
