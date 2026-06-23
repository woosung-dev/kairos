# ISSUE-040 — vector_search / text_search visibility filter regression
"""글로벌 RAG 쿼리 (project_id=None) 에서 private project chunks 가 비-멤버에게
노출되지 않는지 통합 검증. ADR-014 옵션 A 정합.

본 spec 은 integration_session (Docker testcontainers postgres) 의존 — CI 실행.
HNSW 인덱스 없이 chunk_level=2 + cosine 비교만 — small dataset 에서 정확도 OK.
"""
import uuid

import pytest

from src.auth.models import User
from src.embeddings.models import EmbeddingChunk
from src.embeddings.repository import EmbeddingRepository
from src.projects.models import Project, ProjectMember
from src.workspaces.models import WorkspaceMember


def _make_vec(seed: int, dim: int = 1536) -> list[float]:
    base = 0.001 * (seed + 1)
    return [base + (i * 0.0001) for i in range(dim)]


@pytest.mark.asyncio
async def test_vector_search_excludes_private_for_unmapped_member(
    integration_session, auth_user, team_ws
):
    """member 가 ProjectMember 매핑 없으면 private project chunks 가 결과에서 배제."""
    p_public = Project(
        title="공개", workspace_id=team_ws.id, visibility="public",
        created_by_id=auth_user.id,
    )
    p_private = Project(
        title="비공개", workspace_id=team_ws.id, visibility="private",
        created_by_id=auth_user.id,
    )
    integration_session.add_all([p_public, p_private])
    await integration_session.flush()

    pub_chunk = EmbeddingChunk(
        workspace_id=team_ws.id, project_id=p_public.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="public note", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=1),
    )
    priv_chunk = EmbeddingChunk(
        workspace_id=team_ws.id, project_id=p_private.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="private note", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=1),  # 같은 유사도 — visibility filter 만 판가름
    )
    integration_session.add_all([pub_chunk, priv_chunk])
    await integration_session.commit()

    other = User(
        clerk_id="vector_vis_unmapped_member",
        display_name="비매핑 멤버",
        email="vector_vis_unmapped@kairos.test",
    )
    integration_session.add(other)
    await integration_session.commit()

    repo = EmbeddingRepository(integration_session)
    results = await repo.vector_search(
        query_embedding=_make_vec(seed=1),
        workspace_id=team_ws.id,
        requester_user_id=other.id,
        requester_role="member",
        limit=10,
    )
    result_chunks = {r["chunk_text"] for r in results}
    assert "public note" in result_chunks
    assert "private note" not in result_chunks  # 핵심 — leak 차단


@pytest.mark.asyncio
async def test_vector_search_includes_private_for_mapped_member(
    integration_session, auth_user, team_ws
):
    """member 가 ProjectMember 매핑되면 private project chunks 포함."""
    p_private = Project(
        title="비공개2", workspace_id=team_ws.id, visibility="private",
        created_by_id=auth_user.id,
    )
    integration_session.add(p_private)
    await integration_session.flush()

    priv_chunk = EmbeddingChunk(
        workspace_id=team_ws.id, project_id=p_private.id,
        source_id=uuid.uuid4(), source_type="note",
        chunk_text="mapped private note", chunk_index=0, chunk_level=2,
        embedding=_make_vec(seed=5),
    )
    integration_session.add(priv_chunk)
    await integration_session.flush()

    mapped = User(
        clerk_id="vector_vis_mapped_member",
        display_name="매핑 멤버",
        email="vector_vis_mapped@kairos.test",
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
    await integration_session.commit()

    repo = EmbeddingRepository(integration_session)
    results = await repo.vector_search(
        query_embedding=_make_vec(seed=5),
        workspace_id=team_ws.id,
        requester_user_id=mapped.id,
        requester_role="member",
        limit=10,
    )
    result_chunks = {r["chunk_text"] for r in results}
    assert "mapped private note" in result_chunks


@pytest.mark.asyncio
async def test_vector_search_owner_sees_all_visibilities(
    integration_session, auth_user, team_ws
):
    """owner 는 매핑 없이도 private/draft 모두 결과 포함."""
    p_public = Project(
        title="공개3", workspace_id=team_ws.id, visibility="public",
        created_by_id=auth_user.id,
    )
    p_private = Project(
        title="비공개3", workspace_id=team_ws.id, visibility="private",
        created_by_id=auth_user.id,
    )
    p_draft = Project(
        title="작업중3", workspace_id=team_ws.id, visibility="draft",
        created_by_id=auth_user.id,
    )
    integration_session.add_all([p_public, p_private, p_draft])
    await integration_session.flush()

    for proj, text in [
        (p_public, "owner public"),
        (p_private, "owner private"),
        (p_draft, "owner draft"),
    ]:
        chunk = EmbeddingChunk(
            workspace_id=team_ws.id, project_id=proj.id,
            source_id=uuid.uuid4(), source_type="note",
            chunk_text=text, chunk_index=0, chunk_level=2,
            embedding=_make_vec(seed=8),
        )
        integration_session.add(chunk)
    await integration_session.commit()

    repo = EmbeddingRepository(integration_session)
    results = await repo.vector_search(
        query_embedding=_make_vec(seed=8),
        workspace_id=team_ws.id,
        requester_user_id=auth_user.id,
        requester_role="owner",
        limit=10,
    )
    result_chunks = {r["chunk_text"] for r in results}
    assert "owner public" in result_chunks
    assert "owner private" in result_chunks
    assert "owner draft" in result_chunks


@pytest.mark.asyncio
async def test_vector_search_draft_only_creator_visible(
    integration_session, auth_user, team_ws
):
    """draft project chunks 는 본인 작성자만 노출 (member 다른 사람 draft 미노출)."""
    other_creator = User(
        clerk_id="vector_vis_draft_creator",
        display_name="draft 작성자",
        email="vector_vis_draft_creator@kairos.test",
    )
    integration_session.add(other_creator)
    await integration_session.flush()

    p_my_draft = Project(
        title="내 draft", workspace_id=team_ws.id, visibility="draft",
        created_by_id=auth_user.id,
    )
    p_others_draft = Project(
        title="다른사람 draft", workspace_id=team_ws.id, visibility="draft",
        created_by_id=other_creator.id,
    )
    integration_session.add_all([p_my_draft, p_others_draft])
    await integration_session.flush()

    for proj, text in [
        (p_my_draft, "my draft note"),
        (p_others_draft, "others draft note"),
    ]:
        chunk = EmbeddingChunk(
            workspace_id=team_ws.id, project_id=proj.id,
            source_id=uuid.uuid4(), source_type="note",
            chunk_text=text, chunk_index=0, chunk_level=2,
            embedding=_make_vec(seed=12),
        )
        integration_session.add(chunk)
    await integration_session.commit()

    repo = EmbeddingRepository(integration_session)
    results = await repo.vector_search(
        query_embedding=_make_vec(seed=12),
        workspace_id=team_ws.id,
        requester_user_id=auth_user.id,
        requester_role="member",
        limit=10,
    )
    result_chunks = {r["chunk_text"] for r in results}
    assert "my draft note" in result_chunks  # 본인 draft 노출
    assert "others draft note" not in result_chunks  # 다른 사람 draft 미노출
