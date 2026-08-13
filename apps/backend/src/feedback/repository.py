# feedback_entries 저장 repository (AsyncSession)
from src.feedback.models import FeedbackEntry
from sqlmodel.ext.asyncio.session import AsyncSession


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, entry: FeedbackEntry) -> FeedbackEntry:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def commit(self) -> None:
        await self.session.commit()
