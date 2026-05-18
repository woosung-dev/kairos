# backend/src/actions/service.py
"""ActionItem 서비스 — AsyncSession import 금지. 단일 도메인 CRUD.

헌법 I-9 (Sprint 19 PR #1, Codex F-1): 모든 메서드 workspace_id 필수.
Codex F-2 Critical: create / update 시 project_id / meeting_id / assignee_id secondary FK
cross-workspace 거부 (3건 가장 큰 분량).
"""
import uuid
from datetime import date, datetime

from src.actions.exceptions import ActionItemNotFoundError
from src.actions.models import ActionItem
from src.actions.repository import ActionItemRepository
from src.common.exceptions import NotFoundError
from src.meetings.exceptions import MeetingNotFoundError
from src.meetings.repository import MeetingRepository
from src.projects.exceptions import ProjectNotFoundError
from src.projects.repository import ProjectRepository
from src.workspaces.repository import WorkspaceRepository


class ActionItemService:
    def __init__(
        self,
        repo: ActionItemRepository,
        project_repo: ProjectRepository | None = None,
        meeting_repo: MeetingRepository | None = None,
        workspace_repo: WorkspaceRepository | None = None,
    ) -> None:
        self.repo = repo
        # Codex F-2 Critical: 3 secondary FK cross-tenant 검증용
        self.project_repo = project_repo
        self.meeting_repo = meeting_repo
        self.workspace_repo = workspace_repo

    async def _verify_secondary_fks(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None,
        meeting_id: uuid.UUID | None,
        assignee_id: uuid.UUID | None,
    ) -> None:
        """Codex F-2: 3 secondary FK 모두 같은 workspace 인지 검증.

        Codex 2차 Minor 1 (C7): fail-closed — FK 가 들어왔는데 검증 repo 미주입이면
        silent skip 대신 RuntimeError 로 차단 (테스트 사고 방지).
        """
        if project_id is not None:
            if self.project_repo is None:
                raise RuntimeError("project_repo 필수 (F-2 검증)")
            project = await self.project_repo.find_by_id(project_id)
            if project is None or project.workspace_id != workspace_id:
                raise ProjectNotFoundError()
        if meeting_id is not None:
            if self.meeting_repo is None:
                raise RuntimeError("meeting_repo 필수 (F-2 검증)")
            # MeetingRepository.find_by_id 가 이미 workspace_id 시그니처 (Sprint 19 PR #1 commit C1)
            meeting = await self.meeting_repo.find_by_id(meeting_id, workspace_id)
            if meeting is None:
                raise MeetingNotFoundError()
        if assignee_id is not None:
            if self.workspace_repo is None:
                raise RuntimeError("workspace_repo 필수 (F-2 검증)")
            member = await self.workspace_repo.find_member(workspace_id, assignee_id)
            if member is None:
                raise NotFoundError("워크스페이스 멤버")

    async def create_action_item(
        self,
        workspace_id: uuid.UUID,
        title: str,
        description: str | None = None,
        meeting_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        assignee_id: uuid.UUID | None = None,
        due_date: date | None = None,
        priority: str = "medium",
    ) -> dict:
        """액션 아이템 생성. Codex F-2: 3 secondary FK 검증 후 INSERT."""
        await self._verify_secondary_fks(workspace_id, project_id, meeting_id, assignee_id)
        item = ActionItem(
            workspace_id=workspace_id,
            title=title,
            description=description,
            meeting_id=meeting_id,
            project_id=project_id,
            assignee_id=assignee_id,
            due_date=due_date,
            priority=priority,
        )
        item = await self.repo.save(item)
        await self.repo.commit()
        return self._to_dict(item)

    async def list_action_items(
        self,
        workspace_id: uuid.UUID,
        status: str | None = None,
        priority: str | None = None,
        project_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """워크스페이스 액션 아이템 목록 (페이지네이션)."""
        offset = (page - 1) * page_size
        items = await self.repo.find_by_workspace(
            workspace_id,
            status=status,
            priority=priority,
            project_id=project_id,
            offset=offset,
            limit=page_size,
        )
        total = await self.repo.count_by_workspace(workspace_id, status=status)

        return {
            "items": [self._to_dict(i) for i in items],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "hasNext": page * page_size < total,
        }

    async def update_action_item(
        self,
        action_id: uuid.UUID,
        workspace_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        project_id: uuid.UUID | None = None,
        assignee_id: uuid.UUID | None = None,
        meeting_id: uuid.UUID | None = None,
        due_date: date | None = None,
        priority: str | None = None,
        status: str | None = None,
    ) -> dict:
        """액션 아이템 수정. 헌법 I-9 (Codex F-1) + Codex F-2 Critical 3 secondary FK 검증."""
        item = await self.repo.find_by_id(action_id, workspace_id)
        if item is None:
            raise ActionItemNotFoundError()

        # Codex F-2: 3 secondary FK 변경 요청 시 cross-workspace 거부
        await self._verify_secondary_fks(workspace_id, project_id, meeting_id, assignee_id)

        if title is not None:
            item.title = title
        if description is not None:
            item.description = description
        if project_id is not None:
            item.project_id = project_id
        if assignee_id is not None:
            item.assignee_id = assignee_id
        if meeting_id is not None:
            item.meeting_id = meeting_id
        if due_date is not None:
            item.due_date = due_date
        if priority is not None:
            item.priority = priority
        if status is not None:
            item.status = status

        item.updated_at = datetime.utcnow()
        item = await self.repo.save(item)
        await self.repo.commit()
        return self._to_dict(item)

    @staticmethod
    def _to_dict(item: ActionItem) -> dict:
        """ActionItem → camelCase dict 변환."""
        return {
            "id": str(item.id),
            "workspaceId": str(item.workspace_id),
            "meetingId": str(item.meeting_id) if item.meeting_id else None,
            "projectId": str(item.project_id) if item.project_id else None,
            "title": item.title,
            "description": item.description,
            "assigneeId": str(item.assignee_id) if item.assignee_id else None,
            "dueDate": item.due_date.isoformat() if item.due_date else None,
            "priority": item.priority,
            "status": item.status,
            "createdAt": item.created_at.isoformat(),
            "updatedAt": item.updated_at.isoformat(),
        }
