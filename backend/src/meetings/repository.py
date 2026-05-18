# backend/src/meetings/repository.py
"""Meeting Repository — AsyncSession 유일 보유자. 헌법 I-9 workspace_id 필수 (Sprint 19 PR #1)."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

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
        result = await self.session.execute(
            select(Meeting).where(
                Meeting.id == meeting_id,
                Meeting.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

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
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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
        result = await self.session.execute(stmt)
        return result.scalar_one()

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
        result = await self.session.execute(
            select(TranscriptSegment)
            .join(Meeting, TranscriptSegment.meeting_id == Meeting.id)
            .where(
                TranscriptSegment.meeting_id == meeting_id,
                Meeting.workspace_id == workspace_id,
            )
            .order_by(TranscriptSegment.start_sec)
        )
        return list(result.scalars().all())

    async def get_summary(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> MeetingSummary | None:
        """헌법 I-9: Meeting join 으로 workspace 격리 검증."""
        result = await self.session.execute(
            select(MeetingSummary)
            .join(Meeting, MeetingSummary.meeting_id == Meeting.id)
            .where(
                MeetingSummary.meeting_id == meeting_id,
                Meeting.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def commit(self) -> None:
        await self.session.commit()
