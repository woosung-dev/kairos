# RAG 파이프라인 설계 및 고도화 방향

> **관련 문서:** [AI 파이프라인 명세](ai-pipeline.md) (인제스트 파이프라인), [데이터 흐름 예시](data-flow-example.md), [ERD](erd.md)

---

## 1. 개요

Kairos의 RAG(Retrieval-Augmented Generation)는 쌓인 회의록·노트·액션 데이터를 **"질문할 수 있는 자산"** 으로 전환하는 핵심 기능이다.

### 현재 구현 (Phase 2 기본)

```
질문 → pgvector cosine similarity Top-K → Gemini 답변
```

- 512 토큰 flat 청킹, 50 토큰 오버랩
- OpenAI `text-embedding-3-small` (1536차원)
- 단순 유사도 검색 → Gemini 답변

### 목표 구현 (Phase 3 고도화)

```
질문 → Semantic Cache → Query Processing → Hybrid Search → Re-ranking → Gemini 스트리밍 답변 → Cache Store
```

- 하이브리드 검색 (Full-text + Vector + RRF)
- 계층적 청킹 (회의→화자 구간→문단 + 부모 참조)
- Semantic Cache (유사 질문 즉시 반환)
- Re-ranking (Cross-encoder 정밀 선별)
- 범위 기반 검색 (워크스페이스/프로젝트 단위/시간/소스 타입)

---

## 2. 기본 RAG 파이프라인 구조

```
사용자 질문 (+ 검색 범위: 워크스페이스/프로젝트/전체)
    ↓
Query Processing (범위 필터 결정, 질문 정규화)
    ↓
┌──────────────────┬──────────────────┬──────────────────┐
│ 회의록 청크       │ 노트 청크         │ 액션 아이템 청크    │  ← 동일 테이블, source_type 구분
│ (meeting)        │ (note)           │ (action)         │
└───────┬──────────┴───────┬──────────┴───────┬──────────┘
        └──────────────────┼──────────────────┘
                           ↓
                   Re-ranker (Cross-encoder Top-10 선별)
                           ↓
              시스템 프롬프트 + 검색 결과 + 질문
                           ↓
              Gemini → 스트리밍 답변 + 출처 표기
```

### 3가지 조정 축

1. **시스템 프롬프트** (가장 강력) — 답변 스타일, 출처 표기 규칙, 방어 지침
2. **참조 문서** (RAG) — 하이브리드 검색으로 관련 청크 주입
3. **검색 범위** (Scope) — 프로젝트/시간/소스 타입 필터로 정밀 제어

---

## 3. 전체 요청 처리 파이프라인 (6-Layer)

> **Sprint 6 ADR-014 옵션 A 적용**: 진입은 `RagPipelineService.ask` (orchestrator). visibility 검증을 SSE 스트리밍 시작 *전*에 완료한 후 `RagService.ask`로 위임. 권한 위반 시 `error` + `done` SSE 이벤트로 종료 (스트리밍 시작 안 함). ADR-010 M1 RAG 품질 시그널 측정 시 권한 누락이 source 오염 원인 아님 (검증 기준 C-6).

```
┌─────────────────────────────────────────────────────────┐
│                    사용자 인터페이스                        │
│  [프로젝트 범위 선택] [질문 입력] [시간 필터] [소스 필터]     │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│        Layer 0: Visibility 권한 검증 (Sprint 6)           │
│  RagPipelineService.ask 진입에서 SSE 시작 *전* 완료        │
│  - admin/owner: 모든 visibility 우회                      │
│  - draft: creator + admin/owner만 read                    │
│  - private: ProjectMember 매핑된 사용자만 read             │
│  → 검증 실패 시 error + done 이벤트로 종료                  │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Layer 1: Semantic Cache                     │
│  질문 임베딩 → semantic_caches 테이블 검색                 │
│  ├── HIT (유사도 ≥ 0.93) → 즉시 반환 (~50ms, 비용 $0)   │
│  └── MISS → 다음 단계로                                  │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Layer 2: Query Processing                   │
│  1. 워크스페이스 격리 (필수, workspace_id)                  │
│  2. 프로젝트 범위 필터 결정 (project_id)                    │
│  3. 시간 범위 필터 (선택적, "최근 3개월")                   │
│  4. 소스 타입 필터 ("회의만" | "노트만" | "전체")           │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Layer 3: Hybrid Search (PostgreSQL)          │
│  ┌───────────────────┐  ┌───────────────────┐           │
│  │ Full-text Search   │  │ Vector Search     │           │
│  │ pg_trgm + GIN     │  │ pgvector cosine   │           │
│  │ 키워드/이름 정확매칭 │  │ 의미적 유사도      │           │
│  └────────┬──────────┘  └────────┬──────────┘           │
│           └────── RRF 결합 ──────┘                       │
│                Top-50 후보                                │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Layer 4: Re-ranking                         │
│  Cross-encoder로 Top-50 → Top-10 정밀 선별               │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Layer 5: Generation                         │
│  시스템 프롬프트 (RAG_ANSWER_SYSTEM_PROMPT)               │
│  + Re-ranked 검색 결과 Top-10                            │
│  + 출처 메타데이터 (회의명, 날짜, 발언자)                    │
│  + 사용자 질문                                            │
│  → Gemini (gemini-3.1-flash-lite) → 스트리밍 답변 + 출처 표기  │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Layer 6: Cache Store                        │
│  답변을 semantic_caches에 저장 (TTL 7일)                  │
└─────────────────────────────────────────────────────────┘
```

> **Sprint 16 ADR-020 — 인덱스 / 세션 변수 정책** (`docs/adr/020-pgvector-hnsw-halfvec.md`):
> - **Layer 1 (Semantic Cache)** + **Layer 3 (Vector Search)** 인덱스: pgvector **HNSW** on `halfvec(1536)`, `m=16, ef_construction=64`, `halfvec_cosine_ops`
> - 트랜잭션 진입 시 `_apply_hnsw_session_params(session)` (`backend/src/embeddings/repository.py`) 자동 호출 — `SET LOCAL hnsw.ef_search=40` + `iterative_scan=relaxed_order` + `max_scan_tuples=20000`
> - 헌법 강제: CONTEXT-MAP I-20 (타입/인덱스) + I-21 (세션 변수) + `rag/CONTEXT.md` R-13 (Layer 1/3 진입 강제)
> - RBAC/visibility 포스트필터 결과 부족 → `iterative_scan`이 LIMIT 도달 시까지 자동 추가 스캔으로 해소

---

## 4. 하이브리드 검색 전략

### 왜 하이브리드인가

회의 데이터에는 두 종류의 검색 수요가 공존한다:

| 질문 유형 | 예시 | 최적 검색 |
|-----------|------|----------|
| 이름/용어 정확 매칭 | "당근님이 CMS 관련해서 뭐라고 했지?" | Full-text (키워드) |
| 의미적 유사도 | "보안 관련 결정사항이 뭐였지?" | Vector (의미) |
| 복합 | "사부님이 중복 계정 해결 방안으로 제안한 것" | Hybrid (양쪽) |

**벡터 검색만으로는 부족한 이유:**
- 인명("당근님", "튜닝님"), 프로젝트명("CMS 고도화"), 기술 용어("AWS") 등 고유명사는 **키워드 매칭이 벡터보다 정확**
- "보안 이슈에 대한 개선 방안" 같은 추상적 질문은 **벡터가 강함**
- RRF(Reciprocal Rank Fusion)로 **양쪽 장점 동시 활용**

### PostgreSQL 내 구현

Kairos의 데이터 규모(워크스페이스당 1,000~20,000 청크)에서는 별도 벡터 DB(Qdrant 등) 없이 **PostgreSQL 내에서 하이브리드 검색이 가능하다.**

#### Full-text 검색 (pg_trgm)

```sql
-- 트라이그램 확장 및 인덱스 생성
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_chunks_trgm ON embedding_chunks
  USING gin (chunk_text gin_trgm_ops);

-- 키워드 검색 (한국어 포함 부분 매칭 가능)
SELECT id, chunk_text,
       similarity(chunk_text, '당근님 CMS') AS text_score
FROM embedding_chunks
WHERE workspace_id = $1
  AND chunk_text % '당근님 CMS'  -- 유사도 임계값 이상만
ORDER BY text_score DESC
LIMIT 50;
```

> **`pg_trgm`을 선택한 이유:** 한국어 형태소 분석기(`mecab` 등) 없이도 트라이그램 기반으로 부분 매칭이 가능하다. "당근님" → {"당근", "근님"} 트라이그램으로 분해되어 정확 매칭 + 퍼지 매칭 모두 지원.

#### Vector 검색 (pgvector HNSW + halfvec, Sprint 16 ADR-020)

```sql
-- (트랜잭션 진입 시 자동) SET LOCAL hnsw.ef_search = 40;
-- (트랜잭션 진입 시 자동) SET LOCAL hnsw.iterative_scan = 'relaxed_order';
-- (트랜잭션 진입 시 자동) SET LOCAL hnsw.max_scan_tuples = 20000;

-- 벡터 유사도 검색 (cosine, halfvec_cosine_ops 인덱스 사용)
SELECT id, chunk_text,
       1 - (embedding <=> CAST($query_vector AS halfvec)) AS vector_score
FROM embedding_chunks
WHERE workspace_id = $1
ORDER BY embedding <=> CAST($query_vector AS halfvec)
LIMIT 50;
```

> **인덱스 정의** (`backend/alembic/versions/<pgvector_hnsw_halfvec>.py`, Sprint 16 Stage 4):
> ```sql
> CREATE INDEX CONCURRENTLY idx_chunks_hnsw
>   ON embedding_chunks
>   USING hnsw (embedding halfvec_cosine_ops)
>   WITH (m = 16, ef_construction = 64);
> ```
> SET LOCAL은 `embeddings/repository.py:_apply_hnsw_session_params` 헬퍼가 트랜잭션 진입 직전 호출 (R-13 / I-21). `iterative_scan`이 워크스페이스/visibility 포스트필터 적용 후 LIMIT 미달 시 자동 추가 스캔을 수행하므로, 후보 부족으로 인한 "검색 결과 0건" 케이스가 자동 해소된다.

#### RRF 결합 (Reciprocal Rank Fusion)

```python
def reciprocal_rank_fusion(
    text_results: list[SearchResult],
    vector_results: list[SearchResult],
    k: int = 60,
    top_n: int = 50,
) -> list[SearchResult]:
    """
    두 검색 결과를 RRF로 결합한다.
    k=60은 순위 차이에 대한 민감도 조절 파라미터 (표준값).
    """
    scores: dict[str, float] = {}

    for rank, result in enumerate(text_results):
        scores[result.id] = scores.get(result.id, 0) + 1 / (k + rank + 1)

    for rank, result in enumerate(vector_results):
        scores[result.id] = scores.get(result.id, 0) + 1 / (k + rank + 1)

    sorted_ids = sorted(scores, key=scores.get, reverse=True)
    return [get_result(id) for id in sorted_ids[:top_n]]
```

---

## 5. 계층적 청킹 전략

### 왜 계층적 청킹인가

- 300~500자 청크만으로 검색하면 **문맥이 끊김**
- "이 발언의 앞뒤 맥락"을 함께 전달해야 LLM이 정확한 답변 생성
- 계층 구조 → 검색 hit → 상위 화자 구간/토픽 맥락 자동 포함

### 회의 데이터 계층 구조

```
워크스페이스
  └── 회의 (Meeting) — 메타: 제목, 일시, 참석자, 프로젝트 연결
      └── 화자 구간 (Speaker Turn) — 메타: 화자명, 시작/종료 시간
          └── 문단 (Paragraph) — 검색 단위, ~300-500자
              └── 부모 참조 (parent_chunk_id → 화자 구간)
```

### 청킹 레벨

| 레벨 | 단위 | 크기 | 용도 |
|------|------|------|------|
| 0 | 회의 전체 요약 | 제한 없음 | 메타데이터 컨텍스트 (검색 대상 아님) |
| 1 | 화자 구간/토픽 | ~512 토큰 | 중간 맥락 (부모 청크) |
| 2 | 문단 | ~300-500자 | **검색 단위** (자식 청크) |

### 구현

```python
def chunk_transcript(
    transcript_segments: list[TranscriptSegment],
    max_chunk_size: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    """
    트랜스크립트를 계층적으로 청킹한다.
    Level 1: 화자 구간 단위 (parent)
    Level 2: 문단 단위 (child, 실제 검색 대상)
    """
    chunks = []

    # Level 1: 화자 구간 그룹핑
    speaker_groups = group_by_speaker_turn(transcript_segments)

    for group in speaker_groups:
        parent_chunk = Chunk(
            text=group.full_text,
            level=1,
            metadata={
                "speaker": group.speaker,
                "start_sec": group.start_sec,
                "end_sec": group.end_sec,
            },
        )
        chunks.append(parent_chunk)

        # Level 2: 문단 단위 분할
        paragraphs = split_text(group.full_text, max_chunk_size, overlap)
        for i, para in enumerate(paragraphs):
            child_chunk = Chunk(
                text=para,
                level=2,
                chunk_index=i,
                parent_chunk_id=parent_chunk.id,
                metadata=parent_chunk.metadata,
            )
            chunks.append(child_chunk)

    return chunks
```

### 노트 데이터 청킹

```
노트 (Note) — 메타: 제목, 작성자, 프로젝트 연결
  └── 섹션 (Heading 단위) — Level 1 (부모)
      └── 본문 단락 — Level 2 (검색 단위)
```

### 검색 시 부모 맥락 포함

```python
async def search_with_context(
    query: str,
    workspace_id: str,
    project_id: str | None = None,
) -> list[SearchResult]:
    """Level 2 청크에서 검색 후, 부모 청크 맥락을 자동 추가한다."""
    results = await hybrid_search(
        query, workspace_id,
        project_id=project_id,
        chunk_level=2,
    )

    enriched = []
    for result in results:
        if result.parent_chunk_id:
            parent = await get_chunk(result.parent_chunk_id)
            result.context = parent.text  # 더 넓은 맥락
        enriched.append(result)

    return enriched
```

---

## 6. 검색 범위 제어 (Scoped Search)

### 필터 계층

```
[필수] 워크스페이스 격리 (workspace_id) — 멀티테넌시
  ↓
[선택] 프로젝트 범위 (project_id) — "이 프로젝트 범위에서 검색"
  ↓
[선택] 시간 범위 (created_at) — "최근 3개월"
  ↓
[선택] 소스 타입 (source_type) — "회의만" | "노트만" | "전체"
```

### SQL 구현

```sql
SELECT id, chunk_text,
       1 - (embedding <=> $query_vector) AS score
FROM embedding_chunks
WHERE workspace_id = $1                            -- 필수: 워크스페이스 격리
  AND ($2::uuid IS NULL OR project_id = $2)      -- 선택: 프로젝트 범위
  AND ($3::timestamp IS NULL OR created_at >= $3)   -- 선택: 시간 범위
  AND ($4::text IS NULL OR source_type = $4)        -- 선택: 소스 타입
  AND chunk_level = 2                               -- 검색 대상은 Level 2만
ORDER BY embedding <=> $query_vector
LIMIT 50;
```

### UI 연동 (RAG 채팅 패널)

```
┌─────────────────────────────────┐
│ 🔍 지식 검색                      │
│                                 │
│ 범위: [CMS 고도화 프로젝트 ▾]      │
│ 기간: [전체 ▾]  소스: [전체 ▾]     │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ 질문을 입력하세요...           │ │
│ └─────────────────────────────┘ │
│                                 │
│ 💬 CMS 개발 진행 상황은?          │
│ ──────────────────────────────  │
│ 3/20 킥오프 회의에서...           │
│ 📎 출처: 킥오프 회의 (2026-03-20) │
│ 📎 발언자: 튜닝님                 │
└─────────────────────────────────┘
```

---

## 7. Semantic Cache 전략

### 개념

일반 캐시는 **똑같은 문자열**만 히트. Semantic Cache는 **의미적으로 비슷한 질문**도 히트로 처리.

```
일반 캐시:
  "CMS 진행 상황이 어떻게 되나요?" → 캐시 히트 ✅
  "CMS 프로젝트 진행 현황은?"     → 캐시 미스 ❌ (문자열이 다름)

Semantic Cache:
  "CMS 진행 상황이 어떻게 되나요?" → 캐시 히트 ✅
  "CMS 프로젝트 진행 현황은?"     → 캐시 히트 ✅ (유사도 0.96)
  "보안 검토 일정은?"             → 캐시 미스 ❌ (유사도 0.45)
```

### 작동 구조

```
사용자 질문
    ↓
질문 임베딩 생성
    ↓
semantic_caches 테이블에서 유사 질문 검색
    ↓
유사도 ≥ 임계값 (0.93)?
    ├── YES → 캐시된 답변 즉시 반환 (~50ms, 비용 $0)
    └── NO  → 정상 RAG 파이프라인 실행 (2~5초, ~$0.01-0.05)
              → 답변 생성 후 semantic_caches에 저장
```

### 데이터 모델

```sql
CREATE TABLE semantic_caches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    project_id UUID REFERENCES projects(id),  -- 범위별 캐시
    question TEXT NOT NULL,
    question_embedding vector(1536) NOT NULL,
    answer TEXT NOT NULL,
    sources JSONB NOT NULL DEFAULT '[]',           -- 출처 목록
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now(),
    expires_at TIMESTAMP DEFAULT now() + INTERVAL '7 days'
);

CREATE INDEX idx_cache_embedding ON semantic_caches
  USING ivfflat (question_embedding vector_cosine_ops);
CREATE INDEX idx_cache_workspace ON semantic_caches(workspace_id);
```

### 구현

```python
async def check_semantic_cache(
    question_embedding: list[float],
    workspace_id: str,
    project_id: str | None = None,
    threshold: float = 0.93,
) -> CacheResult | None:
    """의미적으로 유사한 질문의 캐시를 검색한다."""
    query = """
    SELECT id, answer, sources,
           1 - (question_embedding <=> $1) AS similarity
    FROM semantic_caches
    WHERE workspace_id = $2
      AND ($3::uuid IS NULL OR project_id = $3)
      AND expires_at > now()
      AND 1 - (question_embedding <=> $1) >= $4
    ORDER BY question_embedding <=> $1
    LIMIT 1
    """
    result = await db.fetch_one(
        query, [question_embedding, workspace_id, project_id, threshold]
    )

    if result:
        await db.execute(
            "UPDATE semantic_caches SET hit_count = hit_count + 1 WHERE id = $1",
            [result.id],
        )
        return CacheResult(answer=result.answer, sources=result.sources)

    return None
```

### 캐시 무효화 정책

| 이벤트 | 동작 |
|--------|------|
| 새 회의 추가 (해당 프로젝트) | 해당 `project_id`의 캐시 삭제 |
| 노트 수정 (해당 프로젝트) | 해당 `project_id`의 캐시 삭제 |
| 7일 경과 | TTL 자동 만료 |
| 임베딩 재생성 | 워크스페이스 전체 캐시 삭제 |

### 파이프라인에서의 위치

```
사용자 질문
    ↓
[Semantic Cache 체크]  ← 가장 앞단
    ├── HIT → 즉시 반환
    └── MISS ↓
[Query Processing]
    ↓
[Hybrid Search]
    ↓
[Re-ranking]
    ↓
[Gemini 답변 생성]
    ↓
[캐시 저장]  ← 가장 뒷단
    ↓
답변 반환
```

파이프라인 **가장 앞에서 체크, 가장 뒤에서 저장** — 기존 검색 구조를 건드리지 않고 앞뒤로 붙이는 형태.

### 비용/성능 예측

```
월 1,000건 질문 기준 (소규모 팀):

캐시 없이:     1,000 x $0.03 = $30/월
히트율 30%:    700 x $0.03   = $21/월 → 월 $9 절감
히트율 40%:    600 x $0.03   = $18/월 → 월 $12 절감

월 5,000건 질문 기준 (성장기):

캐시 없이:     5,000 x $0.03 = $150/월
히트율 40%:    3,000 x $0.03 = $90/월 → 월 $60 절감

응답 시간:
정상 RAG: 2~5초
캐시 히트: ~50ms (40~100배 빠름)
```

---

## 8. Re-ranking 파이프라인

### 구조

```
Layer 3 (Hybrid Search) → Top-50 후보
    ↓
Cross-encoder 모델: 질문 + 각 문서를 쌍(pair)으로 평가
    ↓
Top-10만 Generation Layer에 전달
```

### 왜 중요한가

- Hybrid Search의 1차 검색은 대략적 관련 문서를 넓게 가져옴
- Re-ranker는 질문과 문서를 **동시에 읽고** 관련도를 정밀 판단
- 50개 후보에서 **정말 관련 있는 10개만** 선별하여 LLM 토큰 비용 절감 + 답변 품질 향상

### 추천 모델

| 모델 | 특징 | 한국어 | 적합도 |
|------|------|--------|--------|
| Cohere Rerank v3 | API 서비스, 간편 | 양호 | ★★★★★ |
| `bge-reranker-v2-m3` | 셀프호스팅, 다국어 | 양호 | ★★★★☆ |
| `ms-marco-MiniLM-L-12` | 가볍고 빠름 | 영어 중심 | ★★★☆☆ |

### 구현 (Cohere Rerank 예시)

```python
from cohere import AsyncClient as CohereClient

async def rerank_results(
    query: str,
    candidates: list[SearchResult],
    top_k: int = 10,
) -> list[SearchResult]:
    """Cross-encoder로 Top-50 후보를 Top-10으로 정밀 선별한다."""
    cohere = CohereClient(api_key=settings.cohere_api_key)

    response = await cohere.rerank(
        model="rerank-multilingual-v3.0",
        query=query,
        documents=[c.chunk_text for c in candidates],
        top_n=top_k,
    )

    return [candidates[r.index] for r in response.results]
```

---

## 9. 대용량 고도화 방향 (Phase 4+)

### 방향 1: Query Expansion / Rewriting — ★★★☆☆

```
원본 질문: "보안 관련 결정사항이 뭐였지?"
    ↓ Gemini 전처리
확장된 쿼리:
  - "보안 검토 및 개선 방안에 대한 회의 결정사항"
  - "데이터 유출 사고 대응 및 AWS 전환 관련 논의"
  - "보안성 검토 결과 및 인프라 변경 사항"
    ↓
3개 쿼리로 각각 검색 → 결과 병합 (dedup)
```

**장점:** 사용자의 짧고 모호한 질문을 확장하여 재현율(recall) 대폭 상승
**비용:** Gemini 호출 1회 추가 (~$0.001/쿼리)
**적용 시점:** Phase 4

### 방향 2: Agentic RAG (다단계 검색-추론-검증) — ★★★☆☆

```
사용자 질문: "CMS 프로젝트와 홈페이지 고도화의 관계를 설명해줘"
    ↓
Agent Step 1: "CMS 프로젝트" 관련 검색 → 관련 회의록 5개
Agent Step 2: "홈페이지 고도화" 관련 검색 → 관련 회의록 5개
Agent Step 3: 두 결과 비교 분석 → "관계" 추론
Agent Step 4: 추론 결과 검증할 추가 회의록 검색
    ↓
최종 답변 생성
```

**장점:** 복잡한 비교/분석/크로스 프로젝트 질문에 강함
**단점:** 비용 3~5배, 응답 시간 5~10초
**적용 시점:** Phase 4, "심층 분석" 모드로 선택적 제공

### 방향 3: Cross-Project RAG — ★★★☆☆

Phase 3까지는 프로젝트 범위(프로젝트/영역) 단위 검색. Phase 4에서 워크스페이스 전체 검색 지원.

```
UI 옵션: [전체 워크스페이스 검색 ▾]
  → workspace_id만으로 필터 (project_id 필터 해제)
  → 모든 프로젝트/영역/리소스/아카이브에서 검색
```

**유의:** Archive 데이터도 RAG 소스에 포함되어야 한다 (PRD 핵심 가치).

---

## 10. 임베딩 테이블 확장 설계

### 현재 → 확장

```sql
-- 현재 (Phase 2)
CREATE TABLE embedding_chunks (
    id UUID PRIMARY KEY,
    source_id UUID NOT NULL,
    source_type VARCHAR NOT NULL,       -- meeting | note | action
    embedding vector(1536),
    chunk_text TEXT,
    chunk_index INTEGER,
    created_at TIMESTAMP
);

-- 확장 (Phase 3)
CREATE TABLE embedding_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    project_id UUID REFERENCES projects(id),
    source_id UUID NOT NULL,
    source_type VARCHAR NOT NULL,           -- meeting | note | action
    embedding vector(1536) NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_level INTEGER NOT NULL DEFAULT 2, -- 0: document, 1: section, 2: paragraph
    parent_chunk_id UUID REFERENCES embedding_chunks(id),
    metadata JSONB DEFAULT '{}',            -- {"speaker": "...", "start_sec": 0, "topic": "..."}
    created_at TIMESTAMP DEFAULT now()
);

-- 인덱스
CREATE INDEX idx_chunks_workspace ON embedding_chunks(workspace_id);
CREATE INDEX idx_chunks_para ON embedding_chunks(project_id);
CREATE INDEX idx_chunks_source ON embedding_chunks(source_type, source_id);
CREATE INDEX idx_chunks_parent ON embedding_chunks(parent_chunk_id);
CREATE INDEX idx_chunks_level ON embedding_chunks(chunk_level);
CREATE INDEX idx_chunks_vector ON embedding_chunks
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_chunks_trgm ON embedding_chunks
  USING gin (chunk_text gin_trgm_ops);
```

### 추가 컬럼 설명

| 컬럼 | 용도 |
|------|------|
| `workspace_id` | 멀티테넌시 격리 (필수 필터) |
| `project_id` | 프로젝트 범위 검색 (프로젝트/영역 단위) |
| `chunk_level` | 계층적 청킹 레벨 (검색 시 level=2만 대상) |
| `parent_chunk_id` | 부모 청크 참조 (맥락 확장용) |
| `metadata` | 화자명, 시간, 토픽 등 동적 메타데이터 |

---

## 11. 고도화 방향 요약

| 순위 | 방향 | 추천도 | 난이도 | 적용 시점 |
|------|------|--------|--------|----------|
| 1 | 하이브리드 검색 (Full-text + Vector + RRF) | ★★★★★ | 중 | Phase 3 |
| 2 | 계층적 청킹 (화자 구간→문단 + 부모 참조) | ★★★★★ | 중 | Phase 3 |
| 3 | 검색 범위 제어 (Scoped Search) | ★★★★★ | 낮음 | Phase 3 |
| 4 | Semantic Cache | ★★★★☆ | 낮음 | Phase 3 |
| 5 | Re-ranking (Cross-encoder) | ★★★★☆ | 낮음 | Phase 3~4 |
| 6 | Query Expansion / Rewriting | ★★★☆☆ | 낮음 | Phase 4 |
| 7 | Agentic RAG | ★★★☆☆ | 높음 | Phase 4+ |

### Phase 2 (기본)
- 단순 pgvector 유사도 검색
- Flat 청킹 (512 토큰, 50 토큰 오버랩)
- 워크스페이스 격리만

### Phase 3 (고도화) — 핵심 목표
- 하이브리드 검색 (pg_trgm + pgvector + RRF)
- 계층적 청킹 (화자 구간 → 문단 + 부모 참조)
- 프로젝트 범위 + 시간 범위 + 소스 타입 필터
- Semantic Cache (유사 질문 즉시 반환)
- Gemini 스트리밍 답변 (StreamingResponse)
- RAG 채팅 패널 UI (우측 슬라이드, 범위 선택)

### Phase 4 (심화)
- Re-ranking (Cohere Rerank API)
- Query Expansion (Gemini 전처리)
- Cross-Project RAG (워크스페이스 전체 검색)
- Agentic RAG (복합 질문 → 다단계 검색, "심층 분석" 모드)

---

## 12. truewords-platform과의 비교

Kairos RAG 설계는 truewords-platform의 아키텍처를 참조하되, **프로젝트 특성에 맞게 적응**시켰다.

| 항목 | truewords-platform | Kairos |
|------|-------------------|--------|
| 벡터 DB | Qdrant (별도 서비스) | pgvector (PostgreSQL 내장) |
| Full-text | Qdrant BM25 sparse vector | pg_trgm + GIN 인덱스 |
| 데이터 규모 | ~60만 청크 (615권) | ~1만-2만 청크/워크스페이스 |
| 청킹 단위 | 권→장→문단 | 회의→화자 구간→문단 |
| 멀티테넌시 | 없음 (단일 챗봇) | 워크스페이스 격리 (필수) |
| 검색 범위 | payload 필터 (A\|B\|C 챗봇 버전) | 프로젝트 범위 + 시간 + 소스 타입 |
| 캐시 | Qdrant semantic_cache 컬렉션 | PostgreSQL semantic_caches 테이블 |
| 생성 모델 | Gemini 2.5 | Gemini gemini-3.1-flash-lite (ADR-019 Phase B) |

**핵심 차이:** Kairos는 워크스페이스 단위 소규모 데이터이므로 별도 벡터 DB 불필요. PostgreSQL 하나로 운영 데이터 + 벡터 검색 + Full-text 검색 + 캐시를 모두 처리한다.
