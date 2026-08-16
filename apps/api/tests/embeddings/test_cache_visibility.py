# BL-041 + BL-042 통합 — semantic cache visibility 누출 차단 regression
"""ISSUE-040 후속 fix 의 통합 검증.

시나리오:
1. admin 이 private project 의 chunks 를 sources 로 cache 저장 → max_visibility='private'
2. 비-ProjectMember member 가 동일 question 으로 find_similar_cache 호출 → cache miss
3. ProjectMember 매핑된 member 가 호출 → cache hit
4. owner 가 호출 → 항상 hit (admin/owner 우회)
5. public cache 는 source chunk 가 살아 있고 public 이면 비-admin 도 hit
"""
import uuid

import pytest

from src.auth.models import User
from src.embeddings.models import EmbeddingChunk, SemanticCache
from src.embeddings.repository import EmbeddingRepository
from src.projects.models import Project, ProjectMember
from src.workspaces.models import WorkspaceMember


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
async def test_all_chunks_exist_returns_false_when_no_source_chunks_exist(
    integration_session, team_ws
):
    """F3: 존재하지 않는 source chunk 만 주면 fence 는 False 다."""
    repo = EmbeddingRepository(integration_session)

    exists = await repo.all_chunks_exist([str(uuid.uuid4())])

    assert exists is False


@pytest.mark.asyncio
async def test_all_chunks_exist_returns_true_when_all_source_chunks_exist(
    integration_session, team_ws
):
    """F4: source chunk 가 전부 있으면 fence 는 True 다."""
    chunks = [
        EmbeddingChunk(
            workspace_id=team_ws.id,
            source_id=uuid.uuid4(),
            source_type="note",
            chunk_text=f"F4 chunk {index}",
            chunk_index=index,
            chunk_level=2,
            embedding=_make_vec(seed=70 + index),
        )
        for index in range(2)
    ]
    integration_session.add_all(chunks)
    await integration_session.flush()

    exists = await EmbeddingRepository(integration_session).all_chunks_exist(
        [str(chunk.id) for chunk in chunks]
    )

    assert exists is True


@pytest.mark.asyncio
async def test_all_chunks_exist_returns_false_when_some_source_chunks_are_missing(
    integration_session, team_ws
):
    """F5: source chunk 일부가 없으면 fence 는 False 다."""
    chunk = EmbeddingChunk(
        workspace_id=team_ws.id,
        source_id=uuid.uuid4(),
        source_type="note",
        chunk_text="F5 existing chunk",
        chunk_index=0,
        chunk_level=2,
        embedding=_make_vec(seed=72),
    )
    integration_session.add(chunk)
    await integration_session.flush()

    exists = await EmbeddingRepository(integration_session).all_chunks_exist(
        [str(chunk.id), str(uuid.uuid4())]
    )

    assert exists is False


@pytest.mark.asyncio
async def test_all_chunks_exist_returns_true_for_empty_source_chunks(
    integration_session,
):
    """F6: 빈 source chunk 목록은 예외 없이 True 로 처리한다."""
    exists = await EmbeddingRepository(integration_session).all_chunks_exist([])

    assert exists is True


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
        auth_user_id="cache_vis_other_member",
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
        auth_user_id="cache_vis_mapped_member",
        display_name="매핑 멤버",
        email="cache_vis_mapped@kairos.test",
    )
    integration_session.add(mapped)
    await integration_session.flush()
    # CAND-B: 정당한 매핑 멤버는 워크스페이스 멤버이기도 하다 (gate 가 둘 다 요구).
    integration_session.add(
        WorkspaceMember(
            workspace_id=team_ws.id,
            user_id=mapped.id,
            role="member",
        )
    )
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
async def test_cache_miss_private_when_all_source_chunks_deleted(
    integration_session, auth_user, team_ws
):
    """N1: 삭제된 source 를 참조하는 private cache 는 비멤버에게 MISS."""
    p_private = Project(
        title="N1 private", workspace_id=team_ws.id, visibility="private",
        created_by_id=auth_user.id,
    )
    integration_session.add(p_private)
    await integration_session.flush()

    chunk = EmbeddingChunk(
        workspace_id=team_ws.id, project_id=p_private.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="deleted private source", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=31),
    )
    requester = User(
        auth_user_id="cache_vis_n1_member",
        display_name="N1 비멤버",
        email="cache_vis_n1@kairos.test",
    )
    integration_session.add_all([chunk, requester])
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(
            workspace_id=team_ws.id,
            user_id=requester.id,
            role="member",
        )
    )
    integration_session.add(
        SemanticCache(
            workspace_id=team_ws.id,
            question="n1 deleted private?",
            question_embedding=_make_vec(seed=31),
            answer="삭제된 비공개 답변",
            sources=[{"id": str(chunk.id), "text": "deleted private source"}],
            max_visibility="private",
        )
    )
    await integration_session.commit()

    await integration_session.delete(chunk)
    await integration_session.commit()

    hit = await EmbeddingRepository(integration_session).find_similar_cache(
        question_embedding=_make_vec(seed=31),
        workspace_id=team_ws.id,
        requester_user_id=requester.id,
        requester_role="member",
        threshold=0.90,
    )
    assert hit is None


@pytest.mark.asyncio
async def test_cache_miss_public_when_all_source_chunks_deleted(
    integration_session, auth_user, team_ws
):
    """N2: 삭제된 source 를 참조하는 public cache 는 비멤버에게 MISS."""
    p_public = Project(
        title="N2 public", workspace_id=team_ws.id, visibility="public",
        created_by_id=auth_user.id,
    )
    integration_session.add(p_public)
    await integration_session.flush()

    chunk = EmbeddingChunk(
        workspace_id=team_ws.id, project_id=p_public.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="deleted public source", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=32),
    )
    requester = User(
        auth_user_id="cache_vis_n2_member",
        display_name="N2 비멤버",
        email="cache_vis_n2@kairos.test",
    )
    integration_session.add_all([chunk, requester])
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(
            workspace_id=team_ws.id,
            user_id=requester.id,
            role="member",
        )
    )
    integration_session.add(
        SemanticCache(
            workspace_id=team_ws.id,
            question="n2 deleted public?",
            question_embedding=_make_vec(seed=32),
            answer="삭제된 공개 답변",
            sources=[{"id": str(chunk.id), "text": "deleted public source"}],
            max_visibility="public",
        )
    )
    await integration_session.commit()

    await integration_session.delete(chunk)
    await integration_session.commit()

    hit = await EmbeddingRepository(integration_session).find_similar_cache(
        question_embedding=_make_vec(seed=32),
        workspace_id=team_ws.id,
        requester_user_id=requester.id,
        requester_role="member",
        threshold=0.90,
    )
    assert hit is None


@pytest.mark.asyncio
async def test_cache_miss_private_when_some_source_chunks_deleted(
    integration_session, auth_user, team_ws
):
    """N3: 둘 중 하나만 삭제돼도 private cache 는 비멤버에게 MISS."""
    p_private = Project(
        title="N3 private", workspace_id=team_ws.id, visibility="private",
        created_by_id=auth_user.id,
    )
    p_public = Project(
        title="N3 public", workspace_id=team_ws.id, visibility="public",
        created_by_id=auth_user.id,
    )
    integration_session.add_all([p_private, p_public])
    await integration_session.flush()

    chunks = [
        EmbeddingChunk(
            workspace_id=team_ws.id, project_id=p_private.id,
            source_id=uuid.uuid4(), source_type="note",
            chunk_text="partially deleted private source", chunk_index=0,
            chunk_level=2, embedding=_make_vec(seed=33),
        ),
        EmbeddingChunk(
            workspace_id=team_ws.id, project_id=p_public.id,
            source_id=uuid.uuid4(), source_type="note",
            chunk_text="remaining public source", chunk_index=0,
            chunk_level=2, embedding=_make_vec(seed=33),
        ),
    ]
    requester = User(
        auth_user_id="cache_vis_n3_member",
        display_name="N3 비멤버",
        email="cache_vis_n3@kairos.test",
    )
    integration_session.add_all([*chunks, requester])
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(
            workspace_id=team_ws.id,
            user_id=requester.id,
            role="member",
        )
    )
    integration_session.add(
        SemanticCache(
            workspace_id=team_ws.id,
            question="n3 partially deleted private?",
            question_embedding=_make_vec(seed=33),
            answer="부분 삭제된 비공개 답변",
            sources=[{"id": str(chunk.id), "text": chunk.chunk_text} for chunk in chunks],
            max_visibility="private",
        )
    )
    await integration_session.commit()

    await integration_session.delete(chunks[0])
    await integration_session.commit()

    hit = await EmbeddingRepository(integration_session).find_similar_cache(
        question_embedding=_make_vec(seed=33),
        workspace_id=team_ws.id,
        requester_user_id=requester.id,
        requester_role="member",
        threshold=0.90,
    )
    assert hit is None


@pytest.mark.asyncio
async def test_cache_hit_deleted_sources_for_admin(
    integration_session, auth_user, team_ws
):
    """N4: admin 은 삭제된 source cache 도 정책상 HIT."""
    p_private = Project(
        title="N4 private", workspace_id=team_ws.id, visibility="private",
        created_by_id=auth_user.id,
    )
    integration_session.add(p_private)
    await integration_session.flush()

    chunk = EmbeddingChunk(
        workspace_id=team_ws.id, project_id=p_private.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="admin deleted source", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=34),
    )
    integration_session.add(chunk)
    await integration_session.flush()
    integration_session.add(
        SemanticCache(
            workspace_id=team_ws.id,
            question="n4 admin deleted?",
            question_embedding=_make_vec(seed=34),
            answer="admin 삭제 답변",
            sources=[{"id": str(chunk.id), "text": "admin deleted source"}],
            max_visibility="private",
        )
    )
    await integration_session.commit()

    await integration_session.delete(chunk)
    await integration_session.commit()

    hit = await EmbeddingRepository(integration_session).find_similar_cache(
        question_embedding=_make_vec(seed=34),
        workspace_id=team_ws.id,
        requester_user_id=auth_user.id,
        requester_role="admin",
        threshold=0.90,
    )
    assert hit is not None
    assert hit["answer"] == "admin 삭제 답변"


@pytest.mark.asyncio
async def test_cache_miss_deleted_sources_for_project_member(
    integration_session, auth_user, team_ws
):
    """N5: ProjectMember 본인도 삭제된 private source cache 는 MISS."""
    p_private = Project(
        title="N5 private", workspace_id=team_ws.id, visibility="private",
        created_by_id=auth_user.id,
    )
    integration_session.add(p_private)
    await integration_session.flush()
    integration_session.add(
        ProjectMember(
            project_id=p_private.id,
            user_id=auth_user.id,
            workspace_id=team_ws.id,
            role="member",
        )
    )

    chunk = EmbeddingChunk(
        workspace_id=team_ws.id, project_id=p_private.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="project member deleted source", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=35),
    )
    integration_session.add(chunk)
    await integration_session.flush()
    integration_session.add(
        SemanticCache(
            workspace_id=team_ws.id,
            question="n5 project member deleted?",
            question_embedding=_make_vec(seed=35),
            answer="프로젝트 멤버 삭제 답변",
            sources=[{"id": str(chunk.id), "text": "project member deleted source"}],
            max_visibility="private",
        )
    )
    await integration_session.commit()

    await integration_session.delete(chunk)
    await integration_session.commit()

    hit = await EmbeddingRepository(integration_session).find_similar_cache(
        question_embedding=_make_vec(seed=35),
        workspace_id=team_ws.id,
        requester_user_id=auth_user.id,
        requester_role="member",
        threshold=0.90,
    )
    assert hit is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sources",
    [[], [{"text": "source id 없음"}]],
    ids=["empty_sources", "source_without_id"],
)
async def test_cache_miss_private_without_source_chunk_ids(
    integration_session, auth_user, team_ws, sources
):
    """N6: 비-admin private cache 의 빈·형식 불량 source 는 MISS."""
    requester = User(
        auth_user_id=f"cache_vis_n6_{len(sources)}",
        display_name="N6 비멤버",
        email=f"cache_vis_n6_{len(sources)}@kairos.test",
    )
    integration_session.add(requester)
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(
            workspace_id=team_ws.id,
            user_id=requester.id,
            role="member",
        )
    )
    integration_session.add(
        SemanticCache(
            workspace_id=team_ws.id,
            question=f"n6 missing chunk ids {len(sources)}?",
            question_embedding=_make_vec(seed=36 + len(sources)),
            answer="source id 없는 답변",
            sources=sources,
            max_visibility="private",
        )
    )
    await integration_session.commit()

    hit = await EmbeddingRepository(integration_session).find_similar_cache(
        question_embedding=_make_vec(seed=36 + len(sources)),
        workspace_id=team_ws.id,
        requester_user_id=requester.id,
        requester_role="member",
        threshold=0.90,
    )
    assert hit is None


@pytest.mark.asyncio
async def test_cache_miss_stale_public_visibility_after_project_becomes_private(
    integration_session, auth_user, team_ws
):
    """N7: 살아 있는 chunk 의 public→private stale label 은 비멤버에게 MISS."""
    project = Project(
        title="N7 public then private", workspace_id=team_ws.id,
        visibility="public", created_by_id=auth_user.id,
    )
    integration_session.add(project)
    await integration_session.flush()

    chunk = EmbeddingChunk(
        workspace_id=team_ws.id, project_id=project.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="stale public source", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=38),
    )
    requester = User(
        auth_user_id="cache_vis_n7_member",
        display_name="N7 비멤버",
        email="cache_vis_n7@kairos.test",
    )
    integration_session.add_all([chunk, requester])
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(
            workspace_id=team_ws.id,
            user_id=requester.id,
            role="member",
        )
    )
    integration_session.add(
        SemanticCache(
            workspace_id=team_ws.id,
            question="n7 stale public?",
            question_embedding=_make_vec(seed=38),
            answer="stale 공개 라벨 답변",
            sources=[{"id": str(chunk.id), "text": "stale public source"}],
            max_visibility="public",
        )
    )
    await integration_session.commit()

    project.visibility = "private"
    integration_session.add(project)
    await integration_session.commit()

    hit = await EmbeddingRepository(integration_session).find_similar_cache(
        question_embedding=_make_vec(seed=38),
        workspace_id=team_ws.id,
        requester_user_id=requester.id,
        requester_role="member",
        threshold=0.90,
    )
    assert hit is None


@pytest.mark.asyncio
async def test_cache_hit_public_when_source_chunks_are_visible(
    integration_session, auth_user, team_ws
):
    """살아 있는 public source cache 는 비-admin 사용자도 HIT."""
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
        auth_user_id="cache_vis_random_viewer",
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
