# Sprint 27e — 성능 분석가 발견사항

- 검사 범위: 알고리즘 / DB / 캐싱 / sync blocking / 리소스 / FE / 측정 baseline
- 시나리오: Personal + Team 둘 다
- baseline 측정 일시: 2026-05-25 (정적 분석 only)
- 환경: **로컬 FE/BE 모두 down — 실 latency / Lighthouse / Playwright timing 측정 불가**. Sprint 27d 의 측정값 (BUG-S27d-6 RAG p95 10.6s avg) 만 cited reference.
- 검사 대상 commit: `1b24898` (Sprint 27d 완료, main HEAD), branch `sprint-27e/multi-review` 변경 0

---

## 측정 baseline (필수)

### 환경 미실행 — 직접 측정 불가 metric

| metric | 측정값 | 목표 | 비고 |
|---|---|---|---|
| RAG p95 (실 환경) | **환경 미실행 — 측정 불가** | ≤ 15s (SCOPE GO 조건) | Sprint 27d cited: avg 10.6s, p95 미공개 |
| API workspace list avg | **환경 미실행 — 측정 불가** | ≤ 500ms | curl/timing 측정 권고 |
| dashboard LCP/FCP/TTI | **환경 미실행 — 측정 불가** | LCP ≤ 2.5s | Lighthouse 권고 |
| 회의 처리 (5분 audio) end-to-end | **환경 미실행 — 측정 불가** | ≤ 60s | Whisper + Gemini + embedding stage 누적 |
| 1 페이지 BE 쿼리 수 | **환경 미실행 — 측정 불가** | ≤ 10 | FastAPI middleware 로깅 권고 |
| Cloud Run cold start | **환경 미실행 — 측정 불가** | ≤ 3s | uvicorn lifespan + asyncpg + Gemini client 초기화 |

### 정적 분석 추정값 (코드 기반)

| metric | 추정값 | 근거 | 차이 (목표 대비) |
|---|---|---|---|
| RAG 핵심 path (no-cache, no time_range) | 4-12s | 1× OpenAI embed + 2× DB hybrid (HNSW vector + pg_trgm) + 1× Gemini stream + 1× cache insert + 1× onboarding hook commit (SCOPE BL-S27e-1 추적 중) | 목표 ≤ 15s — 헤드룸 작음 |
| RAG cache hit path | 200-600ms | 1× OpenAI embed (불가피) + 1× cache lookup + 1× onboarding hook commit (cache hit 도 commit 발생 — SCOPE F-2 정합) | OK |
| 회의 5분 audio | 30-60s | Whisper 5-15s + Gemini summary 4-8s + Gemini extract_actions 4-8s + OpenAI embed (N chunks) ~ 5-15s + DB save | 헤드룸 작음 (Gemini timeout 0 → 외부 latency spike 시 60s 초과 위험) |
| dashboard 첫 진입 BE queries | 8-15 | 5+ FE API 동시 fan-out × `require_viewer/member` RoleChecker 매 호출 (BL-036 인덱스로 완화) + lazy seed (BL-S27c-1) | ≤ 10 목표 turbo close |
| `lucide-react` import 총량 | 큼 (정적 import) | `lucide-react` is barrel — tree-shake 안 되면 ~1MB | `Image|font|font` 추적 권고 |
| memory_query_embedding_cache table 성장 | 무한 | TTL lookup-side만 enforce, purge 작업 0 → 시간당 N rows 누적 영구 | P2 P3 carry |

---

## 최적화 기회 매트릭스

| ID | 영역 | 심각도 | 차단? | 영향도 추정 | file:line | 발견 사항 | 최적화 방안 | 비용 |
|---|---|---|---|---|---|---|---|---|
| BUG-S27e-PERF-1 | 리소스 누수 | P1 | NO | -500ms ~ -1.5s per call | `backend/src/common/r2.py:14,27,55,73,87` / `backend/src/memory/service.py:636,654` | aioboto3 client + S3 client 가 매 호출마다 `__aenter__/__aexit__` (BL-008 carry, 호출 빈도: upload 1회/회의 + 1회/memory voice + 1회/cron) | R2Service 에 `async _ensure_client()` + lifespan teardown. memory/service.py 의 직접 boto3 호출은 R2Service public API 로 끌어올림 | 0.5d |
| BUG-S27e-PERF-2 | DB | P1 | NO | -50% to -90% query time on ListBy queries (workspace scale up 시) | `backend/src/meetings/models.py:17` / `backend/src/actions/models.py:32` / `backend/src/inbox/models.py:22` | `meetings/action_items/inbox_items` 의 `workspace_id` 가 `Field(foreign_key=...)` 에 `index=True` 없음. PG FK 는 reference table 측 자동 인덱스 안 만듦. composite UNIQUE `(id, workspace_id)` 는 leftmost=`id` 라 `WHERE workspace_id=X` 만으로는 미사용 | 3개 alembic migration: `idx_meetings_workspace_created`, `idx_actions_workspace_status`, `idx_inbox_workspace_processed` (각 list endpoint 의 WHERE+ORDER BY composite) | 0.5d |
| BUG-S27e-PERF-3 | sync blocking / 리소스 | P1 | NO | OOM 위험 (concurrent 5×500MB = 2.5GB) | `backend/src/upload/router.py:91` + `backend/src/common/r2.py:62` | `await file.read()` → 500MB 까지 RAM 한 번에 적재 → `r2.upload_file_bytes(... data=bytes)` → 또 1회 메모리 사본. Cloud Run instance default 메모리 1-2GB 와 충돌. `file.size` 사전 차단 만으론 정상 큰 파일은 여전히 OOM. | UploadFile.file 의 SpooledTemporaryFile 을 그대로 boto3 `upload_fileobj` 에 전달 (streaming). validator 만 `data[:512]` head 로 운영 (`file.read(512)` 후 `file.seek(0)`) | 1d (검증 4 layer 재배선) |
| BUG-S27e-PERF-4 | sync blocking / AI | P1 | NO | tail-latency unbounded, hang 시 BG task 영구 stuck | `backend/src/services/ai_processing.py:81,127,151` + `backend/src/memory/service.py:682` | Gemini `generate_content` / `generate_content_stream` 호출 모두 **timeout 0 + retry 0 + circuit breaker 0**. Gemini API 지연 (5s → 60s) 시 회의 파이프라인 + RAG 둘 다 hang. Cloud Run request timeout (300s default) 까지 점유 → 가용 worker 감소 | `asyncio.wait_for(client.aio.models.generate_content(...), timeout=30)` + tenacity exponential backoff (max 3 retries) + half-open circuit breaker (5 연속 실패 → 60s open) | 1.5d |
| BUG-S27e-PERF-5 | SSE 리소스 | P1 | NO | 클라이언트 disconnect 후 Gemini stream + token 비용 무한 소진 가능 | `backend/src/rag/router.py:30-42` + `backend/src/rag/service.py:166-172` | SSE `event_generator()` 내부에 `request.is_disconnected()` 체크 없음. RAG 답변 stream 중 사용자 탭 닫음 → BE 는 Gemini 토큰 끝까지 받고 cache 저장. Gemini API 비용 비싸진다 (RAG 1회 ~ 1k-3k token Out) | router.py 의 generator 에 `Request` 인자 추가 → `await request.is_disconnected()` 매 yield 직전 check → True 시 break (cache 저장 skip) | 0.5d |
| BUG-S27e-PERF-6 | 캐싱 | P2 | NO | RAG cache hit rate ~ 0 risk (small data) | `backend/src/meetings/service.py:516` / `backend/src/notes/service.py:469` / `backend/src/embeddings/repository.py:460` | promote BG 가 `delete_caches(target_workspace_id, None)` — 단 1 건 promote 시 target ws 전체 SemanticCache wipe. 회의/노트 invalidate_cache(workspace_id, project_id) 도 project=None 경로 가 ws 전체 wipe. team workspace 에서 dogfooding 빈도 ↑ 시 cache hit 률 0 수렴 | invalidate 범위 좁히기: source_chunk_ids 만 영향받는 cache 만 삭제 (sources::jsonb @> 검색 + 해당 row 만 DELETE). 또는 cache version 컬럼 + scoped 무효화 | 1d |
| BUG-S27e-PERF-7 | 캐싱 / 리소스 | P2 | NO | DB 무한 성장 (10k recall/일 → 30일 후 300k rows + halfvec(1536) 청크 storage) | `backend/src/memory/models.py:128-142` + `backend/src/memory/repository.py:255-311` | `MemoryQueryEmbeddingCache` 의 7일 TTL 은 lookup 시점에만 enforce (cutoff filter). 만료된 row 를 정리하는 cron / vacuum / scheduled DELETE 없음. row 무제한 누적 → halfvec(1536) 컬럼 + HNSW 인덱스 storage 비용 + insert 시 ON CONFLICT seek 시간 증가 | 1) 신규 alembic — partial expression index `WHERE created_at >= now() - interval '7 days'` 로 hot path 한정. 2) Cloud Scheduler cron — `DELETE FROM memory_query_embedding_cache WHERE created_at < now() - interval '7 days'` 1일 1회. 3) 또는 `MemoryItem.cleanup_expired_r2_audio` 패턴으로 router 의 admin endpoint 추가 | 0.5d |
| BUG-S27e-PERF-8 | DB / 알고리즘 | P2 | NO | RAG time_range filter latency degradation (workspace 3개월+ 후) | `backend/src/embeddings/repository.py:209-214,270-274` + `backend/src/embeddings/models.py:47` | `embedding_chunks.created_at` 에 인덱스 없음. RAG `time_range` filter 가 `created_at >= ...` filter post-HNSW 적용 → HNSW 가 top-K 반환 후 filter (BUG-Sprint16 의 iterative_scan relaxed_order 처리 의존). 시간 범위 좁을수록 top-K 의 다수가 filter 탈락 → ef_search 폭주 (`SET LOCAL hnsw.max_scan_tuples = 20000`) | partial expression index `embedding_chunks (workspace_id, created_at DESC) WHERE chunk_level = 2` 신설. 또는 ANN 후보 set 확장만으로 충분한지 EXPLAIN ANALYZE 권고 (사용자 별도) | 0.5d + 측정 |
| BUG-S27e-PERF-9 | 알고리즘 (N+1) | P2 | NO | inbox classify N project_ids 당 RTT N회 (작은 N 영향 미미, 5+ ids 시 ~300ms) | `backend/src/inbox/service.py:100-104` | `for project_id in project_ids: project = await self.project_repo.find_by_id(...)` — N+1. 보통 N=1-3 이라 영향 미미 | `find_by_ids_in_workspace(project_ids, workspace_id)` 신규 repo 메서드 — `WHERE id IN (...)` 1회 쿼리 + N==len(result) assertion fail-closed | 0.25d |
| BUG-S27e-PERF-10 | FE / 번들 | P2 | NO | LCP/TTI 추정 +200-500ms (서버사이드 font fetch 3 origins) | `frontend/src/app/layout.tsx:23-45` | 3개 외부 font CDN (`fonts.googleapis.com`, `api.fontshare.com`, `cdn.jsdelivr.net` Pretendard) 의 `<link rel="stylesheet">` 직접 로딩. `next/font` 미사용 → self-host 안 됨, FOUT/CLS, render-blocking | `next/font/local` + Satoshi/Pretendard woff2 self-host. Geist Mono 는 `next/font/google` (이미 Next.js 16 호환). subset preload | 0.5d |
| BUG-S27e-PERF-11 | FE / 번들 | P2 | NO | 대형 lib (tiptap + dnd-kit) 모든 페이지 entry 에 포함 | `frontend/src/features/notes/components/note-detail.tsx:9-10` / `note-editor.tsx:4-7` + `frontend/src/features/actions/components/action-kanban.tsx:15` | tiptap (`@tiptap/starter-kit` + extensions) ~ 100-150KB minified. dnd-kit ~ 30KB. static `import` 만 사용. notes/[id] 외 페이지에서도 chunk shared 가능 | `next/dynamic(() => import('...'), { ssr: false })` 으로 note editor / kanban 만 lazy. 또는 route segment lazy boundary (`loading.tsx`) 활용 | 0.5d |
| BUG-S27e-PERF-12 | 캐싱 (FE) | P3 | NO | 도메인별 staleTime 정책 부재 — 불필요 refetch | `frontend/src/lib/query-client.tsx:12` + 각 hook | global default `staleTime: 60_000` + `retry: 1`. `refetchOnWindowFocus` 명시 X (default true) → 사용자가 탭 전환할 때마다 모든 active query refetch. 단 onboarding 만 명시 false (line 38) | global default `refetchOnWindowFocus: false` + 명시 필요 곳에만 true (RAG metrics 등). 도메인별 staleTime: 회의 list 5min / RAG cache 30s / projects 1min 등 | 0.5d |
| BUG-S27e-PERF-13 | 알고리즘 | P3 | NO | 임베딩 chunking 비효율 (boundary 단순 char count) | `backend/src/embeddings/service.py:28-42` | `_chunk_text(max_chars=500, overlap=50)` — char count 기반 cut. 문장/문단 boundary 무시. RAG quality 영향 (BL-S27e-1 RAG latency 와 별개). 인코딩 측면은 Python str 이라 OK | sentence boundary 인지 chunker (kss / kiwipiepy / 정규식 `[.!?]\s+`) 또는 langchain RecursiveCharacterTextSplitter. 우선순위 낮음 (현재 working) | 1d |
| BUG-S27e-PERF-14 | 알고리즘 | P3 | NO | onboarding hook 매 RAG/회의/note/project 생성 시 추가 commit | `backend/src/rag/service.py:36-43,95,228` + `backend/src/meetings/pipeline_service.py:163-169` 외 | `OnboardingService.increment_step` 후 별도 `await session.commit()` — RAG cache-hit fast path 에도 commit 1회 추가. step >= target 인 사용자 (대부분의 활성 사용자) 는 no-op repository call 이지만 commit 자체는 RTT 발생 | repo `increment` 가 변경 없을 때 commit skip. 또는 router-level middleware 에서 응답 후 fire-and-forget BG task | 0.5d |
| BUG-S27e-PERF-15 | 리소스 / 알고리즘 | P3 | NO | OpenAI/Gemini client lazy import + recreate per task | `backend/src/memory/service.py:675-682,718-726,742-746` | `_call_distill` / `_call_embedding` / `_call_transcribe` 각 호출마다 `from google import genai` lazy import + `genai.Client(...)` 신규. 모듈-level singleton 또는 dependency injection 권장. AsyncOpenAI 도 동일. 호출 빈도 = memory capture 1회 = 3 calls (distill+embed+optional transcribe) | dependencies.py 에 `get_genai_client` / `get_openai_async_client` lifespan singleton + dependency 주입 | 0.5d |

---

## 개별 발견사항

### BUG-S27e-PERF-1 — R2 boto3 client 매 호출마다 재생성

- **영역**: 리소스 누수
- **심각도**: P1
- **차단**: NO
- **현재 측정값**: 환경 미실행 — 측정 불가. 정적 추정: aioboto3 client `__aenter__` 가 boto3 endpoint resolution + signing key cache 초기화 → 호출당 +300-1500ms (cold) / +50-200ms (warm DNS 캐시)
- **목표**: warm singleton 으로 client 재사용 → presigned-url 발급 / proxy upload / memory voice upload 호출 latency -50%
- **영향도 추정**: per-request -500ms~-1.5s (cold), 외부 5명 dogfooding 시 회의 업로드 path 의 critical UX 개선

#### 증상

`backend/src/common/r2.py` 의 4 메서드 모두 `async with self._session.client("s3", ...) as client` 패턴 — 매 호출마다 새로운 boto3 client 생성. BL-008 (memory/CONTEXT.md:62) 가 이미 P1 으로 식별, Sprint 27 까지 carry.

추가로 `backend/src/memory/service.py:636-649,654-666` 가 R2Service 의 `_session` 내부에 직접 접근하여 다시 client 생성 — 캡슐화 위반 + 동일 비용 2회.

#### Root cause

```python
# backend/src/common/r2.py:14
class R2Service:
    def __init__(self) -> None:
        self._session = aioboto3.Session()  # session 만 보유 — client 는 매 호출 생성

    async def get_presigned_upload_url(self, filename, content_type):
        async with self._session.client("s3", endpoint_url=..., aws_access_key_id=...) as client:
            upload_url = await client.generate_presigned_url(...)
        return {...}
```

```python
# backend/src/memory/service.py:636-649 — R2Service public API 우회
async def _upload_audio_to_r2(self, workspace_id, filename, content):
    ...
    async with self.r2_service._session.client(  # private _session 직접 접근
        "s3", endpoint_url=self.r2_service._get_endpoint_url(),
        aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
        ...
    ) as client:
        await client.put_object(Bucket=..., Key=key, Body=content, ContentType="audio/wav")
```

#### 최적화 방안

```python
# backend/src/common/r2.py
class R2Service:
    def __init__(self) -> None:
        self._session = aioboto3.Session()
        self._client = None
        self._client_lock = asyncio.Lock()

    async def _ensure_client(self):
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    settings = get_settings()
                    cm = self._session.client(
                        "s3",
                        endpoint_url=self._get_endpoint_url(),
                        aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
                        aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
                        region_name="auto",
                    )
                    self._client = await cm.__aenter__()
                    self._cm = cm
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._cm.__aexit__(None, None, None)
            self._client = None

    # FastAPI lifespan 에서 aclose() 호출

    async def get_presigned_upload_url(self, filename, content_type) -> dict:
        client = await self._ensure_client()
        ...

    async def upload_with_key(self, key: str, body: bytes, content_type: str) -> None:
        """memory 의 'memory/{ws}/' prefix path 도 R2Service 안에서. _session 직접 접근 제거."""
        client = await self._ensure_client()
        await client.put_object(Bucket=settings.r2_bucket_name, Key=key, Body=body, ContentType=content_type)
```

`memory/service.py` 의 `_upload_audio_to_r2` / `_download_audio_from_r2` 를 R2Service public API 로 이전.

#### 검증 방법

- 단위: `tests/common/test_r2_singleton.py` — `R2Service.get_presigned_upload_url()` 100 회 호출 후 `self._client` 가 한 번만 instantiate 됐는지 (`with patch.object(aioboto3.Session, 'client') as mock_client`)
- 통합: `time curl -X POST /api/v1/workspaces/{wid}/upload/presigned-url` × 10 회 — avg latency 비교 (전: ~800ms / 후 목표: ~200ms)
- 회귀: 기존 upload_validation 테스트 20건 + memory voice e2e 통과

#### 비용

- 개발: 0.5d
- 운영 비용 변화: -10% Cloud Run CPU time on upload paths (client init 비용 절감). R2 비용 변화 없음.

---

### BUG-S27e-PERF-2 — meetings/actions/inbox `workspace_id` 인덱스 누락

- **영역**: DB
- **심각도**: P1
- **차단**: NO (현재 dogfooding 규모 ~수십 row 에선 영향 미미, 외부 5명+ 시 200-row workspace 도달 시 즉시 발현)
- **현재 측정값**: 환경 미실행 — 측정 불가. 정적 추정: seq scan + sort 가 100 row 기준 ~5ms / 10k row 기준 ~150ms / 100k row 기준 ~2s
- **목표**: workspace list endpoint 모두 ≤ 50ms (Neon RTT 25-50ms 위에)
- **영향도 추정**: ListBy queries -50% to -90% (scale ↑ 시 더 큼)

#### 증상

`meetings/models.py:17`, `actions/models.py:32`, `inbox/models.py:22` 의 `workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")` — `index=True` 없음. PostgreSQL 의 ForeignKeyConstraint 는 **referenced** table 에는 PK 인덱스가 있지만 **referencing** table column 에는 인덱스 자동 생성 안 됨.

Sprint 19 PR #2 가 `meetings(id, workspace_id) UNIQUE` 만들었지만 그건 composite UNIQUE — leftmost 가 `id` 라 `WHERE workspace_id = X` 만으론 안 탐. `notes/models.py` 만 명시 `idx_notes_workspace_id` (e2c3782ab9c6) 존재.

영향 query:
- `meetings.list_meetings` → `WHERE workspace_id = X ORDER BY created_at DESC LIMIT 20` (seq scan + sort)
- `action_items.list_action_items` → `WHERE workspace_id = X AND (status=Y)` (seq scan)
- `inbox_items.list_inbox` → `WHERE workspace_id = X AND is_processed = Y ORDER BY created_at DESC` (seq scan + sort)

#### Root cause

```python
# backend/src/meetings/models.py:17 — index=True 없음
workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")

# vs backend/src/notes/models.py:22 — 명시 index=True
workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
```

#### 최적화 방안

신규 alembic revision — composite covering 인덱스 (BL-036 패턴 정합):

```python
"""Sprint 27e — list-by-workspace 핫패스 인덱스 보강"""
def upgrade() -> None:
    # meetings: workspace_id + created_at DESC (ORDER BY 동반)
    op.create_index(
        "idx_meetings_workspace_created",
        "meetings",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )
    # action_items: workspace_id + status (필터 동반)
    op.create_index(
        "idx_actions_workspace_status",
        "action_items",
        ["workspace_id", "status"],
        unique=False,
    )
    # inbox_items: workspace_id + is_processed + created_at DESC
    op.create_index(
        "idx_inbox_workspace_processed_created",
        "inbox_items",
        ["workspace_id", "is_processed", sa.text("created_at DESC")],
        unique=False,
    )
```

추가로 SQLModel `Field(... index=True)` 도 보수적으로 추가 — drift gate 가 metadata 정합 확인.

#### 검증 방법

- staging 에서 EXPLAIN ANALYZE 전후 비교 (사용자 별도)
- BL-036 패턴 정합: 동일 sprint 의 migration `c3d4e5f6a7b8_bl036_perf_indexes.py` 가 좋은 reference (workspace_members + projects)
- 테스트: `tests/meetings/test_list_pagination.py` 정합 유지

#### 비용

- 개발: 0.5d (3 migration + drift gate 검증)
- 운영 비용 변화: index storage +~5MB per 10k rows. 트레이드오프 정합.

---

### BUG-S27e-PERF-3 — upload proxy 500MB 전체 메모리 적재 (OOM 위험)

- **영역**: sync blocking / 리소스
- **심각도**: P1
- **차단**: NO (외부 5명 dogfooding 동시 업로드 5건 이상 시 위험. 현재 Cloud Run 메모리 default 가 2GB 면 4건 동시 = 2GB consumed)
- **현재 측정값**: 환경 미실행 — 측정 불가. 정적: `file.read()` 500MB → Python bytes 객체 ≈ 530MB heap. 그 다음 `r2.upload_file_bytes(data=bytes)` 가 동일 객체 참조 → boto3 multipart upload 가 또 copy 가능. 피크 ~1GB per upload
- **목표**: streaming upload — 메모리 사용량 64KB chunk 단위로 고정
- **영향도 추정**: 동시 업로드 5건 시 메모리 -95% (~2.5GB → ~100MB)

#### 증상

```python
# backend/src/upload/router.py:91-103
@router.post("/file", status_code=201)
async def upload_file_proxy(...):
    ...
    if file.size is not None and file.size > validator.max_bytes:
        raise HTTPException(status_code=413, ...)

    file_bytes = await file.read()  # ⚠️ 500MB 까지 RAM 적재
    try:
        validator.validate(filename, content_type, file_bytes)
    except ...
    r2 = R2Service()
    file_key = await r2.upload_file_bytes(filename, content_type, file_bytes)  # 또 1회 사본
    return {"fileKey": file_key}
```

```python
# backend/src/common/r2.py:49-68
async def upload_file_bytes(self, filename, content_type, data: bytes) -> str:
    ...
    async with self._session.client("s3", ...) as client:
        await client.put_object(Bucket=..., Key=file_key, Body=data, ContentType=content_type)
    return file_key
```

`file.size` 사전 차단은 정직한 사용자가 500MB 보내는 정상 case 를 막지 못함 — `max_upload_bytes = 500 * 1024 * 1024` (`backend/src/core/config.py:48`).

#### Root cause

FastAPI `UploadFile` 의 spooled file 을 streaming 으로 활용하지 않고 일괄 read.

#### 최적화 방안

content signature 검증은 head 512 bytes 만 필요 — `file.read(512)` + `file.seek(0)` 으로 head 만 검사 후 spool 그대로 boto3 stream:

```python
# backend/src/upload/router.py
@router.post("/file", status_code=201)
async def upload_file_proxy(
    workspace_id: uuid.UUID,
    file: UploadFile = File(...),
    member: WorkspaceMember = Depends(require_member),
    validator: UploadValidator = Depends(get_upload_validator),
):
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"

    # pre-read size
    if file.size is not None and file.size > validator.max_bytes:
        raise HTTPException(status_code=413, ...)

    # head 512 만 읽어 signature 검증
    head = await file.read(512)
    await file.seek(0)

    try:
        validator.validate_head_only(filename, content_type, head, declared_size=file.size)
    except ...

    r2 = R2Service()
    # boto3 upload_fileobj — multipart streaming, 64KB chunk
    file_key = await r2.upload_streaming(file.file, filename, content_type)
    return {"fileKey": file_key}
```

```python
# backend/src/upload/service.py — UploadValidator
def validate_head_only(self, filename, declared_mime, head, declared_size):
    if declared_size is not None:
        if declared_size == 0: raise EmptyFileError()
        if declared_size > self.max_bytes: raise FileTooLargeError(declared_size, self.max_bytes)
    self.validate_pre_upload(filename, declared_mime)
    detected = _detect_mime_from_signature(head)
    if not _is_signature_compatible(detected, declared_mime):
        raise ContentMismatchError(detected or "unknown", declared_mime)
    if not _check_text_content(head, declared_mime):
        raise ContentMismatchError("non-utf8 bytes", declared_mime)
```

```python
# backend/src/common/r2.py — streaming
async def upload_streaming(self, fileobj, filename: str, content_type: str) -> str:
    file_key = f"uploads/{uuid.uuid4()}/{filename}"
    client = await self._ensure_client()  # BUG-S27e-PERF-1 정합
    await client.upload_fileobj(
        Fileobj=fileobj,
        Bucket=settings.r2_bucket_name,
        Key=file_key,
        ExtraArgs={"ContentType": content_type},
    )
    return file_key
```

주의: `file.size` 가 None 일 때 (chunked transfer encoding) — content-length 헤더 검증 dependency 또는 streaming counter 로 enforce.

#### 검증 방법

- 부하 테스트: `locust` 으로 500MB 파일 5건 동시 업로드 → Cloud Run instance 메모리 < 500MB 유지 (Cloud Logging metric)
- 회귀: 기존 upload_validation 20 tests 통과 (head-only 변경 후 signature 검증 정합)

#### 비용

- 개발: 1d (validator 4 layer 재배선 + R2Service streaming API + UploadFile.size 의 None 경로 보강)
- 운영 비용 변화: Cloud Run 메모리 tier 1GB → 512MB 가능 (월 비용 -30%)

---

### BUG-S27e-PERF-4 — Gemini/OpenAI 호출 timeout/retry/circuit breaker 부재

- **영역**: sync blocking / AI
- **심각도**: P1
- **차단**: NO (현재 Gemini API 안정적 — 외부 5명 동시 dogfooding + Gemini incident 시 즉시 발현)
- **현재 측정값**: 환경 미실행. 정적: Gemini API 정상 4-8s, p99 tail latency 가능 (vendor 측 incident 시 30s+ 또는 hang)
- **목표**: tail latency cap 30s + 자동 retry 3회 + circuit breaker open 60s
- **영향도 추정**: 회의 처리 worst-case 5min+ → ≤ 90s 보장. Cloud Run worker hang 회피 → 가용성 +10%

#### 증상

```python
# backend/src/services/ai_processing.py:81
response = await self.client.aio.models.generate_content(
    model=GEMINI_MODEL,
    contents=f"{MEETING_SUMMARY_SYSTEM_PROMPT}\n\n{transcript}",
)  # timeout 0 + retry 0
```

같은 패턴: `extract_actions_and_link:127`, `stream_rag_answer:151`, `memory.service._call_distill:682`. Whisper API (`transcription.py:118`) 도 동일.

Gemini hang → 회의 BG task 가 Cloud Run request timeout (300s, configurable) 까지 점유 → 다른 BG task slot 차단. Cloud Run 의 max-concurrency=80 default 에서 hang 80 건 시 instance 완전 정지.

#### Root cause

httpx (Gemini SDK 내부) 의 default timeout = `None` (무한). 외부 API 안정성을 본 도메인 코드가 책임지지 않음.

#### 최적화 방안

```python
# backend/src/services/ai_processing.py
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

GEMINI_TIMEOUT_SEC = 30
GEMINI_STREAM_TIMEOUT_SEC = 60

class GeminiCircuitBreaker:
    """5 연속 실패 → 60s open → half-open 1 probe."""
    def __init__(self): self.failures = 0; self.opened_at = None
    def can_call(self) -> bool:
        if self.opened_at and (time.time() - self.opened_at) < 60: return False
        return True
    def on_success(self): self.failures = 0; self.opened_at = None
    def on_failure(self):
        self.failures += 1
        if self.failures >= 5: self.opened_at = time.time()

_breaker = GeminiCircuitBreaker()

class AIProcessingService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((asyncio.TimeoutError, httpx.HTTPError)),
    )
    async def summarize(self, transcript: str) -> dict:
        if not _breaker.can_call():
            raise RuntimeError("Gemini circuit breaker OPEN")
        try:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=f"{MEETING_SUMMARY_SYSTEM_PROMPT}\n\n{transcript}",
                ),
                timeout=GEMINI_TIMEOUT_SEC,
            )
        except (asyncio.TimeoutError, Exception) as e:
            _breaker.on_failure()
            raise
        _breaker.on_success()
        raw = parse_json_response(response.text)
        ...
```

streaming 은 timeout 적용 어려움 → 첫 chunk timeout 만 cap (e.g. 10s 안에 첫 토큰 안 오면 cancel).

#### 검증 방법

- 단위: `tests/services/test_ai_timeout.py` — Gemini client mock 으로 `asyncio.sleep(60)` 시 30s 안에 TimeoutError + retry 3회 + 후속 circuit open
- 통합: 의도적 Gemini API key 누락 / network drop 시 BG task 가 정확한 시간 안에 fail → `Meeting.status='failed'` + `error_message` populated

#### 비용

- 개발: 1.5d (3 도메인 × 동일 패턴 적용 + circuit breaker 테스트)
- 운영 비용 변화: 운영 안정성 ↑ — Cloud Run instance count -10% (hang 회피)

---

### BUG-S27e-PERF-5 — RAG SSE disconnect 감지 부재 → Gemini 토큰 비용 누수

- **영역**: SSE / 리소스
- **심각도**: P1
- **차단**: NO (외부 5명 dogfooding 시 사용자 답변 중도 이탈 ~30% 가정 시 즉시 영향)
- **현재 측정값**: 환경 미실행. 정적: RAG 답변 평균 1k-3k token × Gemini Flash-Lite 비용 (~$0.20/1M output) — 1k disconnect/일 시 일일 ~$1 비용 (소액이나 누적)
- **목표**: client disconnect 감지 시 즉시 Gemini stream cancel + cache 저장 skip
- **영향도 추정**: Gemini 토큰 비용 -30% (이탈률 기준), BG task 점유 시간 -50% (긴 답변 도중 이탈 시)

#### 증상

```python
# backend/src/rag/router.py:30-42
async def event_generator():
    async for event in pipeline.ask(
        question=data.question,
        workspace_id=workspace_id,
        ...
    ):
        yield event
return EventSourceResponse(event_generator())
```

- `Request` 객체 미주입 → `request.is_disconnected()` 호출 불가
- `pipeline.ask` / `RagService.ask` 의 `[8] Generation` 블록 안의 `async for token in self.ai_service.stream_rag_answer(...)` 는 사용자가 탭 닫아도 Gemini stream 끝까지 받음

#### Root cause

SSE 의 client cleanup 책임이 명시되지 않음. sse-starlette `EventSourceResponse` 는 disconnect 시 generator 를 `aclose()` 호출하지만 — Gemini stream 은 그 안에서 일반 `async for` 라 cancel propagate 까지 시간 걸림. 명시적 polling 권장.

#### 최적화 방안

```python
# backend/src/rag/router.py
from fastapi import Request

@router.post("/ask")
async def ask_rag(
    request: Request,  # 추가
    workspace_id: uuid.UUID,
    ...
):
    async def event_generator():
        async for event in pipeline.ask(
            question=data.question,
            workspace_id=workspace_id,
            ...
            disconnect_check=lambda: request.is_disconnected(),  # 추가
        ):
            yield event

    return EventSourceResponse(event_generator())
```

```python
# backend/src/rag/service.py — Generation 블록
async for token in self.ai_service.stream_rag_answer(question, sources_text):
    if disconnect_check and await disconnect_check():
        logger.info("RAG client disconnected — Gemini stream cancel + cache skip")
        return  # cache 저장 skip
    full_answer += token
    yield {"event": "answer", "data": ...}
```

또는 더 간단히 `request: Request` 를 `RagPipelineService.ask` 까지 전달.

#### 검증 방법

- 통합: e2e — RAG 답변 시작 후 1초 뒤 fetch abort → BE 로그에서 "client disconnected" + cache rows 증가 없음 확인
- 비용: Cloudflare/Gemini 로그에서 disconnect 직후 outbound token 수 ~ 100 (현재) → ~0 (수정 후)

#### 비용

- 개발: 0.5d
- 운영 비용 변화: Gemini API 비용 -30%

---

### BUG-S27e-PERF-6 — promote 시 cache 무차별 wipe (cache hit 률 0 수렴)

- **영역**: 캐싱
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적: 1 promote → ws 전체 SemanticCache wipe. team workspace 에서 daily 10 promotes 시 cache hit 률 ~ 0
- **목표**: 영향받는 source_chunk_ids 만 무효화 → cache hit 률 60-80% 유지
- **영향도 추정**: RAG p95 latency -50% (cache hit 시 200ms vs miss 시 ~5s)

#### 증상

```python
# backend/src/meetings/service.py:516
# meeting promote BG 의 마지막 단계
embed_repo = _EmbeddingRepository(session)
await embed_repo.delete_caches(target_workspace_id, None)  # ws 전체 wipe
```

```python
# backend/src/meetings/pipeline_service.py:155
await embedding_service.invalidate_cache(meeting.workspace_id, project_id)
# project_id 없으면 ws 전체 wipe (delete_caches 의 default 동작)
```

#### Root cause

cache 의 `sources` JSONB 컬럼이 chunk_id 들을 보유 — `WHERE sources @> '[{"id":"X"}]'` 로 영향 받은 cache row 만 찾을 수 있음. 현재는 broad wipe.

#### 최적화 방안

```python
# backend/src/embeddings/repository.py
async def delete_caches_by_source(self, workspace_id, source_type, source_id) -> None:
    """source_type='meeting' AND source_id 가 cache.sources 에 포함된 row 만 삭제."""
    sql = text("""
        DELETE FROM semantic_caches
        WHERE workspace_id = :wid
          AND sources @> :probe::jsonb
    """)
    probe = json.dumps([{"sourceType": source_type, "sourceId": str(source_id)}])
    await self.session.execute(sql, {"wid": workspace_id, "probe": probe})
    await self.session.flush()
```

호출처 갱신:
- `meetings/pipeline_service.py:155` → `delete_caches_by_source(workspace_id, "meeting", meeting.id)`
- `meetings/service.py:516` (promote BG) → target ws 의 new_meeting_id 기준

#### 검증 방법

- 단위: cache fixture 5 row (다양한 sources) → 1 meeting 의 promote 시 cache 4 row 유지 + 1 row 삭제
- 통합: dashboard cache hit rate metric (`MemoryQueryEmbeddingCache` 의 hit/miss event log)

#### 비용

- 개발: 1d
- 운영 비용 변화: Gemini 비용 -50% (cache hit 률 ↑)

---

### BUG-S27e-PERF-7 — MemoryQueryEmbeddingCache TTL 청소 cron 부재

- **영역**: 캐싱 / 리소스
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적: 7d TTL lookup-side 만, INSERT side 의 cleanup 없음 → 시간당 N row 누적. 100 recall/일 × 30일 = 3000 row × halfvec(1536) 2B/dim = 9MB raw + HNSW 인덱스 ~ 18MB
- **목표**: 7일 후 만료 row 자동 정리
- **영향도 추정**: DB storage 일정 유지, INSERT ON CONFLICT seek 시간 일정

#### 증상

`MemoryQueryEmbeddingCache.get_query_embedding_cache` 는 `cutoff = now - 7d` 로 cutoff filter 후 lookup. INSERT 는 `ON CONFLICT DO NOTHING` — 만료된 row 가 같은 normalized_query 면 갱신 안 됨 (구 embedding 영구 stale).

#### Root cause

테이블의 created_at 인덱스 없음 + 정리 작업 없음.

#### 최적화 방안

옵션 A — partial expression index + scheduled DELETE:

```sql
-- alembic migration
CREATE INDEX idx_memory_qcache_created
  ON memory_query_embedding_cache (created_at)
  WHERE created_at < now() - interval '7 days';
```

```python
# backend/src/memory/service.py
async def cleanup_expired_query_cache(self, days: int = 7) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await self.session.execute(
        text("DELETE FROM memory_query_embedding_cache WHERE created_at < :cutoff"),
        {"cutoff": cutoff},
    )
    deleted = result.rowcount
    await self.session.commit()
    return deleted
```

Cloud Scheduler — `cleanup_expired_r2_audio` 와 동일 cron pattern 정합.

옵션 B — INSERT 시 expired 같은 normalized_query 발견 시 UPDATE:

```python
stmt = pg_insert(...).on_conflict_do_update(
    index_elements=["workspace_id", "normalized_query"],
    set_={
        "embedding": embedding,
        "created_at": datetime.utcnow(),
    },
    where=text("memory_query_embedding_cache.created_at < now() - interval '7 days'"),
)
```

#### 검증 방법

- 단위: 8d 전 row 1건 + 정상 row 2건 fixture → `cleanup_expired_query_cache()` 후 row 2건 잔존
- 운영: Neon 의 monitoring — `memory_query_embedding_cache` row count 안정

#### 비용

- 개발: 0.5d
- 운영 비용 변화: Neon storage -5MB/month (작음)

---

### BUG-S27e-PERF-8 — embedding_chunks.created_at 인덱스 부재 (RAG time_range filter)

- **영역**: DB / 알고리즘
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적: HNSW 가 ef_search=40 으로 후보 set 만들고 time_range filter 가 post-filter — 시간 범위 좁고 후보 부족 시 `max_scan_tuples=20000` 까지 확장 — 100ms+ tail latency 가능
- **목표**: time_range 적용된 RAG p95 ≤ 5s
- **영향도 추정**: BL-S27e-1 (RAG p95 < 5s) 의 일부분

#### 증상

`embedding_chunks.created_at` 컬럼이 `default_factory=datetime.utcnow` 만, index 없음. RAG 의 vector_search / text_search 는:

```sql
WHERE workspace_id = X AND chunk_level = 2
  AND created_at >= CAST(now() - CAST(:time_window AS interval) AS timestamp)
ORDER BY embedding <=> :qvec  -- HNSW
LIMIT 50
```

PG planner 가 HNSW 인덱스 우선 사용 → time_range filter 는 row-by-row 평가 → post-filter 탈락 비율 ↑ 시 `hnsw.max_scan_tuples` 까지 ef_search 확장 (Sprint 16 SET LOCAL 정책 정합).

#### Root cause

time-window query 가 의외로 흔한 케이스 (대시보드 "지난 1주 회의" RAG 요청 등). HNSW 가 시간 정렬과 직교 → 후보 set 의 일부만 time-pass.

#### 최적화 방안

partial composite index:

```python
op.execute("""
    CREATE INDEX CONCURRENTLY idx_chunks_ws_created
    ON embedding_chunks (workspace_id, created_at DESC)
    WHERE chunk_level = 2
""")
```

PG planner 가 작은 time-window 일 때 bitmap-and (workspace_id + time) → vector ANN ordered subset 으로 plan 가능. 다만 ANN 의 정확도 trade-off 가 있어 EXPLAIN ANALYZE 권고.

#### 검증 방법

- 사용자 별도 EXPLAIN ANALYZE on staging (Neon SQL editor)
- 회귀: 기존 RAG e2e tests 통과

#### 비용

- 개발: 0.5d + 측정 0.5d
- 운영 비용 변화: storage +~3MB/10k chunks

---

### BUG-S27e-PERF-9 — inbox classify N+1

- **영역**: 알고리즘 (N+1)
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적: N=1 (95% 경우) 면 ~25-50ms / N=5 시 ~125-250ms
- **목표**: 1 회 쿼리로 batch verify
- **영향도 추정**: N>=3 inbox classify request 의 latency -60%

#### 증상

```python
# backend/src/inbox/service.py:100-104
verified_projects: list = []
for project_id in project_ids:
    project = await self.project_repo.find_by_id(project_id, workspace_id)  # N RTT
    if project is None:
        raise ProjectNotFoundError()
    verified_projects.append(project)
```

#### Root cause

`project_repo.find_by_id` 가 단건 메서드 — bulk variant 부재.

#### 최적화 방안

```python
# backend/src/projects/repository.py
async def find_by_ids_in_workspace(self, project_ids: list[uuid.UUID], workspace_id: uuid.UUID) -> dict[uuid.UUID, Project]:
    if not project_ids:
        return {}
    result = await self.session.exec(
        select(Project).where(
            Project.workspace_id == workspace_id,
            Project.id.in_(project_ids),
        )
    )
    return {p.id: p for p in result.all()}
```

```python
# backend/src/inbox/service.py
projects_map = await self.project_repo.find_by_ids_in_workspace(project_ids, workspace_id)
missing = [pid for pid in project_ids if pid not in projects_map]
if missing:
    raise ProjectNotFoundError()
verified_projects = list(projects_map.values())
```

#### 검증 방법

- 단위: `tests/inbox/test_classify.py` — 3 project_ids 통과 시 1 query (mock counter)
- 회귀: 기존 cross-workspace 검증 정합 (workspace_id filter intact)

#### 비용

- 개발: 0.25d

---

### BUG-S27e-PERF-10 — FE 폰트 3 origin 외부 stylesheet (next/font 미사용)

- **영역**: FE / 번들
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: 환경 미실행 — Lighthouse 측정 권고. 정적: 3 외부 origin × ~150ms DNS+TLS+stylesheet GET + render-blocking
- **목표**: self-host woff2 + preload + display=swap → LCP -300~500ms
- **영향도 추정**: dashboard LCP -300~500ms

#### 증상

```tsx
// frontend/src/app/layout.tsx:23-45
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
<link rel="preconnect" href="https://api.fontshare.com" />
<link rel="preconnect" href="https://cdn.fontshare.com" crossOrigin="anonymous" />
<link href="https://api.fontshare.com/v2/css?f[]=satoshi@..." rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Geist+Mono..." rel="stylesheet" />
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css" rel="stylesheet" />
```

#### Root cause

`next/font` 미사용 → preload 자동화 + 인라인 fallback 못 받음. 3개 외부 origin DNS lookup + render-blocking stylesheet.

#### 최적화 방안

`next/font/local` 로 Satoshi/Pretendard self-host:

```tsx
import localFont from 'next/font/local';
import { Geist_Mono } from 'next/font/google';

const satoshi = localFont({
  src: [
    { path: './fonts/Satoshi-Variable.woff2', weight: '400 700', style: 'normal' },
  ],
  display: 'swap',
  variable: '--font-satoshi',
});

const pretendard = localFont({
  src: './fonts/PretendardVariable.woff2',
  display: 'swap',
  variable: '--font-pretendard',
});

const geistMono = Geist_Mono({ weight: ['400', '500'], display: 'swap', variable: '--font-geist-mono' });

export default function RootLayout({ children }) {
  return (
    <html lang="ko" className={`${satoshi.variable} ${pretendard.variable} ${geistMono.variable}`}>
      ...
```

#### 검증 방법

- Lighthouse 전후 비교 (LCP / CLS)
- bundle-analyzer 로 font payload 추적

#### 비용

- 개발: 0.5d (woff2 다운로드 + 라이센스 확인 — Fontshare 무료 상업용 OK / Pretendard OFL)

---

### BUG-S27e-PERF-11 — tiptap + dnd-kit 정적 import (대형 lib)

- **영역**: FE / 번들
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: 환경 미실행 — `next build && analyze` 권고. 정적: tiptap ~ 120KB minified + ext-character-count ~ 5KB + ext-placeholder ~ 3KB + dnd-kit ~ 30KB = ~160KB shared chunk
- **목표**: notes/[id] 와 actions/kanban 에서만 로딩 → 다른 페이지 -160KB
- **영향도 추정**: dashboard TTI -200ms

#### 증상

```tsx
// frontend/src/features/notes/components/note-editor.tsx
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { CharacterCount } from "@tiptap/extension-character-count";
```

```tsx
// frontend/src/features/actions/components/action-kanban.tsx
import { ... } from "@dnd-kit/core";
```

#### Root cause

static import → Next.js bundler 가 shared chunk 로 split 가능하지만 client-side hydration 으로 모든 페이지 entry 에서 일부 로딩.

#### 최적화 방안

```tsx
// frontend/src/features/notes/components/note-editor-lazy.tsx
import dynamic from "next/dynamic";

export const NoteEditor = dynamic(
  () => import("./note-editor").then(m => m.NoteEditor),
  { ssr: false, loading: () => <NoteEditorSkeleton /> }
);
```

같은 패턴: `action-kanban-lazy.tsx`.

#### 검증 방법

- `next build` 후 `.next/analyze/client.html` 에서 entry chunk 크기 비교
- e2e: notes/[id] 진입 시 editor 정상 작동

#### 비용

- 개발: 0.5d

---

### BUG-S27e-PERF-12 — React Query global stale time / refetchOnWindowFocus 정책 부재

- **영역**: 캐싱 (FE)
- **심각도**: P3
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적: 사용자가 탭 전환마다 모든 active query refetch (default true)
- **목표**: 도메인별 stale time + window focus 정책
- **영향도 추정**: BE 요청 -30~50% (탭 전환 사용자)

#### 증상

```tsx
// frontend/src/lib/query-client.tsx
new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      retry: 1,
    },
  },
});
```

`refetchOnWindowFocus` 미설정 = default `true`. only `frontend/src/features/onboarding/hooks.ts:38` 가 명시 false.

#### Root cause

React Query default 가 active development 친화적 (focus 시 latest) — production 정합 X.

#### 최적화 방안

```tsx
new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,  // 도메인별로 명시 true 설정
      refetchOnReconnect: true,
    },
  },
});
```

도메인별 stale:
- meetings list — `staleTime: 5 * 60_000` (5min)
- projects list — `staleTime: 60_000` + `refetchOnWindowFocus: true` (협업 갱신)
- workspace member — `staleTime: 10 * 60_000`
- onboarding — 이미 적용
- RAG metrics — `refetchInterval: 30_000` 그대로

#### 검증 방법

- e2e: 두 탭 동시 열고 한 탭에서 데이터 변경 → 다른 탭 invalidate via window event (manual)
- BE 로그: `/api/v1/workspaces/{wid}/meetings` 호출 빈도 추적

#### 비용

- 개발: 0.5d

---

### BUG-S27e-PERF-13 — chunk_text boundary 단순 char count

- **영역**: 알고리즘
- **심각도**: P3
- **차단**: NO
- **현재 측정값**: 환경 미실행. RAG quality 영향이지 latency 직접 영향은 아님
- **목표**: sentence/paragraph aware chunker
- **영향도 추정**: RAG 답변 quality +10-20% (관련도)

#### 증상

```python
# backend/src/embeddings/service.py:28-42
@staticmethod
def _chunk_text(text: str, max_chars: int = 500, overlap_chars: int = 50) -> list[str]:
    if len(text) <= max_chars: return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start = end - overlap_chars
    return chunks
```

500 char boundary cut — 한국어 단어/문장 가운데를 잘라 의미 손실.

#### 최적화 방안

```python
import re

@staticmethod
def _chunk_text(text: str, max_chars: int = 500, overlap_chars: int = 50) -> list[str]:
    """문장 boundary 인지 chunking. 한국어 . ! ? 또는 영문 [.!?]"""
    if len(text) <= max_chars: return [text]
    sentences = re.split(r'(?<=[.!?。])\s+', text)
    chunks, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_chars:
            current += (" " + sent) if current else sent
        else:
            if current: chunks.append(current.strip())
            current = sent[-overlap_chars:] + " " + sent if len(current) > overlap_chars else sent
    if current: chunks.append(current.strip())
    return chunks
```

또는 production-grade chunker — `langchain.text_splitter.RecursiveCharacterTextSplitter`.

#### 비용

- 개발: 1d (validation + e2e RAG quality 회귀)

---

### BUG-S27e-PERF-14 — onboarding hook 매 RAG/회의/note/project 호출 시 추가 commit

- **영역**: 알고리즘
- **심각도**: P3
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적: commit RTT ~ 25-50ms × cache-hit RAG (otherwise hidden in latency)
- **목표**: step >= target 시 commit skip
- **영향도 추정**: cache-hit RAG fast path -25-50ms

#### 증상

```python
# backend/src/rag/service.py:36-43
async def _advance_onboarding(self, user_id):
    try:
        from src.onboarding.service import OnboardingService
        session = self.embedding_repo.session
        onboarding = OnboardingService(session)
        await onboarding.increment_step(user_id, 4)
        await session.commit()  # 항상 commit
    except ...
```

`OnboardingService.increment_step` 는 idempotent — 현재 step >= target 이면 no-op. 하지만 `commit()` 은 호출됨.

#### 최적화 방안

`increment_step` 의 반환을 `bool` (실제 변경 여부) → 변경 0 이면 commit skip:

```python
async def increment_step(self, user_id, target_step) -> bool:
    """반환: True if 변경 발생 (commit 필요)."""
    return await self._repo.increment(user_id, target_step) > 0  # rowcount
```

```python
# 호출처
changed = await onboarding.increment_step(user_id, 4)
if changed:
    await session.commit()
```

#### 비용

- 개발: 0.5d

---

### BUG-S27e-PERF-15 — Gemini/OpenAI client 매 호출마다 lazy import + 재생성

- **영역**: 리소스 / 알고리즘
- **심각도**: P3
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적: `genai.Client(...)` 또는 `AsyncOpenAI(...)` ~ 10-30ms init (TLS context cache)
- **목표**: lifespan singleton
- **영향도 추정**: per-call -20ms × 3 calls per capture = -60ms

#### 증상

```python
# backend/src/memory/service.py:675-682
async def _call_distill(text):
    from google import genai
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
    ...
```

같은 패턴 3 메서드 (`_call_distill` / `_call_embedding` / `_call_transcribe`).

`AIProcessingService` (`services/ai_processing.py:62`) 와 `TranscriptionService` (`services/transcription.py:74`) 는 `__init__` 에서 1회만 — 비교적 정상. memory/service.py 의 module-level 함수가 문제.

#### Root cause

Memory 도메인은 test monkeypatch 진입점 (`memory/service.py:668` comment) 으로 모듈-level 함수 유지. 그러나 client 인스턴스는 명시적 DI 가능.

#### 최적화 방안

```python
# backend/src/memory/dependencies.py
from functools import cache

@cache
def _genai_client():
    return genai.Client(api_key=get_settings().gemini_api_key.get_secret_value())

@cache
def _openai_client():
    return AsyncOpenAI(api_key=get_settings().openai_api_key.get_secret_value())

# memory/service.py
async def _call_distill(text):
    client = _genai_client()
    ...
```

#### 비용

- 개발: 0.5d

---

## Summary

- 발견 P0: **0건** (RAG / 회의 / dashboard critical path 의 user-acceptable 한계 명백 위반 0)
- 발견 P1: **5건** — BUG-S27e-PERF-1, 2, 3, 4, 5
- 발견 P2: **6건** — BUG-S27e-PERF-6, 7, 8, 9, 10, 11
- 발견 P3: **4건** — BUG-S27e-PERF-12, 13, 14, 15
- 차단 분류: **0건** (SCOPE GO 조건 "RAG ≤ 15s / API ≤ 500ms / 회의 ≤ 60s" 정합 — 정적 추정 헤드룸 작음이지만 명백 violation 0)
- 비차단 분류: **15건**

### 가장 high-impact 3건

1. **BUG-S27e-PERF-3 (P1)** — upload proxy 500MB 메모리 적재. Cloud Run OOM 위험 → 동시 업로드 시 instance 정지. 외부 5명 dogfooding 시 가장 빠르게 발현 가능한 critical resource issue. 메모리 -95%, Cloud Run 메모리 tier 다운 가능 (-30% 비용).

2. **BUG-S27e-PERF-4 (P1)** — Gemini/Whisper 호출 timeout/retry/circuit breaker 부재. AI vendor incident 시 회의 파이프라인 hang → Cloud Run worker 점유 → 가용성 -90%. tail latency cap 30s 보장 + circuit breaker open 60s.

3. **BUG-S27e-PERF-2 (P1)** — `meetings`/`actions`/`inbox` 의 workspace_id 인덱스 누락. dogfooding 규모 ~수십 row 에선 OK, 200 row+ 도달 시 즉시 list latency p95 ↑. 3개 alembic migration 만으로 -90% latency 회복.

### 차단/비차단 분류 기준 정합

본 audit 는 SCOPE.md 의 GO 조건 (RAG ≤ 15s / API ≤ 500ms / 회의 ≤ 60s) 을 anchor 로 분류:

- **차단 (Blocking)** = 정적 분석으로 명백 violation + 외부 5명 dogfooding 즉시 발현 — 0건
- **비차단 (Non-blocking)** = 측정 가능 비효율, scaling 도달 시 발현, 또는 권고 — 15건

P1 5건은 외부 5명 dogfooding 동안 critical 발현 가능성 = 중간. 단기 1-2개 sprint 내 처리 권고. P2/P3 는 Sprint 28+ 또는 production scale (>1만 사용자) 도달 시.

### 검증 환경 제약 명시

본 audit 는 **정적 분석 only** — FE/BE down 환경에서 실 latency / Lighthouse / DB query plan / Cloud Run metric 수집 불가. SCOPE.md "성능 critical path p95" 의 정량 검증은 다음 환경에서 실측 권고:

1. local: FE port 3000 + BE port 8000 up → curl `-w "%{time_total}"` + Lighthouse + FastAPI middleware query log
2. staging: Cloud Run `kairos-api-imrsiyibaa-du.a.run.app` + Neon DB → Cloud Logging metric + Neon SQL editor EXPLAIN ANALYZE
3. production (사용자 결정 시): RAG endpoint 5 sample p95 + dashboard LCP/TTI + 회의 처리 e2e timing

본 audit 의 정적 추정값은 코드 read 기반의 conservative estimate — 실측 결과로 갱신 권고.
