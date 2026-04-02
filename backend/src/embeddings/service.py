# backend/src/embeddings/service.py
"""임베딩 서비스 — 청킹 + OpenAI 임베딩 생성 + 저장."""
import logging
import uuid

from openai import AsyncOpenAI

from src.core.config import get_settings
from src.embeddings.models import EmbeddingChunk
from src.embeddings.repository import EmbeddingRepository

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, repo: EmbeddingRepository) -> None:
        self.repo = repo
        settings = get_settings()
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    # --- 청킹 ---

    @staticmethod
    def _chunk_text(
        text: str, max_chars: int = 500, overlap_chars: int = 50
    ) -> list[str]:
        """텍스트를 max_chars 단위로 분할, overlap_chars 오버랩."""
        if len(text) <= max_chars:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + max_chars
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap_chars
        return chunks

    @staticmethod
    def _group_segments_by_speaker(
        segments: list[dict],
    ) -> list[dict]:
        """연속 화자 세그먼트를 그룹핑 → Level 1 단위."""
        if not segments:
            return []

        groups: list[dict] = []
        current = {
            "speaker": segments[0].get("speaker", "Unknown"),
            "text": segments[0].get("text", ""),
            "start_sec": segments[0].get("start_sec", 0),
            "end_sec": segments[0].get("end_sec", 0),
        }

        for seg in segments[1:]:
            if seg.get("speaker") == current["speaker"]:
                current["text"] += seg.get("text", "")
                current["end_sec"] = seg.get("end_sec", 0)
            else:
                groups.append(current)
                current = {
                    "speaker": seg.get("speaker", "Unknown"),
                    "text": seg.get("text", ""),
                    "start_sec": seg.get("start_sec", 0),
                    "end_sec": seg.get("end_sec", 0),
                }

        groups.append(current)
        return groups

    # --- 임베딩 생성 ---

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """OpenAI text-embedding-3-small batch 호출."""
        if not texts:
            return []

        response = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        return [item.embedding for item in response.data]

    # --- 회의 임베딩 ---

    async def embed_meeting(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None,
        title: str,
        segments: list[dict],
    ) -> int:
        """회의 트랜스크립트 → 계층적 청크 → 임베딩 저장. 생성된 청크 수 반환."""
        await self.repo.delete_by_source("meeting", meeting_id)

        full_text = " ".join(seg.get("text", "") for seg in segments)
        if not full_text.strip():
            return 0

        speaker_groups = self._group_segments_by_speaker(segments)

        all_chunks: list[EmbeddingChunk] = []
        texts_to_embed: list[str] = []

        for group_idx, group in enumerate(speaker_groups):
            # Level 1 청크 (화자 구간)
            level1_id = uuid.uuid4()
            level1_chunk = EmbeddingChunk(
                id=level1_id,
                workspace_id=workspace_id,
                project_id=project_id,
                source_id=meeting_id,
                source_type="meeting",
                chunk_text=group["text"],
                chunk_index=group_idx,
                chunk_level=1,
                parent_chunk_id=None,
                metadata_json={
                    "speaker": group["speaker"],
                    "start_sec": group["start_sec"],
                    "end_sec": group["end_sec"],
                    "title": title,
                },
            )
            all_chunks.append(level1_chunk)
            texts_to_embed.append(group["text"])

            # Level 2 청크 (문단)
            paragraphs = self._chunk_text(group["text"])
            for para_idx, para_text in enumerate(paragraphs):
                level2_chunk = EmbeddingChunk(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    source_id=meeting_id,
                    source_type="meeting",
                    chunk_text=para_text,
                    chunk_index=para_idx,
                    chunk_level=2,
                    parent_chunk_id=level1_id,
                    metadata_json={
                        "speaker": group["speaker"],
                        "start_sec": group["start_sec"],
                        "end_sec": group["end_sec"],
                        "title": title,
                    },
                )
                all_chunks.append(level2_chunk)
                texts_to_embed.append(para_text)

        # 배치 임베딩 생성
        embeddings = await self.generate_embeddings(texts_to_embed)
        for chunk, emb in zip(all_chunks, embeddings):
            chunk.embedding = emb

        await self.repo.save_chunks(all_chunks)
        await self.repo.commit()

        logger.info(f"회의 {meeting_id} 임베딩 완료: {len(all_chunks)}개 청크")
        return len(all_chunks)

    # --- 노트 임베딩 ---

    async def embed_note(
        self,
        note_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None,
        title: str,
        plain_text: str,
    ) -> int:
        """노트 plain_text → 청크 → 임베딩 저장. 생성된 청크 수 반환."""
        await self.repo.delete_by_source("note", note_id)

        if not plain_text.strip():
            return 0

        all_chunks: list[EmbeddingChunk] = []
        texts_to_embed: list[str] = []

        # Level 1: 노트 전체 (단일)
        level1_id = uuid.uuid4()
        level1_chunk = EmbeddingChunk(
            id=level1_id,
            workspace_id=workspace_id,
            project_id=project_id,
            source_id=note_id,
            source_type="note",
            chunk_text=plain_text,
            chunk_index=0,
            chunk_level=1,
            parent_chunk_id=None,
            metadata_json={"title": title},
        )
        all_chunks.append(level1_chunk)
        texts_to_embed.append(plain_text)

        # Level 2: 문단 청크
        paragraphs = self._chunk_text(plain_text)
        for para_idx, para_text in enumerate(paragraphs):
            level2_chunk = EmbeddingChunk(
                workspace_id=workspace_id,
                project_id=project_id,
                source_id=note_id,
                source_type="note",
                chunk_text=para_text,
                chunk_index=para_idx,
                chunk_level=2,
                parent_chunk_id=level1_id,
                metadata_json={"title": title},
            )
            all_chunks.append(level2_chunk)
            texts_to_embed.append(para_text)

        embeddings = await self.generate_embeddings(texts_to_embed)
        for chunk, emb in zip(all_chunks, embeddings):
            chunk.embedding = emb

        await self.repo.save_chunks(all_chunks)
        await self.repo.commit()

        logger.info(f"노트 {note_id} 임베딩 완료: {len(all_chunks)}개 청크")
        return len(all_chunks)

    # --- 캐시 무효화 ---

    async def invalidate_cache(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> None:
        """새 임베딩 생성 시 관련 시맨틱 캐시 삭제."""
        await self.repo.delete_caches(workspace_id, project_id)
        await self.repo.commit()
