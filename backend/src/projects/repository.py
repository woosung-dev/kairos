# backend/src/projects/repository.py
"""Project Repository — AsyncSession 유일 보유자.

Sprint 19 PR #1 C9 (Codex F-1/F-3): 헌법 I-9 강제.
모든 find/mutation 메서드가 workspace_id 명시 파라미터 + WHERE 절 적용.
add_meeting_link / remove_meeting_link / find_projects_by_meeting 는
MeetingProjectLink 에 workspace_id 컬럼이 없으므로 (PR #2 분리) Project
join + WHERE Project.workspace_id 로 사전 tenant 검증.
"""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import and_, delete, exists, func, or_, select

from src.projects.exceptions import ProjectNotFoundError
from src.projects.models import MeetingProjectLink, Project, ProjectMember


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(
        self, project_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> Project | None:
        """헌법 I-9 (Codex F-1): project_id + workspace_id 동시 필터."""
        return (await self.session.exec(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
        )).one_or_none()

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
        return list((await self.session.exec(stmt)).all())

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
        return (await self.session.exec(stmt)).one()

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

    # --- ProjectMember (Sprint 6 L-6, Sprint 19 PR #1 C9 workspace_id 강제) ---

    async def find_members(
        self, project_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> list[ProjectMember]:
        """헌법 I-9 (Codex F-1): project_members 도 workspace_id 필터."""
        stmt = (
            select(ProjectMember)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.workspace_id == workspace_id,
            )
            .order_by(ProjectMember.created_at)
        )
        return list((await self.session.exec(stmt)).all())

    async def is_member(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        """헌법 I-9 (Codex F-1): is_member 도 workspace_id 필터."""
        stmt = select(ProjectMember.id).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
            ProjectMember.workspace_id == workspace_id,
        )
        return (await self.session.exec(stmt)).one_or_none() is not None

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
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        """헌법 I-9 (Codex F-1/F-5): mutation 도 workspace_id WHERE."""
        await self.session.exec(
            delete(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
                ProjectMember.workspace_id == workspace_id,
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

    # --- Meeting-Project Link (PR #1 C9: project tenant 사전 검증) ---

    async def add_meeting_link(
        self,
        meeting_id: uuid.UUID,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> MeetingProjectLink:
        """헌법 I-9 (Codex F-1/F-3): project 가 workspace 소속인지 사전 검증.

        Sprint 19 PR #2 D6 (BUG-C01-EXT-FK / 헌법 I-9 (10)): MeetingProjectLink 에 workspace_id 컬럼 신설.
        composite FK (workspace_id, project_id) + (workspace_id, meeting_id) 가 DB-level 차단.
        """
        project = await self.find_by_id(project_id, workspace_id)
        if project is None:
            raise ProjectNotFoundError()
        # Sprint 29 R1 (inbox-IB5): 재분류 멱등성 — 동일 (meeting_id, project_id) 링크가
        # 이미 있으면 no-op 으로 기존 행 반환. uq_meeting_project 위반(IntegrityError → 500)
        # 회피 + IB-5 idempotent 불변식 충족. meeting↔project 는 many-to-many 이므로
        # 같은 meeting 의 타 프로젝트 링크는 정상 생성된다.
        existing = (await self.session.exec(
            select(MeetingProjectLink).where(
                MeetingProjectLink.meeting_id == meeting_id,
                MeetingProjectLink.project_id == project_id,
                MeetingProjectLink.workspace_id == workspace_id,
            )
        )).one_or_none()
        if existing is not None:
            return existing
        link = MeetingProjectLink(
            meeting_id=meeting_id, project_id=project_id, workspace_id=workspace_id
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def remove_meeting_link(
        self,
        meeting_id: uuid.UUID,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        """헌법 I-9 (Codex F-1/F-3 + v2 F-7): 사전 project tenant 검증 + mutation WHERE workspace_id."""
        project = await self.find_by_id(project_id, workspace_id)
        if project is None:
            raise ProjectNotFoundError()
        await self.session.exec(
            delete(MeetingProjectLink).where(
                MeetingProjectLink.meeting_id == meeting_id,
                MeetingProjectLink.project_id == project_id,
                # Sprint 19 PR #2 D6 (Codex v2 F-7): mutation 도 workspace_id anchor (헌법 I-9 (2))
                MeetingProjectLink.workspace_id == workspace_id,
            )
        )
        await self.session.flush()

    async def find_projects_by_meeting(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> list[Project]:
        """헌법 I-9 (Codex F-1 + v2 F-7): JOIN + WHERE workspace_id 강제 (mpl + project 양쪽)."""
        stmt = (
            select(Project)
            .join(
                MeetingProjectLink,
                MeetingProjectLink.project_id == Project.id,
            )
            .where(
                MeetingProjectLink.meeting_id == meeting_id,
                # Sprint 19 PR #2 D6 (Codex v2 F-7): mpl 측도 workspace_id anchor (헌법 I-9 (1))
                MeetingProjectLink.workspace_id == workspace_id,
                Project.workspace_id == workspace_id,
            )
            .order_by(Project.sort_order, Project.created_at.desc())
        )
        return list((await self.session.exec(stmt)).all())
