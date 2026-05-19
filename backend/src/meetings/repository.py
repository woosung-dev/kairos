# backend/src/meetings/repository.py
"""Meeting Repository — AsyncSession 유일 보유자. 헌법 I-9 workspace_id 필수 (Sprint 19 PR #1)."""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import func, select

from src.common.promote_models import ItemPromotionAudit
from src.embeddings.models import EmbeddingChunk
from src.meetings.models import Meeting, MeetingSummary, TranscriptSegment
from src.projects.models import MeetingProjectLink


class MeetingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, meeting: Meeting) -> Meeting:
        self.session.add(meeting)
        await self.session.flush()
        return meeting

    async def find_by_id(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> Meeting | None:
        """헌법 I-9 (Codex F-1): meeting_id + workspace_id 동시 필터."""
        return (await self.session.exec(
            select(Meeting).where(
                Meeting.id == meeting_id,
                Meeting.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
        project_id: uuid.UUID | None = None,
    ) -> list[Meeting]:
        stmt = select(Meeting).where(Meeting.workspace_id == workspace_id)
        if project_id is not None:
            stmt = stmt.join(
                MeetingProjectLink,
                MeetingProjectLink.meeting_id == Meeting.id,
            ).where(MeetingProjectLink.project_id == project_id)
        stmt = stmt.order_by(Meeting.created_at.desc()).offset(offset).limit(limit)
        return list((await self.session.exec(stmt)).all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Meeting)
            .where(Meeting.workspace_id == workspace_id)
        )
        if project_id is not None:
            stmt = stmt.join(
                MeetingProjectLink,
                MeetingProjectLink.meeting_id == Meeting.id,
            ).where(MeetingProjectLink.project_id == project_id)
        return (await self.session.exec(stmt)).one()

    async def update_status(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """헌법 I-9 (Codex F-1): mutating 호출도 workspace_id 검증."""
        meeting = await self.find_by_id(meeting_id, workspace_id)
        if meeting:
            meeting.status = status
            meeting.error_message = error_message
            self.session.add(meeting)
            await self.session.flush()

    async def set_has_transcript(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID, value: bool
    ) -> None:
        meeting = await self.find_by_id(meeting_id, workspace_id)
        if meeting:
            meeting.has_transcript = value
            self.session.add(meeting)
            await self.session.flush()

    async def set_has_summary(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID, value: bool
    ) -> None:
        meeting = await self.find_by_id(meeting_id, workspace_id)
        if meeting:
            meeting.has_summary = value
            self.session.add(meeting)
            await self.session.flush()

    async def save_segments(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        segments: list[TranscriptSegment],
    ) -> None:
        """헌법 I-9 (Codex F-1): meeting workspace 사전 검증 후 INSERT."""
        meeting = await self.find_by_id(meeting_id, workspace_id)
        if meeting is None:
            return
        for seg in segments:
            seg.meeting_id = meeting_id
            self.session.add(seg)
        await self.session.flush()

    async def save_summary(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        summary_data: dict,
    ) -> MeetingSummary | None:
        """헌법 I-9 (Codex F-1): meeting workspace 사전 검증 후 INSERT."""
        meeting = await self.find_by_id(meeting_id, workspace_id)
        if meeting is None:
            return None
        summary = MeetingSummary(
            meeting_id=meeting_id,
            summary=summary_data.get("summary", ""),
            key_decisions=summary_data.get("key_decisions", []),
            topics=summary_data.get("topics", []),
        )
        self.session.add(summary)
        await self.session.flush()
        return summary

    async def get_segments(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> list[TranscriptSegment]:
        """헌법 I-9: Meeting join 으로 workspace 격리 검증."""
        return list((await self.session.exec(
            select(TranscriptSegment)
            .join(Meeting, TranscriptSegment.meeting_id == Meeting.id)
            .where(
                TranscriptSegment.meeting_id == meeting_id,
                Meeting.workspace_id == workspace_id,
            )
            .order_by(TranscriptSegment.start_sec)
        )).all())

    async def get_summary(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> MeetingSummary | None:
        """헌법 I-9: Meeting join 으로 workspace 격리 검증."""
        return (await self.session.exec(
            select(MeetingSummary)
            .join(Meeting, MeetingSummary.meeting_id == Meeting.id)
            .where(
                MeetingSummary.meeting_id == meeting_id,
                Meeting.workspace_id == workspace_id,
            )
        )).one_or_none()

    # ── Sprint 23 D4 Task 2 Step 2.2: promote 지원 메서드 ──

    async def save_promoted_meeting(self, meeting: Meeting) -> Meeting:
        """promote 복제본 Meeting INSERT — workspace_id 는 호출자가 target 으로 설정.

        save() 와 시그니처 동일하지만, promote 흐름에서 명시적으로 호출 출처 분리.
        I-9 검증은 호출자 (service.promote) 가 사전에 target workspace 멤버십을 확인.
        """
        self.session.add(meeting)
        await self.session.flush()
        return meeting

    async def save_promoted_summary(
        self, summary: MeetingSummary
    ) -> MeetingSummary:
        """promote 복제본 MeetingSummary INSERT — meeting_id 는 호출자가 새 meeting.id 로 설정."""
        self.session.add(summary)
        await self.session.flush()
        return summary

    async def save_promoted_segments(
        self, segments: list[TranscriptSegment]
    ) -> None:
        """promote 복제본 TranscriptSegment[] INSERT — meeting_id 는 호출자가 새 meeting.id 로 설정."""
        for seg in segments:
            self.session.add(seg)
        await self.session.flush()

    async def save_item_promotion_audit(
        self, audit: ItemPromotionAudit
    ) -> ItemPromotionAudit:
        """4 도메인 공통 ItemPromotionAudit INSERT — commit 은 호출자."""
        self.session.add(audit)
        await self.session.flush()
        return audit

    async def find_meeting_chunks(
        self, meeting_id: uuid.UUID, source_workspace_id: uuid.UUID
    ) -> list[EmbeddingChunk]:
        """promote BG 흐름용: source meeting 의 모든 EmbeddingChunk 조회 (target ws 복제용).

        I-9 4-C: source_workspace_id WHERE 필터 강제 — cross-workspace 격리.
        """
        return list((await self.session.exec(
            select(EmbeddingChunk).where(
                EmbeddingChunk.source_type == "meeting",
                EmbeddingChunk.source_id == meeting_id,
                EmbeddingChunk.workspace_id == source_workspace_id,
            )
        )).all())

    async def commit(self) -> None:
        await self.session.commit()
