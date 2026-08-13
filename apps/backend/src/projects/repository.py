# backend/src/projects/repository.py
"""Project Repository — AsyncSession 유일 보유자.

Sprint 19 PR #1 C9 (Codex F-1/F-3): 헌법 I-9 강제.
모든 find/mutation 메서드가 workspace_id 명시 파라미터 + WHERE 절 적용.
add_meeting_link / remove_meeting_link / find_projects_by_meeting 는
MeetingProjectLink 에 workspace_id 컬럼이 없으므로 (PR #2 분리) Project
join + WHERE Project.workspace_id 로 사전 tenant 검증.
"""
import uuid

from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import and_, delete, exists, func, select

from src.common.visibility import RequesterContext, apply_project_visibility
from src.projects.exceptions import ProjectNotFoundError
from src.projects.models import MeetingProjectLink, Project, ProjectMember


def _tag_contains(tag: str):
    """JSON 배열 tags 에 태그 포함 여부 (PostgreSQL @> 연산자).

    PR-2 c1 fix: sa_type=JSON 컬럼의 .contains() 는 문자열 LIKE(`json ~~ text`)로
    컴파일돼 실 Postgres 에서 UndefinedFunctionError 500 — JSONB cast 후 @> 적용.
    """
    from sqlalchemy import cast
    from sqlalchemy.dialects.postgresql import JSONB

    return cast(Project.tags, JSONB).contains([tag])


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
            stmt = stmt.where(_tag_contains(tag))
        stmt = stmt.order_by(Project.sort_order, Project.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        return list((await self.session.exec(stmt)).all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
        status: str | None = None,
        tag: str | None = None,
    ) -> int:
        """count 는 find_by_workspace 와 동일 필터 계약 (PR-2 c1 — 이전엔
        tag 를 못 받아 태그 필터된 list 와 total/hasNext 가 불일치)."""
        stmt = (
            select(func.count())
            .select_from(Project)
            .where(Project.workspace_id == workspace_id)
        )
        stmt = self._apply_visibility_filter(stmt, requester_user_id, requester_role)
        if status:
            stmt = stmt.where(Project.status == status)
        if tag:
            stmt = stmt.where(_tag_contains(tag))
        return (await self.session.exec(stmt)).one()

    @staticmethod
    def _apply_visibility_filter(
        stmt,
        requester_user_id: uuid.UUID | None,
        requester_role: str | None,
    ):
        """visibility 권한 분기 (Sprint 6 ADR-014 옵션 A 정합).

        규칙 정의는 common/visibility.py SSOT — projects 전용 어댑터 위임
        (D1: requester 부재 → public-only 보수 모드 / admin·owner 우회 /
        CAND-B ProjectMember ∧ WorkspaceMember flatten EXISTS, codex P2 보존).
        """
        return apply_project_visibility(
            stmt, RequesterContext(requester_user_id, requester_role)
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
        """헌법 I-9 (Codex F-1): is_member 도 workspace_id 필터.

        CAND-B fix — ProjectMember 행이 있어도 현 워크스페이스 멤버가 아니면 False.
        워크스페이스에서 제거된 멤버의 orphan ProjectMember 잔재가 private project
        접근을 되찾지 못하도록 차단 (offboard→re-invite privilege residue).
        """
        from src.workspaces.models import WorkspaceMember

        ws_member = (
            exists()
            .where(
                and_(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == user_id,
                )
            )
        )
        stmt = select(ProjectMember.id).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
            ProjectMember.workspace_id == workspace_id,
            ws_member,
        )
        return (await self.session.exec(stmt)).one_or_none() is not None

    async def add_member(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "member",
    ) -> ProjectMember | None:
        """F4 (2026-06-23 fullsweep): 동시 INSERT race backstop.

        이전 plain add+flush 는 동시 (project_id, user_id) INSERT 시 uq_project_member
        UNIQUE 위반 → 미처리 IntegrityError → asyncpg+greenlet MissingGreenlet → HTTP 500.
        WorkspaceMember(QA-0617-D) 와 동일하게 ON CONFLICT DO NOTHING RETURNING 으로
        race-safe. RETURNING 이 row 를 내면 INSERT 성공, 없으면 이미 멤버(충돌) → None.
        (feedback_asyncpg_greenlet_precheck: flush + try/except IntegrityError 금지)
        """
        member = ProjectMember(
            project_id=project_id, workspace_id=workspace_id, user_id=user_id, role=role
        )
        row = (await self.session.exec(
            text(
                """
                INSERT INTO project_members (id, project_id, workspace_id, user_id, role, created_at)
                VALUES (:id, :project_id, :workspace_id, :user_id, :role, :created_at)
                ON CONFLICT (project_id, user_id) DO NOTHING
                RETURNING id
                """
            ).bindparams(
                id=member.id,
                project_id=project_id,
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                created_at=member.created_at,
            )
        )).one_or_none()
        if row is None:
            return None
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

    async def count_content(
        self, project_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> tuple[int, int]:
        """BL-S27e-5: 삭제 차단 판정용 콘텐츠(노트/액션) 개수.

        notes/action_items 는 projects 도메인 비소유 테이블이라 raw count 로 조회한다.
        반환 (notes, actions). 둘 중 하나라도 >0 이면 service 가 409-block.
        """
        result = await self.session.execute(
            text(
                "SELECT "
                "(SELECT COUNT(*) FROM notes "
                " WHERE project_id = :pid AND workspace_id = :wid), "
                "(SELECT COUNT(*) FROM action_items "
                " WHERE project_id = :pid AND workspace_id = :wid)"
            ),
            {"pid": project_id, "wid": workspace_id},
        )
        notes, actions = result.one()
        return int(notes), int(actions)

    async def delete(self, project: Project) -> None:
        # BUG-PROJECT-DELETE-FK (2026-07-05 T20 발견): ondelete CASCADE 부재 + private
        # 생성 시 creator ProjectMember 자동 추가(락아웃 fix)로 join 행이 상시 존재 —
        # 같은 트랜잭션에서 join 행(멤버십/미팅 링크) 선삭제.
        await self.session.exec(
            delete(ProjectMember).where(
                ProjectMember.project_id == project.id,
                ProjectMember.workspace_id == project.workspace_id,
            )
        )
        await self.session.exec(
            delete(MeetingProjectLink).where(
                MeetingProjectLink.project_id == project.id,
                MeetingProjectLink.workspace_id == project.workspace_id,
            )
        )
        # BL-S27e-5 파생/참조 FK 정리 (비소유 테이블 → raw text, workspaces cascade 패턴).
        # notes/action_items(콘텐츠)는 service.delete_project 가 사전 count 로 409-block.
        # embeddings/caches = DELETE: 재생성 가능한 파생 인덱스 + SET NULL 시 project_id
        #   IS NULL 이 RAG visibility 필터를 무조건 통과 → private 청크 누수(헌법 위반)라
        #   삭제로 원천 차단. 캐시는 같은 논리를 workspace 전량으로 확장한다 (아래 참조).
        # inbox 제안 / promotion_audit 타깃 / 외부 문서 project = SET NULL: 항목 자체는
        #   워크스페이스에 보존하고, 죽은 프로젝트 포인터만 정리한다.
        await self.session.exec(
            text(
                "DELETE FROM embedding_chunks "
                "WHERE project_id = :pid AND workspace_id = :wid"
            ).bindparams(pid=project.id, wid=project.workspace_id)
        )
        # BL-EXT-CACHE-1 (2026-07-31 실 DB 관측): 캐시는 workspace 전량 무효화한다.
        #   project scope 로 좁히면 전역 캐시행(project_id IS NULL)이 살아남는데 그 행의
        #   sources 는 방금 지운 청크를 가리킨다. ALL_CHUNKS_VISIBLE_SQL 은 *존재하는*
        #   청크만 검사하는 anti-join 이라 사라진 id 는 위반을 만들지 못하고(fail-open)
        #   비-멤버가 삭제된 private 프로젝트 본문을 캐시 HIT 으로 받는다.
        #   프로젝트 삭제는 드문 연산이고 캐시는 재생성 가능한 파생물이라 전량 무효화가
        #   맞는 트레이드오프 — integrations 의 purge/unpublish/재동기화도 같은 결론으로
        #   delete_caches(workspace_id, None) 을 쓴다 (2026-07-31 기준).
        await self.session.exec(
            text(
                "DELETE FROM semantic_caches WHERE workspace_id = :wid"
            ).bindparams(wid=project.workspace_id)
        )
        await self.session.exec(
            text(
                "UPDATE inbox_items SET ai_suggested_project_id = NULL "
                "WHERE ai_suggested_project_id = :pid AND workspace_id = :wid"
            ).bindparams(pid=project.id, wid=project.workspace_id)
        )
        await self.session.exec(
            text(
                "UPDATE promotion_audit SET target_project_id = NULL "
                "WHERE target_project_id = :pid"
            ).bindparams(pid=project.id)
        )
        await self.session.exec(
            text(
                "UPDATE external_documents SET project_id = NULL "
                "WHERE project_id = :pid AND workspace_id = :wid"
            ).bindparams(pid=project.id, wid=project.workspace_id)
        )
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
