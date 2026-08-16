# apps/api/src/embeddings/service.py
"""임베딩 서비스 — 청킹 + OpenAI 임베딩 생성 + 저장.

I-9 4-C 진입 assertion은 `EmbeddingRepository.save_chunk` 가 강제한다.
본 서비스는 AsyncSession을 직접 보유하지 않는다 (Repository 경유).
"""
import logging
import uuid

from openai import AsyncOpenAI

from src.core.config import get_settings
from src.embeddings.models import EmbeddingChunk
from src.embeddings.repository import EmbeddingRepository

logger = logging.getLogger(__name__)

# BL-EXT-EMBED-1: 외부 문서 L1 입력 문자 상한.
# text-embedding-3-small 의 입력 상한은 8191 토큰이다. cl100k_base BPE 는 UTF-8 바이트
# 위에서 동작하므로 토큰 수는 바이트 수를 넘지 않고, 코드포인트 하나는 최대 4 바이트다
# → 토큰 수 <= 4 * 문자 수. 2000 자면 한글(3 바이트/자)·영어(1 바이트/자) 혼합 문서 어느
# 쪽이든 최악 8000 토큰으로 상한 아래에 머문다.
_EXTERNAL_L1_MAX_CHARS = 2_000

# BL-EXT-EMBED-1: 외부 문서 임베딩 요청당 입력 개수 상한.
# L2 청크는 _chunk_text 기본값상 500 자(위 환산으로 최악 2000 토큰)이므로 128 개면
# 최악 256k 토큰 — 요청당 입력 배열 한도(2048)와 토큰 한도(300k) 양쪽 아래다.
_EXTERNAL_EMBED_BATCH_SIZE = 128

# PERF-r2-2: 요청마다 AsyncOpenAI 재생성(TLS/커넥션 풀 재수립) 방지 — 모듈 싱글턴.
# 캐시 키 = 생성자 identity: 테스트가 AsyncOpenAI 를 patch 하면 자동으로 새(mock)
# 클라이언트를 만들고, patch 해제 후엔 실 클라이언트로 자가 복원 (테스트 진입점 보존).
_openai_client_cache: tuple[object, AsyncOpenAI] | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client_cache
    ctor = AsyncOpenAI
    if _openai_client_cache is None or _openai_client_cache[0] is not ctor:
        settings = get_settings()
        _openai_client_cache = (
            ctor,
            ctor(api_key=settings.openai_api_key.get_secret_value()),
        )
    return _openai_client_cache[1]


class EmbeddingService:
    def __init__(self, repo: EmbeddingRepository) -> None:
        self.repo = repo
        self.openai = _get_openai_client()

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

    async def embed_external_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        source_workspace_id: uuid.UUID,
        project_id: uuid.UUID | None,
        title: str,
        origin_url: str,
        plain_text: str,
    ) -> int:
        """외부 문서 본문을 L1/L2 청크로 저장한다."""
        await self.repo.delete_by_source("external_document", document_id)

        if not plain_text.strip():
            await self.repo.commit()
            return 0

        # BL-EXT-EMBED-1: 절단은 **임베딩 입력에만** 적용하고 저장되는 chunk_text 는
        # 전문을 유지한다. 이 비대칭은 의도적이다 (2026-08-01 코드 확인).
        # · L1 벡터는 검색 경로에 오르지 않는다 — repository.py:206(vector_search) /
        #   :266(text_search) 이 `chunk_level = 2` 로 하드 필터한다 (CONTEXT.md E-2).
        # · 반대로 L1 의 chunk_text 는 rag/service.py:323 이 parent_text 로 읽어
        #   :381 에서 LLM 프롬프트의 근거 본문이 된다 → 절단하면 근거가 잘린다.
        level1_embed_input = plain_text[:_EXTERNAL_L1_MAX_CHARS]
        paragraphs = self._chunk_text(plain_text)
        texts_to_embed = [level1_embed_input, *paragraphs]
        # 요청당 한도를 넘지 않도록 슬라이스 반복 호출 — 결과를 순서대로 이어붙여
        # 인덱스 0 = L1, 이후 L2 문단 순의 대응을 유지한다.
        embeddings: list[list[float]] = []
        for batch_start in range(0, len(texts_to_embed), _EXTERNAL_EMBED_BATCH_SIZE):
            embeddings.extend(
                await self.generate_embeddings(
                    texts_to_embed[batch_start : batch_start + _EXTERNAL_EMBED_BATCH_SIZE]
                )
            )
        metadata_json = {"title": title, "originUrl": origin_url}

        level1_chunk = await self.repo.save_chunk(
            workspace_id=workspace_id,
            source_workspace_id=source_workspace_id,
            source_type="external_document",
            source_id=document_id,
            chunk_text=plain_text,
            embedding=embeddings[0],
            chunk_index=0,
            chunk_level=1,
            project_id=project_id,
            metadata_json=metadata_json,
        )
        for chunk_index, (paragraph, embedding) in enumerate(
            zip(paragraphs, embeddings[1:])
        ):
            await self.repo.save_chunk(
                workspace_id=workspace_id,
                source_workspace_id=source_workspace_id,
                source_type="external_document",
                source_id=document_id,
                chunk_text=paragraph,
                embedding=embedding,
                chunk_index=chunk_index,
                chunk_level=2,
                parent_chunk_id=level1_chunk.id,
                project_id=project_id,
                metadata_json=metadata_json,
            )

        await self.repo.commit()
        return len(paragraphs) + 1

    # --- 캐시 무효화 ---

    async def invalidate_cache(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> None:
        """새 임베딩 생성 시 관련 시맨틱 캐시 삭제."""
        await self.repo.delete_caches(workspace_id, project_id)
        await self.repo.commit()
