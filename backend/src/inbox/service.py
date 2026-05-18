# backend/src/inbox/service.py
"""Inbox 서비스 — 크로스 레포지토리 (InboxRepo + ProjectRepo)."""
import uuid
from datetime import datetime

from src.inbox.exceptions import InboxItemNotFoundError
from src.inbox.models import InboxItem
from src.inbox.repository import InboxRepository
from src.projects.exceptions import ProjectNotFoundError
from src.projects.repository import ProjectRepository


class InboxService:
    def __init__(
        self,
        inbox_repo: InboxRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self.inbox_repo = inbox_repo
        self.project_repo = project_repo

    async def list_inbox(
        self,
        workspace_id: uuid.UUID,
        is_processed: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """워크스페이스 Inbox 목록 (페이지네이션)."""
        offset = (page - 1) * page_size
        items = await self.inbox_repo.find_by_workspace(
            workspace_id, is_processed=is_processed, offset=offset, limit=page_size
        )
        total = await self.inbox_repo.count_by_workspace(
            workspace_id, is_processed=is_processed
        )

        return {
            "items": [self._to_dict(item) for item in items],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "hasNext": page * page_size < total,
        }

    async def classify(
        self,
        inbox_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_ids: list[uuid.UUID],
    ) -> dict:
        """Inbox 아이템을 프로젝트에 연결 확정.

        헌법 I-9 (Codex F-1): workspace_id 필수.
        Codex F-2 Critical: project_ids 모두 같은 workspace 내인지 사전 검증.
        """
        item = await self.inbox_repo.find_by_id(inbox_id, workspace_id)
        if item is None:
            raise InboxItemNotFoundError()

        # Codex F-2 Critical: project_ids 모두 같은 workspace 인지 사전 검증
        # (add_meeting_link 가 cross-workspace meeting/project 링크 생성하는 것 차단)
        verified_projects: list = []
        for project_id in project_ids:
            project = await self.project_repo.find_by_id(project_id)
            if project is None or project.workspace_id != workspace_id:
                raise ProjectNotFoundError()
            verified_projects.append(project)

        item.is_processed = True
        item.updated_at = datetime.utcnow()
        await self.inbox_repo.save(item)

        # source_type 이 "meeting" 이면 → 각 프로젝트에 회의 연결
        linked_projects: list[dict] = []
        if item.source_type == "meeting":
            for project in verified_projects:
                await self.project_repo.add_meeting_link(item.source_id, project.id)
                linked_projects.append(
                    {"id": str(project.id), "title": project.title}
                )

        # 동일 session 이므로 한 번만 commit
        await self.inbox_repo.commit()

        result = self._to_dict(item)
        result["linkedProjects"] = linked_projects
        return result

    async def dismiss(
        self, inbox_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> dict:
        """Inbox 아이템 무시 처리. 헌법 I-9 workspace_id 필수 (Codex F-1)."""
        item = await self.inbox_repo.find_by_id(inbox_id, workspace_id)
        if item is None:
            raise InboxItemNotFoundError()

        item.is_processed = True
        item.updated_at = datetime.utcnow()
        await self.inbox_repo.save(item)
        await self.inbox_repo.commit()

        return self._to_dict(item)

    @staticmethod
    def _to_dict(item: InboxItem) -> dict:
        """InboxItem → camelCase dict 변환."""
        return {
            "id": str(item.id),
            "workspaceId": str(item.workspace_id),
            "title": item.title,
            "summary": item.summary,
            "sourceType": item.source_type,
            "sourceId": str(item.source_id),
            "aiSuggestedProjectId": (
                str(item.ai_suggested_project_id)
                if item.ai_suggested_project_id
                else None
            ),
            "aiSuggestedProjectTitle": item.ai_suggested_project_title,
            "aiSuggestedTags": item.ai_suggested_tags,
            "aiConfidence": item.ai_confidence,
            "isProcessed": item.is_processed,
            "createdAt": item.created_at.isoformat(),
            "updatedAt": item.updated_at.isoformat(),
        }
