# backend/src/notes/service.py
"""노트 비즈니스 로직."""
import uuid
from datetime import datetime

from src.embeddings.service import EmbeddingService
from src.notes.exceptions import NoteNotFoundError
from src.notes.models import Note
from src.notes.repository import NoteRepository


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
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.repo = repo
        self.embedding_service = embedding_service

    async def create_note(
        self,
        workspace_id: uuid.UUID,
        created_by_id: uuid.UUID,
        title: str = "",
        content: dict | None = None,
        project_id: uuid.UUID | None = None,
    ) -> dict:
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

    async def get_note(self, note_id: uuid.UUID) -> dict:
        note = await self.repo.find_by_id(note_id)
        if note is None:
            raise NoteNotFoundError()
        return self._to_dict(note)

    async def update_note(
        self,
        note_id: uuid.UUID,
        title: str | None = None,
        content: dict | None = None,
        project_id: uuid.UUID | None = ...,  # type: ignore[assignment]
    ) -> dict:
        note = await self.repo.find_by_id(note_id)
        if note is None:
            raise NoteNotFoundError()

        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
            note.plain_text = extract_plain_text(content)
        if project_id is not ...:
            note.project_id = project_id  # type: ignore[assignment]

        note.updated_at = datetime.utcnow()
        note = await self.repo.save(note)
        await self.repo.commit()
        return self._to_dict(note)

    async def delete_note(self, note_id: uuid.UUID) -> None:
        note = await self.repo.find_by_id(note_id)
        if note is None:
            raise NoteNotFoundError()

        if self.embedding_service:
            await self.embedding_service.repo.delete_by_source("note", note_id)

        await self.repo.delete(note)
        await self.repo.commit()

    async def embed_note_async(self, note_id: uuid.UUID) -> None:
        """BackgroundTasks용 임베딩 생성."""
        if not self.embedding_service:
            return
        note = await self.repo.find_by_id(note_id)
        if not note or not note.plain_text:
            return
        await self.embedding_service.embed_note(
            note_id=note.id,
            workspace_id=note.workspace_id,
            project_id=note.project_id,
            title=note.title,
            plain_text=note.plain_text,
        )
        await self.embedding_service.invalidate_cache(
            note.workspace_id, note.project_id
        )

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
