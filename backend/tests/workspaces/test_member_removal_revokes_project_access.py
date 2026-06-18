# CAND-B 회귀 — 워크스페이스 멤버 제거 시 private project 접근 잔재(ProjectMember orphan) 차단
"""CAND-B (P0 IDOR): offboard 후 재초대된 plain member 가 private project 접근/RAG 를 되찾으면 안 됨.

시나리오 (PROBE-SENTINEL-03 의 실 codepath 재현, mock 없음):
  1. owner 가 team_ws + private project 생성
  2. member 가 invite 수락 → ws member 가 됨
  3. owner 가 member 를 private project 의 ProjectMember 로 추가
  4. member 가 private project GET 200 + private RAG chunk 노출 (정상)
  5. owner 가 member 를 워크스페이스에서 제거 (InviteService.remove_member)
  6. member 가 다시 invite 수락 (plain member, ProjectMember 재추가 없음)
  7. member 의 private project GET → 404 + private RAG chunk 미노출 이어야 함

본 spec 은 InviteService.remove_member / ProjectService.get_project /
EmbeddingRepository.vector_search 의 실 seam 을 그대로 탄다. 외부 경계(OpenAI/Gemini)는
쿼리 임베딩을 결정적 벡터로 직접 주입해 우회한다 (버그 지점은 mock 하지 않는다).
"""
import uuid

import pytest

from src.auth.models import User
from src.auth.repository import UserRepository
from src.embeddings.models import EmbeddingChunk
from src.embeddings.repository import EmbeddingRepository
from src.projects.exceptions import ProjectNotFoundError
from src.projects.models import Project
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.invite_service import InviteService
from src.workspaces.models import Workspace, WorkspaceInvite, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository

pytestmark = pytest.mark.integration


def _make_vec(seed: int, dim: int = 1536) -> list[float]:
    base = 0.001 * (seed + 1)
    return [base + (i * 0.0001) for i in range(dim)]


async def _create_user(session, tag: str) -> User:
    user = User(
        clerk_id=f"clerk_{tag}_{uuid.uuid4().hex}",
        display_name=tag,
        email=f"{tag}_{uuid.uuid4().hex}@example.com",
    )
    session.add(user)
    await session.flush()
    return user


def _make_invite_service(session) -> InviteService:
    return InviteService(
        repo=WorkspaceRepository(session),
        user_repo=UserRepository(session),
    )


def _make_project_service(session) -> ProjectService:
    return ProjectService(
        repo=ProjectRepository(session),
        ws_repo=WorkspaceRepository(session),
    )


async def test_ws_removal_revokes_private_project_access_on_reinvite(
    integration_session,
):
    """CAND-B: remove → re-invite plain member → private project GET 404 + RAG 미노출."""
    session = integration_session

    owner = await _create_user(session, "owner")
    member = await _create_user(session, "member")

    ws = Workspace(name="팀 워크스페이스", owner_id=owner.id, type="team")
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner"))
    await session.flush()

    private_project = Project(
        title="비공개 프로젝트",
        workspace_id=ws.id,
        visibility="private",
        created_by_id=owner.id,
    )
    session.add(private_project)
    await session.flush()

    # private project 의 RAG chunk (MAGENTA99 시그니처).
    priv_chunk = EmbeddingChunk(
        workspace_id=ws.id,
        project_id=private_project.id,
        source_id=uuid.uuid4(),
        source_type="note",
        chunk_text="MAGENTA99 secret private content",
        chunk_index=0,
        chunk_level=2,
        embedding=_make_vec(seed=7),
    )
    session.add(priv_chunk)
    await session.flush()

    invite = WorkspaceInvite(
        workspace_id=ws.id,
        code="reinvitecode01",
        role="member",
        created_by_id=owner.id,
    )
    session.add(invite)
    await session.commit()

    invite_service = _make_invite_service(session)
    project_service = _make_project_service(session)
    embed_repo = EmbeddingRepository(session)

    # 1) member 가 invite 수락 → ws member.
    accept1 = await invite_service.accept_invite("reinvitecode01", member.id)
    member_id_1 = uuid.UUID(accept1["memberId"])

    # 2) owner 가 member 를 private project 의 ProjectMember 로 추가.
    await project_service.add_member(
        workspace_id=ws.id, project_id=private_project.id, user_id=member.id
    )

    # 3) sanity: member 가 private project 접근 200 + RAG chunk 노출 (잔재 발생 전 정상 경로).
    got = await project_service.get_project(
        workspace_id=ws.id,
        project_id=private_project.id,
        requester_user_id=member.id,
        requester_role="member",
    )
    assert got["id"] == str(private_project.id)
    rag_before = await embed_repo.vector_search(
        query_embedding=_make_vec(seed=7),
        workspace_id=ws.id,
        requester_user_id=member.id,
        requester_role="member",
        limit=10,
    )
    assert any("MAGENTA99" in r["chunk_text"] for r in rag_before)

    # 4) owner 가 member 를 워크스페이스에서 제거.
    await invite_service.remove_member(workspace_id=ws.id, member_id=member_id_1)

    # 5) member 재초대 + 수락 (plain member — ProjectMember 재추가 없음).
    await invite_service.accept_invite("reinvitecode01", member.id)

    # 6) 핵심 검증 — 잔재 차단.
    #    (a) private project GET → ProjectNotFoundError (404)
    with pytest.raises(ProjectNotFoundError):
        await project_service.get_project(
            workspace_id=ws.id,
            project_id=private_project.id,
            requester_user_id=member.id,
            requester_role="member",
        )

    #    (b) private RAG chunk 미노출 (MAGENTA99 leak 차단)
    rag_after = await embed_repo.vector_search(
        query_embedding=_make_vec(seed=7),
        workspace_id=ws.id,
        requester_user_id=member.id,
        requester_role="member",
        limit=10,
    )
    assert not any("MAGENTA99" in r["chunk_text"] for r in rag_after), (
        "재초대된 plain member 가 orphan ProjectMember 로 private RAG 를 되찾음 (CAND-B leak)"
    )
