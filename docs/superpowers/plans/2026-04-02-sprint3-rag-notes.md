# Sprint 3: RAG + 노트 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 회의/노트 데이터를 자연어로 질문 가능한 지식 자산으로 전환 — Hybrid Search + SSE 스트리밍 RAG + Tiptap 노트 에디터

**Architecture:** 5개 Vertical Slice 순차 진행 (RAG-First). 각 Slice는 독립적으로 merge + 검증 가능. 백엔드는 기존 도메인 패턴(Router/Service/Repository/Dependencies) 준수. 프론트엔드는 FSD Lite + React Query + Zustand 패턴 유지.

**Tech Stack:** FastAPI + SQLModel + pgvector + pg_trgm + sse-starlette + OpenAI Embeddings + Gemini 2.5-flash / Next.js 16 + Tiptap + React Query + Zustand

**설계 문서:** `docs/superpowers/specs/2026-04-02-sprint3-rag-notes-design.md`

---

## Slice 1: 임베딩 인프라 (BE)

### Task 1: PostgreSQL 확장 + 마이그레이션

**Files:**
- Modify: `backend/alembic/env.py` (새 모델 import 추가)
- Create: `backend/src/embeddings/__init__.py`
- Create: `backend/src/embeddings/models.py`
- Create: `backend/src/notes/__init__.py`
- Create: `backend/src/notes/models.py`
- Create: `backend/alembic/versions/<auto>_add_sprint3_tables.py`

- [ ] **Step 1: 임베딩 모델 생성**

```python
# backend/src/embeddings/__init__.py
# (빈 파일)
```

```python
# backend/src/embeddings/models.py
"""임베딩 청크 + 시맨틱 캐시 모델."""
import uuid
from datetime import datetime

from sqlalchemy import Column, Index, Text, text
from sqlmodel import Field, SQLModel

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # 마이그레이션 생성 시에만 필요


class EmbeddingChunk(SQLModel, table=True):
    """계층적 임베딩 청크. Level 2(문단)가 검색 대상."""

    __tablename__ = "embedding_chunks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id", index=True
    )
    source_id: uuid.UUID = Field(nullable=False)
    source_type: str = Field(nullable=False)  # 'meeting' | 'note' | 'action'
    chunk_text: str = Field(sa_column=Column(Text, nullable=False))
    chunk_index: int = Field(default=0)
    chunk_level: int = Field(default=2)  # 0=문서, 1=섹션/화자, 2=문단
    parent_chunk_id: uuid.UUID | None = Field(
        default=None, foreign_key="embedding_chunks.id", index=True
    )
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(1536)) if Vector else Column(Text),
    )
    metadata_json: dict = Field(default_factory=dict, sa_type="JSON")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SemanticCache(SQLModel, table=True):
    """시맨틱 캐시. 유사 질문 → 캐시 답변 반환."""

    __tablename__ = "semantic_caches"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id"
    )
    question: str = Field(sa_column=Column(Text, nullable=False))
    question_embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(1536)) if Vector else Column(Text),
    )
    answer: str = Field(sa_column=Column(Text, nullable=False))
    sources: list = Field(default_factory=list, sa_type="JSON")
    hit_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = Field(default=None)
```

- [ ] **Step 2: 노트 모델 생성**

```python
# backend/src/notes/__init__.py
# (빈 파일)
```

```python
# backend/src/notes/models.py
"""노트 모델. project_id nullable — CODE 철학(마찰 최소화)."""
import uuid
from datetime import datetime

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class Note(SQLModel, table=True):
    __tablename__ = "notes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id", index=True
    )
    title: str = Field(default="")
    content: dict = Field(default_factory=dict, sa_type="JSON")
    plain_text: str = Field(default="", sa_column=Column(Text, default=""))
    created_by_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 3: alembic/env.py에 모델 import 추가**

`backend/alembic/env.py`의 모델 import 블록에 추가:

```python
# 기존 import 아래에 추가
from src.embeddings.models import EmbeddingChunk, SemanticCache
from src.notes.models import Note
```

- [ ] **Step 4: 마이그레이션 생성 및 실행**

```bash
cd backend
# pgvector, pg_trgm 확장은 Neon에서 이미 사용 가능 (대시보드에서 활성화)
# 마이그레이션 생성
uv run alembic revision --autogenerate -m "add sprint3 tables embedding_chunks semantic_caches notes"
```

생성된 마이그레이션 파일 상단에 pgvector/pg_trgm 확장 + 인덱스 추가:

```python
def upgrade() -> None:
    # PostgreSQL 확장 활성화
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ... autogenerate된 테이블 생성 코드 ...

    # 수동 인덱스 추가 (autogenerate가 못 만드는 것)
    op.execute("""
        CREATE INDEX idx_chunks_vector ON embedding_chunks
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
    """)
    op.execute("""
        CREATE INDEX idx_chunks_trgm ON embedding_chunks
        USING gin (chunk_text gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX idx_chunks_source ON embedding_chunks (source_type, source_id)
    """)
    op.execute("""
        CREATE INDEX idx_cache_vector ON semantic_caches
        USING ivfflat (question_embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    # ... autogenerate된 테이블 삭제 코드 ...
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS vector")
```

```bash
# 마이그레이션 실행
uv run alembic upgrade head
```

- [ ] **Step 5: 의존성 추가**

`backend/pyproject.toml`의 `dependencies`에 추가:

```toml
"pgvector>=0.4.0",
"sse-starlette>=2.0.0",
```

```bash
cd backend && uv sync
```

- [ ] **Step 6: 커밋**

```bash
git add backend/src/embeddings/ backend/src/notes/models.py backend/src/notes/__init__.py backend/alembic/ backend/pyproject.toml
git commit -m "feat: Sprint 3 DB 스키마 — embedding_chunks, semantic_caches, notes + pgvector/pg_trgm"
```

---

### Task 2: EmbeddingService — 청킹 + OpenAI 임베딩

**Files:**
- Create: `backend/src/embeddings/repository.py`
- Create: `backend/src/embeddings/service.py`
- Create: `backend/src/embeddings/dependencies.py`
- Create: `backend/src/embeddings/exceptions.py`
- Create: `backend/tests/embeddings/__init__.py`
- Create: `backend/tests/embeddings/test_chunking.py`
- Create: `backend/tests/embeddings/test_embedding_service.py`

- [ ] **Step 1: 테스트 — 청킹 로직**

```python
# backend/tests/embeddings/__init__.py
# (빈 파일)
```

```python
# backend/tests/embeddings/test_chunking.py
"""청킹 로직 단위 테스트."""
import pytest
from src.embeddings.service import EmbeddingService


class TestChunkText:
    """텍스트를 300-500자 청크로 분할하는 로직."""

    def test_short_text_single_chunk(self):
        """300자 미만 텍스트 → 청크 1개."""
        service = EmbeddingService.__new__(EmbeddingService)
        chunks = service._chunk_text("짧은 텍스트입니다.", max_chars=500, overlap_chars=50)
        assert len(chunks) == 1
        assert chunks[0] == "짧은 텍스트입니다."

    def test_long_text_multiple_chunks(self):
        """1000자 텍스트 → 여러 청크, 각 500자 이하."""
        service = EmbeddingService.__new__(EmbeddingService)
        text = "가나다라마바사아" * 125  # 1000자
        chunks = service._chunk_text(text, max_chars=500, overlap_chars=50)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 550  # max + overlap 여유

    def test_overlap_between_chunks(self):
        """인접 청크 사이에 오버랩이 존재해야 한다."""
        service = EmbeddingService.__new__(EmbeddingService)
        text = "A" * 200 + "B" * 200 + "C" * 200  # 600자
        chunks = service._chunk_text(text, max_chars=300, overlap_chars=50)
        assert len(chunks) >= 2
        # 첫 번째 청크의 끝 50자가 두 번째 청크의 시작에 포함
        overlap = chunks[0][-50:]
        assert chunks[1].startswith(overlap)


class TestChunkMeetingTranscript:
    """회의 트랜스크립트를 계층적 청크로 변환."""

    def test_segments_grouped_by_speaker(self):
        """같은 화자의 연속 세그먼트 → Level 1 그룹."""
        service = EmbeddingService.__new__(EmbeddingService)
        segments = [
            {"speaker": "김철수", "text": "안녕하세요. ", "start_sec": 0, "end_sec": 5},
            {"speaker": "김철수", "text": "오늘 안건을 말씀드리겠습니다. ", "start_sec": 5, "end_sec": 10},
            {"speaker": "이영희", "text": "네 알겠습니다. ", "start_sec": 10, "end_sec": 15},
        ]
        groups = service._group_segments_by_speaker(segments)
        assert len(groups) == 2
        assert groups[0]["speaker"] == "김철수"
        assert groups[1]["speaker"] == "이영희"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd backend && uv run pytest tests/embeddings/test_chunking.py -v
```

Expected: FAIL — `src.embeddings.service` 모듈 없음

- [ ] **Step 3: EmbeddingService 구현 — 청킹 로직**

```python
# backend/src/embeddings/service.py
"""임베딩 서비스 — 청킹 + OpenAI 임베딩 생성 + 저장."""
import uuid
from datetime import datetime

from openai import AsyncOpenAI

from src.core.config import get_settings
from src.embeddings.models import EmbeddingChunk
from src.embeddings.repository import EmbeddingRepository


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
        # 기존 청크 삭제 (재생성)
        await self.repo.delete_by_source("meeting", meeting_id)

        # Level 0: 문서 전체
        full_text = " ".join(seg.get("text", "") for seg in segments)
        if not full_text.strip():
            return 0

        # Level 1: 화자 그룹
        speaker_groups = self._group_segments_by_speaker(segments)

        all_chunks: list[EmbeddingChunk] = []
        texts_to_embed: list[str] = []

        for group_idx, group in enumerate(speaker_groups):
            # Level 1 청크
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

            # Level 2: 문단 청크
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

        # DB 저장
        await self.repo.save_chunks(all_chunks)
        await self.repo.commit()

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
```

- [ ] **Step 4: EmbeddingRepository 구현**

```python
# backend/src/embeddings/repository.py
"""임베딩 청크 + 시맨틱 캐시 DB 접근."""
import uuid

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.embeddings.models import EmbeddingChunk, SemanticCache


class EmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- 청크 ---

    async def save_chunks(self, chunks: list[EmbeddingChunk]) -> None:
        """벌크 저장."""
        for chunk in chunks:
            self.session.add(chunk)
        await self.session.flush()

    async def delete_by_source(
        self, source_type: str, source_id: uuid.UUID
    ) -> None:
        """특정 소스의 모든 청크 삭제 (재생성 전)."""
        stmt = delete(EmbeddingChunk).where(
            EmbeddingChunk.source_type == source_type,
            EmbeddingChunk.source_id == source_id,
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def find_by_parent(
        self, parent_chunk_id: uuid.UUID
    ) -> list[EmbeddingChunk]:
        """Level 1 부모의 자식 청크 조회."""
        result = await self.session.execute(
            select(EmbeddingChunk).where(
                EmbeddingChunk.parent_chunk_id == parent_chunk_id
            )
        )
        return list(result.scalars().all())

    # --- 검색 (Slice 2에서 사용) ---

    async def vector_search(
        self,
        query_embedding: list[float],
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        source_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """pgvector 코사인 유사도 검색."""
        filters = "workspace_id = :wid AND chunk_level = 2"
        params: dict = {"wid": str(workspace_id), "limit": limit}

        if project_id:
            filters += " AND project_id = :pid"
            params["pid"] = str(project_id)
        if source_type:
            filters += " AND source_type = :stype"
            params["stype"] = source_type

        query = text(f"""
            SELECT id, chunk_text, source_id, source_type, metadata_json,
                   parent_chunk_id, created_at,
                   1 - (embedding <=> :qvec::vector) AS score
            FROM embedding_chunks
            WHERE {filters}
            ORDER BY embedding <=> :qvec::vector
            LIMIT :limit
        """)
        params["qvec"] = str(query_embedding)

        result = await self.session.execute(query, params)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def text_search(
        self,
        query_text: str,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        source_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """pg_trgm 트라이그램 유사도 검색."""
        filters = "workspace_id = :wid AND chunk_level = 2"
        params: dict = {"wid": str(workspace_id), "query": query_text, "limit": limit}

        if project_id:
            filters += " AND project_id = :pid"
            params["pid"] = str(project_id)
        if source_type:
            filters += " AND source_type = :stype"
            params["stype"] = source_type

        query = text(f"""
            SELECT id, chunk_text, source_id, source_type, metadata_json,
                   parent_chunk_id, created_at,
                   similarity(chunk_text, :query) AS score
            FROM embedding_chunks
            WHERE {filters}
              AND chunk_text % :query
            ORDER BY similarity(chunk_text, :query) DESC
            LIMIT :limit
        """)

        result = await self.session.execute(query, params)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def find_chunk_by_id(self, chunk_id: uuid.UUID) -> EmbeddingChunk | None:
        """ID로 청크 조회 (parent context 조회용)."""
        result = await self.session.execute(
            select(EmbeddingChunk).where(EmbeddingChunk.id == chunk_id)
        )
        return result.scalar_one_or_none()

    # --- 캐시 ---

    async def find_similar_cache(
        self,
        question_embedding: list[float],
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        threshold: float = 0.93,
    ) -> dict | None:
        """시맨틱 캐시 검색. similarity >= threshold → HIT."""
        filters = "workspace_id = :wid AND expires_at > now()"
        params: dict = {"wid": str(workspace_id), "threshold": threshold}

        if project_id:
            filters += " AND project_id = :pid"
            params["pid"] = str(project_id)

        query = text(f"""
            SELECT id, answer, sources, hit_count,
                   1 - (question_embedding <=> :qvec::vector) AS similarity
            FROM semantic_caches
            WHERE {filters}
              AND 1 - (question_embedding <=> :qvec::vector) >= :threshold
            ORDER BY question_embedding <=> :qvec::vector
            LIMIT 1
        """)
        params["qvec"] = str(question_embedding)

        result = await self.session.execute(query, params)
        row = result.mappings().first()
        if row:
            # hit_count 증가
            await self.session.execute(
                text("UPDATE semantic_caches SET hit_count = hit_count + 1 WHERE id = :id"),
                {"id": str(row["id"])},
            )
            return dict(row)
        return None

    async def save_cache(self, cache: SemanticCache) -> None:
        """캐시 항목 저장."""
        self.session.add(cache)
        await self.session.flush()

    async def delete_caches(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> None:
        """캐시 무효화."""
        stmt = delete(SemanticCache).where(
            SemanticCache.workspace_id == workspace_id
        )
        if project_id:
            stmt = stmt.where(SemanticCache.project_id == project_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
```

- [ ] **Step 5: Dependencies + Exceptions**

```python
# backend/src/embeddings/dependencies.py
"""임베딩 서비스 의존성 주입."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService


async def get_embedding_repository(
    session: AsyncSession = Depends(get_async_session),
) -> EmbeddingRepository:
    return EmbeddingRepository(session)


async def get_embedding_service(
    repo: EmbeddingRepository = Depends(get_embedding_repository),
) -> EmbeddingService:
    return EmbeddingService(repo)
```

```python
# backend/src/embeddings/exceptions.py
"""임베딩 관련 예외."""


class EmbeddingError(Exception):
    """임베딩 생성 실패."""

    def __init__(self, message: str = "임베딩 생성에 실패했습니다") -> None:
        self.message = message
        super().__init__(self.message)
```

- [ ] **Step 6: 테스트 실행 — 통과 확인**

```bash
cd backend && uv run pytest tests/embeddings/test_chunking.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 7: 커밋**

```bash
git add backend/src/embeddings/ backend/tests/embeddings/
git commit -m "feat: EmbeddingService — 계층적 청킹 + OpenAI 임베딩 + Repository"
```

---

### Task 3: MeetingPipelineService에 임베딩 단계 추가

**Files:**
- Modify: `backend/src/meetings/pipeline_service.py`
- Modify: `backend/src/meetings/dependencies.py`
- Modify: `backend/tests/meetings/test_pipeline.py`

- [ ] **Step 1: 테스트 수정 — 임베딩 단계 검증**

`backend/tests/meetings/test_pipeline.py`에 추가:

```python
# 기존 test_process_meeting_success 또는 새 테스트에서
# pipeline_service 생성 시 embedding_service mock 추가

async def test_pipeline_creates_embeddings():
    """파이프라인 완료 후 임베딩이 생성되어야 한다."""
    # MeetingPipelineService에 embedding_service 인자 추가
    mock_embedding_service = AsyncMock()
    mock_embedding_service.embed_meeting.return_value = 10
    mock_embedding_service.invalidate_cache.return_value = None

    # ... (기존 mock 셋업) ...
    # pipeline에 embedding_service 전달 후 process_meeting 호출
    # assert mock_embedding_service.embed_meeting.called
```

- [ ] **Step 2: pipeline_service.py 수정**

`backend/src/meetings/pipeline_service.py`에:

1. `__init__`에 `embedding_service: EmbeddingService` 파라미터 추가
2. `process_meeting` 마지막 단계(완료 전)에 임베딩 생성 호출

```python
# __init__ 시그니처에 추가:
from src.embeddings.service import EmbeddingService

# __init__ body에:
self.embedding_service = embedding_service

# process_meeting의 [3] Completion 직전에 추가:
# [2-6] 임베딩 생성
try:
    # 프로젝트 ID 조회 (자동확정된 경우)
    project_id = None
    if confidence >= 0.8 and existing_project_id_str:
        project_id = uuid.UUID(existing_project_id_str)

    segments_data = [
        {"speaker": seg.speaker, "text": seg.text,
         "start_sec": seg.start_sec, "end_sec": seg.end_sec}
        for seg in segments
    ]
    await self.embedding_service.embed_meeting(
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        project_id=project_id,
        title=meeting.title,
        segments=segments_data,
    )
    await self.embedding_service.invalidate_cache(
        meeting.workspace_id, project_id
    )
except Exception as e:
    # 임베딩 실패는 파이프라인 전체를 실패시키지 않음
    import logging
    logging.getLogger(__name__).warning(f"임베딩 생성 실패 (비치명적): {e}")
```

- [ ] **Step 3: dependencies.py 수정**

`backend/src/meetings/dependencies.py`의 `get_pipeline_service`에:

```python
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService

async def get_pipeline_service(
    session: AsyncSession = Depends(get_async_session),
) -> MeetingPipelineService:
    return MeetingPipelineService(
        meeting_repo=MeetingRepository(session),
        project_repo=ProjectRepository(session),
        action_repo=ActionItemRepository(session),
        inbox_repo=InboxRepository(session),
        r2_service=R2Service(),
        transcription_service=TranscriptionService(),
        ai_service=AIProcessingService(),
        embedding_service=EmbeddingService(EmbeddingRepository(session)),  # 추가
    )
```

- [ ] **Step 4: 테스트 실행**

```bash
cd backend && uv run pytest tests/meetings/test_pipeline.py -v
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/src/meetings/pipeline_service.py backend/src/meetings/dependencies.py backend/tests/meetings/
git commit -m "feat: MeetingPipeline에 임베딩 단계 추가 — 회의 완료 시 자동 임베딩"
```

---

## Slice 2: RAG 검색 (BE + FE)

### Task 4: RAG 프롬프트 + AIProcessingService 스트리밍

**Files:**
- Modify: `backend/src/common/prompts.py`
- Modify: `backend/src/services/ai_processing.py`
- Create: `backend/tests/services/test_rag_prompt.py`

- [ ] **Step 1: RAG 프롬프트 추가**

`backend/src/common/prompts.py`에 추가:

```python
RAG_SYSTEM_PROMPT = """당신은 Kairos 팀 지식 검색 AI입니다.

## 규칙
1. 제공된 소스를 기반으로만 답변하세요
2. 소스에 없는 정보는 "제공된 소스에서 관련 정보를 찾지 못했습니다"라고 명시하세요
3. 답변에 반드시 출처를 인용하세요 (예: "📎 킥오프 회의 (2026-03-20)")
4. 3개월 이상 된 소스는 "⚠️ 오래된 소스입니다 (YYYY-MM-DD 기준)" 경고를 포함하세요
5. 한국어로 답변하되, 기술 용어는 원문 그대로 사용하세요
6. 간결하고 구조화된 답변을 제공하세요 (불릿 포인트 활용)

## 소스
{sources}

## 질문
{question}
"""
```

- [ ] **Step 2: AIProcessingService에 스트리밍 메서드 추가**

`backend/src/services/ai_processing.py`에 추가:

```python
from collections.abc import AsyncGenerator

async def stream_rag_answer(
    self,
    question: str,
    sources_text: str,
) -> AsyncGenerator[str, None]:
    """RAG 답변 스트리밍. Gemini의 토큰을 하나씩 yield."""
    from src.common.prompts import RAG_SYSTEM_PROMPT

    prompt = RAG_SYSTEM_PROMPT.format(
        sources=sources_text,
        question=question,
    )

    response = await self.client.aio.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    async for chunk in response:
        if chunk.text:
            yield chunk.text
```

- [ ] **Step 3: 커밋**

```bash
git add backend/src/common/prompts.py backend/src/services/ai_processing.py
git commit -m "feat: RAG 프롬프트 + Gemini 스트리밍 답변 메서드"
```

---

### Task 5: RagService + Router (SSE)

**Files:**
- Create: `backend/src/rag/__init__.py`
- Create: `backend/src/rag/service.py`
- Create: `backend/src/rag/router.py`
- Create: `backend/src/rag/schemas.py`
- Create: `backend/src/rag/dependencies.py`
- Create: `backend/src/rag/exceptions.py`
- Modify: `backend/src/main.py`
- Create: `backend/tests/rag/__init__.py`
- Create: `backend/tests/rag/test_rag_service.py`

- [ ] **Step 1: RAG 스키마**

```python
# backend/src/rag/__init__.py
# (빈 파일)
```

```python
# backend/src/rag/schemas.py
"""RAG 요청/응답 스키마."""
from pydantic import BaseModel, Field


class RagAskRequest(BaseModel):
    question: str = Field(min_length=1)
    project_id: str | None = Field(default=None, alias="projectId")
    time_range: str | None = Field(default=None, alias="timeRange")  # 1m, 3m, 6m
    source_type: str | None = Field(default=None, alias="sourceType")  # meeting, note

    model_config = {"populate_by_name": True}
```

```python
# backend/src/rag/exceptions.py
class RagError(Exception):
    def __init__(self, message: str = "RAG 검색 중 오류가 발생했습니다") -> None:
        self.message = message
        super().__init__(self.message)
```

- [ ] **Step 2: RagService 구현**

```python
# backend/src/rag/service.py
"""RAG 서비스 — 캐시 확인 → Hybrid Search → RRF → Gemini SSE."""
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta

from src.embeddings.models import SemanticCache
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.services.ai_processing import AIProcessingService


class RagService:
    def __init__(
        self,
        embedding_repo: EmbeddingRepository,
        embedding_service: EmbeddingService,
        ai_service: AIProcessingService,
    ) -> None:
        self.embedding_repo = embedding_repo
        self.embedding_service = embedding_service
        self.ai_service = ai_service

    async def ask(
        self,
        question: str,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        time_range: str | None = None,
        source_type: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        """RAG 파이프라인. SSE 이벤트를 yield."""

        # [1] 질문 임베딩
        embeddings = await self.embedding_service.generate_embeddings([question])
        question_embedding = embeddings[0]

        # [2] Semantic Cache 확인
        cache_hit = await self.embedding_repo.find_similar_cache(
            question_embedding, workspace_id, project_id
        )
        if cache_hit:
            yield {"event": "search_results", "data": json.dumps(
                {"chunks": cache_hit["sources"]}, ensure_ascii=False
            )}
            yield {"event": "answer", "data": json.dumps(
                {"token": cache_hit["answer"]}, ensure_ascii=False
            )}
            yield {"event": "done", "data": json.dumps(
                {"cached": True, "sourceCount": len(cache_hit["sources"])}
            )}
            return

        # [3] Thinking
        yield {"event": "thinking", "data": json.dumps(
            {"status": "검색 중..."}, ensure_ascii=False
        )}

        # [4] Hybrid Search
        vector_results = await self.embedding_repo.vector_search(
            question_embedding, workspace_id, project_id, source_type, limit=50
        )
        text_results = await self.embedding_repo.text_search(
            question, workspace_id, project_id, source_type, limit=50
        )

        # [5] RRF 융합
        fused = self._reciprocal_rank_fusion(text_results, vector_results, top_n=10)

        if not fused:
            yield {"event": "answer", "data": json.dumps(
                {"token": "제공된 소스에서 관련 정보를 찾지 못했습니다."}, ensure_ascii=False
            )}
            yield {"event": "done", "data": json.dumps(
                {"cached": False, "sourceCount": 0}
            )}
            return

        # [6] Context Enrichment — parent 청크 포함
        enriched = await self._enrich_context(fused)

        # [7] search_results 이벤트
        sources_for_client = self._format_sources(enriched)
        yield {"event": "search_results", "data": json.dumps(
            {"chunks": sources_for_client}, ensure_ascii=False
        )}

        # [8] Generation (Gemini SSE)
        sources_text = self._format_sources_for_prompt(enriched)
        full_answer = ""
        async for token in self.ai_service.stream_rag_answer(question, sources_text):
            full_answer += token
            yield {"event": "answer", "data": json.dumps(
                {"token": token}, ensure_ascii=False
            )}

        # [9] Cache Store
        cache = SemanticCache(
            workspace_id=workspace_id,
            project_id=project_id,
            question=question,
            question_embedding=question_embedding,
            answer=full_answer,
            sources=sources_for_client,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        await self.embedding_repo.save_cache(cache)
        await self.embedding_repo.commit()

        yield {"event": "done", "data": json.dumps(
            {"cached": False, "sourceCount": len(sources_for_client)}
        )}

    @staticmethod
    def _reciprocal_rank_fusion(
        text_results: list[dict],
        vector_results: list[dict],
        k: int = 60,
        top_n: int = 10,
    ) -> list[dict]:
        """RRF 융합. k=60 표준값."""
        scores: dict[str, float] = {}
        result_map: dict[str, dict] = {}

        for rank, r in enumerate(text_results):
            rid = str(r["id"])
            scores[rid] = scores.get(rid, 0) + 1 / (k + rank + 1)
            result_map[rid] = r

        for rank, r in enumerate(vector_results):
            rid = str(r["id"])
            scores[rid] = scores.get(rid, 0) + 1 / (k + rank + 1)
            result_map[rid] = r

        sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
        return [result_map[rid] for rid in sorted_ids[:top_n]]

    async def _enrich_context(self, results: list[dict]) -> list[dict]:
        """Level 2 검색 결과에 parent Level 1 컨텍스트 추가."""
        enriched = []
        for r in results:
            parent_text = ""
            if r.get("parent_chunk_id"):
                parent = await self.embedding_repo.find_chunk_by_id(
                    r["parent_chunk_id"]
                )
                if parent:
                    parent_text = parent.chunk_text
            enriched.append({**r, "parent_text": parent_text})
        return enriched

    @staticmethod
    def _format_sources(results: list[dict]) -> list[dict]:
        """클라이언트용 소스 포맷."""
        sources = []
        for r in results:
            meta = r.get("metadata_json") or {}
            created = r.get("created_at")
            freshness = "recent"
            if created:
                age = datetime.utcnow() - created
                if age > timedelta(days=90):
                    freshness = "stale"
                elif age > timedelta(days=30):
                    freshness = "normal"

            sources.append({
                "id": str(r["id"]),
                "text": r["chunk_text"][:200],
                "source": meta.get("title", ""),
                "sourceType": r.get("source_type", ""),
                "date": created.isoformat() if created else "",
                "speaker": meta.get("speaker"),
                "score": round(float(r.get("score", 0)), 3),
                "freshness": freshness,
            })
        return sources

    @staticmethod
    def _format_sources_for_prompt(results: list[dict]) -> str:
        """Gemini 프롬프트용 소스 텍스트."""
        parts = []
        for i, r in enumerate(results, 1):
            meta = r.get("metadata_json") or {}
            header = f"[소스 {i}] {meta.get('title', '제목 없음')}"
            if meta.get("speaker"):
                header += f" — 발언자: {meta['speaker']}"
            if r.get("created_at"):
                header += f" ({r['created_at'].strftime('%Y-%m-%d')})"

            text = r.get("parent_text", "") or r["chunk_text"]
            parts.append(f"{header}\n{text}")
        return "\n\n---\n\n".join(parts)
```

- [ ] **Step 3: RAG Router (SSE)**

```python
# backend/src/rag/router.py
"""RAG 엔드포인트 — SSE 스트리밍."""
import uuid

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.rag.dependencies import get_rag_service
from src.rag.schemas import RagAskRequest
from src.rag.service import RagService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/rag",
    tags=["rag"],
)


@router.post("/ask")
async def ask_rag(
    workspace_id: uuid.UUID,
    data: RagAskRequest,
    current_user: User = Depends(get_current_user),
    service: RagService = Depends(get_rag_service),
):
    """RAG 질문 → SSE 스트리밍 답변."""
    project_id = uuid.UUID(data.project_id) if data.project_id else None

    async def event_generator():
        async for event in service.ask(
            question=data.question,
            workspace_id=workspace_id,
            project_id=project_id,
            time_range=data.time_range,
            source_type=data.source_type,
        ):
            yield event

    return EventSourceResponse(event_generator())
```

- [ ] **Step 4: RAG Dependencies**

```python
# backend/src/rag/dependencies.py
"""RAG 서비스 의존성."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.rag.service import RagService
from src.services.ai_processing import AIProcessingService


async def get_rag_service(
    session: AsyncSession = Depends(get_async_session),
) -> RagService:
    repo = EmbeddingRepository(session)
    return RagService(
        embedding_repo=repo,
        embedding_service=EmbeddingService(repo),
        ai_service=AIProcessingService(),
    )
```

- [ ] **Step 5: main.py에 라우터 등록**

`backend/src/main.py`에 추가:

```python
from src.rag.router import router as rag_router

# app.include_router(...) 블록에 추가:
app.include_router(rag_router)
```

- [ ] **Step 6: 커밋**

```bash
git add backend/src/rag/ backend/src/main.py backend/src/services/ai_processing.py backend/src/common/prompts.py
git commit -m "feat: RAG 엔드포인트 — Hybrid Search + RRF + Gemini SSE 스트리밍"
```

---

### Task 6: 프론트엔드 RAG UI

**Files:**
- Modify: `frontend/src/features/rag/types.ts`
- Create: `frontend/src/features/rag/api.ts`
- Create: `frontend/src/features/rag/hooks.ts`
- Create: `frontend/src/features/rag/store.ts`
- Rewrite: `frontend/src/features/rag/components/rag-chat.tsx`
- Rewrite: `frontend/src/features/rag/components/rag-input.tsx`
- Rewrite: `frontend/src/features/rag/components/rag-home.tsx`
- Create: `frontend/src/features/rag/components/rag-message.tsx`
- Create: `frontend/src/features/rag/components/rag-sources.tsx`
- Rewrite: `frontend/src/features/rag/components/search-scope.tsx`
- Rewrite: `frontend/src/components/layout/rag-panel.tsx`

- [ ] **Step 1: RAG 타입 업데이트**

```typescript
// frontend/src/features/rag/types.ts
import type { UUID } from "@/types";

export type SourceFreshness = "recent" | "normal" | "stale";

export interface RagMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: RagSource[];
  isStreaming?: boolean;
  createdAt: string;
}

export interface RagSource {
  id: string;
  text: string;
  source: string;
  sourceType: "meeting" | "note";
  date: string;
  speaker?: string;
  score: number;
  freshness: SourceFreshness;
}

export interface SearchFilter {
  projectId?: UUID;
  timeRange?: "1m" | "3m" | "6m" | null;
  sourceType?: "meeting" | "note" | null;
}

export interface RagAskRequest {
  question: string;
  projectId?: string | null;
  timeRange?: string | null;
  sourceType?: string | null;
}

// SSE 이벤트 타입
export interface SSEThinkingEvent {
  status: string;
}

export interface SSESearchResultsEvent {
  chunks: RagSource[];
}

export interface SSEAnswerEvent {
  token: string;
}

export interface SSEDoneEvent {
  cached: boolean;
  sourceCount: number;
}
```

- [ ] **Step 2: RAG API — SSE fetch**

```typescript
// frontend/src/features/rag/api.ts
import type { RagAskRequest } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const ragKeys = {
  all: ["rag"] as const,
};

export async function askRag(
  token: string,
  wid: string,
  data: RagAskRequest,
): Promise<Response> {
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces/${wid}/rag/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(`RAG 요청 실패: ${res.status}`);
  }

  return res;
}
```

- [ ] **Step 3: RAG Zustand 스토어**

```typescript
// frontend/src/features/rag/store.ts
"use client";

import { create } from "zustand";
import type { RagMessage, SearchFilter } from "./types";

interface RagState {
  messages: RagMessage[];
  isStreaming: boolean;
  searchFilter: SearchFilter;
  addMessage: (message: RagMessage) => void;
  updateLastAssistantMessage: (content: string) => void;
  setSourcesOnLastAssistant: (sources: RagMessage["sources"]) => void;
  setIsStreaming: (streaming: boolean) => void;
  setSearchFilter: (filter: Partial<SearchFilter>) => void;
  clearMessages: () => void;
}

export const useRagStore = create<RagState>((set) => ({
  messages: [],
  isStreaming: false,
  searchFilter: {},

  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  updateLastAssistantMessage: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + content };
      }
      return { messages: msgs };
    }),

  setSourcesOnLastAssistant: (sources) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, sources };
      }
      return { messages: msgs };
    }),

  setIsStreaming: (streaming) => set({ isStreaming: streaming }),

  setSearchFilter: (filter) =>
    set((s) => ({ searchFilter: { ...s.searchFilter, ...filter } })),

  clearMessages: () => set({ messages: [] }),
}));
```

- [ ] **Step 4: useRagStream 훅**

```typescript
// frontend/src/features/rag/hooks.ts
"use client";

import { useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { askRag } from "./api";
import { useRagStore } from "./store";
import type {
  SSEThinkingEvent,
  SSESearchResultsEvent,
  SSEAnswerEvent,
  SSEDoneEvent,
} from "./types";

export function useRagStream() {
  const { getToken } = useAuth();
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const {
    addMessage,
    updateLastAssistantMessage,
    setSourcesOnLastAssistant,
    setIsStreaming,
    searchFilter,
  } = useRagStore();

  const ask = useCallback(
    async (question: string) => {
      if (!wid) return;

      const token = await getToken();
      if (!token) return;

      // 사용자 메시지 추가
      addMessage({
        id: crypto.randomUUID(),
        role: "user",
        content: question,
        createdAt: new Date().toISOString(),
      });

      // 어시스턴트 메시지 플레이스홀더
      addMessage({
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        isStreaming: true,
        createdAt: new Date().toISOString(),
      });

      setIsStreaming(true);

      try {
        const response = await askRag(token, wid, {
          question,
          projectId: searchFilter.projectId ?? null,
          timeRange: searchFilter.timeRange ?? null,
          sourceType: searchFilter.sourceType ?? null,
        });

        const reader = response.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let currentEvent = "";
          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              const data = line.slice(5).trim();
              if (!data) continue;

              try {
                const parsed = JSON.parse(data);
                switch (currentEvent) {
                  case "thinking":
                    // 검색 중 상태 (UI에서 로딩 표시)
                    break;
                  case "search_results": {
                    const sr = parsed as SSESearchResultsEvent;
                    setSourcesOnLastAssistant(sr.chunks);
                    break;
                  }
                  case "answer": {
                    const ans = parsed as SSEAnswerEvent;
                    updateLastAssistantMessage(ans.token);
                    break;
                  }
                  case "done":
                    break;
                }
              } catch {
                // JSON 파싱 실패 무시
              }
            }
          }
        }
      } catch (error) {
        updateLastAssistantMessage(
          "오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        );
      } finally {
        setIsStreaming(false);
      }
    },
    [wid, getToken, addMessage, updateLastAssistantMessage, setSourcesOnLastAssistant, setIsStreaming, searchFilter]
  );

  return { ask };
}
```

- [ ] **Step 5: RAG 컴포넌트 구현**

각 컴포넌트의 전체 코드를 작성합니다. 설계 문서의 UI 명세에 따라 구현하되, DESIGN.md의 CSS 변수 체계를 사용합니다:

**RagMessage, RagSources, RagChat, RagInput, SearchScope, RagHome 컴포넌트 + RagPanel 교체**

> 이 단계는 6개 컴포넌트를 생성/수정합니다. 각 컴포넌트는 기존 features/rag/components/ 패턴을 따릅니다. 상세 코드는 구현 시 DESIGN.md + 기존 컴포넌트 패턴 참조.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/features/rag/ frontend/src/components/layout/rag-panel.tsx
git commit -m "feat: RAG 채팅 UI — SSE 스트리밍 + 소스 표시 + 검색 필터"
```

---

### Task 7: Slice 2 E2E 검증

- [ ] **Step 1: 백엔드 서버 시작**

```bash
cd backend && uv run uvicorn src.main:app --reload
```

- [ ] **Step 2: 프론트엔드 서버 시작**

```bash
cd frontend && pnpm dev
```

- [ ] **Step 3: 검증 시나리오**

1. 회의 업로드 → 파이프라인 완료 → DB에서 embedding_chunks 확인
2. RAG 패널에서 질문 → 스트리밍 답변 + 소스 표시 확인
3. SearchScope 필터 변경 후 질문 → 필터 적용 확인

- [ ] **Step 4: 커밋 (필요 시 버그 수정)**

```bash
git add -A && git commit -m "fix: Slice 2 E2E 검증 후 수정"
```

---

## Slice 3: Semantic Cache

### Task 8: 캐시 동작 검증

캐시 로직은 이미 RagService에 포함되어 있습니다 (Task 5). 이 Task는 캐시 동작을 독립 테스트합니다.

**Files:**
- Create: `backend/tests/rag/test_cache.py`

- [ ] **Step 1: 캐시 테스트 작성**

```python
# backend/tests/rag/test_cache.py
"""Semantic Cache 동작 테스트."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_answer():
    """similarity >= 0.93 → 캐시 답변 반환, Gemini 호출 없음."""
    from src.rag.service import RagService

    mock_repo = AsyncMock()
    mock_repo.find_similar_cache.return_value = {
        "id": "cache-1",
        "answer": "캐시된 답변입니다.",
        "sources": [{"id": "s1", "text": "소스", "source": "회의"}],
        "hit_count": 1,
    }

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]

    mock_ai = AsyncMock()

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    import uuid
    events = []
    async for event in service.ask("테스트 질문", uuid.uuid4()):
        events.append(event)

    # Gemini 호출 없어야 함
    mock_ai.stream_rag_answer.assert_not_called()

    # done 이벤트에 cached=True
    done_event = [e for e in events if e["event"] == "done"][0]
    assert '"cached": true' in done_event["data"]


@pytest.mark.asyncio
async def test_cache_miss_calls_gemini():
    """캐시 미스 → Hybrid Search + Gemini 호출."""
    from src.rag.service import RagService

    mock_repo = AsyncMock()
    mock_repo.find_similar_cache.return_value = None
    mock_repo.vector_search.return_value = []
    mock_repo.text_search.return_value = []

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]

    mock_ai = AsyncMock()

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    import uuid
    events = []
    async for event in service.ask("테스트 질문", uuid.uuid4()):
        events.append(event)

    # 검색 결과 없으면 "정보 없음" 답변
    answer_event = [e for e in events if e["event"] == "answer"][0]
    assert "찾지 못했습니다" in answer_event["data"]
```

- [ ] **Step 2: 테스트 실행**

```bash
cd backend && uv run pytest tests/rag/test_cache.py -v
```

Expected: PASS

- [ ] **Step 3: 커밋**

```bash
git add backend/tests/rag/
git commit -m "test: Semantic Cache 동작 테스트 — HIT/MISS 시나리오"
```

---

## Slice 4: 노트 도메인 (BE + FE)

### Task 9: Note CRUD Backend

**Files:**
- Create: `backend/src/notes/repository.py`
- Create: `backend/src/notes/service.py`
- Create: `backend/src/notes/router.py`
- Create: `backend/src/notes/schemas.py`
- Create: `backend/src/notes/dependencies.py`
- Create: `backend/src/notes/exceptions.py`
- Modify: `backend/src/main.py`
- Create: `backend/tests/notes/__init__.py`
- Create: `backend/tests/notes/test_notes_api.py`

- [ ] **Step 1: Note 스키마**

```python
# backend/src/notes/schemas.py
"""노트 요청/응답 스키마."""
from pydantic import BaseModel, Field


class CreateNoteRequest(BaseModel):
    title: str = ""
    content: dict = Field(default_factory=dict)
    project_id: str | None = Field(default=None, alias="projectId")

    model_config = {"populate_by_name": True}


class UpdateNoteRequest(BaseModel):
    title: str | None = None
    content: dict | None = None
    project_id: str | None = Field(default=None, alias="projectId")

    model_config = {"populate_by_name": True}
```

- [ ] **Step 2: Note Repository**

```python
# backend/src/notes/repository.py
"""노트 DB 접근."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.notes.models import Note


class NoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, note: Note) -> Note:
        self.session.add(note)
        await self.session.flush()
        return note

    async def find_by_id(self, note_id: uuid.UUID) -> Note | None:
        result = await self.session.execute(
            select(Note).where(Note.id == note_id)
        )
        return result.scalar_one_or_none()

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Note]:
        stmt = select(Note).where(Note.workspace_id == workspace_id)
        if project_id:
            stmt = stmt.where(Note.project_id == project_id)
        stmt = stmt.order_by(Note.updated_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Note)
            .where(Note.workspace_id == workspace_id)
        )
        if project_id:
            stmt = stmt.where(Note.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete(self, note: Note) -> None:
        await self.session.delete(note)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
```

- [ ] **Step 3: Note Service**

```python
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
        total = await self.repo.count_by_workspace(workspace_id, project_id=project_id)
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
        project_id: uuid.UUID | None = ...,  # sentinel: None = 연결 해제
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
            note.project_id = project_id

        note.updated_at = datetime.utcnow()
        note = await self.repo.save(note)
        await self.repo.commit()
        return self._to_dict(note)

    async def delete_note(self, note_id: uuid.UUID) -> None:
        note = await self.repo.find_by_id(note_id)
        if note is None:
            raise NoteNotFoundError()

        # 관련 임베딩 삭제
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
```

- [ ] **Step 4: Note Router + Dependencies + Exceptions**

```python
# backend/src/notes/exceptions.py
from src.common.exceptions import NotFoundError

class NoteNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("노트")
```

```python
# backend/src/notes/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.notes.repository import NoteRepository
from src.notes.service import NoteService


async def get_note_service(
    session: AsyncSession = Depends(get_async_session),
) -> NoteService:
    embedding_repo = EmbeddingRepository(session)
    return NoteService(
        repo=NoteRepository(session),
        embedding_service=EmbeddingService(embedding_repo),
    )
```

```python
# backend/src/notes/router.py
"""노트 CRUD 엔드포인트."""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.notes.dependencies import get_note_service
from src.notes.schemas import CreateNoteRequest, UpdateNoteRequest
from src.notes.service import NoteService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/notes",
    tags=["notes"],
)


@router.get("")
async def list_notes(
    workspace_id: uuid.UUID,
    project_id: str | None = Query(default=None, alias="projectId"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    service: NoteService = Depends(get_note_service),
):
    pid = uuid.UUID(project_id) if project_id else None
    return await service.list_notes(workspace_id, project_id=pid, page=page, page_size=page_size)


@router.get("/{note_id}")
async def get_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: NoteService = Depends(get_note_service),
):
    return await service.get_note(note_id)


@router.post("", status_code=201)
async def create_note(
    workspace_id: uuid.UUID,
    data: CreateNoteRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: NoteService = Depends(get_note_service),
):
    pid = uuid.UUID(data.project_id) if data.project_id else None
    result = await service.create_note(
        workspace_id=workspace_id,
        created_by_id=current_user.id,
        title=data.title,
        content=data.content,
        project_id=pid,
    )
    # 비동기 임베딩
    background_tasks.add_task(service.embed_note_async, uuid.UUID(result["id"]))
    return result


@router.patch("/{note_id}")
async def update_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    data: UpdateNoteRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: NoteService = Depends(get_note_service),
):
    pid = ...  # sentinel: 필드 없으면 변경 안 함
    if data.project_id is not None:
        pid = uuid.UUID(data.project_id) if data.project_id else None

    result = await service.update_note(
        note_id=note_id,
        title=data.title,
        content=data.content,
        project_id=pid,
    )
    # 내용 변경 시 재임베딩
    if data.content is not None:
        background_tasks.add_task(service.embed_note_async, note_id)
    return result


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: NoteService = Depends(get_note_service),
):
    await service.delete_note(note_id)
```

- [ ] **Step 5: main.py에 노트 라우터 등록**

```python
from src.notes.router import router as notes_router
app.include_router(notes_router)
```

- [ ] **Step 6: 테스트 작성 + 실행**

```python
# backend/tests/notes/__init__.py
# (빈 파일)
```

```python
# backend/tests/notes/test_notes_api.py
"""노트 API 통합 테스트."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.auth.dependencies import get_current_user
from src.notes.dependencies import get_note_service


@pytest_asyncio.fixture
async def mock_user():
    user = MagicMock()
    user.id = "00000000-0000-0000-0000-000000000001"
    user.clerk_id = "clerk_test"
    user.email = "test@test.com"
    return user


@pytest_asyncio.fixture
async def client(mock_user):
    mock_service = AsyncMock()
    mock_service.create_note.return_value = {
        "id": "00000000-0000-0000-0000-000000000010",
        "workspaceId": "00000000-0000-0000-0000-000000000002",
        "projectId": None,
        "title": "테스트 노트",
        "content": {},
        "plainText": "",
        "createdById": str(mock_user.id),
        "createdAt": "2026-04-02T00:00:00",
        "updatedAt": "2026-04-02T00:00:00",
    }
    mock_service.list_notes.return_value = {
        "items": [],
        "total": 0,
        "page": 1,
        "pageSize": 20,
        "hasNext": False,
    }
    mock_service.embed_note_async = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_note_service] = lambda: mock_service

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_note(client):
    wid = "00000000-0000-0000-0000-000000000002"
    res = await client.post(
        f"/api/v1/workspaces/{wid}/notes",
        json={"title": "테스트 노트"},
    )
    assert res.status_code == 201
    assert res.json()["title"] == "테스트 노트"


@pytest.mark.asyncio
async def test_list_notes(client):
    wid = "00000000-0000-0000-0000-000000000002"
    res = await client.get(f"/api/v1/workspaces/{wid}/notes")
    assert res.status_code == 200
    assert "items" in res.json()
```

```bash
cd backend && uv run pytest tests/notes/ -v
```

Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add backend/src/notes/ backend/tests/notes/ backend/src/main.py
git commit -m "feat: Note CRUD API — 5개 엔드포인트 + 비동기 임베딩"
```

---

### Task 10: 프론트엔드 노트 기능

**Files:**
- Create: `frontend/src/features/notes/types.ts`
- Create: `frontend/src/features/notes/api.ts`
- Create: `frontend/src/features/notes/hooks.ts`
- Create: `frontend/src/features/notes/components/note-editor.tsx`
- Create: `frontend/src/features/notes/components/note-list.tsx`
- Modify: `frontend/src/app/(app)/projects/[id]/page.tsx` (노트 탭 추가)
- Modify: `frontend/src/components/layout/sidebar.tsx` (노트 메뉴 추가)
- Modify: `frontend/package.json` (Tiptap 의존성)

- [ ] **Step 1: Tiptap 의존성 설치**

```bash
cd frontend && pnpm add @tiptap/react @tiptap/starter-kit @tiptap/extension-placeholder @tiptap/extension-character-count
```

- [ ] **Step 2: 노트 타입 + API + 훅**

```typescript
// frontend/src/features/notes/types.ts
import type { UUID, Timestamped } from "@/types";

export interface Note extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  projectId: UUID | null;
  title: string;
  content: Record<string, unknown>;
  plainText: string;
  createdById: UUID;
}

export interface CreateNoteRequest {
  title?: string;
  content?: Record<string, unknown>;
  projectId?: string | null;
}

export interface UpdateNoteRequest {
  title?: string;
  content?: Record<string, unknown>;
  projectId?: string | null;
}
```

```typescript
// frontend/src/features/notes/api.ts
import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type { Note, CreateNoteRequest, UpdateNoteRequest } from "./types";

export const noteKeys = {
  all: ["notes"] as const,
  list: (wid: string, projectId?: string) =>
    [...noteKeys.all, "list", wid, projectId ?? "all"] as const,
  detail: (wid: string, id: string) =>
    [...noteKeys.all, "detail", wid, id] as const,
};

export async function fetchNotes(
  token: string,
  wid: string,
  projectId?: string,
  page?: number,
): Promise<PaginatedResponse<Note>> {
  const params = new URLSearchParams();
  if (projectId) params.set("projectId", projectId);
  if (page) params.set("page", String(page));
  const query = params.toString();
  return apiClient<PaginatedResponse<Note>>(
    `/workspaces/${wid}/notes${query ? `?${query}` : ""}`,
    { token },
  );
}

export async function fetchNote(
  token: string,
  wid: string,
  id: string,
): Promise<Note> {
  return apiClient<Note>(`/workspaces/${wid}/notes/${id}`, { token });
}

export async function createNote(
  token: string,
  wid: string,
  data: CreateNoteRequest,
): Promise<Note> {
  return apiClient<Note>(`/workspaces/${wid}/notes`, {
    token,
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateNote(
  token: string,
  wid: string,
  id: string,
  data: UpdateNoteRequest,
): Promise<Note> {
  return apiClient<Note>(`/workspaces/${wid}/notes/${id}`, {
    token,
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteNote(
  token: string,
  wid: string,
  id: string,
): Promise<void> {
  return apiClient<void>(`/workspaces/${wid}/notes/${id}`, {
    token,
    method: "DELETE",
  });
}
```

```typescript
// frontend/src/features/notes/hooks.ts
"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { noteKeys, fetchNotes, fetchNote, createNote, updateNote, deleteNote } from "./api";
import type { CreateNoteRequest, UpdateNoteRequest } from "./types";

export function useNotes(wid: string | undefined, projectId?: string) {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: noteKeys.list(wid ?? "", projectId),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchNotes(token, wid!, projectId);
    },
    enabled: !!wid,
  });
}

export function useNote(wid: string | undefined, id: string) {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: noteKeys.detail(wid ?? "", id),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchNote(token, wid!, id);
    },
    enabled: !!wid,
  });
}

export function useCreateNote(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateNoteRequest) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return createNote(token, wid!, data);
    },
    onSuccess: () => {
      if (wid) queryClient.invalidateQueries({ queryKey: noteKeys.all });
    },
  });
}

export function useUpdateNote(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateNoteRequest }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return updateNote(token, wid!, id, data);
    },
    onSuccess: (_data, variables) => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: noteKeys.detail(wid, variables.id) });
        queryClient.invalidateQueries({ queryKey: noteKeys.all });
      }
    },
  });
}

export function useDeleteNote(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return deleteNote(token, wid!, id);
    },
    onSuccess: () => {
      if (wid) queryClient.invalidateQueries({ queryKey: noteKeys.all });
    },
  });
}
```

- [ ] **Step 3: Tiptap 노트 에디터 컴포넌트**

```typescript
// frontend/src/features/notes/components/note-editor.tsx
"use client";

import { useCallback, useEffect, useRef } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import CharacterCount from "@tiptap/extension-character-count";
import { useUpdateNote } from "../hooks";

interface NoteEditorProps {
  noteId: string;
  workspaceId: string;
  initialTitle: string;
  initialContent: Record<string, unknown>;
}

export function NoteEditor({
  noteId,
  workspaceId,
  initialTitle,
  initialContent,
}: NoteEditorProps) {
  const updateNote = useUpdateNote(workspaceId);
  const titleRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: "내용을 입력하세요..." }),
      CharacterCount,
    ],
    content: initialContent as Record<string, unknown>,
    onUpdate: ({ editor }) => {
      // debounce 500ms 자동저장
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        updateNote.mutate({
          id: noteId,
          data: { content: editor.getJSON() },
        });
      }, 500);
    },
  });

  const handleTitleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        updateNote.mutate({
          id: noteId,
          data: { title: e.target.value },
        });
      }, 500);
    },
    [noteId, updateNote],
  );

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <div className="flex flex-col h-full">
      <input
        ref={titleRef}
        defaultValue={initialTitle}
        onChange={handleTitleChange}
        placeholder="제목 없음"
        className="w-full bg-transparent text-xl font-semibold outline-none px-4 py-3 border-b"
        style={{
          color: "var(--text-primary)",
          fontFamily: "var(--font-display)",
          borderColor: "var(--border-subtle)",
        }}
      />
      <div className="flex-1 overflow-y-auto px-4 py-3">
        <EditorContent
          editor={editor}
          className="prose prose-invert max-w-none text-sm"
          style={{ color: "var(--text-primary)" }}
        />
      </div>
      {editor && (
        <div
          className="px-4 py-2 text-xs border-t"
          style={{ color: "var(--text-muted)", borderColor: "var(--border-subtle)" }}
        >
          {editor.storage.characterCount.characters()} 자
          {updateNote.isPending && " · 저장 중..."}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 노트 목록 컴포넌트**

```typescript
// frontend/src/features/notes/components/note-list.tsx
"use client";

import { useNotes, useCreateNote } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import type { Note } from "../types";

interface NoteListProps {
  projectId?: string;
  onSelect: (noteId: string) => void;
}

export function NoteList({ projectId, onSelect }: NoteListProps) {
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const { data, isLoading } = useNotes(wid ?? undefined, projectId);
  const createNote = useCreateNote(wid ?? undefined);

  const handleCreate = async () => {
    const result = await createNote.mutateAsync({
      title: "",
      projectId: projectId ?? null,
    });
    onSelect(result.id);
  };

  if (isLoading) {
    return (
      <div className="p-4 text-sm" style={{ color: "var(--text-muted)" }}>
        로딩 중...
      </div>
    );
  }

  const notes = data?.items ?? [];

  return (
    <div className="flex flex-col">
      <div className="px-4 py-3 border-b flex items-center justify-between"
        style={{ borderColor: "var(--border-subtle)" }}>
        <h3 className="text-sm font-semibold"
          style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}>
          노트
        </h3>
        <button
          onClick={handleCreate}
          className="text-xs px-2 py-1 rounded"
          style={{ background: "var(--accent)", color: "var(--background)", borderRadius: "var(--radius-sm)" }}
        >
          + 새 노트
        </button>
      </div>
      {notes.length === 0 ? (
        <div className="p-4 text-sm text-center" style={{ color: "var(--text-muted)" }}>
          아직 노트가 없습니다
        </div>
      ) : (
        <div className="flex flex-col">
          {notes.map((note: Note) => (
            <button
              key={note.id}
              onClick={() => onSelect(note.id)}
              className="text-left px-4 py-3 border-b transition-colors hover:opacity-80"
              style={{ borderColor: "var(--border-subtle)" }}
            >
              <div className="text-sm font-medium truncate"
                style={{ color: "var(--text-primary)" }}>
                {note.title || "제목 없음"}
              </div>
              <div className="text-xs mt-1 truncate"
                style={{ color: "var(--text-muted)" }}>
                {note.plainText?.slice(0, 80) || "내용 없음"}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: 프로젝트 상세 페이지에 노트 탭 추가**

`frontend/src/features/projects/components/project-detail.tsx`에 노트 탭 추가. 기존 TABS 상수에 `"노트"` 추가하고, 노트 탭 선택 시 `NoteList` + `NoteEditor` 렌더링.

- [ ] **Step 6: 사이드바에 노트 메뉴 추가**

`frontend/src/components/layout/sidebar.tsx`에 "노트" 네비게이션 항목 추가 (FileText 아이콘).

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/features/notes/ frontend/src/features/projects/components/project-detail.tsx frontend/src/components/layout/sidebar.tsx frontend/package.json frontend/pnpm-lock.yaml
git commit -m "feat: 노트 기능 — Tiptap 에디터 + debounce 자동저장 + CRUD"
```

---

### Task 11: Slice 4 E2E 검증

- [ ] **Step 1: 검증 시나리오**

1. 프로젝트 상세 → 노트 탭 → 새 노트 생성
2. Tiptap 에디터에 내용 입력 → 500ms 후 자동저장 확인
3. 저장된 노트가 RAG 검색에 포함되는지 확인
4. 노트 삭제 → 임베딩도 삭제 확인

- [ ] **Step 2: 커밋 (필요 시 버그 수정)**

```bash
git add -A && git commit -m "fix: Slice 4 E2E 검증 후 수정"
```

---

## Slice 5: Polish

### Task 12: Cmd+K RAG 통합 + 신선도 + Archive

**Files:**
- Modify: `frontend/src/components/layout/cmd-k.tsx`
- Modify: `frontend/src/features/rag/components/rag-sources.tsx` (신선도 표시)
- Modify: `frontend/src/features/projects/components/project-detail.tsx` (Archive 버튼)

- [ ] **Step 1: Cmd+K에 RAG 모드 추가**

`frontend/src/components/layout/cmd-k.tsx`에:
- `?` 접두사 입력 시 RAG 질문 모드로 전환
- RAG 모드에서 Enter → `useRagStream().ask()` 호출 + RAG 패널 열기

- [ ] **Step 2: 소스 신선도 표시**

`rag-sources.tsx`에서 `freshness` 필드 기반 스타일링:
- `"recent"`: 표시 없음
- `"normal"`: `text-muted` 색상 + "N개월 전 기반"
- `"stale"`: `text-warning` 색상 + "⚠️ 오래된 소스입니다"

- [ ] **Step 3: Archive 버튼**

프로젝트 상세에 Archive 버튼 추가. 확인 다이얼로그 → `useUpdateProject` 으로 `status: "archived"` 변경.

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/components/layout/cmd-k.tsx frontend/src/features/rag/ frontend/src/features/projects/
git commit -m "feat: Cmd+K RAG 통합 + 신선도 표시 + Archive 버튼"
```

---

### Task 13: 전체 QA + 문서 업데이트

- [ ] **Step 1: 전체 흐름 QA**

1. 회의 업로드 → AI 요약 → 임베딩 생성 ✅
2. RAG 질문 → 스트리밍 답변 + 소스 ✅
3. Semantic Cache (동일 질문 재시도) ✅
4. 노트 생성/수정 → 자동저장 → RAG 검색 ✅
5. Cmd+K RAG 모드 ✅
6. 소스 신선도 표시 ✅
7. Archive → RAG 포함 확인 ✅

- [ ] **Step 2: endpoints.md 업데이트**

`docs/api/endpoints.md`에 Sprint 3 엔드포인트 추가:
- `POST /workspaces/{wid}/rag/ask` (SSE)
- `GET/POST/PATCH/DELETE /workspaces/{wid}/notes`

- [ ] **Step 3: PRD 현재 컨텍스트 업데이트**

`docs/requirements/prd.md` §8 현재 컨텍스트 업데이트.

- [ ] **Step 4: 커밋**

```bash
git add docs/
git commit -m "docs: Sprint 3 문서 업데이트 — endpoints.md, prd.md"
```

---

## Sprint 4+ 후보 (명시적 제외 기록)

아래 항목은 Sprint 3에서 의도적으로 제외되었다. Sprint 4 계획 시 재검토.

| 항목 | 이유 | 재검토 조건 |
|------|------|------------|
| Cohere Rerank v3 | RRF Top-10으로 MVP 충분 | RAG 품질 부족 시 |
| 노트 Inbox 연동 | 수동 프로젝트 연결로 시작 | Sprint 4 Inbox 확장 시 |
| 2-Layer 승격 모델 | ADR-004 미결정 (복사 vs 링크) | 상세 기획 확정 후 |
| L3 프로젝트 인사이트 | 별도 프롬프트 + UI 필요 | Archive UX 고도화 시 |
| Query Expansion/Rewriting | rag-pipeline.md Phase 4 | 검색 품질 개선 필요 시 |
| Cross-project RAG | 조직 전체 검색 | 워크스페이스 규모 확대 시 |
