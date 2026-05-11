# backend/src/projects/service.py
"""Project 서비스 — AsyncSession import 금지. 단일 도메인 CRUD만."""
import uuid
from datetime import datetime

from src.projects.exceptions import ProjectNotFoundError
from src.projects.models import Project
from src.projects.repository import ProjectRepository


class ProjectService:
    def __init__(self, repo: ProjectRepository) -> None:
        self.repo = repo

    async def create_project(
        self,
        workspace_id: uuid.UUID,
        title: str,
        created_by_id: uuid.UUID,
        description: str | None = None,
        visibility: str = "public",
        tags: list[str] | None = None,
    ) -> dict:
        """프로젝트 생성."""
        project = Project(
            workspace_id=workspace_id,
            title=title,
            created_by_id=created_by_id,
            description=description,
            visibility=visibility,
            tags=tags or [],
        )
        project = await self.repo.save(project)
        await self.repo.commit()
        return self._to_dict(project)

    async def list_projects(
        self,
        workspace_id: uuid.UUID,
        status: str | None = None,
        tag: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """워크스페이스 프로젝트 목록 (페이지네이션)."""
        offset = (page - 1) * page_size
        projects = await self.repo.find_by_workspace(
            workspace_id, status=status, tag=tag, offset=offset, limit=page_size
        )
        total = await self.repo.count_by_workspace(workspace_id, status=status)

        return {
            "items": [self._to_dict(p) for p in projects],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "hasNext": page * page_size < total,
        }

    async def get_project(self, project_id: uuid.UUID) -> dict:
        """프로젝트 상세."""
        project = await self.repo.find_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError()
        return self._to_dict(project)

    async def update_project(
        self,
        project_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        visibility: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """프로젝트 수정."""
        project = await self.repo.find_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError()

        if title is not None:
            project.title = title
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status
        if visibility is not None:
            project.visibility = visibility
        if tags is not None:
            project.tags = tags

        project.updated_at = datetime.utcnow()
        project = await self.repo.save(project)
        await self.repo.commit()
        return self._to_dict(project)

    async def delete_project(self, project_id: uuid.UUID) -> None:
        """프로젝트 삭제."""
        project = await self.repo.find_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError()
        await self.repo.delete(project)
        await self.repo.commit()

    async def archive_project(self, project_id: uuid.UUID) -> dict:
        """프로젝트 아카이브 (status → archived)."""
        return await self.update_project(project_id, status="archived")

    async def add_meeting_project(
        self, meeting_id: uuid.UUID, project_id: uuid.UUID
    ) -> dict:
        """회의-프로젝트 연결."""
        # 프로젝트 존재 확인
        project = await self.repo.find_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError()

        link = await self.repo.add_meeting_link(meeting_id, project_id)
        await self.repo.commit()
        return {
            "id": str(link.id),
            "meetingId": str(link.meeting_id),
            "projectId": str(link.project_id),
        }

    async def remove_meeting_project(
        self, meeting_id: uuid.UUID, project_id: uuid.UUID
    ) -> None:
        """회의-프로젝트 연결 해제."""
        await self.repo.remove_meeting_link(meeting_id, project_id)
        await self.repo.commit()

    async def get_meeting_projects(
        self, meeting_id: uuid.UUID
    ) -> list[dict]:
        """회의에 연결된 프로젝트 목록."""
        projects = await self.repo.find_projects_by_meeting(meeting_id)
        return [self._to_dict(p) for p in projects]

    @staticmethod
    def _to_dict(project: Project) -> dict:
        """Project → camelCase dict 변환."""
        return {
            "id": str(project.id),
            "workspaceId": str(project.workspace_id),
            "title": project.title,
            "description": project.description,
            "status": project.status,
            "visibility": project.visibility,
            "tags": project.tags,
            "sortOrder": project.sort_order,
            "createdById": str(project.created_by_id),
            "createdAt": project.created_at.isoformat(),
            "updatedAt": project.updated_at.isoformat(),
        }
