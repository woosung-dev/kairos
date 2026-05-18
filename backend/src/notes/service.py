# backend/src/notes/service.py
"""노트 비즈니스 로직 — 순수 노트 CRUD (ADR-014 옵션 A: embedding 의존 제거).

embeddings.service 호출은 NotePipelineService(orchestrator) 내부에서만 수행 — 헌법 §4.2 정합.
헌법 I-9 (Sprint 19 PR #1, Codex F-1): 모든 메서드 workspace_id 필수.
Codex F-2 (Critical): create/update 시 project_id cross-workspace 검증 (secondary FK).
"""
import json
import uuid
from datetime import datetime

from src.notes.exceptions import NoteNotFoundError
from src.notes.models import Note
from src.notes.repository import NoteRepository
from src.projects.exceptions import ProjectNotFoundError
from src.projects.repository import ProjectRepository


def extract_plain_text(tiptap_json: dict) -> str:
    """Tiptap JSON에서 텍스트만 재귀 추출."""
    texts: list[str] = []
    for node in tiptap_json.get("content", []):
        if "text" in node:
            texts.append(node["text"])
        if "content" in node:
            texts.append(extract_plain_text(node))
    return "\n".join(filter(None, texts))


class NoteService:
    def __init__(
        self,
        repo: NoteRepository,
        project_repo: ProjectRepository | None = None,
    ) -> None:
        self.repo = repo
        # Codex F-2: project_id secondary FK cross-tenant 검증용
        self.project_repo = project_repo

    async def _verify_project_in_workspace(
        self, project_id: uuid.UUID | None, workspace_id: uuid.UUID
    ) -> None:
        """Codex F-2: project_id 가 같은 workspace 인지 검증. None 이면 통과."""
        if project_id is None:
            return
        if self.project_repo is None:
            return
        project = await self.project_repo.find_by_id(project_id)
        if project is None or project.workspace_id != workspace_id:
            raise ProjectNotFoundError()

    async def create_note(
        self,
        workspace_id: uuid.UUID,
        created_by_id: uuid.UUID,
        title: str = "",
        content: dict | None = None,
        project_id: uuid.UUID | None = None,
    ) -> dict:
        # Codex F-2: cross-workspace project_id 거부
        await self._verify_project_in_workspace(project_id, workspace_id)
        plain_text = extract_plain_text(content) if content else ""
        note = Note(
            workspace_id=workspace_id,
            project_id=project_id,
            title=title,
            content=content or {},
            plain_text=plain_text,
            created_by_id=created_by_id,
        )
        note = await self.repo.save(note)
        await self.repo.commit()
        return self._to_dict(note)

    async def list_notes(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        offset = (page - 1) * page_size
        notes = await self.repo.find_by_workspace(
            workspace_id, project_id=project_id, offset=offset, limit=page_size
        )
        total = await self.repo.count_by_workspace(
            workspace_id, project_id=project_id
        )
        return {
            "items": [self._to_dict(n) for n in notes],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "hasNext": page * page_size < total,
        }

    async def get_note(
        self, note_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> dict:
        """헌법 I-9 (Codex F-1): workspace_id 필수."""
        note = await self.repo.find_by_id(note_id, workspace_id)
        if note is None:
            raise NoteNotFoundError()
        return self._to_dict(note)

    async def update_note(
        self,
        note_id: uuid.UUID,
        workspace_id: uuid.UUID,
        title: str | None = None,
        content: dict | None = None,
        project_id: uuid.UUID | None = ...,  # type: ignore[assignment]
    ) -> dict:
        """헌법 I-9 (Codex F-1) + Codex F-2 Critical: project_id cross-workspace 거부."""
        note = await self.repo.find_by_id(note_id, workspace_id)
        if note is None:
            raise NoteNotFoundError()

        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
            note.plain_text = extract_plain_text(content)
        if project_id is not ...:
            # Codex F-2: 새 project_id 가 같은 workspace 인지 검증
            await self._verify_project_in_workspace(project_id, workspace_id)
            note.project_id = project_id  # type: ignore[assignment]

        note.updated_at = datetime.utcnow()
        note = await self.repo.save(note)
        await self.repo.commit()
        return self._to_dict(note)

    async def delete_note(
        self, note_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """노트 삭제 (순수). embedding cleanup은 NotePipelineService 책임."""
        note = await self.repo.find_by_id(note_id, workspace_id)
        if note is None:
            raise NoteNotFoundError()
        await self.repo.delete(note)
        await self.repo.commit()

    async def export_note(
        self, note_id: uuid.UUID, workspace_id: uuid.UUID, fmt: str
    ) -> tuple[str, str, str]:
        """노트 내보내기. (content, filename, media_type) 반환."""
        note = await self.repo.find_by_id(note_id, workspace_id)
        if note is None:
            raise NoteNotFoundError()

        title = note.title or "Untitled"

        if fmt == "md":
            content = f"# {title}\n\n{note.plain_text}"
            return content, f"{title}.md", "text/markdown; charset=utf-8"
        else:
            data = {
                "id": str(note.id),
                "title": title,
                "content": note.content,
                "plainText": note.plain_text,
                "createdAt": note.created_at.isoformat(),
                "updatedAt": note.updated_at.isoformat(),
            }
            content = json.dumps(data, ensure_ascii=False, indent=2)
            return content, f"{title}.json", "application/json; charset=utf-8"

    @staticmethod
    def _to_dict(note: Note) -> dict:
        return {
            "id": str(note.id),
            "workspaceId": str(note.workspace_id),
            "projectId": str(note.project_id) if note.project_id else None,
            "title": note.title,
            "content": note.content,
            "plainText": note.plain_text,
            "createdById": str(note.created_by_id),
            "createdAt": note.created_at.isoformat(),
            "updatedAt": note.updated_at.isoformat(),
        }
