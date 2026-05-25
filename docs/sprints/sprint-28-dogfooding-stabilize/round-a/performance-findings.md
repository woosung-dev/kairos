# Sprint 28 Round A — Performance 정적 audit

> 검사 일시: 2026-05-25 KST
> baseline: `sprint-28/dogfooding-stabilize` 분기 (main HEAD `3e41893` — Sprint 27e PR #109 + Round 2 PR #110 + QA dynamic verify post-merge fix 3e41893 머지된 상태)
> 환경: FE/BE down 상태에서 정적 분석 only. Round B 가 dynamic verify (Lighthouse / Playwright network timing / RAG p95 / Cloud Run cold start) 진행.
> 검사자 시각: Sprint 27 carry verify (이미 fix / 회귀) + Round 1/2 가 catch 못 한 신규 영역.

---

## 0. 측정 baseline

### 직접 측정 불가 metric (Round B 위임)

| metric | Sprint 27 cited | 목표 | Round B 측정 |
|---|---|---|---|
| dashboard LCP/FCP/TTI | 환경 미실행 | LCP ≤ 2.5s | Lighthouse 또는 Playwright timing |
| 첫 진입 fanout | QA dynamic 7.5s → fix 후 1.4-2.2s (3e41893) | ≤ 2s | network timing 5 endpoint × ms |
| RAG p95 | localhost dev 5 sample avg 10.6s, p95 14.2s | ≤ 15s (SCOPE) / ≤ 5s (BL-S27e-1) | staging Cloud Run 10 sample p95 |
| 회의 5분 audio | 환경 미실행 | ≤ 60s | sample 1건 e2e timing |
| Cloud Run cold start | 환경 미실행 | ≤ 3s | 재시작 후 첫 요청 |
| 1 페이지 BE 쿼리 수 | 환경 미실행 | ≤ 10 | FastAPI middleware log |

### 정적 분석 추정값 (Sprint 28 baseline = post-fix)

| metric | Sprint 27 추정 | Sprint 28 (post-fix) 추정 | 차이 |
|---|---|---|---|
| dashboard 첫 진입 fanout (실측 QA-1 fix 후) | 4-12s | 1.5-3s (실측 1.4-2.2s confirmed) | -70% 회복, 잔여 hidden = 5 list endpoints × `find_by_workspace + count` 2 RTT sequential = ~500ms 미해소 |
| RAG cache hit path | 200-600ms | 200-600ms | 동일 — 미해소 |
| RAG no-cache path | 4-12s | 4-12s | 동일 — 미해소 |
| 회의 5분 e2e | 30-60s | 30-60s | PERF-4 (Gemini timeout) 잔여로 worst-case 5min+ 가능 |
| JWT verify cost | sub-ms (cache hit) / 50-150ms (cache miss) | 동일 (leeway=10 추가) | BUG-QA-2 회복 |

---

## 1. Sprint 27 carry verify

> Sprint 27 Round 1/2 가 carry 한 항목과 QA dynamic verify (PR #111, fix 3e41893) 처리 결과 verify.

| ID | Sprint 27 분류 | Sprint 28 검증 (file:line) | 결과 |
|---|---|---|---|
| **BUG-QA-1** dashboard 7.5s | dogfooding-blocker | `auth/dependencies.py:181-186` — fast path `user.onboarding_step >= 1` 분기 명시 적용 | ✅ **RESOLVED** (실측 7.5s → 1.4-2.2s) |
| **BUG-QA-2** JWT 1분 expiry | dogfooding-blocker | `auth/dependencies.py:127` — `decode_kwargs["leeway"] = 10` 명시 적용 | ✅ **RESOLVED** |
| **BUG-QA-3** 추천 질문 prefill only | P3 UX | (FE) commit 3e41893 본문 명시 — verify 미진행 (Round B FE 확인 권고) | ✅ 추정 RESOLVED (commit 본문) |
| **PERF-4 (P0 격상)** Gemini timeout/circuit | 외부 진입 *전* 권고 | `services/ai_processing.py:81,127,151` — raw `generate_content` / `generate_content_stream` 그대로. `asyncio.wait_for` / tenacity / circuit breaker 0건. `memory/service.py:678,725,745` 동일. `services/transcription.py:118` Whisper 도 timeout 0 | ❌ **carry — 외부 진입 *전* fix 필수 (P0)** |
| **PERF-10 (P1 격상)** next/font local | 외부 진입 *전* 권고 | `frontend/src/app/layout.tsx:23-45` — 3 외부 font CDN stylesheet 그대로 (`fonts.googleapis.com` / `api.fontshare.com` / `cdn.jsdelivr.net`). `next/font` 미사용 | ❌ **carry — LCP 직접** |
| **PERF-1** R2 boto3 singleton | BL-S27e-C | `common/r2.py:14,27,55,73,87` — 4 메서드 모두 `async with self._session.client(...)` 매 호출 패턴 그대로 | ❌ carry |
| **PERF-2** DB workspace_id 인덱스 3건 | BL-S27e-C | `meetings/models.py:17` / `actions/models.py:32` / `inbox/models.py:22` — workspace_id FK `index=True` 미명시. `alembic/versions/c3d4e5f6a7b8_bl036_perf_indexes.py` 는 workspace_members + projects 만 cover. meetings/actions/inbox 의 ListBy 패턴 인덱스 0 | ❌ carry |
| **PERF-3** streaming upload | BL-S27e-C | `upload/router.py:91` — `file_bytes = await file.read()` 그대로. `r2.upload_file_bytes(filename, content_type, data: bytes)` 호출 — streaming 미적용 | ❌ carry |
| **PERF-5** SSE disconnect 감지 | BL-S27e-C | `rag/router.py:30-42` — `event_generator()` 내부 `request.is_disconnected()` 0건. `Request` 인자 미주입 | ❌ carry |
| **PERF-r2-2** AI client lifespan singleton | BL-S27e-C | `core/lifespan.py:13-18` — `init_engine` 만, genai/openai client 0. `rag/dependencies.py:18-26` + `embeddings/service.py:23` + `services/ai_processing.py:64` + `services/transcription.py:76` 모두 매 init `genai.Client(...)` / `AsyncOpenAI(...)` | ❌ carry |
| **PERF-r2-3** RAG hybrid 병렬 | BL-S27e-C | `rag/service.py:112-131` — `vector_search` await → `text_search` await 그대로 sequential | ❌ carry |
| **PERF-r2-4** lazy seed hidden cost (BUG-QA-1 root cause) | dogfooding-blocker | `auth/dependencies.py:181-186` fast path 적용 — **부분 RESOLVED** (1차 진입 lazy seed 그대로 4-5 statement, 2차 이후 fast path SELECT 1만). 실측 7.5s → 1.4-2.2s | 부분 ✅ |
| **PERF-6** SemanticCache wipe broad | BL-S27e-D | `embeddings/repository.py:460-472` — `delete_caches(workspace_id, project_id)` 여전히 ws 또는 project 전체 wipe. source_chunk_ids 기반 selective wipe 미적용 | ❌ carry |
| **PERF-7** cache cleanup cron | BL-S27e-D | `memory/service.py:210` `cleanup_expired_r2_audio` 만 존재. `cleanup_expired_query_cache` / SemanticCache expired wipe 0. APScheduler / Cloud Run Jobs 미신설 | ❌ carry |
| **PERF-8** embedding_chunks.created_at 인덱스 | BL-S27e-D | `embeddings/models.py:47` — index 미명시. RAG time_range filter 의존 (현재 사용 빈도 추정 0) | ❌ carry |
| **PERF-9** inbox classify N+1 | BL-S27e-D | `inbox/service.py:100` `for project_id in project_ids:` 그대로 | ❌ carry |
| **PERF-11** tiptap dynamic import | BL-S27e-D | `note-editor.tsx` / `note-detail.tsx` — `import dynamic` 미사용 (정적 import 그대로 추정 — 본 audit 미 read 만 read 결과 0건 `next/dynamic`) | ❌ carry |
| **PERF-12** React Query refetchOnWindowFocus | BL-S27e-D | `frontend/src/lib/query-client.tsx:12` — `staleTime: 60_000` + `retry: 1` 만 명시. `refetchOnWindowFocus` 미지정 → default true. 도메인별 staleTime 도 `memory/hooks.ts:103` 30s + `onboarding/hooks.ts:32,38` 만 명시 | ❌ carry |
| **PERF-r2-5** asyncpg pool size 정합 | BL-S27e-D | `common/database.py:20-27` — `pool_size=5 + max_overflow=10` 그대로. Cloud Run config 미확인 | ❌ carry |
| **PERF-r2-6** lifespan cold start | BL-S27e-D | PERF-r2-2 의존 fix — 동시 해소 | ❌ carry |
| **PERF-r2-7** BG task session leak | BL-S27e-D | `core/lifespan.py` BG task set 관리 미신설. `meetings/router.py:42,67` + `memory/service.py:129` 등 `background_tasks.add_task` 그대로 — graceful shutdown 보장 0 | ❌ carry |
| **PERF-r2-8** EmbeddingService 매 request 신규 | BL-S27e-D | PERF-r2-2 sub-finding — `embeddings/service.py:23` AsyncOpenAI 매 init 그대로 | ❌ carry |
| **PERF-r2-9** in-app cron 인프라 | BL-S27e-D | APScheduler / Cloud Run Jobs 미신설. R2 audio cleanup 만 Cloud Scheduler 외부 cron | ❌ carry |
| **PERF-r2-10** SemanticCache `expires_at` filter | BL-S27e-D | `embeddings/repository.py:332` — `expires_at > now()` 명시 적용됨 (Round 2 추정 false, Sprint 27e Round 1 통합 시점부터 이미 정합) | ✅ **이미 정합 — Round 2 misclassification, errata** |
| **PERF-r2-11** Sentry trace 0 | BL-S27e-D | `main.py:57` `if settings.sentry_dsn:` 조건 그대로. SEC-11 / ADR-022 SKIP 정책 유지 | ❌ carry (정책 SKIP) |
| **PERF-13** chunk_text boundary | P3 | `embeddings/service.py:28-42` — char count cut 그대로 | ❌ carry |
| **PERF-14** onboarding hook commit | P3 | `onboarding/repository.py:17,22-24` `increment()` 반환 None. `onboarding/service.py:22-24` `increment_step()` rowcount 분기 0. 매 RAG/회의/note hook 호출 시 `await session.commit()` 발생 | ❌ carry (P3) |
| **PERF-15** memory genai/openai client lazy | P3 → P1 격상 (Round 2) | `memory/service.py:678,725,745` — `genai.Client(...)` / `AsyncOpenAI(...)` 매 호출 lazy 그대로 | ❌ carry (PERF-r2-2 와 통합 fix 권고) |

**Sprint 27 carry 정량**:
- ✅ RESOLVED: 4건 (BUG-QA-1, BUG-QA-2, BUG-QA-3, PERF-r2-10 errata)
- 부분 ✅: 1건 (PERF-r2-4 — lazy seed fast path 만 적용, 1차 진입 lazy seed 자체는 그대로)
- ❌ carry: 21건 (PERF-1/2/3/4/5/6/7/8/9/10/11/12/13/14/15 + PERF-r2-2/3/5/6/7/8/9/11)

## 2. 신규 발견 매트릭스 (Round 1/2 blind spot)

| ID | 영역 | 심각도 | 차단 (dogfooding-blocker?) | file:line | 발견 | 권장 fix |
|---|---|:-:|:-:|---|---|---|
| **BUG-S28-PERF-1** | DB / list endpoints | **P1** | NO (외부 5명 진입 *전* 권고) | `meetings/service.py:95-98` / `notes/service.py:123-126` / `actions/service.py:128-136` / `projects/service.py:105-114` / `inbox/service.py:66-69` | dashboard 5 list endpoints **모두 `find_by_workspace` + `count_by_workspace` 2 sequential await** 패턴. single AsyncSession 위 sequential = 2 RTT. dashboard 첫 진입 fanout = **10 DB RTT × Neon 25-50ms = 250-500ms hidden** (PERF-r2-4 lazy seed fast path fix 후 잔여 hidden). 5 endpoint × 2 query 가 각각 client 측에선 5 동시 fanout 이지만 BE 내부에선 sequential — concurrent 5 instance × 2 queue = pool 도달 위험 | (a) `find_by_workspace` 가 `(items, total)` tuple 반환하도록 single SQL `SELECT *, COUNT(*) OVER() FROM ...` window function 변경. 또는 (b) cursor-based pagination (`hasNext` 만 필요 시 `LIMIT N+1` 으로 N+1 detection — total 제거) — BL-S27e-1 RAG p95 와 별개. dashboard 의 inbox/actions/meetings/notes/projects 5 endpoint 모두 적용 시 dashboard fanout -250-500ms |
| **BUG-S28-PERF-2** | sync blocking / Whisper | **P1** | NO | `services/transcription.py:118-123` + `services/chunked_transcription.py:113-116,229,234` | Whisper API `transcriptions.create` **timeout 0 + retry 0**. PERF-4 가 Gemini 만 다룬 후속 발견. `download_audio:140` timeout=300 있으나 transcribe 본문 자체는 무한. 회의 4hr chunked 모드는 `asyncio.gather` 로 parallel batch 처리 (concurrency=batch size) — chunk 1개 hang 시 batch 전체 stuck, Cloud Run worker 점유 | PERF-4 fix 패턴 정합: `asyncio.wait_for(self.client.audio.transcriptions.create(...), timeout=60)` + tenacity retry 3. 짧은 chunk 60s cap, full 1hr chunk 는 별도 처리 |
| **BUG-S28-PERF-3** | sync blocking / 메모리 | P1 | NO (정상 5명 acceptable, 동시 4hr+ 시 OOM) | `meetings/pipeline_service.py:203` + `services/chunked_transcription.py:113` | BG task 가 R2 download 전체 메모리 적재 — `audio_bytes = await self.transcription_service.download_audio(audio_url)` 그대로 보유 후 `transcribe_with_chunking(audio_bytes, ...)` 호출. 4hr 회의 = ~500MB-1GB. chunked_transcription 안에서 다시 `Path(audio_path).read_bytes()` (line 113) → bytes 2회 사본. PERF-3 (upload OOM) 와 다른 path — proxy upload 와 별개로 background pipeline 도 동일 risk | streaming download — `httpx.AsyncClient.stream("GET", url)` + chunk 단위 tempfile 작성 → `transcribe_with_chunking` 이 file path 받도록 시그니처 변경 |
| **BUG-S28-PERF-4** | DB / connection pool | P2 | NO (Cloud Run autoscale 1+ instance 분산 시 완화) | `common/database.py:20-27` + `meetings/router.py:42,67` + `memory/service.py:129` 외 다수 | `pool_size=5 + max_overflow=10` × Cloud Run 1 instance burst 시 BG task (audio pipeline + memory distill + RAG) 가 main request 와 동일 pool 공유. `audio pipeline 1건 = 3-5 connection (find_by_id × N stages + ws lookup + segment INSERT 등) × 평균 30-60s 점유` → 동시 audio 2건 = pool 10 점유 → main request pool 부족 → tail latency 폭주. Sprint 27 PERF-r2-5 가 burst 시나리오 다뤘으나 BG task 누적은 다른 dimension | (a) BG pool 분리 — `init_bg_engine(database_url, pool_size=10, max_overflow=5)` 별도 + `get_bg_session_factory()` (b) main pool size ↑ 권고 (PERF-r2-5 와 통합) |
| **BUG-S28-PERF-5** | algorithm / RBAC | P2 | NO | `auth/rbac.py` 의 RoleChecker (require_viewer/member/owner) 가 매 보호 endpoint 호출 시 `workspace_members` SELECT | dashboard fanout 5 endpoint × `require_viewer/member` × BL-036 인덱스 hit = 5 RTT (인덱스 있음 ~ 5ms each). Cache 안 됨 → fast path 가능 vs 항상 fresh. fast path 안 하면 5 endpoint × 2 query (`workspace_members` + `users` `ON CONFLICT`) = 10 + N total RTT | `WorkspaceMember(user_id, workspace_id, role)` 도 JWT cache 와 동일 in-process TTL cache 30s. Sprint 24 Wave 2 T-BE-PERF top 1 fix (JWT) 의 동일 패턴 — 적용 권고 |
| **BUG-S28-PERF-6** | FE / 번들 | P2 | NO | `frontend/src/lib/query-client.tsx:7-17` + `frontend/src/features/*/hooks.ts` | `QueryProvider` 가 `useState(() => new QueryClient(...))` — 매 render 마다 new 안 하지만 default options 가 너무 기본. `staleTime: 60_000` 만 명시 → mutation 후 invalidate 안 한 query 가 1분 stale 후 자동 refetch (window focus 시 default true 와 결합 시 BE 부하 ↑). 도메인별 명시 (`memory/hooks.ts:103` 30s, `onboarding/hooks.ts:32,38` 30s + focus=false) 2건만 | (a) global default `refetchOnWindowFocus: false` + `gcTime: 5*60_000` + 도메인별 staleTime 명시 (5min for meetings list / 30s for inbox / etc.) (b) PERF-12 와 동시 fix |
| **BUG-S28-PERF-7** | FE / UX | P3 | NO | `frontend/src/features/home/hooks.ts:44-49` (`useActivityFeed`) | dashboard 가 5 React Query (inbox/actions/meetings/notes/projects) parallel fetch + 3 useMemo aggregate. `isReady` 가 4개 isLoading 검사 (projects 빠짐) — projects 가 마지막 isLoading 일 때 isReady=true 인데 actionsDue 가 projectsQuery.data 의존 → race 가능 (실 영향 측정 불가, 환경 미실행) | `isReady` 에 `projectsQuery.isLoading` 추가 (1 line) |
| **BUG-S28-PERF-8** | algorithm / RAG | P3 | NO | `rag/service.py:112-131` `limit=50` + `_reciprocal_rank_fusion top_n=10` | hybrid search vector+text 각각 50 결과 후 RRF 로 10 추출. parent enrich `_enrich_context` (line 261-278) 가 batch 1 query 처리는 OK. **but** RRF k=60 default 와 top_n=10 의 비율 = RRF 신뢰도 (60+10 = 70 candidate 이 합리 — 50+50 candidate 에서) OK. **PERF-r2-3 fix 후** vector+text 병렬 시 sequence 50+50 = 100 → 합산 = 더 적합. 현재는 sequence cost dominant | PERF-r2-3 fix 가 본 결함 자연 해소 |
| **BUG-S28-PERF-9** | DB / N+1 promote | P3 | NO | `meetings/service.py:516` (Round 1 PERF-6 본문 인용) + `notes/service.py:469` + `embeddings/repository.py:460` | promote BG 의 cache invalidate 가 ws 전체 wipe. **신규 발견**: promote BG 자체는 target_workspace_id 의 chunk 복제 + meeting copy 패턴 — target ws 의 embedding_chunks INSERT N건 시 chunk 별 vector_search index update 별도. HNSW maintenance cost. promote 1건 = ~10-100 chunk 복제 = HNSW insert RTT ~ ms-scale × N | bulk INSERT (single statement multi-row) + 단일 commit. 현재 별 chunk per session.add ? (확인 필요 — 본 audit 미 read) |
| **BUG-S28-PERF-10** | algorithm / chunk | P3 | NO | `embeddings/service.py:28-42` (PERF-13 carry) + chunk count limit | chunk_text 가 boundary char count + 최대 chunk 갯수 limit 없음 → 회의 4hr transcript = ~50k char = 100 chunks. embedding cost = 100 × OpenAI embedding RTT (batch 100 OK). but BL-001 (meetings pipeline status commit 단일화) 와 결합 시 100 chunk INSERT = 100 RTT (또는 batch). 단일 회의 e2e = chunk-bound | bulk save_chunks 또는 batch INSERT (1 commit per N) |
| **BUG-S28-PERF-11** | meta / observability | P3 | NO | `core/lifespan.py:13-18` + Sentry SKIP | Cloud Run cold start 측정 인프라 0 — `lifespan` 의 startup 시간 log 0. 첫 request log 의 latency 가 Cloud Run cold start 의 proxy | `main.py` startup log — `time.perf_counter` 로 `lifespan` enter/exit 시간 log. middleware 에 첫 N request 추가 marker `cold_start_first_request=true` (counter 기반) |
| **BUG-S28-PERF-12** | algorithm / DI 정합 | P3 | NO | `rag/dependencies.py:18-26` + `meetings/dependencies.py:41-50` + memory/notes/inbox dependencies | PERF-r2-2 의 sub-finding — 5 도메인 dependencies 모두 동일 패턴 (매 request `Service(repo, AsyncOpenAI(), genai.Client())`) — PERF-r2-2 fix 시 5 도메인 모두 patch 필요. fix scope 확인용 audit | (PERF-r2-2 fix 와 통합) |

---

## 3. 차단 결함 상세 (외부 5명 dogfooding 진입 *전* 권고)

### BUG-S28-PERF-1 — list endpoints `find_by_workspace + count_by_workspace` 2 RTT sequential (P1)

- **영역**: DB / list endpoints
- **심각도**: P1
- **차단**: NO (외부 진입 후 dogfooding-stabilize 즉시 처리 권고)
- **실측 baseline**: QA dynamic verify 의 7.5s → 1.4-2.2s fix 후 잔여 hidden 의 일부. 5 endpoint × 2 RTT = ~250-500ms

#### 증상

dashboard 첫 진입 5 endpoint fanout (`useActivityFeed`):
- `inbox/service.py:66-69` — `inbox_repo.find_by_workspace` await → `inbox_repo.count_by_workspace` await
- `actions/service.py:128-136` — `repo.find_by_workspace` await → `repo.count_by_workspace` await
- `meetings/service.py:95-98` — 동일
- `notes/service.py:123-126` — 동일
- `projects/service.py:105-114` — 동일

각 endpoint = 2 sequential DB RTT (single AsyncSession 위 2 query). FE 5 endpoint parallel fanout 이지만 BE 내부에선 endpoint 마다 2 RTT 순차.

#### Root cause

서비스 layer 가 pagination 응답에 `total` 필요 — `count_by_workspace` 따로 호출. single SQL window function `COUNT(*) OVER()` 또는 cursor pagination 미적용.

#### 권장 fix

옵션 A — window function (단일 query):

```python
# backend/src/meetings/repository.py
async def find_by_workspace_with_count(
    self, workspace_id, offset, limit, project_id=None,
) -> tuple[list[Meeting], int]:
    """단일 SQL 로 (items, total) — COUNT(*) OVER() window."""
    stmt = text("""
        SELECT m.*, COUNT(*) OVER() AS _total
        FROM meetings m
        WHERE m.workspace_id = :wid
          {project_join}
        ORDER BY m.created_at DESC
        OFFSET :offset LIMIT :limit
    """)
    rows = list(await self.session.execute(...))
    total = rows[0]._mapping["_total"] if rows else 0
    return [...], total
```

옵션 B — cursor pagination (`hasNext` 만 — total 제거):

- 5 endpoint 의 `total` 응답 필드를 client 측에서 사용 빈도 측정 (currently `useActivityFeed:hasContent` 의 fallback path).

#### 검증 방법

- 단위: `tests/meetings/test_list_pagination.py` 에 single query count 검증
- 통합: BE middleware query count log — dashboard 진입 시 5+5=10 → 5+0=5

#### 비용

- 개발: 1.5d (5 도메인 × 동일 패턴)
- 운영: dashboard fanout -250-500ms

---

### BUG-S28-PERF-2 — Whisper API timeout/retry 0 (P1)

- **영역**: sync blocking / Whisper
- **심각도**: P1
- **차단**: NO (Gemini 와 동일 패턴 — PERF-4 와 묶음 권고)
- **현재 추정**: Whisper API 정상 5-15s, hang 시 무한

#### 증상

```python
# backend/src/services/transcription.py:118-123
response = await self.client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file,
    response_format="verbose_json",
    timestamp_granularities=["segment"],
)  # timeout 0 + retry 0
```

`chunked_transcription.py:229,234` 의 `asyncio.gather` batch — chunk 1개 hang 시 batch 전체 stuck. 4hr 회의 = 4 chunk × 1hr = 한 chunk hang 시 batch 가 대기.

#### Root cause

OpenAI SDK default timeout = settings 기반 (httpx default `Timeout(timeout=600.0, connect=5.0)`). 600s 가 Cloud Run request timeout (300s default) 보다 김 — request 자체는 cut 되지만 BG task 가 hung resource 점유.

#### 권장 fix

PERF-4 와 동일 패턴:

```python
# backend/src/services/transcription.py
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

WHISPER_TIMEOUT_SEC = 90  # 5분 audio 기준 worst-case + buffer
WHISPER_CHUNK_TIMEOUT_SEC = 120  # 1hr chunk worst-case

class TranscriptionService:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, max=20))
    async def transcribe(self, audio_bytes, filename="audio.mp3"):
        ...
        response = await asyncio.wait_for(
            self.client.audio.transcriptions.create(...),
            timeout=WHISPER_TIMEOUT_SEC,
        )
        ...
```

PERF-4 의 circuit breaker 와 단일 인스턴스 공유 권고 (Gemini + Whisper 둘 다 외부 AI vendor — incident correlated 가능).

#### 검증 방법

- 단위: mock OpenAI 의 `asyncio.sleep(120)` 시 TimeoutError + retry 3
- 통합: 의도적 OpenAI key invalid → BG task 가 정확한 시간 안에 fail → `Meeting.status='failed'`

#### 비용

- 개발: 0.5d (PERF-4 와 묶음 1d)

---

### BUG-S28-PERF-3 — meetings BG pipeline audio 전체 메모리 적재 (P1 edge)

- **영역**: sync blocking / 메모리
- **심각도**: P1
- **차단**: NO (정상 외부 5명 acceptable, 동시 4hr 회의 + BG task 누적 시 OOM)
- **현재 추정**: 5min 회의 = 5-10MB OK. 1hr = ~50-100MB. 4hr = ~200-400MB × 2회 memory 사본

#### 증상

```python
# backend/src/meetings/pipeline_service.py:203
audio_bytes = await self.transcription_service.download_audio(audio_url)
# audio_bytes 가 BG task scope 안 전체 보유

# backend/src/services/transcription.py:137-142
async def download_audio(self, url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=300.0)
        resp.raise_for_status()
        return resp.content  # 전체 bytes 반환
```

```python
# backend/src/services/chunked_transcription.py:113
audio_bytes = Path(audio_path).read_bytes()  # tempfile → 또 1회 메모리 사본
```

#### Root cause

PERF-3 (upload proxy OOM) 는 router 측 fix. 본 발견은 BG task pipeline 측 — download → chunk transcribe 흐름의 메모리 적재. transcription_service.transcribe 가 `audio_bytes: bytes` 시그니처라 client 측에서 streaming 불가.

#### 권장 fix

```python
# transcription_service.download_audio → file path 반환
async def download_audio_to_file(self, url: str) -> Path:
    """streaming download → tempfile path."""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".audio", delete=False)
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url, timeout=300.0) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=65536):
                tmp.write(chunk)
    tmp.close()
    return Path(tmp.name)

# meetings/pipeline_service.py
audio_path = await self.transcription_service.download_audio_to_file(audio_url)
try:
    segments, duration = await self.transcription_service.transcribe_with_chunking(audio_path, filename)
finally:
    audio_path.unlink(missing_ok=True)
```

`transcribe_with_chunking(file_path: Path, filename: str)` 시그니처 변경 + chunked_transcription 도 path 전달 (이미 ffmpeg 가 path 기반이라 자연 정합).

#### 비용

- 개발: 1.5d (transcription/pipeline/chunked 3 file 시그니처 변경 + e2e regression)

---

## 4. 비차단 carry

### Sprint 27 carry (21건) — BL-S27e-C/D cluster

Sprint 27e final-integrated-report.md §"Sprint 28 진입 권고 항목" + sprint-28 plan 의 carry list 정합.

**BL-S27e-C** (P1, 외부 진입 *후* 우선): PERF-1 / PERF-2 / PERF-3 / PERF-5 + PERF-r2-2 / PERF-r2-3 / **PERF-r2-4 부분 잔여 (1차 진입 lazy seed)**

**BL-S27e-D** (P2, dogfooding-stabilize sprint 진입 후): PERF-6 / PERF-7 / PERF-8 / PERF-9 / PERF-11 / PERF-12 + PERF-r2-5 / r2-6 / r2-7 / r2-8 / r2-9 / r2-11

**P3 carry**: PERF-13 (chunk boundary) / PERF-14 (onboarding hook commit) / PERF-15 (genai memory client)

### Sprint 28 신규 (12건) — 등재 권고

| ID | 묶음 |
|---|---|
| BUG-S28-PERF-1 | BL-S27e-C (외부 진입 *전* 또는 직후 권고) |
| BUG-S28-PERF-2 | BL-S27e-C (PERF-4 와 동시 fix) |
| BUG-S28-PERF-3 | BL-S27e-C (PERF-3 streaming upload 와 동시) |
| BUG-S28-PERF-4 | BL-S27e-D (PERF-r2-5 와 통합) |
| BUG-S28-PERF-5 | BL-S27e-D (Sprint 28+) |
| BUG-S28-PERF-6 | BL-S27e-D (PERF-12 와 통합) |
| BUG-S28-PERF-7~12 | BL-S27e-D 또는 P3 |

### Errata (Round 2 misclassification)

- **PERF-r2-10** SemanticCache `expires_at` filter — 이미 적용된 상태 (`embeddings/repository.py:332`). Round 2 가 검증 미완료 명시 후 P2 분류 → 본 Round A 가 read 후 verify. **이미 정합**.

---

## 5. Summary

### 정량

- **차단 (Blocking) 결함**: **0건** (외부 5명 dogfooding 진입 자체에 차단 없음 — QA dynamic verify 의 BUG-QA-1/2 가 dogfooding-blocker 였으나 fix 3e41893 으로 RESOLVED)
- **외부 5명 진입 *전* fix 권고**: **2건** (Sprint 27 carry)
  - PERF-4 (P0 격상) — Gemini timeout/circuit breaker
  - PERF-10 (P1 격상) — next/font local self-host
- 신규 P1: **3건** — BUG-S28-PERF-1 (list endpoints 2 RTT) / BUG-S28-PERF-2 (Whisper timeout) / BUG-S28-PERF-3 (audio BG OOM)
- 신규 P2: **3건** — BUG-S28-PERF-4 (BG pool 분리) / BUG-S28-PERF-5 (member cache) / BUG-S28-PERF-6 (FE staleTime 정책)
- 신규 P3: **6건** — BUG-S28-PERF-7~12
- 신규 발견 총: **12건**
- Sprint 27 carry verify: 26 항목 중 ✅ 4 + 부분 ✅ 1 + ❌ 21 (대부분 BL-S27e-C/D 미진행)
- Errata: **1건** (PERF-r2-10 이미 정합)

### 가장 high-impact 3건 (Sprint 28 신규)

1. **BUG-S28-PERF-1 (P1)** — list endpoints 의 `find_by_workspace + count_by_workspace` 2 sequential await 패턴. 5 도메인 (meetings/actions/notes/inbox/projects) 모두 동일. dashboard 첫 진입 fanout 잔여 hidden ~ 250-500ms (QA-1 fix 후 1.4-2.2s 의 일부). 단일 SQL `COUNT(*) OVER()` 또는 cursor pagination 으로 -50% RTT.

2. **BUG-S28-PERF-2 (P1)** — Whisper API timeout/retry 0. PERF-4 (Gemini) 와 동일 패턴 잔재. 회의 4hr chunked transcription 의 chunk 1개 hang 시 batch stuck → Cloud Run worker 점유. PERF-4 fix 묶음 권고.

3. **BUG-S28-PERF-3 (P1 edge)** — meetings BG pipeline 의 audio 전체 메모리 적재. PERF-3 (upload proxy) 와 별개 path. 4hr 회의 동시 처리 시 instance OOM 위험. streaming download → tempfile 패턴 권고.

### 외부 5명 dogfooding 진입 verdict (Performance only)

| 분기 | 판정 |
|---|---|
| **외부 5명 dogfooding 진입 (current main `3e41893`)** | **GO** (차단 0건, BUG-QA-1/2 RESOLVED) |
| **외부 5명 진입 *전* fix 권고 적용 후** (PERF-4 + PERF-10) | **GO+** (vendor incident 가용성 + 첫 인상 LCP 보강) |
| **dogfooding-stabilize sprint 진입 후** | BL-S27e-C cluster 21 + 신규 12 = ~33건 처리 권고 (~5-7d) |

### 검증 환경 제약 (Round 1/2 동일)

본 Round A 도 정적 분석 only. 실측 baseline 확립 = Round B (MCP Playwright runtime smoke) 가 dependency:
- dashboard LCP/TTI (Lighthouse 또는 playwright timing) — BUG-S28-PERF-1 의 hidden cost 실측 확정
- RAG p95 staging 10 sample (PERF-r2-1) — BL-S27e-1 의 baseline
- 회의 5분 e2e timing — PERF-4 + BUG-S28-PERF-2 영향 측정
- BE middleware query count log — BUG-S28-PERF-1 의 5 endpoint × 2 query verify

### 차단/비차단 분류 기준 정합

본 Round A 는 final-integrated-report.md 의 GO 조건 + qa-dynamic-verify.md 의 dogfooding-blocker 정의 anchor:

- **차단 (Blocking) = dogfooding-blocker** — 외부 5명 *진입 자체* 막는 결함 → **0건** (BUG-QA-1/2 RESOLVED)
- **외부 진입 *전* 권고** — vendor incident 가용성 또는 첫 인상 직접 영향 → **2건** (PERF-4 P0 격상, PERF-10 P1 격상)
- **비차단 carry** — Sprint 28 dogfooding-stabilize sprint 안 처리 → **33건** (21 carry + 12 신규)
