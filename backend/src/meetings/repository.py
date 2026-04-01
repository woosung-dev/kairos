# backend/src/meetings/repository.py
"""Meeting Repository — AsyncSession 유일 보유자."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.meetings.models import Meeting, MeetingSummary, TranscriptSegment


class MeetingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, meeting: Meeting) -> Meeting:
        self.session.add(meeting)
        await self.session.flush()
        return meeting

    async def find_by_id(self, meeting_id: uuid.UUID) -> Meeting | None:
        result = await self.session.execute(
            select(Meeting).where(Meeting.id == meeting_id)
        )
        return result.scalar_one_or_none()

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Meeting]:
        result = await self.session.execute(
            select(Meeting)
            .where(Meeting.workspace_id == workspace_id)
            .order_by(Meeting.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_workspace(self, workspace_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Meeting)
            .where(Meeting.workspace_id == workspace_id)
        )
        return result.scalar_one()

    async def update_status(
        self,
        meeting_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
    ) -> None:
        meeting = await self.find_by_id(meeting_id)
        if meeting:
            meeting.status = status
            meeting.error_message = error_message
            self.session.add(meeting)
            await self.session.flush()

    async def set_has_transcript(self, meeting_id: uuid.UUID, value: bool) -> None:
        meeting = await self.find_by_id(meeting_id)
        if meeting:
            meeting.has_transcript = value
            self.session.add(meeting)
            await self.session.flush()

    async def set_has_summary(self, meeting_id: uuid.UUID, value: bool) -> None:
        meeting = await self.find_by_id(meeting_id)
        if meeting:
            meeting.has_summary = value
            self.session.add(meeting)
            await self.session.flush()

    async def save_segments(
        self, meeting_id: uuid.UUID, segments: list[TranscriptSegment]
    ) -> None:
        for seg in segments:
            seg.meeting_id = meeting_id
            self.session.add(seg)
        await self.session.flush()

    async def save_summary(
        self, meeting_id: uuid.UUID, summary_data: dict
    ) -> MeetingSummary:
        summary = MeetingSummary(
            meeting_id=meeting_id,
            summary=summary_data.get("summary", ""),
            key_decisions=summary_data.get("key_decisions", []),
            topics=summary_data.get("topics", []),
        )
        self.session.add(summary)
        await self.session.flush()
        return summary

    async def get_segments(self, meeting_id: uuid.UUID) -> list[TranscriptSegment]:
        result = await self.session.execute(
            select(TranscriptSegment)
            .where(TranscriptSegment.meeting_id == meeting_id)
            .order_by(TranscriptSegment.start_sec)
        )
        return list(result.scalars().all())

    async def get_summary(self, meeting_id: uuid.UUID) -> MeetingSummary | None:
        result = await self.session.execute(
            select(MeetingSummary).where(MeetingSummary.meeting_id == meeting_id)
        )
        return result.scalar_one_or_none()

    async def commit(self) -> None:
        await self.session.commit()
