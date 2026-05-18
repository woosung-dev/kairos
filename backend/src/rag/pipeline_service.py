# backend/src/rag/pipeline_service.py
"""RAG 오케스트레이터 — visibility/member 검증 + RagService.ask AsyncGenerator 위임.

ADR-014 옵션 A: D-3 부채(rag → embeddings.{models, repository, service}) 해소 1차.
검증 기준 6 (C-6): SSE 스트리밍 시작 *전*에 visibility + member 검증 완료.
"""
import json
import logging
import uuid
from collections.abc import AsyncGenerator

from src.projects.repository import ProjectRepository
from src.rag.service import RagService

logger = logging.getLogger(__name__)


def _sse_error_done(message: str) -> tuple[dict, dict]:
    """SSE error + done 이벤트 쌍 — 권한 위반 시 보일러플레이트 통합 (BL-029)."""
    return (
        {"event": "error", "data": json.dumps({"message": message}, ensure_ascii=False)},
        {"event": "done", "data": json.dumps({"cached": False, "sourceCount": 0})},
    )


class RagPipelineService:
    def __init__(
        self,
        rag_service: RagService,
        project_repo: ProjectRepository,
    ) -> None:
        self.rag_service = rag_service
        self.project_repo = project_repo

    async def _check_project_access(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID,
    ) -> str | None:
        """프로젝트 접근 검증. 위반 시 사용자용 에러 메시지 반환, 통과 시 None.

        admin/owner 우회는 caller 책임 (ADR-014 옵션 A).
        """
        # Sprint 19 PR #1 C9 (Codex F-1 cascade): find_by_id / is_member workspace_id 강제
        project = await self.project_repo.find_by_id(project_id, workspace_id)
        if project is None:
            return "프로젝트를 찾을 수 없거나 접근 권한이 없습니다."
        if project.visibility == "draft" and project.created_by_id != requester_user_id:
            return "Draft 프로젝트는 작성자만 접근 가능합니다."
        if project.visibility == "private":
            is_member = await self.project_repo.is_member(project_id, requester_user_id, workspace_id)
            if not is_member:
                return "Private 프로젝트는 명시적 멤버만 접근 가능합니다."
        return None

    async def ask(
        self,
        question: str,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID,
        requester_role: str,
        project_id: uuid.UUID | None = None,
        time_range: str | None = None,
        source_type: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        """RAG 질의 — visibility 검증 후 RagService.ask 위임.

        SSE 시작 *전* 권한 검증 완료 (ADR-010 M1 RAG 품질 시그널 오염 방지).
        권한 위반 시 error 이벤트 + done 이벤트로 종료.
        """
        # 권한 검증 (project_id 있을 때만, admin 이상은 우회)
        if project_id is not None and requester_role not in ("admin", "owner"):
            error_msg = await self._check_project_access(
                project_id, workspace_id, requester_user_id
            )
            if error_msg is not None:
                for event in _sse_error_done(error_msg):
                    yield event
                return

        # 검증 통과 — RagService.ask로 위임 (AsyncGenerator 위임 표준 패턴)
        # ISSUE-040: requester 정보 forward — 글로벌 쿼리 visibility filter 위해.
        async for event in self.rag_service.ask(
            question=question,
            workspace_id=workspace_id,
            requester_user_id=requester_user_id,
            requester_role=requester_role,
            project_id=project_id,
            time_range=time_range,
            source_type=source_type,
        ):
            yield event
