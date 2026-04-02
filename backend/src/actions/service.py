# backend/src/actions/service.py
"""ActionItem 서비스 — AsyncSession import 금지. 단일 도메인 CRUD만."""
import uuid
from datetime import date, datetime

from src.actions.exceptions import ActionItemNotFoundError
from src.actions.models import ActionItem
from src.actions.repository import ActionItemRepository


class ActionItemService:
    def __init__(self, repo: ActionItemRepository) -> None:
        self.repo = repo

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
        """액션 아이템 생성."""
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
        title: str | None = None,
        description: str | None = None,
        project_id: uuid.UUID | None = None,
        assignee_id: uuid.UUID | None = None,
        due_date: date | None = None,
        priority: str | None = None,
        status: str | None = None,
    ) -> dict:
        """액션 아이템 수정."""
        item = await self.repo.find_by_id(action_id)
        if item is None:
            raise ActionItemNotFoundError()

        if title is not None:
            item.title = title
        if description is not None:
            item.description = description
        if project_id is not None:
            item.project_id = project_id
        if assignee_id is not None:
            item.assignee_id = assignee_id
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
