# backend/src/projects/repository.py
"""Project Repository — AsyncSession 유일 보유자."""
import uuid

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.projects.models import MeetingProjectLink, Project, ProjectMember


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
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Project]:
        stmt = select(Project).where(Project.workspace_id == workspace_id)
        stmt = self._apply_visibility_filter(stmt, requester_user_id, requester_role)
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
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
        status: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Project)
            .where(Project.workspace_id == workspace_id)
        )
        stmt = self._apply_visibility_filter(stmt, requester_user_id, requester_role)
        if status:
            stmt = stmt.where(Project.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    def _apply_visibility_filter(
        stmt,
        requester_user_id: uuid.UUID | None,
        requester_role: str | None,
    ):
        """visibility 권한 분기 (Sprint 6 ADR-014 옵션 A 정합).

        - admin/owner: 모든 visibility 접근 가능 (필터 없음)
        - member/viewer (또는 requester 정보 없음): visibility 별 분기
          * public: 모두 접근
          * draft: creator만 접근 (AD-24)
          * private: ProjectMember 매핑된 사람만 (L-6)
        """
        # admin 이상은 필터 우회 (모든 visibility 접근)
        if requester_role in ("admin", "owner"):
            return stmt
        # requester 정보 없음 = 보수적으로 public만 노출
        if requester_user_id is None:
            return stmt.where(Project.visibility == "public")
        # member/viewer: public + draft(creator) + private(ProjectMember)
        member_exists = (
            exists()
            .where(
                and_(
                    ProjectMember.project_id == Project.id,
                    ProjectMember.user_id == requester_user_id,
                )
            )
        )
        return stmt.where(
            or_(
                Project.visibility == "public",
                and_(
                    Project.visibility == "draft",
                    Project.created_by_id == requester_user_id,
                ),
                and_(
                    Project.visibility == "private",
                    member_exists,
                ),
            )
        )

    # --- ProjectMember (Sprint 6 L-6) ---

    async def find_members(
        self, project_id: uuid.UUID
    ) -> list[ProjectMember]:
        stmt = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def is_member(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        stmt = select(ProjectMember.id).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def add_member(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "member",
    ) -> ProjectMember:
        member = ProjectMember(
            project_id=project_id, workspace_id=workspace_id, user_id=user_id, role=role
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def remove_member(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        await self.session.execute(
            delete(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        await self.session.flush()

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
