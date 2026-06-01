# backend/src/notes/pipeline_service.py
"""노트 오케스트레이터 — embeddings.service 호출 + 권한 검증 일원화.

ADR-014 옵션 A: D-2 (notes → embeddings.service) 부채 해소.
헌법 §4.2: embeddings.service 호출은 orchestrator 내부에서만 허용.

권한 검증 책임 (Sprint 6):
- visibility=Private 노트: ProjectMember 매핑된 사람만 read/write
- visibility=Draft 노트: creator + admin 이상만 read/write
- project_id=None: 워크스페이스 멤버 누구나 (단순)
실제 권한 검증은 router의 require_*(RBAC decorator)에서 1차 진행 + 본 진입 메서드에서
project visibility 동적 검증 (admin 이상은 우회).
"""
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.notes.repository import NoteRepository
from src.projects.repository import ProjectRepository


class NotePipelineService:
    def __init__(
        self,
        note_repo: NoteRepository,
        embedding_service: EmbeddingService,
        project_repo: ProjectRepository,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.note_repo = note_repo
        self.embedding_service = embedding_service
        self.project_repo = project_repo
        # P0 fix (2026-06-01): BG embedding 은 fresh 세션 필요 — request-scoped 세션은
        # HTTP 응답 직후 닫혀 BackgroundTasks 실행 시 사용 불가 (Sprint 9 버그 클래스 재발 방지).
        self.session_factory = session_factory

    async def embed_note_async(
        self, note_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """BackgroundTasks용 임베딩 생성 + 캐시 무효화 (D-2 부채 해소).

        embedding 호출은 본 orchestrator 내부에서만 — 헌법 §4.2 정합.
        헌법 I-9 (Codex F-1): workspace_id 필수.

        P0 fix (2026-06-01): request-scoped 세션은 HTTP 응답 직후 닫히므로
        BackgroundTasks 실행 시점엔 사용 불가 → session_factory 로 fresh 세션 생성
        (meetings.pipeline_service 와 동일 패턴).
        """
        if self.session_factory is None:
            raise RuntimeError(
                "NotePipelineService.embed_note_async 는 session_factory 가 필요합니다 "
                "(BackgroundTasks fresh 세션)."
            )
        async with self.session_factory() as session:
            note_repo = NoteRepository(session)
            embedding_service = EmbeddingService(EmbeddingRepository(session))
            note = await note_repo.find_by_id(note_id, workspace_id)
            if not note or not note.plain_text:
                return
            await embedding_service.embed_note(
                note_id=note.id,
                workspace_id=note.workspace_id,
                project_id=note.project_id,
                title=note.title,
                plain_text=note.plain_text,
            )
            await embedding_service.invalidate_cache(
                note.workspace_id, note.project_id
            )

    async def delete_note_with_cleanup(
        self, note_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """노트 삭제 + embedding chunk cleanup + 캐시 무효화 (D-2 부채 해소).

        Codex H2 / 옵션 A: pipeline 시그니처 자체에 workspace_id 필수 → pipeline 우회 IDOR 차단.
        Codex 2차 F-4: cross-tenant 또는 missing note → NoteNotFoundError (404). 이전 silent return
        은 router 가 204 success 로 응답해 F-4 lock-in 위반 (C7 fix).
        """
        from src.notes.exceptions import NoteNotFoundError

        note = await self.note_repo.find_by_id(note_id, workspace_id)
        if note is None:
            raise NoteNotFoundError()
        project_id = note.project_id
        # embedding chunk 삭제 (repository 직접 호출 = 헌법 §4.2 OK, read-only가 아니지만
        # embeddings 도메인은 cross-domain shared service로 분류 — ADR-014 §1)
        await self.embedding_service.repo.delete_by_source("note", note_id)
        # 노트 삭제
        await self.note_repo.delete(note)
        await self.note_repo.commit()
        # 캐시 무효화
        await self.embedding_service.invalidate_cache(workspace_id, project_id)

    async def check_project_access(
        self,
        project_id: uuid.UUID | None,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID,
        requester_role: str,
    ) -> bool:
        """note의 project visibility 권한 검증 (Sprint 6 권한 일원화 자리).

        Returns True if requester has access, False otherwise.
        admin/owner는 우회. project_id=None은 워크스페이스 멤버 누구나 OK.
        Sprint 19 PR #1 C9 (Codex F-1 cascade): workspace_id 시그니처 강제.
        """
        if requester_role in ("admin", "owner"):
            return True
        if project_id is None:
            return True
        project = await self.project_repo.find_by_id(project_id, workspace_id)
        if project is None:
            return False
        if project.visibility == "public":
            return True
        if project.visibility == "draft":
            return project.created_by_id == requester_user_id
        if project.visibility == "private":
            return await self.project_repo.is_member(project_id, requester_user_id, workspace_id)
        return False
