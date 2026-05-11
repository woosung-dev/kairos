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


class RagPipelineService:
    def __init__(
        self,
        rag_service: RagService,
        project_repo: ProjectRepository,
    ) -> None:
        self.rag_service = rag_service
        self.project_repo = project_repo

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
            project = await self.project_repo.find_by_id(project_id)
            if project is None or project.workspace_id != workspace_id:
                yield {
                    "event": "error",
                    "data": json.dumps(
                        {"message": "프로젝트를 찾을 수 없거나 접근 권한이 없습니다."},
                        ensure_ascii=False,
                    ),
                }
                yield {"event": "done", "data": json.dumps({"cached": False, "sourceCount": 0})}
                return
            if project.visibility == "draft":
                if project.created_by_id != requester_user_id:
                    yield {
                        "event": "error",
                        "data": json.dumps(
                            {"message": "Draft 프로젝트는 작성자만 접근 가능합니다."},
                            ensure_ascii=False,
                        ),
                    }
                    yield {"event": "done", "data": json.dumps({"cached": False, "sourceCount": 0})}
                    return
            elif project.visibility == "private":
                is_member = await self.project_repo.is_member(project_id, requester_user_id)
                if not is_member:
                    yield {
                        "event": "error",
                        "data": json.dumps(
                            {"message": "Private 프로젝트는 명시적 멤버만 접근 가능합니다."},
                            ensure_ascii=False,
                        ),
                    }
                    yield {"event": "done", "data": json.dumps({"cached": False, "sourceCount": 0})}
                    return

        # 검증 통과 — RagService.ask로 위임 (AsyncGenerator 위임 표준 패턴)
        async for event in self.rag_service.ask(
            question=question,
            workspace_id=workspace_id,
            project_id=project_id,
            time_range=time_range,
            source_type=source_type,
        ):
            yield event
