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

    async def sync_note_project_id(
        self, note_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """project_id 변경 시 EmbeddingChunk.project_id 동기화 + old/new 캐시 무효화.

        Sprint 29 R1 (notes-stale): content 변경이 없으면 embed_note_async(BG) 가
        실행되지 않아 chunk.project_id 가 stale 로 남아 RAG project-scope 필터가 틀린다.
        재임베딩 없이 chunk 의 project_id 만 갱신(vector 보존) + 변경 전/후 project scope
        의 SemanticCache 를 무효화한다.

        request-scoped 세션 동기 처리 — note 의 현재(갱신된) project_id 와 기존 chunk 의
        old project_id 를 같은 트랜잭션에서 읽으므로 embed_note_async 실행 순서와 무관하게
        정확하다. embeddings 도메인은 cross-domain shared service (ADR-014 §4.2) 라
        orchestrator 내부에서 EmbeddingRepository 직접 호출 허용.
        """
        note = await self.note_repo.find_by_id(note_id, workspace_id)
        if note is None:
            return
        new_project_id = note.project_id
        embed_repo = self.embedding_service.repo
        old_project_ids = await embed_repo.find_chunk_project_ids("note", note_id)
        if not old_project_ids:
            # 아직 임베딩 전(plain_text 빈 노트 등) → 동기화 대상 없음.
            # content 변경 시 embed_note_async 가 새 project_id 로 chunk 를 생성한다.
            return
        await embed_repo.update_project_id("note", note_id, new_project_id)
        # 변경 전(old) + 변경 후(new) project scope 의 캐시 모두 무효화.
        for scope in old_project_ids | {new_project_id}:
            await embed_repo.delete_caches(workspace_id, scope)
        await embed_repo.commit()

    async def delete_note_with_cleanup(
        self,
        note_id: uuid.UUID,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> None:
        """노트 삭제 + embedding chunk cleanup + 캐시 무효화 (D-2 부채 해소).

        Codex H2 / 옵션 A: pipeline 시그니처 자체에 workspace_id 필수 → pipeline 우회 IDOR 차단.
        Codex 2차 F-4: cross-tenant 또는 missing note → NoteNotFoundError (404). 이전 silent return
        은 router 가 204 success 로 응답해 F-4 lock-in 위반 (C7 fix).

        CAND-A completeness: SOURCE 노트의 project visibility 게이트 — 비-멤버가
        private/draft 프로젝트의 노트를 삭제하는 write IDOR 차단 (비-멤버 → 404).
        check_project_access (admin/owner 우회 / project None / public / draft creator /
        private member) 재사용 — _verify_note_visibility 와 동일 규칙.
        requester_role 미전달(None) = 내부 호출 → 게이트 skip (하위호환).
        """
        from src.notes.exceptions import NoteNotFoundError

        note = await self.note_repo.find_by_id(note_id, workspace_id)
        if note is None:
            raise NoteNotFoundError()
        if requester_role is not None and requester_user_id is not None:
            has_access = await self.check_project_access(
                note.project_id, workspace_id, requester_user_id, requester_role
            )
            if not has_access:
                # fail-closed 404 — 존재성/소속 누출 방지 (get/list 와 동일 시그널)
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
