<!-- Sprint 24 Wave 2 Phase 6 T-BE-PERF Spike Report -->

# Sprint 24 Wave 2 T-BE-PERF Spike Report

> **목적**: BUG-MOBILE-005 (Multi-Agent QA Mobile 측정 — localhost BE API workspaces/members/meetings/inbox 첫 진입 **3015-3865ms**) profiling 진단 + Top 1 bottleneck fix.
>
> **측정 환경**: localhost FastAPI + Testcontainers PostgreSQL (Neon production cold start 미reflect)
> **측정 script**: `backend/scripts/sprint24_wave2_perf_spike.py`
> **raw 결과**: `be-perf-spike.json`
> **측정일**: 2026-05-20

---

## 1. 측정 결과 요약

### 1.1 JWT verify timing
| 구간 | 값 |
|---|---|
| jwt_verify_cold_ms (PyJWKClient 초기화 포함) | **0.31ms** |
| jwt_verify_no_cache_p50_ms | 0.09ms |
| jwt_verify_with_cache_p50_ms | **0.0ms** (cache hit dict lookup) |
| **JWT cache 절감** | dashboard 4 API × JWT verify cost 0 화 |

### 1.2 Dashboard 4 API 직렬 timing (localhost)
| API | First-call ms | Warm p50 ms |
|---|---|---|
| workspaces | 12.63 | 3.03 |
| members | 8.20 | 5.42 |
| meetings | 11.51 | 6.46 |
| inbox | 11.02 | 7.07 |
| **직렬 4 API 합산** | **24.6ms** | **25.3ms** |

### 1.3 Top 10 slow queries
모두 **boot phase** (`CREATE EXTENSION vector` / `CREATE TABLE projects/meeting_summaries/users` 등 schema 초기화). 1회성. 실 사용자 phase 아님.

### 1.4 cProfile cumulative top 30
- `simulate_dashboard_first_visit` 가 2.6s cumulative (importlib + testcontainers postgres boot 가 대부분 = 1.6s `main.py:1(<module>)` + 1.4s `testcontainers/__enter__`).
- 실제 hot path (FastAPI request handler) 는 ms 단위.

---

## 2. 진단

### 2.1 localhost ≠ production 갭

localhost (Testcontainers) 측정 = **직렬 4 API 25ms** (sub-second). Multi-Agent QA Mobile 보고 = **3015-3865ms**. **갭 ~150x**.

→ **production 3-4s 의 origin 은 BE 로직이 아닌 cold start + 외부 인프라**:
1. **Neon serverless cold start** (HTTP wake-up + connection pool 미warm)
2. **Cloud Run cold start** (container 시작 + Python import)
3. **Vercel → Cloud Run 네트워크 RTT**
4. **Clerk JWT JWKS 첫 fetch** (production endpoint 외부 호출)

### 2.2 BE 로직 측 영향 가능 항목

JWT verify 가 (cold) 0.31ms × 4 API = ~1.2ms. 절대량 영향 적음. **단 production 환경에서 Clerk JWKS 외부 fetch 가 cold 시 100-500ms 가 될 수 있음** → JWT cache TTL 60s 가 200-2000ms 절감 가능.

---

## 3. Top 1 Fix (적용 완료)

### `_JWT_CLAIMS_CACHE` in-process TTL cache 도입 (`backend/src/auth/dependencies.py`)

- **Scope**: verify_clerk_token 의 token hash → (claims, expires_at) dict cache
- **TTL**: 60s (token 자체 exp 보다 짧게)
- **maxsize**: 1000 (LRU 단순 dict + 만료 청소)
- **Hit path**: dict lookup 만 → PyJWKClient + jwt.decode 우회
- **Miss path**: 원본 흐름 + 결과 저장
- **보강**: `PyJWKClient(cache_keys=True)` (kid lookup overhead 제거, JWKS set cache 와 별개)

### 효과 측정
- localhost: cache hit 시 0.09ms → 0.0ms (절감 100% but 절대량 작음)
- **production 추정**: Clerk JWKS 외부 fetch (cold ~200-500ms 추정) × 4 API → 0ms × 4 = **400-2000ms 절감 추정**

### Regression 가드
- 신규 5 pytest: `backend/tests/auth/test_jwt_cache.py` (hit / miss / TTL 만료 / maxsize 회전 / hash 분리)
- 기존 401 pytest 회귀 0

---

## 4. Carry-over (별도 sprint)

### BL-NEW-BE-PERF-COLD-START
- **상태**: Sprint 24 Wave 2 carry, Sprint 25+ 진입 조건 = production Sentry trace 수집
- **scope**: Cloud Run cold start 단축 (min-instances=1 vs cost trade) + Neon connection pool pre-warm + Vercel→Cloud Run 네트워크 진단
- **측정 도구**: Sentry distributed trace + Cloud Run startup time + Neon DB log
- **예상**: 1500-2500ms 단축 가능 (cold start 자체가 main bottleneck)

### BL-NEW-BE-PERF-PARALLEL-API
- **상태**: Sprint 25+ 검토
- **scope**: dashboard 4 API 가 직렬 호출 (FE Promise.all 안 함) 패턴 검토 → 병렬화 시 25ms → 12ms 추정 (localhost), production 추정 800-1200ms 절감
- **fix 위치**: `frontend/src/app/(app)/dashboard/page.tsx` + `useWorkspaces` + `useMembers` + `useMeetings` + `useInbox` hook 의존 매트릭스 검토 (workspaceId 가 다른 hook 의존인지 확인)

---

## 5. 결론

- **localhost spike 측정**: BE 로직 자체는 sub-second (25ms). production 3-4s 의 main bottleneck 은 **cold start + 외부 인프라**.
- **본 sprint Top 1 fix**: JWT cache (적용 완료) — production 환경에서 의미 있는 절감 추정. localhost 측정 절대량은 작음.
- **carry-over**: cold start 진단 + parallel API 호출 (Sprint 25+ Sentry trace 수집 후 진행).

본 Spike 의 정답 = **localhost 측정 한계 인식 + production cold start 별도 spike 필요**.
