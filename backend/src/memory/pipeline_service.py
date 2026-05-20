# Memory 도메인 cross-domain orchestrator — embeddings 호출 격리 (BL-006 해소, Sprint 24 Wave 2)
"""Memory pipeline orchestrator.

헌법 §4.2 + ADR-014 옵션 A:
- `memory/service.py` 는 단일 도메인 책임만. `embeddings.*` import 금지.
- `embeddings.repository.EmbeddingRepository.save_chunk` 호출은 본 orchestrator 안에서만.
- service 는 BackgroundTask 내부에서 본 orchestrator 의 `save_memory_chunk` 를 호출하여
  embeddings 도메인 캡슐화 우회 없이 청크를 적재.

호출자:
- `memory/service.py:_bg_distill_and_embed` — text/voice capture 후 distill→embed 흐름
- `memory/service.py` 모듈-level `_bg_promote_embed` — R6 promote 1-button 흐름

session 정책:
- `save_memory_chunk` 는 호출자가 이미 보유한 `AsyncSession` 을 인자로 받는다.
  (text/voice capture 흐름은 `MemoryRepository(session)` 와 동일 session 공유 — 단일 트랜잭션 정합.)
- session lifecycle (open/commit/close) 은 호출자 책임. orchestrator 는 1 회 `flush` 까지만 수행.

비책임:
- promote 의 audit row 작성 / status 전이 / R2 처리 (service 가 그대로 보유).
- query embedding cache (memory/repository.py 직접 보유 — repository-level 책임이므로 E-9 외부
  사용처 유지 결정. CONTEXT-MAP I-21 + embeddings/CONTEXT.md E-9).
- AI 호출 (`_call_distill` / `_call_embedding` / `_call_transcribe`) — Sprint 25 BL-007 후속.
"""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from src.embeddings.models import EmbeddingChunk
from src.embeddings.repository import EmbeddingRepository


class MemoryPipelineService:
    """memory ↔ embeddings 경계 orchestrator.

    상태를 갖지 않는다 (session 은 인자로 받음). dependencies.py 에서 1 회 생성 후
    `MemoryService` 생성자에 주입. service 는 본 인스턴스의 메서드만 호출하며,
    `from src.embeddings.*` 직접 import 는 본 모듈에서만 허용.
    """

    async def save_memory_chunk(
        self,
        session: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        source_workspace_id: uuid.UUID,
        source_id: uuid.UUID,
        chunk_text: str,
        embedding: list[float],
        chunk_index: int = 0,
        chunk_level: int = 2,
    ) -> EmbeddingChunk:
        """memory source 의 EmbeddingChunk 1건 insert.

        I-9 4-C: `EmbeddingRepository.save_chunk` 가 workspace_id 일치를 assertion 으로 강제.
        `source_type='memory'` 는 본 orchestrator 가 고정 — service 에서 임의 변경 불가.
        """
        repo = EmbeddingRepository(session)
        return await repo.save_chunk(
            workspace_id=workspace_id,
            source_workspace_id=source_workspace_id,
            source_type="memory",
            source_id=source_id,
            chunk_text=chunk_text,
            embedding=embedding,
            chunk_index=chunk_index,
            chunk_level=chunk_level,
        )
