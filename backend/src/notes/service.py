# backend/src/notes/service.py
"""노트 비즈니스 로직 — 순수 노트 CRUD (ADR-014 옵션 A: embedding 의존 제거).

embeddings.service 호출은 NotePipelineService(orchestrator) 내부에서만 수행 — 헌법 §4.2 정합.
헌법 I-9 (Sprint 19 PR #1, Codex F-1): 모든 메서드 workspace_id 필수.
Codex F-2 (Critical): create/update 시 project_id cross-workspace 검증 (secondary FK).

Sprint 23 D4 Task 2 Step 2.3: cross-workspace promote 추가 (4 도메인 중 note).
- I-18 (복제 + tombstone): 원본 보존 + target ws Note 복제 + ItemPromotionAudit.
- workspace_repo / session_factory 옵션 주입 — promote 호출 시 필수 (없으면 RuntimeError).
"""
import json
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

if TYPE_CHECKING:
    from src.notes.pipeline_service import NotePipelineService

from src.common.promote_helpers import (
    PromoteValidationError,
    build_item_promotion_audit,
    validate_promote_target,
)
from src.embeddings.models import EmbeddingChunk
from src.notes.exceptions import (
    CannotPromoteToPersonalError,
    CannotPromoteToSameWorkspaceError,
    NoteNotFoundError,
    NotePromoteNotEmbeddedError,
    TargetWorkspaceInvalidError,
)
from src.notes.models import Note
from src.notes.repository import NoteRepository
from src.notes.schemas import EmbeddingStatusOut, NotePromoteOut
from src.projects.exceptions import ProjectNotFoundError
from src.projects.repository import ProjectRepository
from src.workspaces.repository import WorkspaceRepository

logger = logging.getLogger(__name__)


def extract_plain_text(tiptap_json: dict) -> str:
    """Tiptap JSON에서 텍스트만 재귀 추출."""
    texts: list[str] = []
    for node in tiptap_json.get("content", []):
        if "text" in node:
            texts.append(node["text"])
        if "content" in node:
            texts.append(extract_plain_text(node))
    return "\n".join(filter(None, texts))


class NoteService:
    def __init__(
        self,
        repo: NoteRepository,
        project_repo: ProjectRepository | None = None,
        workspace_repo: WorkspaceRepository | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.repo = repo
        # Codex F-2: project_id secondary FK cross-tenant 검증용
        self.project_repo = project_repo
        # Sprint 23 D4 (Task 2 Step 2.3): promote 흐름 필수 의존성.
        # 일반 CRUD 흐름은 None 허용 — promote 호출 시점에 fail-closed 검증.
        self.workspace_repo = workspace_repo
        self._session_factory = session_factory

    async def _verify_project_in_workspace(
        self, project_id: uuid.UUID | None, workspace_id: uuid.UUID
    ) -> None:
        """Codex F-2: project_id 가 같은 workspace 인지 검증. None 이면 통과.

        Codex 2차 Minor 1 (C7): fail-closed — project_id 가 들어왔는데 project_repo
        미주입이면 RuntimeError 로 차단 (silent skip 금지).
        """
        if project_id is None:
            return
        if self.project_repo is None:
            raise RuntimeError("project_repo 필수 (F-2 검증)")
        # Sprint 19 PR #1 C9 (Codex F-1 cascade): find_by_id workspace_id 강제
        project = await self.project_repo.find_by_id(project_id, workspace_id)
        if project is None:
            raise ProjectNotFoundError()

    async def create_note(
        self,
        workspace_id: uuid.UUID,
        created_by_id: uuid.UUID,
        title: str = "",
        content: dict | None = None,
        project_id: uuid.UUID | None = None,
    ) -> dict:
        # Codex F-2: cross-workspace project_id 거부
        await self._verify_project_in_workspace(project_id, workspace_id)
        plain_text = extract_plain_text(content) if content else ""
        note = Note(
            workspace_id=workspace_id,
            project_id=project_id,
            title=title,
            content=content or {},
            plain_text=plain_text,
            created_by_id=created_by_id,
        )
        note = await self.repo.save(note)
        await self.repo.commit()
        return self._to_dict(note)

    async def list_notes(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> dict:
        """CAND-A completeness: requester visibility 게이트 (private/draft 본문 누출 차단).

        requester_role 미전달(None) = 내부/파이프라인 호출 → 게이트 skip (하위호환).
        """
        offset = (page - 1) * page_size
        notes = await self.repo.find_by_workspace(
            workspace_id,
            project_id=project_id,
            offset=offset,
            limit=page_size,
            requester_user_id=requester_user_id,
            requester_role=requester_role,
        )
        total = await self.repo.count_by_workspace(
            workspace_id,
            project_id=project_id,
            requester_user_id=requester_user_id,
            requester_role=requester_role,
        )
        return {
            "items": [self._to_dict(n) for n in notes],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "hasNext": page * page_size < total,
        }

    async def _verify_note_visibility(
        self,
        note: Note,
        requester_user_id: uuid.UUID | None,
        requester_role: str | None,
    ) -> None:
        """CAND-A: note 의 owning project visibility 게이트 (get_project 정합).

        require_viewer/member 만으론 private/draft project 노트가 비-ProjectMember 에게
        노출된다 (visibility-residue IDOR). project-detail 과 동일 규칙으로 게이트:
        - admin/owner: 우회 (모든 visibility)
        - project_id=None: 워크스페이스 멤버 누구나 OK
        - draft: 작성자(created_by_id)만, 그 외 404
        - private: ProjectMember 매핑된 사람만, 그 외 404

        requester_role 미전달(None) = 내부/특권 호출 → 게이트 skip (하위호환).
        """
        if requester_role is None:
            return
        if requester_role in ("admin", "owner"):
            return
        if note.project_id is None:
            return
        if self.project_repo is None:
            raise RuntimeError("project_repo 필수 (CAND-A visibility 검증)")
        project = await self.project_repo.find_by_id(
            note.project_id, note.workspace_id
        )
        if project is None:
            # cross-tenant 또는 dangling project → fail-closed 404
            raise NoteNotFoundError()
        if project.visibility == "draft":
            if project.created_by_id != requester_user_id:
                raise NoteNotFoundError()
        elif project.visibility == "private":
            if requester_user_id is None or not await self.project_repo.is_member(
                note.project_id, requester_user_id, note.workspace_id
            ):
                raise NoteNotFoundError()

    async def get_note(
        self,
        note_id: uuid.UUID,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> dict:
        """헌법 I-9 (Codex F-1): workspace_id 필수. CAND-A: project visibility 게이트."""
        note = await self.repo.find_by_id(note_id, workspace_id)
        if note is None:
            raise NoteNotFoundError()
        await self._verify_note_visibility(note, requester_user_id, requester_role)
        return self._to_dict(note)

    async def update_note(
        self,
        note_id: uuid.UUID,
        workspace_id: uuid.UUID,
        title: str | None = None,
        content: dict | None = None,
        project_id: uuid.UUID | None = ...,  # type: ignore[assignment]
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> dict:
        """헌법 I-9 (Codex F-1) + Codex F-2 Critical: project_id cross-workspace 거부.

        CAND-A completeness: SOURCE 노트의 project visibility 게이트 — 비-멤버가
        private/draft 프로젝트의 노트를 mutate 하는 write IDOR 차단 (비-멤버 → 404).
        """
        note = await self.repo.find_by_id(note_id, workspace_id)
        if note is None:
            raise NoteNotFoundError()
        await self._verify_note_visibility(note, requester_user_id, requester_role)

        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
            note.plain_text = extract_plain_text(content)
        if project_id is not ...:
            # Codex F-2: 새 project_id 가 같은 workspace 인지 검증
            await self._verify_project_in_workspace(project_id, workspace_id)
            note.project_id = project_id  # type: ignore[assignment]

        note.updated_at = datetime.utcnow()
        note = await self.repo.save(note)
        await self.repo.commit()
        return self._to_dict(note)

    async def delete_note(
        self, note_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """노트 삭제 (순수). embedding cleanup은 NotePipelineService 책임."""
        note = await self.repo.find_by_id(note_id, workspace_id)
        if note is None:
            raise NoteNotFoundError()
        await self.repo.delete(note)
        await self.repo.commit()

    async def export_note(
        self,
        note_id: uuid.UUID,
        workspace_id: uuid.UUID,
        fmt: str,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> tuple[str, str, str]:
        """노트 내보내기. (content, filename, media_type) 반환. CAND-A: visibility 게이트."""
        note = await self.repo.find_by_id(note_id, workspace_id)
        if note is None:
            raise NoteNotFoundError()
        await self._verify_note_visibility(note, requester_user_id, requester_role)

        title = note.title or "Untitled"

        if fmt == "md":
            content = f"# {title}\n\n{note.plain_text}"
            return content, f"{title}.md", "text/markdown; charset=utf-8"
        else:
            data = {
                "id": str(note.id),
                "title": title,
                "content": note.content,
                "plainText": note.plain_text,
                "createdAt": note.created_at.isoformat(),
                "updatedAt": note.updated_at.isoformat(),
            }
            content = json.dumps(data, ensure_ascii=False, indent=2)
            return content, f"{title}.json", "application/json; charset=utf-8"

    @staticmethod
    def _to_dict(note: Note) -> dict:
        return {
            "id": str(note.id),
            "workspaceId": str(note.workspace_id),
            "projectId": str(note.project_id) if note.project_id else None,
            "title": note.title,
            "content": note.content,
            "plainText": note.plain_text,
            "createdById": str(note.created_by_id),
            "createdAt": note.created_at.isoformat(),
            "updatedAt": note.updated_at.isoformat(),
        }

    # ── Sprint 23 D4 Task 2 Step 2.3: promote 1-button ──

    async def promote(
        self,
        *,
        note_id: uuid.UUID,
        source_workspace_id: uuid.UUID,
        target_workspace_id: uuid.UUID,
        promoted_by_user_id: uuid.UUID,
        background_tasks: BackgroundTasks,
        requester_role: str | None = None,
    ) -> NotePromoteOut:
        """1-button promote: 원본 보존 + target ws 복제 + audit + bg embedding 복제.

        I-18 (Promotion = 복제 + tombstone, 이동 금지): source Note 변경 없음.
        검증: source != target / target type='team' / promoter 가 target ws 멤버.
        helper: common/promote_helpers.validate_promote_target + build_item_promotion_audit.

        project_id 처리: cross-workspace 이므로 target ws 에서는 project 미연결 (None).
        사용자가 target ws 에서 PATCH /notes/{id} 로 별도 연결.

        Sprint 24 BL-064: chunk 0 + plain_text 존재 시 → 400 대신 promote OK +
        `_bg_regenerate_embed_with_audit` BG schedule (audit lifecycle 책임).
        Sprint 24 Gemini P2 fix: wrapper 가 자체 session_factory 로 fresh NotePipelineService
        를 인스턴스화 — request-scoped pipeline 전달 제거 (connection pool 점유 방지).
        """
        # Sprint 23 D4 (Task 2 Step 2.3): promote 흐름 의존성 fail-closed 검증.
        if self._session_factory is None:
            raise RuntimeError(
                "session_factory 필수 (I-18 promote BG embedding 복제, fail-closed)"
            )

        # 1. promote target 검증 (헬퍼 — 4 도메인 공통 패턴)
        try:
            await validate_promote_target(
                source_workspace_id=source_workspace_id,
                target_workspace_id=target_workspace_id,
                promoted_by_user_id=promoted_by_user_id,
                workspace_repo=self.workspace_repo,
            )
        except PromoteValidationError as exc:
            # PromoteValidationError.code → notes 도메인 HTTPException 매핑.
            if exc.code == "same_workspace":
                raise CannotPromoteToSameWorkspaceError() from exc
            if exc.code == "target_personal":
                raise CannotPromoteToPersonalError() from exc
            # target_invalid / not_member → 403 (meetings/memory 패턴 정렬)
            raise TargetWorkspaceInvalidError() from exc

        # 2. 원본 Note fetch (I-9 workspace_id 강제)
        source = await self.repo.find_by_id(note_id, source_workspace_id)
        if source is None:
            raise NoteNotFoundError()

        # CAND-A completeness: SOURCE 노트의 project visibility 게이트 — 비-멤버가
        # private/draft 프로젝트의 노트를 team ws 로 promote(=복제 노출)하는 IDOR 차단.
        # promoter 는 source ws 멤버지만 ProjectMember 가 아닐 수 있음 → 비-멤버 → 404.
        await self._verify_note_visibility(
            source, promoted_by_user_id, requester_role
        )

        # Sprint 24 BL-064: chunk 0 + plain_text 분기 보강.
        # plain_text 부재 → 400 회귀 가드 유지 (Sprint 23 6차 P2).
        # plain_text 존재 + chunk 0 → 400 대신 BG re-embedding schedule.
        if not source.plain_text or not source.plain_text.strip():
            raise NotePromoteNotEmbeddedError()

        existing_chunks = await self.repo.find_note_chunks(
            source.id, source_workspace_id
        )
        needs_embed_regenerate = not existing_chunks
        # Sprint 24 Gemini P2 fix: wrapper 가 자체 pipeline 인스턴스화 — caller 의 pipeline DI 불요.

        # 3. 복제 Note (id 새로 발급, workspace_id=target, project_id=None).
        # I-18: 원본 보존 — source 미변경.
        # project_id=None: source.project_id 는 source ws 의 project — target ws 와 무관 (cross-workspace
        # 제약, secondary FK ck). 사용자가 target ws 에서 별도 연결 권장.
        new_note = Note(
            workspace_id=target_workspace_id,
            project_id=None,
            title=source.title,
            content=dict(source.content or {}),
            plain_text=source.plain_text,
            created_by_id=promoted_by_user_id,
        )
        new_note = await self.repo.save_promoted_note(new_note)

        # 4. ItemPromotionAudit row (helper) — pending 초기값
        audit = build_item_promotion_audit(
            item_type="note",
            source_item_id=source.id,
            new_item_id=new_note.id,
            source_workspace_id=source_workspace_id,
            target_workspace_id=target_workspace_id,
            promoted_by_user_id=promoted_by_user_id,
            embedding_status="pending",
        )
        await self.repo.save_item_promotion_audit(audit)

        await self.repo.commit()

        # 5. background task schedule — 분기.
        # session 종료 시 source.id 등 객체 expire 가능성 — 원시 UUID 로 전달.
        if needs_embed_regenerate:
            # Sprint 24 BL-064: chunk 0 + plain_text → embedding 신규 생성 + audit lifecycle.
            # Codex 2차 P1: pipeline.embed_note_async 만 호출 시 audit pending stuck —
            # wrapper 가 audit pending → processing → completed/failed 책임.
            background_tasks.add_task(
                _bg_regenerate_embed_with_audit,
                new_note_id=new_note.id,
                target_workspace_id=target_workspace_id,
                audit_id=audit.id,
                session_factory=self._session_factory,
            )
        else:
            # 기존 Sprint 23 D4 흐름 — source chunk 들을 target ws 로 복제.
            background_tasks.add_task(
                _bg_promote_embed_note,
                source_note_id=source.id,
                source_workspace_id=source_workspace_id,
                new_note_id=new_note.id,
                target_workspace_id=target_workspace_id,
                audit_id=audit.id,
                session_factory=self._session_factory,
            )

        return NotePromoteOut(
            new_note_id=new_note.id,
            audit_id=audit.id,
            status="embedding_pending",
            embedding_status="pending",
        )

    # ── Sprint 24 BL-064: embedding-status polling endpoint 지원 ──

    async def get_embedding_status(
        self,
        workspace_id: uuid.UUID,
        note_id: uuid.UUID,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> EmbeddingStatusOut:
        """target note 의 embedding 진행 상태 + 실 chunk count 반환.

        - audit row 가 있으면 raw embedding_status + 실 chunk count.
        - audit row 가 없으면 (promote 외 흐름의 일반 note):
            - chunk count > 0 → "completed"
            - chunk count == 0 → "pending" (embed_note_async 가 곧 호출됨)

        CAND-A completeness: project visibility 게이트 — 비-멤버가 private/draft 노트의
        embedding 진행 상태(존재성)를 polling 으로 캐내는 status leak 차단 (비-멤버 → 404).
        """
        note = await self.repo.find_by_id(note_id, workspace_id)
        if note is None:
            raise NoteNotFoundError()
        await self._verify_note_visibility(note, requester_user_id, requester_role)

        chunk_count = await self.repo.count_note_chunks(note_id, workspace_id)
        audit = await self.repo.find_latest_audit_for_note(note_id, workspace_id)
        if audit is None:
            status: "EmbeddingStatusValue" = (  # type: ignore[name-defined]
                "completed" if chunk_count > 0 else "pending"
            )
            return EmbeddingStatusOut(status=status, chunk_count=chunk_count)

        return EmbeddingStatusOut(
            status=audit.embedding_status,  # type: ignore[arg-type]
            chunk_count=chunk_count,
        )


# ── Sprint 23 D4 Task 2 Step 2.3: promote BG embedding 복제 헬퍼 ──


async def _bg_promote_embed_note(
    source_note_id: uuid.UUID,
    source_workspace_id: uuid.UUID,
    new_note_id: uuid.UUID,
    target_workspace_id: uuid.UUID,
    audit_id: uuid.UUID,
    session_factory: "async_sessionmaker[AsyncSession]",
) -> None:
    """note promote BG: source ws 의 EmbeddingChunk 들을 target ws 로 복제 + audit status 갱신.

    pending → processing → completed/failed 흐름. session_factory 로 별도 session.
    임베딩 vector 자체는 그대로 복사 (재계산 불필요 — OpenAI cost 절감).
    """
    from sqlmodel import update as _update

    from src.common.promote_models import ItemPromotionAudit

    async with session_factory() as session:
        repo = NoteRepository(session)
        # processing 마크
        await session.exec(
            _update(ItemPromotionAudit)
            .where(ItemPromotionAudit.id == audit_id)
            .values(embedding_status="processing")
        )
        await session.commit()

        try:
            source_chunks = await repo.find_note_chunks(
                source_note_id, source_workspace_id
            )
            # chunk 0개 → audit n/a. embed_note_async 가 호출되지 않은 (plain_text 빈) note 케이스.
            if not source_chunks:
                await session.exec(
                    _update(ItemPromotionAudit)
                    .where(ItemPromotionAudit.id == audit_id)
                    .values(embedding_status="n/a")
                )
                await session.commit()
                return

            # parent_chunk_id (L1) 매핑 유지: old_id → new_id.
            id_map: dict[uuid.UUID, uuid.UUID] = {}
            # 1차: L1 chunk 먼저 (parent_chunk_id 없음) 복제
            for src_chunk in source_chunks:
                if src_chunk.parent_chunk_id is None:
                    new_id = uuid.uuid4()
                    id_map[src_chunk.id] = new_id
                    dup = EmbeddingChunk(
                        id=new_id,
                        workspace_id=target_workspace_id,
                        project_id=None,  # promote 시 target ws 의 project 미연결 (사용자가 별도 연결)
                        source_id=new_note_id,
                        source_type="note",
                        chunk_text=src_chunk.chunk_text,
                        chunk_index=src_chunk.chunk_index,
                        chunk_level=src_chunk.chunk_level,
                        parent_chunk_id=None,
                        embedding=src_chunk.embedding,
                        metadata_json=dict(src_chunk.metadata_json or {}),
                    )
                    session.add(dup)
            # 2차: L2 chunk (parent_chunk_id 가 1차에서 매핑된 새 UUID 로 변환)
            for src_chunk in source_chunks:
                if src_chunk.parent_chunk_id is not None:
                    parent_new_id = id_map.get(src_chunk.parent_chunk_id)
                    # parent 가 source set 에 없으면 (이론상 발생 X) None 으로 fallback
                    dup = EmbeddingChunk(
                        workspace_id=target_workspace_id,
                        project_id=None,
                        source_id=new_note_id,
                        source_type="note",
                        chunk_text=src_chunk.chunk_text,
                        chunk_index=src_chunk.chunk_index,
                        chunk_level=src_chunk.chunk_level,
                        parent_chunk_id=parent_new_id,
                        embedding=src_chunk.embedding,
                        metadata_json=dict(src_chunk.metadata_json or {}),
                    )
                    session.add(dup)
            await session.flush()

            # Sprint 23 Codex 5차 P2-1 fix: target ws 의 SemanticCache 무효화 — 새 chunk 가
            # 추가됐으니 stale RAG 답변 (TTL 7d) 이 우회되도록.
            # 기존 note embedding pipeline 도 chunk 변경 후 invalidate_cache 호출 (pattern 정합).
            from src.embeddings.repository import EmbeddingRepository as _EmbeddingRepository

            embed_repo = _EmbeddingRepository(session)
            await embed_repo.delete_caches(target_workspace_id, None)

            await session.exec(
                _update(ItemPromotionAudit)
                .where(ItemPromotionAudit.id == audit_id)
                .values(embedding_status="completed")
            )
            await session.commit()
        except Exception as exc:
            logger.warning(
                "note promote embedding 복제 실패 (audit=%s): %s",
                audit_id, exc,
            )
            # Sprint 23 Codex 4차 P2-2 fix: rollback 먼저 — session.flush() 실패 시 transaction
            # state failed → 후속 update 도 fail → audit 가 'processing' stuck. rollback 으로
            # session 재사용 가능 상태로 복구 후 failed mark.
            await session.rollback()
            await session.exec(
                _update(ItemPromotionAudit)
                .where(ItemPromotionAudit.id == audit_id)
                .values(embedding_status="failed")
            )
            await session.commit()


# ── Sprint 24 BL-064: chunk 0 + plain_text 분기용 audit lifecycle wrapper ──


async def _bg_regenerate_embed_with_audit(
    new_note_id: uuid.UUID,
    target_workspace_id: uuid.UUID,
    audit_id: uuid.UUID,
    session_factory: "async_sessionmaker[AsyncSession]",
) -> None:
    """chunk 0 + plain_text 분기 — target note 에 신규 embedding 생성 + audit lifecycle.

    Sprint 23 D4 `_bg_promote_embed_note` 패턴 정합 (audit pending → processing → completed/failed).
    pipeline.embed_note_async 만 호출 시 audit 가 pending stuck — wrapper 가 lifecycle 책임
    (Codex 2차 P1 fix).

    Sprint 24 Gemini review P2 fix: 이전 구현은 request-scoped pipeline 을 BG task 에
    전달 → request 의 AsyncSession 이 long-running OpenAI embedding 호출 동안 connection
    pool 점유 → pool exhaustion 위험. 본 wrapper 가 session_factory 의 새 session 으로
    NotePipelineService 를 인스턴스화 — Sprint 23 `_bg_promote_embed_note` 와 동일 패턴.
    """
    from sqlmodel import update as _update

    from src.common.promote_models import ItemPromotionAudit
    from src.embeddings.repository import EmbeddingRepository
    from src.embeddings.service import EmbeddingService
    from src.notes.pipeline_service import NotePipelineService
    from src.notes.repository import NoteRepository
    from src.projects.repository import ProjectRepository

    async with session_factory() as session:
        # processing 마크
        await session.exec(
            _update(ItemPromotionAudit)
            .where(ItemPromotionAudit.id == audit_id)
            .values(embedding_status="processing")
        )
        await session.commit()

        try:
            # Sprint 24 Gemini P2 fix: 새 session 으로 fresh NotePipelineService 인스턴스 생성.
            # 본 wrapper 의 session 만 사용 — request-scoped session pool 점유 방지.
            # QA fix (2026-06-17): session_factory 미전달 시 embed_note_async 가 RuntimeError →
            # audit "failed" → 승격 note 미임베딩(RAG 비가시). session_factory 전달로 해소.
            bg_pipeline = NotePipelineService(
                note_repo=NoteRepository(session),
                embedding_service=EmbeddingService(EmbeddingRepository(session)),
                project_repo=ProjectRepository(session),
                session_factory=session_factory,
            )
            # plain_text fallback 가드 (pipeline_service.py:41) 가 plain_text 부재 시 early return —
            # promote 흐름에서 plain_text 존재 확인됨, 정상 신규 embedding 생성.
            await bg_pipeline.embed_note_async(new_note_id, target_workspace_id)

            await session.exec(
                _update(ItemPromotionAudit)
                .where(ItemPromotionAudit.id == audit_id)
                .values(embedding_status="completed")
            )
            await session.commit()
        except Exception as exc:
            logger.warning(
                "note promote chunk 0 BG embedding 재생성 실패 (audit=%s): %s",
                audit_id, exc,
            )
            # Sprint 23 D4 Codex 4차 P2-2 패턴: rollback 먼저 후 failed mark.
            await session.rollback()
            await session.exec(
                _update(ItemPromotionAudit)
                .where(ItemPromotionAudit.id == audit_id)
                .values(embedding_status="failed")
            )
            await session.commit()
