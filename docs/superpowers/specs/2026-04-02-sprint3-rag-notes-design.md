# Sprint 3 설계: RAG + 노트 — "질문할 수 있는 지식"

> **날짜:** 2026-04-02
> **상태:** 설계 리뷰 중
> **근거 문서:** PRD §Sprint 3, `rag-pipeline.md`, `second-brain.md`, `ADR-004`
> **접근법:** RAG-First Vertical Slice

---

## 1. 목표

> "지난 회의에서 CMS 관련 결정이 뭐였지?" → 2초 내 스트리밍 답변

기존 회의/노트/액션 데이터를 자연어로 질문 가능한 지식 자산으로 전환한다.

### 핵심 가치 흐름

```
[기존 Sprint 1-2]
  회의 업로드 → STT → AI 요약 → 액션 추출 → Inbox → 프로젝트 연결

[Sprint 3 추가]
  → 임베딩 생성 (계층적 청킹)
  → RAG 검색 (Hybrid Search + SSE 스트리밍)
  → 노트 작성 + 자동 임베딩
  → Semantic Cache (비용/성능 최적화)
```

---

## 2. 설계 결정 요약

| 결정 | 선택 | 근거 |
|------|------|------|
| 검색 방식 | Hybrid (pg_trgm + pgvector + RRF) | 이름(키워드) + 의미(시맨틱) 모두 커버 |
| Re-ranking | **Sprint 3 제외** → Sprint 4+ 후보 | MVP에서 RRF Top-10 충분. Cohere API 의존성/비용 추가 불필요 |
| 벡터 DB | PostgreSQL (pgvector) | 소규모 (~1K-20K chunks/workspace), 별도 인프라 불필요 |
| 임베딩 모델 | OpenAI text-embedding-3-small (1536d) | 기존 설계 유지 |
| LLM | Gemini gemini-2.5-flash (고정) | 프로젝트 제약사항 |
| SSE 구현 | sse-starlette | SSE 표준 준수 (event/data/id), PRD 이벤트 타입 구분 필요 |
| Note.project_id | nullable | CODE 철학 "마찰 최소화". 프로젝트 없이도 노트 생성 가능 |
| 노트 에디터 | Tiptap (StarterKit + Placeholder + CharacterCount) | PRD 명세 |
| 노트 Inbox 연동 | **Sprint 3 제외** → Sprint 4+ 후보 | 수동 프로젝트 연결로 시작, AI 추천은 추후 |
| 2-Layer 승격 모델 | **Sprint 3 제외** → Sprint 4+ 후보 | ADR-004 미결정 사항 (복사 vs 링크 등) |
| Archive 인사이트 | **Sprint 3 제외** → Sprint 4+ 후보 | L3 프로젝트 인사이트 = 별도 프롬프트+UI 필요 |
| Archive 전환 | status 변경만 + RAG 검색 포함 | 기존 PATCH API로 충분 |
| Semantic Cache 임계값 | similarity ≥ 0.93 | rag-pipeline.md 설계 유지 |
| Cache TTL | 7일 | rag-pipeline.md 설계 유지 |

---

## 3. 데이터 모델

### 3.1 EmbeddingChunk (새 테이블)

```sql
CREATE TABLE embedding_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    project_id UUID REFERENCES projects(id),
    source_id UUID NOT NULL,
    source_type VARCHAR NOT NULL,  -- 'meeting' | 'note' | 'action'
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_level INTEGER NOT NULL DEFAULT 2,  -- 0=문서, 1=섹션/화자, 2=문단(검색 대상)
    parent_chunk_id UUID REFERENCES embedding_chunks(id),
    embedding vector(1536) NOT NULL,
    metadata JSONB DEFAULT '{}',  -- speaker, start_sec, end_sec, topic
    created_at TIMESTAMP DEFAULT now()
);

-- 인덱스
CREATE INDEX idx_chunks_workspace ON embedding_chunks(workspace_id);
CREATE INDEX idx_chunks_project ON embedding_chunks(project_id);
CREATE INDEX idx_chunks_source ON embedding_chunks(source_type, source_id);
CREATE INDEX idx_chunks_parent ON embedding_chunks(parent_chunk_id);
CREATE INDEX idx_chunks_level ON embedding_chunks(chunk_level);
CREATE INDEX idx_chunks_vector ON embedding_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_chunks_trgm ON embedding_chunks
    USING gin (chunk_text gin_trgm_ops);
```

### 3.2 SemanticCache (새 테이블)

```sql
CREATE TABLE semantic_caches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    project_id UUID REFERENCES projects(id),
    question TEXT NOT NULL,
    question_embedding vector(1536) NOT NULL,
    answer TEXT NOT NULL,
    sources JSONB NOT NULL DEFAULT '[]',
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now(),
    expires_at TIMESTAMP DEFAULT (now() + INTERVAL '7 days')
);

CREATE INDEX idx_cache_embedding ON semantic_caches
    USING ivfflat (question_embedding vector_cosine_ops);
CREATE INDEX idx_cache_workspace ON semantic_caches(workspace_id);
CREATE INDEX idx_cache_expires ON semantic_caches(expires_at);
```

### 3.3 Note (새 테이블)

```sql
CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    project_id UUID REFERENCES projects(id),  -- nullable: CODE 철학
    title VARCHAR NOT NULL DEFAULT '',
    content JSONB DEFAULT '{}',               -- Tiptap JSON
    plain_text TEXT DEFAULT '',               -- 임베딩용 평문
    created_by_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_notes_workspace ON notes(workspace_id);
CREATE INDEX idx_notes_project ON notes(project_id);
CREATE INDEX idx_notes_created_by ON notes(created_by_id);
```

### 3.4 기존 테이블 변경

없음. `source_type + source_id` 폴리모픽 참조로 기존 모델 수정 불필요.

---

## 4. 임베딩 파이프라인

### 4.1 계층적 청킹 전략

**회의:**
```
Level 0: 회의 전체 (메타데이터: 제목, 일시, 참여자)
  └── Level 1: 화자 구간 (TranscriptSegment 그룹, speaker + 시간대)
      └── Level 2: 문단 (300-500자, 50자 오버랩) ← 검색 대상
```

**노트:**
```
Level 0: 노트 전체 (메타데이터: 제목, 작성자)
  └── Level 1: 섹션/헤딩 단위
      └── Level 2: 문단 (300-500자, 50자 오버랩) ← 검색 대상
```

### 4.2 임베딩 생성 시점

| 트리거 | 동작 |
|--------|------|
| 회의 파이프라인 완료 (status=completed) | 트랜스크립트 → 청킹 → 임베딩 저장 |
| 노트 저장 (debounce 후) | plain_text → 청킹 → 기존 청크 삭제 → 재생성 |
| 노트 project_id 변경 | 해당 청크의 project_id 일괄 업데이트 |

### 4.3 서비스 구조

```
backend/src/embeddings/
├── models.py      — EmbeddingChunk, SemanticCache (SQLModel)
├── repository.py  — EmbeddingRepository (벡터/텍스트 검색 쿼리)
├── service.py     — EmbeddingService
│   ├── chunk_meeting(meeting_id)
│   ├── chunk_note(note_id)
│   ├── generate_embeddings(texts: list[str]) → list[list[float]]
│   ├── save_chunks(chunks: list[EmbeddingChunk])
│   └── delete_by_source(source_type, source_id)
├── dependencies.py
└── exceptions.py
```

- OpenAI `text-embedding-3-small` batch 호출 (최대 2048 토큰/청크)
- 회의 임베딩: `MeetingPipelineService` 마지막 단계로 추가
- 노트 임베딩: `BackgroundTasks` 비동기 처리

### 4.4 캐시 무효화

| 이벤트 | 무효화 범위 |
|--------|------------|
| 새 회의 임베딩 완료 | 해당 project_id의 semantic_caches 삭제 |
| 노트 수정/생성 | 해당 project_id의 semantic_caches 삭제 |
| 임베딩 전체 재생성 | workspace 전체 캐시 삭제 |

---

## 5. RAG 검색 파이프라인

### 5.1 전체 흐름 (5-Layer, Rerank 제외)

```
사용자 질문
  → [1] Semantic Cache (similarity ≥ 0.93)
      HIT → 캐시 답변 즉시 반환 (~50ms)
      MISS → 계속
  → [2] Query Processing
      workspace_id (필수) + project_id, time_range, source_type (선택)
  → [3] Hybrid Search
      Full-text (pg_trgm) Top-50 + Vector (pgvector) Top-50
      → RRF 융합 → Top-10
  → [4] Context Enrichment
      Top-10 Level 2 청크 → parent Level 1 자동 포함
      소스 메타데이터 첨부 (회의명, 날짜, 화자, 신선도)
  → [5] Generation (Gemini gemini-2.5-flash, SSE)
      System prompt + Top-10 + 질문 → 스트리밍 답변
  → [6] Cache Store
      질문 임베딩 + 답변 + 소스 → 7일 TTL 저장
```

### 5.2 Hybrid Search 상세

**Full-text (pg_trgm):**
```sql
SELECT id, chunk_text,
       similarity(chunk_text, :query) AS text_score
FROM embedding_chunks
WHERE workspace_id = :wid
  AND chunk_level = 2
  AND chunk_text % :query
ORDER BY text_score DESC
LIMIT 50;
```

**Vector (pgvector):**
```sql
SELECT id, chunk_text,
       1 - (embedding <=> :query_vector) AS vector_score
FROM embedding_chunks
WHERE workspace_id = :wid
  AND chunk_level = 2
ORDER BY embedding <=> :query_vector
LIMIT 50;
```

**RRF 융합:**
```python
def reciprocal_rank_fusion(
    text_results: list[SearchResult],
    vector_results: list[SearchResult],
    k: int = 60,
    top_n: int = 10,
) -> list[SearchResult]:
    scores: dict[str, float] = {}
    for rank, r in enumerate(text_results):
        scores[r.id] = scores.get(r.id, 0) + 1 / (k + rank + 1)
    for rank, r in enumerate(vector_results):
        scores[r.id] = scores.get(r.id, 0) + 1 / (k + rank + 1)
    sorted_ids = sorted(scores, key=scores.get, reverse=True)
    return [get_result(id) for id in sorted_ids[:top_n]]
```

### 5.3 SSE 이벤트 시퀀스

```
event: thinking
data: {"status": "검색 중..."}

event: search_results
data: {"chunks": [{"id", "text", "source", "date", "speaker", "score"}]}

event: answer
data: {"token": "3/20 킥오프 회의에서..."}

event: done
data: {"cached": false, "sourceCount": 5}
```

### 5.4 API 명세

```
POST /api/v1/workspaces/{wid}/rag/ask
Content-Type: application/json
Authorization: Bearer <JWT>

Request:
{
  "question": "CMS 개발 진행 상황은?",
  "projectId": "uuid" | null,
  "timeRange": "1m" | "3m" | "6m" | null,
  "sourceType": "meeting" | "note" | null
}

Response: 200 OK
Content-Type: text/event-stream
```

### 5.5 프롬프트 관리

`backend/src/common/prompts.py`에 추가:

- `RAG_SYSTEM_PROMPT` — 소스 기반 답변, 출처 인용 필수, 소스에 없으면 "정보 없음"
- 지식 신선도: 3개월+ 소스에 "오래된 소스" 경고 포함 (ADR-004 §Slite 벤치마킹)

### 5.6 서비스 구조

```
backend/src/rag/
├── router.py       — POST /rag/ask (SSE, sse-starlette)
├── service.py      — RagService
│   ├── ask(question, filters) → AsyncGenerator[SSE events]
│   ├── _check_cache()
│   ├── _hybrid_search()
│   ├── _enrich_context()
│   ├── _generate_answer() → Gemini 스트리밍
│   └── _store_cache()
├── repository.py   — RagRepository (벡터/텍스트 검색)
├── schemas.py
├── dependencies.py
└── exceptions.py
```

---

## 6. 노트 도메인

### 6.1 API 명세

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/workspaces/{wid}/notes` | 전체 노트 (page, pageSize, projectId 필터) |
| `GET` | `/workspaces/{wid}/notes/{id}` | 노트 상세 |
| `POST` | `/workspaces/{wid}/notes` | 노트 생성 (projectId 선택적) |
| `PATCH` | `/workspaces/{wid}/notes/{id}` | 노트 수정 (debounce 자동저장) |
| `DELETE` | `/workspaces/{wid}/notes/{id}` | 노트 삭제 (204) |

### 6.2 서비스 구조

```
backend/src/notes/
├── models.py       — Note (SQLModel)
├── router.py
├── service.py      — NoteService
│   ├── create_note() — plain_text 추출 + 저장 + BackgroundTasks 임베딩
│   ├── update_note() — plain_text 재추출 + BackgroundTasks 재임베딩
│   └── delete_note() — 삭제 + 관련 청크 삭제
├── repository.py   — NoteRepository
├── schemas.py
├── dependencies.py
└── exceptions.py
```

### 6.3 Tiptap JSON → plain_text

```python
def extract_plain_text(tiptap_json: dict) -> str:
    """Tiptap JSON에서 텍스트만 재귀 추출"""
    texts = []
    for node in tiptap_json.get("content", []):
        if "text" in node:
            texts.append(node["text"])
        if "content" in node:
            texts.append(extract_plain_text(node))
    return "\n".join(texts)
```

---

## 7. 프론트엔드

### 7.1 RAG 채팅 패널

```
┌─────────────────────────────┐
│ 지식 검색              [필터] │
├─────────────────────────────┤
│ [프로젝트 ▾] [기간 ▾] [소스 ▾]│
├─────────────────────────────┤
│  (빈 상태 또는 대화)          │
│  🔍 검색 중...               │
│  📎 소스 5건 (접기/펼치기)    │
│  AI 답변 스트리밍             │
├─────────────────────────────┤
│ [질문 입력...]        [전송] │
└─────────────────────────────┘
```

**컴포넌트:**
```
features/rag/
├── components/
│   ├── RagHome.tsx      — 빈 상태 + 추천 질문
│   ├── RagChat.tsx      — 메시지 목록
│   ├── RagInput.tsx     — 입력 (Shift+Enter 줄바꿈, Enter 전송)
│   ├── RagMessage.tsx   — 개별 메시지 (스트리밍 애니메이션)
│   ├── RagSources.tsx   — 소스 카드 (접기/펼치기, 신선도 표시)
│   └── SearchScope.tsx  — 프로젝트/기간/소스 필터
├── hooks.ts  — useRagStream() (fetch + ReadableStream SSE 파싱)
├── api.ts    — SSE 연결 함수
├── types.ts  — RagMessage, RagSource, SearchFilter
└── store.ts  — 대화 히스토리 (Zustand, 세션 단위)
```

**SSE 연결:** `fetch` + `getReader()` (POST 지원 필요, EventSource는 GET 전용)

### 7.2 노트 에디터

- Tiptap: `StarterKit` + `Placeholder` + `CharacterCount`
- debounce 500ms → `PATCH` 자동저장
- 프로젝트 상세 → "노트" 탭
- 사이드바 → "노트" 메뉴 (전체 목록)
- 독립 노트 생성: Cmd+K "새 노트" 또는 사이드바

### 7.3 지식 신선도 (ADR-004 Slite 벤치마킹)

| 소스 경과 | 표시 |
|-----------|------|
| 1개월 이내 | 표시 없음 |
| 1~3개월 | `text-muted` "N개월 전 기반" |
| 3개월+ | `text-warning` "오래된 소스입니다" |

### 7.4 Cmd+K 통합

기존 CmdK 컴포넌트에 RAG 모드 추가:
- 일반 입력 → 네비게이션 검색
- `?` 접두사 또는 자연어 질문 감지 → RAG 질문 전환

---

## 8. Archive (Sprint 3 범위)

- 기존 `PATCH /projects/{id}` 로 `status: "archived"` 전환 (이미 가능)
- Archive된 프로젝트의 임베딩 = RAG 검색에 **포함** (제외하지 않음)
- UI: 프로젝트 상세 "Archive" 버튼 → 확인 다이얼로그

---

## 9. Vertical Slice 분해

Sprint 2 교훈 반영: **Slice별 merge + 검증**

### Slice 1: 임베딩 인프라 (BE)

- pgvector + pg_trgm 확장 활성화
- EmbeddingChunk, SemanticCache, Note 테이블 마이그레이션
- EmbeddingService (청킹 + OpenAI 임베딩 + 저장)
- MeetingPipelineService에 임베딩 단계 추가
- **검증:** 회의 업로드 → 임베딩 생성 확인 (DB 조회)

### Slice 2: RAG 검색 (BE + FE)

- RagService (캐시 확인 → Hybrid Search → RRF → Gemini SSE)
- `POST /rag/ask` 엔드포인트 (sse-starlette)
- FE: RagChat, RagInput, RagSources, SearchScope, useRagStream
- **검증:** 질문 → 스트리밍 답변 + 소스 표시 E2E

### Slice 3: Semantic Cache (BE)

- 캐시 확인 (similarity ≥ 0.93)
- 캐시 저장 (답변 완료 후)
- 캐시 무효화 (새 임베딩 시)
- **검증:** 동일 질문 2회 → 2회째 ~50ms

### Slice 4: 노트 도메인 (BE + FE)

- Note CRUD API 5개 엔드포인트
- 노트 임베딩 (BackgroundTasks)
- Tiptap 에디터 + debounce 500ms 자동저장
- 노트 목록 (프로젝트 내 + 전체)
- 사이드바 "노트" 메뉴
- **검증:** 노트 작성 → RAG 검색 가능 E2E

### Slice 5: Polish (FE)

- Cmd+K RAG 모드 통합
- 지식 신선도 표시
- Archive 버튼 + RAG 포함 확인
- **검증:** 전체 흐름 QA

### 의존성

```
Slice 1 → Slice 2 → Slice 3 → Slice 4 → Slice 5
```

---

## 10. Sprint 3 명시적 제외 → Sprint 4+ 후보

아래 항목은 의도적으로 Sprint 3에서 제외한다. Sprint 4 계획 시 재검토.

| 항목 | 이유 | 재검토 조건 |
|------|------|------------|
| **Cohere Rerank v3** | RRF Top-10으로 MVP 충분 | RAG 품질 부족 시 |
| **노트 Inbox 연동** | 수동 프로젝트 연결로 시작 | Sprint 4 Inbox 확장 시 |
| **2-Layer 승격 모델** | ADR-004 미결정 (복사 vs 링크, 퇴사 처리) | 상세 기획 확정 후 |
| **L3 프로젝트 인사이트** | 별도 프롬프트 + UI 필요 | Archive UX 고도화 시 |
| **Query Expansion/Rewriting** | rag-pipeline.md Phase 4 | 검색 품질 개선 필요 시 |
| **Cross-project RAG** | 조직 전체 검색 = Phase 4 | 워크스페이스 규모 확대 시 |

---

## 11. 완료 기준

- [ ] "지난 회의에서 CMS 관련 결정이 뭐였지?" → 2초 내 스트리밍 답변
- [ ] 회의 업로드 → 임베딩 자동 생성
- [ ] 노트 작성 → RAG 검색 가능
- [ ] Semantic Cache 동작 (동일 질문 ~50ms)
- [ ] 소스 신선도 표시
- [ ] Cmd+K RAG 통합

---

## 12. 기술 의존성 추가

### Backend (pyproject.toml)

```
sse-starlette          # SSE 스트리밍
pgvector               # SQLAlchemy pgvector 타입
```

### Frontend (package.json)

```
@tiptap/react
@tiptap/starter-kit
@tiptap/extension-placeholder
@tiptap/extension-character-count
```

### PostgreSQL Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- 트라이그램
```
