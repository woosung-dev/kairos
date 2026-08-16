# apps/api/src/notes/repository.py
"""노트 DB 접근."""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import func, select

from src.common.promote_models import ItemPromotionAudit
from src.common.visibility import RequesterContext, apply_fk_project_visibility
from src.embeddings.models import EmbeddingChunk
from src.notes.models import Note


def _note_visibility_filter(
    stmt,
    requester_user_id: uuid.UUID | None,
    requester_role: str | None,
):
    """CAND-A completeness: note LIST 에 project visibility 게이트 적용.

    규칙 정의는 common/visibility.py SSOT — FK-상관 어댑터 위임
    (project_id IS NULL 통과 / role=None 내부호출 skip / admin·owner 우회 /
    private 는 ProjectMember ∧ WorkspaceMember flatten EXISTS, CAND-B).
    """
    return apply_fk_project_visibility(
        stmt, Note.project_id, RequesterContext(requester_user_id, requester_role)
    )


class NoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, note: Note) -> Note:
        self.session.add(note)
        await self.session.flush()
        return note

    async def find_by_id(
        self, note_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> Note | None:
        """헌법 I-9 (Codex F-1): note_id + workspace_id 동시 필터."""
        return (await self.session.exec(
            select(Note).where(
                Note.id == note_id,
                Note.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> list[Note]:
        stmt = select(Note).where(Note.workspace_id == workspace_id)
        if project_id:
            stmt = stmt.where(Note.project_id == project_id)
        # CAND-A completeness: project visibility 게이트 (비-멤버 private/draft 본문 누출 차단).
        stmt = _note_visibility_filter(stmt, requester_user_id, requester_role)
        stmt = stmt.order_by(Note.updated_at.desc()).offset(offset).limit(limit)
        return list((await self.session.exec(stmt)).all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Note)
            .where(Note.workspace_id == workspace_id)
        )
        if project_id:
            stmt = stmt.where(Note.project_id == project_id)
        # CAND-A completeness: total 도 필터된 집합 기준 (pagination 정합).
        stmt = _note_visibility_filter(stmt, requester_user_id, requester_role)
        return (await self.session.exec(stmt)).one()

    async def delete(self, note: Note) -> None:
        await self.session.delete(note)
        await self.session.flush()

    # ── Sprint 23 D4 Task 2 Step 2.3: promote 지원 메서드 ──

    async def save_promoted_note(self, note: Note) -> Note:
        """promote 복제본 Note INSERT — workspace_id 는 호출자가 target 으로 설정.

        save() 와 시그니처 동일하지만, promote 흐름에서 명시적으로 호출 출처 분리.
        I-9 검증은 호출자 (service.promote) 가 사전에 target workspace 멤버십을 확인.
        """
        self.session.add(note)
        await self.session.flush()
        return note

    async def save_item_promotion_audit(
        self, audit: ItemPromotionAudit
    ) -> ItemPromotionAudit:
        """4 도메인 공통 ItemPromotionAudit INSERT — commit 은 호출자."""
        self.session.add(audit)
        await self.session.flush()
        return audit

    async def find_note_chunks(
        self, note_id: uuid.UUID, source_workspace_id: uuid.UUID
    ) -> list[EmbeddingChunk]:
        """promote BG 흐름용: source note 의 모든 EmbeddingChunk 조회 (target ws 복제용).

        I-9 4-C: source_workspace_id WHERE 필터 강제 — cross-workspace 격리.
        """
        return list((await self.session.exec(
            select(EmbeddingChunk).where(
                EmbeddingChunk.source_type == "note",
                EmbeddingChunk.source_id == note_id,
                EmbeddingChunk.workspace_id == source_workspace_id,
            )
        )).all())

    # ── Sprint 24 BL-064: embedding-status polling endpoint 지원 ──

    async def count_note_chunks(
        self, note_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> int:
        """target note 의 실 EmbeddingChunk 개수 — polling 응답 chunkCount.

        I-9 4-C: workspace_id WHERE 필터 강제.
        """
        return (await self.session.exec(
            select(func.count())
            .select_from(EmbeddingChunk)
            .where(
                EmbeddingChunk.source_type == "note",
                EmbeddingChunk.source_id == note_id,
                EmbeddingChunk.workspace_id == workspace_id,
            )
        )).one()

    async def find_latest_audit_for_note(
        self, note_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> ItemPromotionAudit | None:
        """target ws 의 note 에 대한 가장 최신 ItemPromotionAudit (new_item_id 기준).

        promote 외 흐름의 note 는 audit 부재 — None 반환.
        """
        stmt = (
            select(ItemPromotionAudit)
            .where(
                ItemPromotionAudit.item_type == "note",
                ItemPromotionAudit.new_item_id == note_id,
                ItemPromotionAudit.target_workspace_id == workspace_id,
            )
            .order_by(ItemPromotionAudit.created_at.desc())
            .limit(1)
        )
        return (await self.session.exec(stmt)).one_or_none()

    async def commit(self) -> None:
        await self.session.commit()
