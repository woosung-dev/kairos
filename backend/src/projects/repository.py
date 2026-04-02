# backend/src/projects/repository.py
"""Project Repository — AsyncSession 유일 보유자."""
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.projects.models import MeetingProjectLink, Project


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, project_id: uuid.UUID) -> Project | None:
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        status: str | None = None,
        tag: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Project]:
        stmt = select(Project).where(Project.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(Project.status == status)
        if tag:
            # JSON 배열에 태그 포함 여부 (PostgreSQL @> 연산자)
            stmt = stmt.where(Project.tags.contains([tag]))
        stmt = stmt.order_by(Project.sort_order, Project.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        status: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Project)
            .where(Project.workspace_id == workspace_id)
        )
        if status:
            stmt = stmt.where(Project.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def save(self, project: Project) -> Project:
        self.session.add(project)
        await self.session.flush()
        return project

    async def delete(self, project: Project) -> None:
        await self.session.delete(project)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    # --- Meeting-Project Link ---

    async def add_meeting_link(
        self, meeting_id: uuid.UUID, project_id: uuid.UUID
    ) -> MeetingProjectLink:
        link = MeetingProjectLink(meeting_id=meeting_id, project_id=project_id)
        self.session.add(link)
        await self.session.flush()
        return link

    async def remove_meeting_link(
        self, meeting_id: uuid.UUID, project_id: uuid.UUID
    ) -> None:
        await self.session.execute(
            delete(MeetingProjectLink).where(
                MeetingProjectLink.meeting_id == meeting_id,
                MeetingProjectLink.project_id == project_id,
            )
        )
        await self.session.flush()

    async def find_projects_by_meeting(
        self, meeting_id: uuid.UUID
    ) -> list[Project]:
        stmt = (
            select(Project)
            .join(
                MeetingProjectLink,
                MeetingProjectLink.project_id == Project.id,
            )
            .where(MeetingProjectLink.meeting_id == meeting_id)
            .order_by(Project.sort_order, Project.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
