# Sprint 27e Round 2 — 성능 Cross-Check + 정적 보완

- 검사 일시: 2026-05-25 KST
- baseline commit: `b7e704e` (main HEAD, PR #109 머지 완료)
- 환경: FE/BE down → 실측 SKIP. alembic + core/database.py + core/lifespan.py + dependencies.py 정합 검토 only.
- 검사자 시각: Round 1 의 정적 추정값 검증 + 정적 분석으로 놓친 영역 (race / lifespan / connection pool / DI 인스턴스 폭주) 보완.

## 0. Sprint 27d cited baseline 신뢰성 검증

`agent-3-cto.md:28` (Sprint 27d) — **RAG localhost dev 5 sample**: min 7.3s / p50 10.8s / max 14.2s / avg 10.6s.

→ baseline 신뢰도 분석:
- 5 sample 만으로 p95 불가 (p95 ≥ 20 sample 필요). 본 측정은 max 14.2s 가 p95 근접 가정 시 **SCOPE GO 한계 ≤ 15s 와 거의 동등 — 헤드룸 ~5% only**.
- localhost dev 환경 (Cloud Run cold start + Neon RTT + Gemini API 외부 호출 모두 다름) → production 시 ±30% 예상.
- ADR-019 Phase B 의 Gemini 3.1-flash-lite 가 이미 적용 (`ai_processing.py:22` GEMINI_MODEL). Phase A spike 의 5.76x speedup 가정 시 2.5-flash 였다면 ~60s — 즉 본 baseline 이미 Phase B 효과 반영. 추가 모델 swap 여지 없음.
- → **Round 1 의 정적 추정 (RAG 4-12s) 가 cited 측정값 (avg 10.6s) 과 lower 일치. 외부 5명 dogfooding 진입 시 cold start + concurrent + RTT 추가로 평균 15s 초과 risk 가 sprint-28 까지 부재한 정량 baseline 으로는 unknown**.

→ baseline 갭 = **production p95 측정값 0 건**. 본 Round 2 신규 발견 BUG-S27e-PERF-r2-1.

---

## 1. Round 1 priority 검증 (PERF-1~15) — 외부 5명 즉시 발현 확률 재평가

| Round 1 ID | 시각 (Round 1) | 본 Round 2 재분류 | 외부 5명 진입 즉시 발현 확률 | 비고 |
|---|---|---|---:|---|
| PERF-1 | P1 R2 boto3 reuse | **P1 유지** | ~40% | 회의 1건 / memory voice 1건 / cron 1건 = 3 호출/일 × 5명 = 15회/일. cold path 누적 latency 가 dogfooding feedback 의 "느리다" 인지 임계 (Sprint 27d agent-5 P3 가능성 ↑) |
| PERF-2 | P1 DB index 누락 | **P1 유지, scale dependent** | ~10% (수십 row), ~80% (100+ row) | 외부 5명 × 1주 = ~50-200 회의/노트 row 도달 → seq scan 임계 진입. 즉 외부 5명 *진입* 보단 *2-3주 차* 위험 |
| PERF-3 | P1 upload OOM | **P1 유지, edge case** | ~5% (정상 외부 5명), ~95% (50MB+ 다중 동시 업로드) | 외부 5명 dogfooding 평균 회의 30분 ~ 30MB. 5명 동시 1GB 업로드 시나리오 X. **하지만 한 명의 잘못된 동작 (4hr meeting 5번 동시) 시 instance OOM = 다중 사용자 동시 다운** |
| PERF-4 | P1 Gemini timeout 부재 | **P0 격상 권장** | ~20% (Gemini incident 시 100%) | Gemini Vendor incident 1주에 1회 평균 (Anthropic/OpenAI/Google 모두). incident 시 회의 BG task hang → Cloud Run worker 점유 → 5명 dogfooding 중 다중 동시 다운 가능. Cloud Run timeout 600s default 인지 확인 필요 |
| PERF-5 | P1 SSE disconnect | **P1 유지** | ~30% | 외부 5명 dogfooding 시 RAG 질문 후 탭 전환 / 다른 작업 흔함. 비용 누수 + cache 오염 모두 |
| PERF-6 | P2 cache 무차별 wipe | **P2 유지** | ~10% | team workspace 외부 5명 시나리오 가정 시 발현. personal-only 면 영향 미미 |
| PERF-7 | P2 cache cleanup cron | **P3 강등 권장** | ~0% (외부 5명 1주), ~5% (1개월) | 7d TTL × 외부 5명 × 100 recall = 3500 row 누적. halfvec storage ~12MB. 명백 운영 위험 없음 |
| PERF-8 | P2 created_at 인덱스 | **P3 강등 권장** | ~0% (Sprint 28+) | time_range filter 사용 빈도 측정 0 (FE 가 default "all"). 외부 5명 dogfooding 시 발현 사실상 0 |
| PERF-9 | P2 inbox N+1 | **P3 강등 권장** | ~0% | N=1-3 평균. inbox classify request 빈도 자체가 낮음 |
| PERF-10 | P2 FE 폰트 외부 CDN | **P1 격상 권장 (외부 사용자 첫 인상)** | ~95% | 외부 5명 첫 dashboard 진입 시 LCP 직접 영향. Sprint 27d agent-5 의 "느리다 인지" 직접 원인 |
| PERF-11 | P2 tiptap 정적 import | **P2 유지** | ~50% | notes/[id] 진입 빈도가 외부 5명 시나리오에 따라 다름 |
| PERF-12 | P3 React Query staleTime | **P3 유지** | ~30% | refetchOnWindowFocus default true → 탭 전환마다 BE fanout. 외부 5명 동시 시 BE 부하 ↑ |
| PERF-13 | P3 chunk_text boundary | **P3 유지** | 0% | RAG quality 영향, latency X |
| PERF-14 | P3 onboarding hook commit | **P3 유지** | ~5% | cache-hit fast path 의 hidden cost. step ≥ target 일 때 commit no-op 인지 검증 (`OnboardingRepository.increment` 의 rowcount 분기 미확인) |
| PERF-15 | P3 client lazy import | **P1 격상 권장 (RAG / meetings path 도 동일)** | ~50% | Round 1 은 memory 도메인만 다뤘으나 본 Round 2 검증 결과 RAG/meetings dependencies 도 동일 패턴. PERF-r2-2 참조 |

**Round 1 priority 재분류 summary**:
- P0 격상 권장: PERF-4 (Gemini timeout 부재) — 외부 incident 시 다중 다운
- P1 격상 권장: PERF-10 (font CDN — LCP 직접), PERF-15 (client recreate — RAG path)
- P3 강등 권장: PERF-7/8/9 (외부 5명 dogfooding 1주 시나리오 영향 미미)

---

## 2. Round 2 신규 발견 매트릭스 (Round 1 blind spot)

| ID | 영역 | 심각도 | 차단 | file:line | 발견 요약 | 권장 fix |
|---|---|:-:|:-:|---|---|---|
| **BUG-S27e-PERF-r2-1** | baseline / 측정 | P1 | NO | (sprint infra) | **production p95 측정값 0 건**. Sprint 27d 의 localhost 5 sample (avg 10.6s) 만 cited → SCOPE GO 한계 ≤ 15s 헤드룸 ~5% 외 unknown. dogfooding 진입 후에도 정량 baseline 없으면 BL-S27e-C cluster fix 효과 측정 불가 | Sentry Performance 또는 simple BE middleware (RAG endpoint timing log) — dogfooding 진입 *전* 5 sample local + staging 1회씩 |
| **BUG-S27e-PERF-r2-2** | DI / 리소스 | **P1** | NO | `backend/src/rag/dependencies.py:18-26` + `backend/src/meetings/dependencies.py:41-50` | RAG/meetings dependencies 가 매 request 마다 `AIProcessingService()` + `EmbeddingService(repo)` 신규 생성 → 매번 `genai.Client(api_key=...)` + `AsyncOpenAI(api_key=...)` 인스턴스 생성. Round 1 PERF-15 는 memory 도메인만 다룸 — RAG 가 더 critical path | `lifespan` 에 `app.state.genai_client` + `app.state.openai_client` 싱글톤 + `Depends(get_genai_client)` 주입. AIProcessingService 는 client 만 받도록 refactor |
| **BUG-S27e-PERF-r2-3** | DB / 알고리즘 | P1 | NO | `backend/src/rag/service.py:112-131` | RAG hybrid search 의 `vector_search` + `text_search` 가 **sequential await** (총 2× Neon RTT 50-100ms = 100-200ms 추가). single AsyncSession 의 connection 1개 제약으로 직접 `asyncio.gather` 불가 — 별도 session 분리 필요 | 두 search 를 별도 session 으로 분리 후 `asyncio.gather` 병렬. 또는 single SQL UNION + RRF 후 분리 (DB 측 RRF). Round 1 미언급 |
| **BUG-S27e-PERF-r2-4** | sync blocking / auth | **P1** | NO | `backend/src/auth/dependencies.py:174-249` | `get_current_user` 가 **매 인증 request 마다 3 SQL statement (users + workspaces + workspace_members INSERT) + 1 onboarding hook + 1 commit** 실행 — JWT cache hit 시점에도. 1 page load = 5+ API fan-out = 5+ × 4 statement = 20+ SQL/load. Neon RTT 25-50ms × 20 = 500ms-1s hidden latency | `users.onboarding_step >= 1` 인 사용자는 lazy seed SKIP (fast path SELECT 1만). 또는 lazy seed 결과 캐시 (in-memory TTL 5min × clerk_id) |
| **BUG-S27e-PERF-r2-5** | connection pool / Cloud Run | P1 | NO | `backend/src/common/database.py:20-27` | `pool_size=5 + max_overflow=10` = max 15 connections/instance. Cloud Run min_instances=1, max-concurrency=80 default → 1 instance 가 80 동시 request 처리 시 15 connection 으로 부족 → asyncpg queue 대기 → tail latency p99 폭주. 외부 5명 동시 = ~10-20 동시 active request 정도라 acceptable, but burst 시 (20+ 동시) immediate 발현 | `pool_size=10 + max_overflow=20` (총 30) 또는 max-concurrency=10-20 으로 낮춤 + min_instances=2. Cloud Run config 확인 필요 (사용자 정책 SKIP) |
| **BUG-S27e-PERF-r2-6** | lifespan / cold start | P2 | NO | `backend/src/core/lifespan.py:13-18` | lifespan 이 `init_engine` 만. genai/openai client 초기화 X (현재 lazy) → 첫 RAG 요청에서 client init + Gemini API key validation + DNS resolution 동시 → cold start +500ms~1s. Cloud Run cold start 총 ~3-5s 가능 (Round 1 의 ≤ 3s 목표 위반 risk) | lifespan 에 genai/openai client + `await ready_check` (Gemini API ping) — 첫 request fast path. min_instances=1 정합 |
| **BUG-S27e-PERF-r2-7** | session cancel / leak | P2 | NO | `backend/src/memory/service.py:509-620` + `backend/src/notes/service.py:381+497` | BG task (`_bg_distill_and_embed` 외) 가 `async with self._session_factory() as session` 으로 session 보유 — Cloud Run instance autoscale-down 또는 request cancel 시 BG task asyncio.cancel propagate 안 됨 (FastAPI BackgroundTasks 는 graceful shutdown 보장 0). session leak + Gemini 비용 누수 가능 | BG task 시작 시 `lifespan.bg_tasks_set.add(task)` 후 shutdown 시 `asyncio.gather(*tasks, return_exceptions=True)` cancel 대기. 또는 SQS/Celery 같은 외부 queue (대규모 변경) |
| **BUG-S27e-PERF-r2-8** | DI / 리소스 | P2 | NO | `backend/src/rag/dependencies.py:18-26` | `EmbeddingService(repo)` 가 매 request 마다 신규 — 단순 service 는 stateless 라 OK 이지만 `EmbeddingService.__init__` 가 `AsyncOpenAI(api_key=...)` 생성 → PERF-r2-2 와 동일 leak. RAG path 1 request = AI client 2 회 신규 (AIProcessingService + EmbeddingService) | PERF-r2-2 와 동시 해소 (singleton OpenAI/genai client + DI 주입) |
| **BUG-S27e-PERF-r2-9** | memory / cron 부재 | P2 | NO | (전 도메인) | Cloud Scheduler 외부 cron 외 in-app 정기 작업 0 — `memory_query_embedding_cache` cleanup (Round 1 PERF-7), `r2 audio cleanup` (Sprint 15 R-CRON, `memory/service.py:210`), expired SemanticCache (`expires_at` 컬럼 존재하나 cleanup 없음) | APScheduler 또는 Cloud Run Jobs (별도 service) 권장. 단일 source-of-truth `cron/` 디렉토리 신설 |
| **BUG-S27e-PERF-r2-10** | DB / 알고리즘 | P2 | NO | `backend/src/embeddings/repository.py:460-472` | `delete_caches(workspace_id, project_id=None)` 가 ws 전체 wipe (Round 1 PERF-6 와 동일 file). 추가 발견: SemanticCache 에 `expires_at` 컬럼 (TTL 7일) 존재 하나 `find_similar_cache` 에서 만료 filter 적용 여부 미확인. 만료 row 가 cache hit 으로 잘못 반환되면 stale answer 노출 | `find_similar_cache` 의 SQL 에 `expires_at > now()` 명시 (Round 1 미언급) |
| **BUG-S27e-PERF-r2-11** | meta / monitoring | P2 | NO | `backend/src/main.py` (Sentry SKIP) | Sentry traces_sample_rate 0.1 (`core/config.py:53`) 이지만 sentry_dsn 미설정 시 `main.py:57` 의 if 조건으로 init skip → APM trace 0 건. 외부 5명 dogfooding 시 RAG p95 / Gemini error rate / DB query slow log 모두 unknown | Sentry Production DSN 발급 (BUG-S27e-SEC-11 carry) + sentry_sdk.start_transaction 명시 wrap (RAG ask / meeting process) |
| **BUG-S27e-PERF-r2-12** | DB / 알고리즘 | P3 | NO | `backend/src/embeddings/repository.py:455-458` | `save_cache` 가 `session.add` + `session.flush` — `pg_insert(...).on_conflict_do_nothing` 미사용. 중복 question (cache key 정합) 의 두 번째 INSERT 가 UniqueViolation 가능 (cache PK 가 ID 라 unique 안 함이면 OK). PK 검토 필요 | (검토 후) ON CONFLICT 명시 |

---

## 3. 개별 발견사항

### BUG-S27e-PERF-r2-1 — production p95 측정값 0 건 (baseline 갭)

- **영역**: baseline / 측정
- **심각도**: P1
- **차단**: NO (Sprint 27d 의 5 sample 만으로 GO 결정한 정합)
- **현재 측정값**: localhost dev avg 10.6s × 5 sample (agent-3-cto.md:28). production 0 sample. **dogfooding 진입 후 BL-S27e-C cluster fix 효과 측정 baseline 없음**
- **목표**: 외부 5명 dogfooding 진입 직전 staging Cloud Run 환경 RAG p95 10 sample 측정 → baseline 등재
- **영향도 추정**: BL-S27e-C cluster fix 의 ROI 정량 평가 불가능 → priority 결정 정확도 ↓

#### 증상

Sprint 27d agent-3-cto.md:20-28 의 5 sample = max 14.2s. p95 추정값으로 부적합 (n ≥ 20 권장). 본 Round 2 의 `cited reference` 신뢰도 ~60%.

#### Root cause

dogfooding 진입 직전 staging 측정 단계 미정의 (SCOPE.md/sprint-27d 산출물 모두). Sprint 28 진입 후에야 production 측정.

#### 최적화 방안

```bash
# staging Cloud Run 환경에서 10 sample 권고
for i in {1..10}; do
  start=$(date +%s%3N)
  curl -N -X POST "https://kairos-api-imrsiyibaa-du.a.run.app/api/v1/workspaces/{wid}/rag/ask" \
    -H "Authorization: Bearer ${CLERK_JWT}" -H "Content-Type: application/json" \
    -d '{"question":"오늘 회의 무슨 결정?","time_range":"all"}' \
    -o /tmp/rag_$i.txt
  end=$(date +%s%3N)
  echo "sample $i: $((end - start))ms"
done | sort -k3 -n
```

또는 **간단한 BE middleware** (3 줄):

```python
# backend/src/main.py — RAG endpoint timing log
@app.middleware("http")
async def rag_timing_log(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    if "/rag/ask" in str(request.url):
        ms = (time.perf_counter() - start) * 1000
        logger.info("rag_ask_ms=%.0f", ms)
    return response
```

#### 검증 방법

- staging Cloud Run 환경 10 sample → p50 / p95 / max 산출
- Cloud Logging 의 `rag_ask_ms` log 집계

#### 비용

- 개발: 0.25d (timing log) + 0.25d (10 sample 측정)
- 외부 5명 dogfooding 진입 직전 1회 + 진입 2주 후 1회 (총 2회)

---

### BUG-S27e-PERF-r2-2 — RAG/meetings AI client 매 request 마다 신규 인스턴스

- **영역**: DI / 리소스
- **심각도**: **P1**
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적 추정: `genai.Client(api_key=...)` ~10-30ms init (httpx client + TLS context) + `AsyncOpenAI(api_key=...)` 동급. RAG 1 request = 두 client 신규 = ~40-60ms hidden cost
- **목표**: lifespan singleton — RAG p95 -40-60ms
- **영향도 추정**: per-RAG-call -40-60ms (Round 1 PERF-15 의 memory 도메인보다 큰 영향 — RAG 빈도 ↑)

#### 증상

```python
# backend/src/rag/dependencies.py:18-26
async def get_rag_service(
    session: AsyncSession = Depends(get_async_session),
) -> RagService:
    repo = EmbeddingRepository(session)
    return RagService(
        embedding_repo=repo,
        embedding_service=EmbeddingService(repo),  # ⚠️ 매 request AsyncOpenAI() 신규
        ai_service=AIProcessingService(),          # ⚠️ 매 request genai.Client() 신규
    )
```

```python
# backend/src/embeddings/service.py:19-23
class EmbeddingService:
    def __init__(self, repo: EmbeddingRepository) -> None:
        self.repo = repo
        settings = get_settings()
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())  # ⚠️ per-instance
```

```python
# backend/src/services/ai_processing.py:62-66
class AIProcessingService:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value()  # ⚠️ per-instance
        )
```

같은 패턴: `backend/src/meetings/dependencies.py:49` (`AIProcessingService()`), `backend/src/services/transcription.py:74` (`TranscriptionService.__init__` 의 AsyncOpenAI).

#### Root cause

Round 1 PERF-15 가 memory/service.py 의 module-level `_call_distill` 만 발견. 본 Round 2 grep 결과 RAG/meetings/transcription 도 동일 — DI 단계에서 매번 신규.

#### 최적화 방안

```python
# backend/src/core/lifespan.py — singleton client
from google import genai
from openai import AsyncOpenAI

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    init_engine(settings.database_url)
    app.state.genai_client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
    app.state.openai_client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    yield
    await app.state.openai_client.close()
    await dispose_engine()
```

```python
# backend/src/services/ai_processing.py
class AIProcessingService:
    def __init__(self, client: genai.Client) -> None:
        self.client = client
```

```python
# backend/src/rag/dependencies.py
def get_genai_client(request: Request) -> genai.Client:
    return request.app.state.genai_client

def get_openai_client(request: Request) -> AsyncOpenAI:
    return request.app.state.openai_client

async def get_rag_service(
    session: AsyncSession = Depends(get_async_session),
    genai_c: genai.Client = Depends(get_genai_client),
    openai_c: AsyncOpenAI = Depends(get_openai_client),
) -> RagService:
    repo = EmbeddingRepository(session)
    return RagService(
        embedding_repo=repo,
        embedding_service=EmbeddingService(repo, openai_c),
        ai_service=AIProcessingService(genai_c),
    )
```

#### 검증 방법

- BE timing log middleware 로 RAG p95 전후 비교 (PERF-r2-1 dependency)
- 단위: `tests/services/test_ai_singleton.py` — RAG 호출 100회 시 `genai.Client(...)` mock 이 1회만 호출

#### 비용

- 개발: 0.5d (RAG + meetings + transcription + memory 4 도메인 patch)
- 운영 비용 변화: per-RAG-call -40-60ms, Cloud Run CPU time -5% 추정

---

### BUG-S27e-PERF-r2-3 — RAG hybrid search sequential await (asyncio.gather 미사용)

- **영역**: DB / 알고리즘
- **심각도**: P1
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적 추정: Neon RTT 50-100ms × 2 (vector + text) sequential = 100-200ms. RAG 10s 의 ~1-2%
- **목표**: 두 search 병렬 → 50-100ms 절감
- **영향도 추정**: per-RAG-call -50-100ms (PERF-r2-2 와 함께 시 합 -100-160ms = ~1% RAG total)

#### 증상

```python
# backend/src/rag/service.py:112-131
vector_results = await self.embedding_repo.vector_search(...)  # await
text_results = await self.embedding_repo.text_search(...)      # await — sequential
```

#### Root cause

Single `AsyncSession` 의 underlying asyncpg connection 은 1 query/time. 직접 `asyncio.gather` 적용 시 `InterfaceError: cannot perform operation on busy connection` 발생 가능.

#### 최적화 방안

옵션 A — 별도 session 두 개:

```python
# backend/src/rag/dependencies.py
async def get_rag_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> RagService:
    # session 은 service 내부에서 두 개 생성
    ...

# backend/src/rag/service.py
async def _hybrid_search_parallel(self, ...):
    async with self._session_factory() as s1, self._session_factory() as s2:
        repo1 = EmbeddingRepository(s1)
        repo2 = EmbeddingRepository(s2)
        v, t = await asyncio.gather(
            repo1.vector_search(...),
            repo2.text_search(...),
        )
    return v, t
```

옵션 B — DB 측 UNION + RRF (1 query 로 통합, 더 단순):

```sql
WITH vec AS (SELECT id, score, ROW_NUMBER() OVER (ORDER BY embedding <=> :qvec) AS rk
             FROM embedding_chunks WHERE ...),
     txt AS (SELECT id, score, ROW_NUMBER() OVER (ORDER BY similarity(...) DESC) AS rk
             FROM embedding_chunks WHERE ...)
SELECT id, SUM(1.0/(60+rk)) AS rrf_score FROM (
  SELECT id, rk FROM vec
  UNION ALL
  SELECT id, rk FROM txt
) GROUP BY id ORDER BY rrf_score DESC LIMIT 10;
```

옵션 B 더 권장 (Neon RTT 1회 + DB 처리 효율).

#### 비용

- 옵션 A: 0.5d
- 옵션 B: 1d (SQL 재설계 + RRF 검증 + e2e regression)

---

### BUG-S27e-PERF-r2-4 — get_current_user 매 request 마다 3 INSERT (lazy seed 항상 실행)

- **영역**: sync blocking / auth
- **심각도**: **P1**
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적 추정: 3 INSERT + onboarding hook + commit = 4-5 Neon RTT = 100-250ms hidden auth cost. JWT cache hit 도 동일
- **목표**: fast path (이미 seeded 사용자) — SELECT 1 + commit skip 으로 RTT 50ms
- **영향도 추정**: per-page-load -300-500ms (5 API fanout × 4 RTT 절감)

#### 증상

```python
# backend/src/auth/dependencies.py:174-249
# 매 인증 request 마다:
# 1. SELECT users WHERE clerk_id
# 2. INSERT users ON CONFLICT (신규/기존 모두 실행)
# 3. SELECT users WHERE clerk_id (re-fetch)
# 4. INSERT workspaces ON CONFLICT (신규/기존 모두 실행)
# 5. INSERT workspace_members WHERE NOT EXISTS (신규/기존 모두 실행)
# 6. onboarding.increment_step (UPDATE 또는 no-op)
# 7. await session.commit()
```

JWT cache hit (line 108-110) 이 verify_clerk_token 만 우회. `get_current_user` 의 lazy seed 는 캐시 X.

#### Root cause

lazy seed 가 user-already-seeded 분기 X. ON CONFLICT 가 효율적이지만 여전히 statement parse + plan + send + ack = ~RTT 비용.

#### 최적화 방안

```python
# backend/src/auth/dependencies.py
async def get_current_user(
    claims: dict = Depends(verify_clerk_token),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    repo = UserRepository(session)
    user = await repo.find_by_clerk_id(claims["sub"])

    # Fast path: 이미 seed 된 사용자 (onboarding_step >= 1) — INSERT skip
    if user is not None and user.onboarding_step >= 1:
        return user

    # Slow path: 신규 또는 미seed 사용자만 lazy seed
    # (기존 lazy seed 로직)
    ...
```

또는 in-memory cache (TTL 5min × clerk_id):

```python
_user_seed_cache: dict[str, float] = {}  # clerk_id → expires_at

async def get_current_user(...):
    cached_until = _user_seed_cache.get(claims["sub"])
    if cached_until and time.time() < cached_until:
        # fast path
        user = await repo.find_by_clerk_id(claims["sub"])
        if user: return user
    # slow path + 캐시 등록
```

#### 검증 방법

- BE timing log: `/api/v1/workspaces` 등 인증 endpoint 의 p50 비교 (전후)
- 단위: `tests/auth/test_lazy_seed_fast_path.py` — 이미 seed 된 사용자 호출 시 INSERT 0 회 (mock session.execute counter)

#### 비용

- 개발: 0.5d (조건 분기) 또는 0.75d (in-memory cache)
- 운영 비용 변화: per-page-load -300-500ms (5+ API fanout)

---

### BUG-S27e-PERF-r2-5 — asyncpg pool 크기 vs Cloud Run max-concurrency 정합 미검증

- **영역**: connection pool / Cloud Run
- **심각도**: P1
- **차단**: NO (현재 외부 5명 dogfooding 규모는 acceptable)
- **현재 측정값**: 환경 미실행. 정적: `pool_size=5 + max_overflow=10` = max 15 connection/instance. Cloud Run max-concurrency default = 80
- **목표**: instance 당 15 connection × Neon plan limit (Neon free = 100, paid varies) 정합 + Cloud Run min/max instances 조정
- **영향도 추정**: 20+ 동시 request burst 시 pool exhausted → asyncpg `QueuePool limit of size 5 overflow 10 reached` 또는 hang

#### 증상

```python
# backend/src/common/database.py:20-27
_engine = create_async_engine(
    database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=240,
)
```

```yaml
# Cloud Run service 설정 미확인 (사용자 정책 SKIP). default = max-concurrency 80, min-instances 0/1
```

5 + 10 = 15 connection/instance. 외부 5명 × 5 동시 active request (page fanout) = 25 request — 1 instance 면 10 request queue 대기.

#### Root cause

asyncpg pool 설정과 Cloud Run instance 설정 정합 검증 안 됨. Sprint 16 의 BL-034 (pool_pre_ping 추가) 이후 변경 0.

#### 최적화 방안

옵션 A — pool ↑:

```python
_engine = create_async_engine(
    database_url,
    pool_size=10,
    max_overflow=20,  # max 30/instance
    pool_pre_ping=True,
    pool_recycle=240,
)
```

옵션 B — Cloud Run max-concurrency ↓ + min-instances ↑ (사용자 정책 SKIP):

```yaml
container:
  concurrency: 20  # default 80 → 20
scaling:
  min_instances: 1  # cold start 회피
  max_instances: 5
```

Neon plan limit 검토 필수 — Neon Free = 100 connection, Hobby/Scale = 다름.

#### 검증 방법

- 부하 테스트 `locust -u 50 -r 5` → asyncpg queue 대기 시간 로그
- Cloud Logging metric: `cloudsql.googleapis.com/database/postgresql/num_backends`

#### 비용

- 개발: 0.25d (pool 조정) — 사용자 정책 (Cloud Run config) SKIP 이라 정확한 fix 어려움
- 운영: Neon 비용 변화 없음 (connection 수 만 증가)

---

### BUG-S27e-PERF-r2-6 — lifespan 이 AI client 초기화 X (cold start 첫 RAG 추가 지연)

- **영역**: lifespan / cold start
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적 추정: 첫 RAG request 의 cold start 추가 +500ms-1s (genai/openai client init + DNS resolution + TLS handshake)
- **목표**: lifespan 에 client 초기화 → 첫 request fast path
- **영향도 추정**: cold start RAG -500-1000ms (Round 1 의 ≤ 3s 목표 위반 risk 회피)

#### 증상

```python
# backend/src/core/lifespan.py:13-18
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    init_engine(settings.database_url)
    yield
    await dispose_engine()
```

genai/openai client 초기화 X. 첫 request 가 dependencies.py 호출 → `genai.Client(...)` + `AsyncOpenAI(...)` 처음 생성.

#### Root cause

PERF-r2-2 (singleton DI) fix 시 자연 해소. 두 발견은 동일 fix.

#### 최적화 방안

PERF-r2-2 의 lifespan singleton 패턴 정합. 추가 옵션 — Gemini API key validation ping (선택):

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    init_engine(settings.database_url)
    app.state.genai_client = genai.Client(api_key=...)
    app.state.openai_client = AsyncOpenAI(api_key=...)
    # 선택: API key validation ping (실패 시 startup abort)
    try:
        await app.state.openai_client.models.list()
    except Exception as e:
        logger.warning("OpenAI key validation 실패: %s", e)
    yield
    ...
```

#### 비용

- 개발: PERF-r2-2 와 동일 fix (0.5d 합)

---

### BUG-S27e-PERF-r2-7 — BG task session leak / graceful shutdown 보장 X

- **영역**: session cancel / leak
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적: Cloud Run autoscale-down 시 BG task 진행 중 = session 강제 close + Gemini 미완료 응답 = 비용 누수
- **목표**: BG task lifecycle 명시 관리 — graceful shutdown 시 모든 BG task 완료 대기 (또는 timeout cancel)
- **영향도 추정**: Cloud Run autoscale-down 빈도 × 평균 BG task 진행률 (불명, 측정 필요)

#### 증상

`backend/src/memory/service.py:509+580` `_bg_distill_and_embed` / `_bg_transcribe_distill_embed` 등 BG handler 들이 `async with self._session_factory() as session` 사용 — Cloud Run instance shutdown 시 외부에서 cancel propagate 안 됨.

FastAPI `BackgroundTasks` 는 response 송출 직후 실행 — Cloud Run idle timeout (300s default) 안에 끝나면 OK 이지만 회의 4hr 처리 (chunked_transcription) 등은 timeout 초과 가능 → cancel.

#### Root cause

FastAPI BackgroundTasks 가 production-grade BG task 아님 (공식 권고 — Celery/RQ/SQS 사용).

#### 최적화 방안

옵션 A (단기) — lifespan 에 active BG task set 관리:

```python
# backend/src/core/lifespan.py
_bg_tasks: set[asyncio.Task] = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine(settings.database_url)
    app.state.bg_tasks = _bg_tasks
    yield
    # graceful shutdown — 30s 안에 완료된 BG task 만 대기
    if _bg_tasks:
        await asyncio.wait(_bg_tasks, timeout=30)
        for t in _bg_tasks:
            if not t.done():
                t.cancel()
    await dispose_engine()
```

옵션 B (장기) — Cloud Run Jobs 또는 외부 queue (Sprint 28+ 권고).

#### 비용

- 옵션 A: 1d
- 옵션 B: 3-5d (별도 sprint)

---

### BUG-S27e-PERF-r2-8 — EmbeddingService 매 request 신규 (OpenAI client 폭주)

- **영역**: DI / 리소스
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적 추정: PERF-r2-2 와 동일 cost
- **목표**: PERF-r2-2 와 함께 해소

#### 증상

PERF-r2-2 와 동일 file:line (`backend/src/rag/dependencies.py:24`). 본 발견은 PERF-r2-2 의 sub-finding — 명시적으로 분리한 이유는 EmbeddingService 가 RAG 외 meetings/notes/inbox/memory 모두에서 사용 → 영향 범위 ↑.

#### 최적화 방안

PERF-r2-2 와 동일 lifespan singleton.

#### 비용

PERF-r2-2 에 포함.

---

### BUG-S27e-PERF-r2-9 — in-app cron / scheduled task 인프라 부재

- **영역**: memory / cron 부재
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적: Cloud Scheduler 외부 1건 (R2 audio cleanup) 만, in-app 정기 작업 0
- **목표**: 통합 cron 인프라 (APScheduler 또는 Cloud Run Jobs)
- **영향도 추정**: 만료 row 누적으로 DB storage 무한 증가 (PERF-7 + SemanticCache + audit_events 등)

#### 증상

- `MemoryQueryEmbeddingCache` 7d TTL — cleanup 0 (PERF-7)
- `SemanticCache.expires_at` 7d TTL — cleanup 0 (Round 2 발견)
- `MemoryItem.r2_audio_key` 30d TTL — Cloud Scheduler cron (1건만 working)
- `item_promotion_audit` — TTL 정책 미정 (영구 보관 또는 6m archive 필요)
- `memory_events` — Sprint 15 R7 metrics. TTL 정책 미정

#### 최적화 방안

옵션 A — APScheduler in-app (단순):

```python
# backend/src/common/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("cron", hour=3)
async def cleanup_query_cache():
    # ...
```

옵션 B — Cloud Run Jobs 별도 service (분리도 ↑, Cloud Run 이미 사용 중이라 자연):

```yaml
# kairos-cron-job (별도 Cloud Run service)
schedule: "0 3 * * *"
command: ["uv", "run", "python", "-m", "src.scripts.cleanup_caches"]
```

#### 비용

- 옵션 A: 1d
- 옵션 B: 1.5d (Cloud Run Jobs 설정 + secret 분리)

---

### BUG-S27e-PERF-r2-10 — SemanticCache `expires_at` filter 적용 여부 미검증 (stale cache hit risk)

- **영역**: DB / 알고리즘
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적: `find_similar_cache` SQL 미확인. 만료 row 가 cache hit 시 stale answer 반환 risk
- **목표**: `expires_at > now()` filter 명시
- **영향도 추정**: 만료 답변 노출 (UX 영향) — frequency 측정 필요

#### 증상

`SemanticCache` 의 `expires_at = datetime.utcnow() + timedelta(days=7)` (rag/service.py:217) — 7d TTL 컬럼 존재. 하지만 `find_similar_cache` SQL 의 cutoff filter 적용 여부 미확인 (검증 필요).

#### Root cause

cache lookup 시 `expires_at` filter 의 명시 코드 read 못 함 (본 Round 2 시간 제약).

#### 최적화 방안

```python
# backend/src/embeddings/repository.py find_similar_cache
async def find_similar_cache(self, q_emb, workspace_id, ...):
    query = text("""
        SELECT ... FROM semantic_caches
        WHERE workspace_id = :wid
          AND expires_at > now()  -- ⚠️ 명시 추가
          AND ...
        ORDER BY question_embedding <=> :qvec
        LIMIT 1
    """)
```

#### 비용

- 개발: 0.25d (검증 + 명시 추가)
- 별도 PERF-r2-9 cron 으로 만료 row DELETE

---

### BUG-S27e-PERF-r2-11 — Sentry trace 0 건 (production observability 0)

- **영역**: meta / monitoring
- **심각도**: P2
- **차단**: NO
- **현재 측정값**: Sentry traces_sample_rate=0.1 설정만, sentry_dsn 미설정 → init skip → trace 0
- **목표**: Sentry Production DSN + transaction wrap (RAG / meeting)
- **영향도 추정**: 외부 5명 dogfooding 시 RAG p95 / Gemini error rate / DB query slow log 모두 unknown

#### 증상

```python
# backend/src/main.py:57
if settings.sentry_dsn:
    sentry_sdk.init(...)
```

sentry_dsn 미설정 시 모든 telemetry 0.

#### Root cause

BUG-S27e-SEC-11 (Sprint 27e Round 1 carry) 와 동일 — Sentry SKIP 정책 영향.

#### 최적화 방안

BUG-S27e-SEC-11 fix 와 동시 — Sentry Production DSN 발급 + 본 PERF-r2-1 의 timing log 와 통합.

```python
# RAG ask transaction
with sentry_sdk.start_transaction(op="rag.ask", name="rag_ask"):
    async for event in pipeline.ask(...):
        yield event
```

#### 비용

- 개발: 0.5d (DSN 발급 사용자 결정 + transaction wrap)

---

### BUG-S27e-PERF-r2-12 — SemanticCache save 의 ON CONFLICT 명시 검토

- **영역**: DB / 알고리즘
- **심각도**: P3
- **차단**: NO
- **현재 측정값**: 환경 미실행. 정적: `session.add` + `flush` — PK 정합 확인 필요
- **목표**: PK 정의 검토 후 ON CONFLICT 필요 여부 결정

#### 증상

```python
# backend/src/embeddings/repository.py:455-458
async def save_cache(self, cache: SemanticCache) -> None:
    self.session.add(cache)
    await self.session.flush()
```

SemanticCache PK = id (auto UUID) 면 unique 충돌 없음. (workspace_id, question_hash) 같은 composite unique 있으면 ON CONFLICT 필요.

#### Root cause

(검증 미완료)

#### 최적화 방안

`embeddings/models.py:64+` SemanticCache 모델 read → PK 확인 후 결정.

#### 비용

- 개발: 0.1d (검토만)

---

## 4. Round 1 BL 우선순위 재평가 — 외부 5명 진입 *전* fix 필요 매트릭스

| Round 1 ID | 본 Round 2 재분류 | 외부 5명 진입 *전* fix 필요? | 사유 |
|---|---|:-:|---|
| PERF-1 R2 boto3 | P1 유지 | NO (carry) | 외부 5명 dogfooding 1주 시나리오 영향 ~40% — 즉시 차단 아님 |
| PERF-2 DB index | P1 scale dependent | NO (carry) | 외부 5명 × 1주 = 수십 row, 영향 미미 |
| PERF-3 upload OOM | P1 edge | NO (carry) | 정상 외부 5명 시나리오에서 OOM 도달 안 함. 단 가드레일 (Cloud Run 메모리 alarm) 필수 |
| PERF-4 Gemini timeout | **P0 격상 권장** | **YES** | Gemini incident 1주에 1회 → 외부 5명 동시 다운 risk. **외부 진입 *전* fix 권장** |
| PERF-5 SSE disconnect | P1 유지 | NO (carry) | 비용 누수만, 다운 risk 없음 |
| PERF-6 cache wipe | P2 유지 | NO (carry) | Team workspace 사용 시 발현 — 외부 5명 dogfooding 시나리오 가정 시 |
| PERF-7 cache cron | P3 강등 | NO (carry) | 1개월 시나리오 영향 |
| PERF-8 chunks index | P3 강등 | NO (carry) | time_range filter 사용 빈도 0 가정 |
| PERF-9 inbox N+1 | P3 강등 | NO (carry) | 영향 미미 |
| PERF-10 font CDN | **P1 격상 권장** | **YES** | 외부 5명 첫 진입 LCP 직접 영향. dogfooding feedback 의 "느리다" 직접 원인 |
| PERF-11 tiptap | P2 유지 | NO (carry) | notes 사용 빈도 dependent |
| PERF-12 staleTime | P3 유지 | NO (carry) | BE 부하 ↑ 정도, 즉시 다운 아님 |
| PERF-13 chunk boundary | P3 유지 | NO (carry) | RAG quality 만 |
| PERF-14 onboarding hook | P3 유지 | NO (carry) | hidden 25-50ms |
| PERF-15 client lazy | **P1 격상 권장** | NO (carry) | RAG path 의 hidden 40-60ms — 외부 진입 *후* 우선 |

**외부 5명 진입 *전* fix 권장 (Round 1 + Round 2 통합)**:
- **PERF-4** (Gemini timeout/circuit breaker) — vendor incident 가용성 risk
- **PERF-10** (font self-host) — 첫 인상 LCP 직접

**Sprint 28 BL-S27e-C cluster (carry, 외부 5명 dogfooding 진행 중 처리)**:
- PERF-1/2/3/5 + PERF-r2-2/3/4 — 외부 진입 *후* 우선순위

---

## 5. Summary

- **Round 1 priority 재분류**:
  - P0 격상 권장: PERF-4 (1건)
  - P1 격상 권장: PERF-10, PERF-15 (2건)
  - P3 강등 권장: PERF-7, PERF-8, PERF-9 (3건)

- **Round 2 신규 발견 (PERF-r2)**:
  - 신규 P0: **0건** (차단 0)
  - 신규 P1: **5건** — PERF-r2-1 (baseline), PERF-r2-2 (RAG client recreate), PERF-r2-3 (hybrid search sequential), PERF-r2-4 (auth lazy seed always), PERF-r2-5 (pool 정합)
  - 신규 P2: **6건** — PERF-r2-6, 7, 8, 9, 10, 11
  - 신규 P3: **1건** — PERF-r2-12

- **차단 (Blocking)**: **0건** (실측 SKIP 상태에서 명백 violation 추정 불가)

- **외부 5명 진입 *전* fix 권장 (Round 1+Round 2 통합)**: 2건
  - PERF-4 (Gemini timeout/circuit breaker)
  - PERF-10 (font self-host)

- **baseline 측정 권장 (PERF-r2-1)**: 외부 5명 진입 직전 staging 10 sample 측정 → BL-S27e-C cluster fix ROI 정량 결정

### 가장 high-impact 3건 (Round 2 신규)

1. **PERF-r2-4 (P1)** — `get_current_user` 매 request 마다 3 INSERT lazy seed. fast path (`onboarding_step >= 1`) 분기 추가만으로 page load -300-500ms. 외부 5명 dogfooding 즉시 발현 가능한 hidden auth cost.

2. **PERF-r2-2 (P1)** — RAG/meetings AI client 매 request 신규 인스턴스. Round 1 PERF-15 가 memory 만 다뤘으나 RAG path 가 더 critical. lifespan singleton 으로 RAG p95 -40-60ms.

3. **PERF-r2-1 (P1)** — production p95 측정값 0. dogfooding 진입 *전* staging 10 sample 측정 + BE timing log middleware (3 줄) 추가 권고. 측정 없이는 BL-S27e-C fix priority 결정 불가.

### 검증 환경 제약 (Round 1 동일)

본 Round 2 도 정적 분석 only. 실측 baseline 확립 = PERF-r2-1 fix 가 dependency. Cloud Run config (max-concurrency, min/max instances) 미확인 = PERF-r2-5 정확도 ~70%. PERF-r2-10 의 SemanticCache `expires_at` filter 검증은 추가 코드 read 필요 (본 audit 미완료).
