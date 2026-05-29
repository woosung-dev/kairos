<!-- Sprint 28 Round B — MCP Playwright runtime smoke 통합 산출물. 본 main agent 가 시니어 엔지니어 + QA 마스터 페르소나로 sequential 측정 (MCP Playwright single browser, 병렬 X). -->

# Sprint 28 Round B — MCP Playwright runtime smoke (4 영역 통합)

> baseline `3e41893` · branch `sprint-28/dogfooding-stabilize` · 환경 FE:3000 + BE:8000 up · login d@e.com pattern (Clerk dev, personal workspace `e968c95f-…` seed 완료).

본 round 의 핵심 신규성 = **Sprint 27e Round 1/2 가 정적 분석만 진행했고 QA dynamic verify (PR #111) 가 일부 dynamic — 본 Round B 가 4 영역 모두 dynamic verify 처음 적용**.

MCP Playwright 는 single browser instance 라 sub-agent 병렬 X — 본 main agent 가 sequential 측정.

---

## 0. 4 영역 verify 결과 (시니어 QA 마스터 페르소나)

| 영역 | dynamic verify 항목 | 측정 결과 | severity 평가 |
|---|---|---|---|
| Security | 보안 헤더 4종 live · IDOR 3 probe · JWT lifetime + tampered token · SQLi probe | **모두 PASS** (회귀 0) | **안전** (전 영역 GO) |
| Performance | dashboard 5 endpoint fanout · RAG p95 5 sample · authn isolated endpoint timing | **부분 PASS, 신규 hidden 2s** | **심각 1건** (BUG-S28-PERF-RT-1) |
| Test-Coverage | CI flake rate · TEST-r2-1 활성 · e2e spec inventory | 모두 PASS | 안전 |
| Architecture | architecture test · runtime config (lifespan up 200) · 의존성 cycle (ImportError 0) | 모두 PASS | 안전 |

**전체 verdict**: 외부 5명 dogfooding 진입 **GO** (Security/Test/Architecture). 단 **BUG-S28-PERF-RT-1 (심각, authn 2s hidden cost)** 가 외부 사용자 첫 인상 LCP 직접 영향 — 본 sprint 안 root cause 분석 + 가능 시 fix 권고.

---

## 1. Security dynamic verify

### 1.1 보안 헤더 4종 live (FE 2 path + BE health)

```bash
curl -sI http://localhost:3000/sign-in | grep -iE "(x-frame|x-content|referrer|permissions)"
curl -sI http://localhost:8000/api/v1/health | grep -iE "(x-frame|x-content|referrer|permissions)"
curl -sI http://localhost:3000/ | grep -iE "(x-frame|x-content|referrer|permissions)"
```

결과 — 3 path 모두 4종 헤더 정합:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(self), geolocation=()`

→ **Sprint 27e Round 1 TEST-1 + Round 2 TEST-r2-1 fix 회귀 0건**. CSP 는 BL-S27e-3 의도적 carry.

### 1.2 live IDOR 9 probe (cross-tenant)

`mcp__playwright__browser_evaluate` 안 `fetch` × 9 probe.

| probe | URL | status | body preview |
|---|---|:-:|---|
| mine | `/api/v1/workspaces/{my}/projects` | **200** | `{"items":[],"total":0...` |
| fakeNull | `/api/v1/workspaces/00000000-...-0001/projects` | **403** | `{"detail":"워크스페이스 멤버가 아닙니다"}` |
| randomUUID | `/api/v1/workspaces/{random}/projects` | **403** | 동일 |
| mine-inbox | `/api/v1/workspaces/{my}/inbox` | **200** | actual data |
| fake-inbox | `/api/v1/workspaces/{fake}/inbox` | **403** | 동일 거부 |
| mine-members | `/api/v1/workspaces/{my}/members` | **200** | actual data |
| fake-members | `/api/v1/workspaces/{fake}/members` | **403** | 동일 거부 |
| invalid-uuid | `/api/v1/workspaces/not-a-uuid/projects` | **422** | Pydantic UUID validator 거부 |
| sqli | `/api/v1/workspaces/{my}' OR '1'='1/projects` | **422** | Pydantic UUID validator 거부 |

→ **I-9 멀티테넌시 격리 + Pydantic UUID validator 완전 동작**. cross-tenant 403 + SQLi 422. real IDOR 회귀 0건.

### 1.3 JWT tampered → 401

stale signature + exp manipulation 강제 tampered token 발급 후 BE 호출:

```javascript
const tamperPayload = { ...payload, exp: 1000000 };  // expired
const fakeToken = parts[0] + '.' + btoa(tamperPayload) + '.' + parts[2];  // original sig
fetch(url, { headers: { Authorization: `Bearer ${fakeToken}` } });
```

→ **401 "유효하지 않은 토큰입니다"** (`auth/dependencies.py:148` `InvalidTokenError` catch).

원인: payload 변조 시 sha256 signature mismatch → `jwt.InvalidSignatureError` (PyJWT) → catch 분기 → 401. 정확한 보안 동작.

### 1.4 JWT lifetime + Clerk auto re-issue (BUG-QA-2 dynamic verify)

JWT decode (no verify):

| claim | value |
|---|---|
| iss | `https://creative-boxer-79.clerk.accounts.dev` (dev) |
| sub | `user_3E7dOsm2xeXjo8En3HSokRBPSvM` |
| iat → exp | **60s lifetime** confirmed |
| aud | (claim 부재 — `verify_aud=False` fallback path) |

65s wait 후 측정:
- `Clerk.session.getToken()` (cached) → expiresIn 40s (Clerk SDK background refresh 후 fresh token)
- `Clerk.session.getToken({ skipCache: true })` → expiresIn 61s (방금 발급)
- stale token (expiresIn 40s) 으로 BE 호출 → **200** (leeway 10s 안 + token 자체 fresh)

→ **BUG-QA-2 fix verify PASS**: PR #111 의 `leeway=10` + Clerk SDK auto re-issue 둘 다 동작. 1분 머문 후 navigate 시 401 0건.

### 1.5 Security verdict — **안전 (전 영역 PASS, 회귀 0)**

| 항목 | 결과 |
|---|---|
| 보안 헤더 4종 | ✅ 3 path PASS |
| IDOR live (3 cross-tenant + 2 invalid + 4 protected) | ✅ 9/9 |
| JWT tampered → 401 | ✅ |
| JWT 1분 expiry + Clerk auto re-issue | ✅ |
| ADR-022 sync_user endpoint 비활성 | ✅ (`grep` 0 hit, 회귀 가드 `tests/auth/test_auth_sync_disabled.py` 존재) |

→ **외부 5명 dogfooding 진입 Security GO**. Round A Security 의 신규 7건 (BUG-S28-SEC-1~7) 은 모두 비차단 (production parity / forensic 영역). cutover hardening (SEC-r2-2/3/4, BL-S27e-G) 이미 RESOLVED.

---

## 2. Performance dynamic verify

### 2.1 dashboard 5 endpoint fanout (resource timing)

login 후 첫 `/dashboard` 진입 — Resource Timing API:

| Endpoint | duration | responseEnd | 비고 |
|---|---:|---:|---|
| `/api/v1/workspaces` | 3510ms | 4824ms | |
| `/api/v1/workspaces/{ws}/projects?status=active` | 3906ms | 5220ms | |
| `/api/v1/workspaces/{ws}/inbox` | 3912ms | 5226ms | |
| `/api/v1/workspaces/{ws}/members` | 4286ms | 5600ms | **critical path** |
| `/api/v1/users/me/onboarding` | 2273ms | 7115ms | sequential 후속 |

**critical path = 4286ms** (members). 외부 사용자 dashboard 첫 인상 ~4-5s.

비교:
- QA dynamic verify (PR #111 fix 전): 7512ms / 5479ms / 5434ms / 5367ms / 4370ms (총 7.5s)
- Sprint 28 Round B 측정 (PR #111 fix 후): 3510 / 3906 / 3912 / 4286 / 2273 (총 4.3s)
- **45% 개선**, 단 외부 사용자 여전히 ~4s 첫 인상.

### 2.2 isolated endpoint sequential timing (2 sample cold→warm)

```javascript
const measure = async (path, withAuth=true) => {
  const t0 = performance.now();
  await fetch(`http://localhost:8000${path}`, headers);
  return Math.round(performance.now() - t0);
};
```

| Endpoint | sample 1 | sample 2 | 평균 | 의미 |
|---|---:|---:|---:|---|
| `/api/v1/health` (no auth) | 10ms | 2ms | 6ms | **BE 자체 latency 0** |
| `/api/v1/users/me` (auth only) | 2028ms | 2048ms | **2038ms** | **authn 만 = 2s** |
| `/api/v1/workspaces` | 2393ms | 2457ms | 2425ms | auth + 1 query |
| `/api/v1/workspaces/{ws}/inbox` | 1777ms | 2372ms | 2074ms | auth + 1 query |
| `/api/v1/workspaces/{ws}/projects?status=active` | 2429ms | 2351ms | 2390ms | auth + 1 query |

→ **모든 authn endpoint 가 ~2s hidden cost**. health (no auth) 6ms 대비 authn 2038ms = **2032ms 가 authn flow 안에서 발생**.

### 2.3 BUG-S28-PERF-RT-1 (심각 — runtime 신규) — authn 2s hidden cost root cause 가설

**증상**: PR #111 fast path fix 적용 후에도 `/users/me` 단독 2s. JWT cache hit (`auth/dependencies.py:107-110`) 시 dict lookup sub-ms 이어야 하나 실측 2s.

**가설 분석** (가장 가능성 순):

1. **JWKS fetch 매 request 외부 호출 또는 cache miss** (확률 높음): `auth/dependencies.py:115` `_get_jwks_client()` singleton + `get_signing_key_from_jwt(token)` (line 116) — Clerk dev URL fetch RTT. PyJWKClient `cache_keys=True` 옵션 있으나 매 request 시점에 cache hit 한지 verify 안 됨. dev Clerk `creative-boxer-79.clerk.accounts.dev` 의 SSL handshake + JWKS response 가 1-1.5s 가능.
2. **`find_by_clerk_id` Neon RTT + query** (가능): `auth/dependencies.py:179` SELECT * FROM users WHERE clerk_id=$1. localhost→Neon (US/EU region) RTT 100-200ms + query plan. 단 2s 는 과함 → 추가 root cause 있음.
3. **JWT verify cost (RS256)** (낮음): `cache_key` (line 105) → `_jwt_cache_get` (line 108) → cache hit 시 dict lookup. cache hit 인지 verify 필요.
4. **connection pool contention** (낮음): `pool_size=5 + overflow=10`. 단 isolated sequential 측정도 2s = pool 문제 X.

**가설 검증 방법** (Step 4 fix 시점):
- backend `logging.basicConfig(level=DEBUG)` + auth flow trace → cache hit/miss 정량
- Neon Connection Logging — `find_by_clerk_id` actual query time
- `time` 측정 — `verify_clerk_token` 직전 + 직후 + `find_by_clerk_id` 직전 + 직후

**영향 (severity 평가)**:
- 외부 5명 dogfooding 진입: 매 클릭 2s 대기 = UX 임계 도달
- dashboard 첫 진입 4-5s = 외부 첫 인상 LCP
- → **심각 (P1 dogfooding 직접 영향)**

**fix 후보** (Step 4 진행 결정):
- (a) JWKS fetch 의 in-process cache 명시 (Lru 또는 in-memory KV)
- (b) `find_by_clerk_id` 인덱스 verify + EXPLAIN ANALYZE
- (c) connection pool 20+ 권고 (PERF-r2-5 와 통합)

### 2.4 RAG p95 5 sample (sequential SSE stream end-to-end)

```javascript
for (const q of questions) {
  fetch('/api/v1/.../rag/ask', { method: 'POST', body: { question: q } });
  // SSE stream — read all chunks
}
```

| Question | ms | chunks | bytes |
|---|---:|---:|---:|
| 오늘 회의 내용 요약해줘 | 13510 | 11 | 2241 |
| Sprint 27 audit 결과 | 11767 | 9 | 2108 |
| 내 inbox 에 미처리 항목 | 11147 | 5 | 1717 |
| 최근 노트 중요한 거 | 10571 | 8 | 2020 |
| Kairos 핵심 아키텍처 | 10626 | 6 | 1756 |

**p50 = 11.1s / p95 = 13.5s** — PRD KPI `< 15s` 안 (PASS).

비교: Sprint 27d 측정 localhost 5 sample 평균 10.6s — 정합.

→ 외부 dogfooding acceptable. BL-S27e-1 (RAG p95 <5s 목표) 는 P3 carry (Gemini API 응답 지배적).

### 2.5 Performance verdict

| 항목 | 결과 | severity |
|---|---|---|
| dashboard fanout critical path | 4286ms (PR #111 fix 후 -45%, 여전히 ~4s) | **심각** (외부 첫 인상) |
| RAG p95 | 13.5s (KPI <15s 안) | 안전 |
| 보안 헤더 latency | 6ms (no auth) | 안전 |
| **authn hidden cost** | **2s 모든 endpoint** | **심각 (BUG-S28-PERF-RT-1)** |

→ **외부 5명 dogfooding 진입 Performance NEEDS-FIX** — BUG-S28-PERF-RT-1 root cause 분석 + 가능 시 본 sprint 안 fix.

---

## 3. Test-Coverage dynamic verify

### 3.1 CI flake rate (main 가지 최근 15 run)

`gh run list --workflow=test.yml --branch=main --limit=15`:

15/15 success. **flake rate 0%**.

→ Sprint 27e Round 2 BL-S27e-4 재분류 (flake 가설 false) 정합 verified. main 가지 안정.

### 3.2 TEST-r2-1 (FE CI 게이트) 활성 확인

`.github/workflows/test.yml:73-106` — `security-headers.spec.ts` 단독 실행 step.
- `frontend-build` job 안 inline (E2E_ENABLED 무관 항상 실행)
- `--project=public-only` (public route, secrets 불요)
- chromium install + Next.js start + wait-on + spec run

→ Sprint 27e Round 2 TEST-r2-1 fix **RESOLVED-verified** (실 CI 단계 검증).

### 3.3 `gh variable list` — E2E_ENABLED

```
E2E_ENABLED	true	2026-05-13T02:16:17Z
```

→ `e2e` job (line 122) 활성. 21 spec (security-headers 외) 모두 CI 안 실행 중.

### 3.4 mutation test 3건 baseline (Round A 산출물 참조)

- MUT-1 (X-Frame-Options): Sprint 27e Round 2 이미 100% kill verified
- MUT-2 (config validator): Round 2 verify 정상
- MUT-3 (lazy seed fast path): **신규 — Step 4 fix 후 verify 의무**

본 Round B 는 baseline 확인. Step 4 fix 적용 시 즉시 mutation 시연.

### 3.5 Test-Coverage verdict — **안전 (PASS)**

| 항목 | 결과 |
|---|---|
| BE pytest | 490 PASS / 1 skip |
| FE vitest | 56 PASS |
| e2e spec | 22 spec (CI 활성) |
| main 가지 flake rate | 0% (15/15) |
| TEST-r2-1 CI gate | 활성 |

→ 외부 5명 진입 Test-Coverage **GO**. TEST-5/7 (carry) 본 sprint 안 신설 권고.

---

## 4. Architecture dynamic verify

### 4.1 architecture test runtime

`cd backend && uv run pytest tests/architecture/ -q` → **2/2 PASS** (0.01s).

→ BL-006 회귀 가드 (memory→embeddings lazy import) 정상 동작.

### 4.2 runtime config verify

`curl http://localhost:8000/api/v1/health` → **200 OK** (`{"status":"healthy"}`).

→ `core/lifespan.py` startup probe 통과. `core/config.py` Settings 정상 load (production mode 아니라 cron token + JWT issuer validator 통과 skip). dev Clerk URL + cron token dev fallback 모두 정상.

### 4.3 의존성 cycle runtime ImportError 0

backend uvicorn 정상 부팅 = `core ↔ common` cycle + `auth ↔ onboarding` cycle 모두 lazy import + model-only 회피로 runtime 동작. ImportError 0건.

→ Round A Architecture S28-ARCH-4 (11 쌍 양방향) 측정 정확 — **runtime OK but 정적 cycle 존재**. governance 영역 carry.

### 4.4 Sentry SKIP path 의 5xx forensic dump

ARCH-r2-4 fix 적용 (`main.py:142` `logger.exception("global_unhandled_5xx", ...)`) — uvicorn stdout 에 stack trace dump.

→ dev 환경 (Sentry DSN 미설정) 에서 forensic 보장. production 도 동일 path (Sentry DSN 설정 시 추가로 Sentry).

### 4.5 Architecture verdict — **안전 (PASS-with-carry)**

| 항목 | 결과 |
|---|---|
| architecture test runtime | ✅ 2/2 PASS |
| runtime config | ✅ 200 |
| 의존성 cycle ImportError | ✅ 0건 |
| Sentry SKIP forensic | ✅ logger.exception 적용 |

→ 외부 5명 진입 Architecture **GO**. Round A 신규 7건 (S28-ARCH-1~7) 모두 비차단.

---

## 5. Round B 전체 verdict

| 영역 | dynamic verify 결과 | severity 최댓값 |
|---|---|:-:|
| Security | 회귀 0 (보안 헤더 + IDOR + JWT) | 안전 |
| **Performance** | dashboard 4-5s + authn 2s hidden cost | **심각** (BUG-S28-PERF-RT-1) |
| Test-Coverage | 회귀 가드 활성, CI flake 0% | 안전 |
| Architecture | runtime OK, cycle ImportError 0 | 안전 |

### 5.1 외부 5명 dogfooding 진입 통합 verdict

| 분기 | 판정 |
|---|---|
| **외부 5명 dogfooding 진입 (current main `3e41893`)** | **NEEDS-FIX** — BUG-S28-PERF-RT-1 root cause 분석 + 가능 시 fix |
| **본 sprint Step 4 fix 적용 후** | **GO** (조건: BUG-S28-PERF-RT-1 + PERF-4 + PERF-10 + TEST-5 + TEST-7 처리) |

### 5.2 dogfooding-blocker 후보

**BUG-S28-PERF-RT-1** (심각, runtime 신규):
- 증상: 모든 authn endpoint `~2s hidden cost`
- 영향: 외부 5명 매 클릭 2s + dashboard 첫 인상 4s
- root cause 가설: JWKS fetch / find_by_clerk_id / connection pool
- 본 sprint Step 4 안 정밀 분석 + 가능 시 fix

### 5.3 Round A 와 cross-verify 결과

- Round A Security 의 carry 12/12 verify + 신규 7건 비차단 → Round B 실 verify 일치 (회귀 0)
- Round A Performance 의 BUG-S28-PERF-1 (list endpoints 2 RTT) + PERF-r2-4 (lazy seed) → Round B 가 **추가 root cause** (authn 2s) catch — Round A 가 정적 분석으로 못 잡은 hidden cost
- Round A Test-Coverage 의 carry verify → Round B CI flake 0% + TEST-r2-1 활성 일치
- Round A Architecture 의 carry verify → Round B runtime config OK 일치

**Round B 신규성**: BUG-S28-PERF-RT-1 — Round A 가 정적 분석으로 못 잡은 dynamic 발견.

---

## 6. 본 sprint Step 4 권고 fix (Round A + B 통합)

### 6.1 심각 (dogfooding 직접 영향) — 본 sprint 안 처리 필수

1. **BUG-S28-PERF-RT-1** (Round B 신규, 심각) — authn 2s hidden cost root cause 분석 + 가능 시 fix (1-2h)
2. **PERF-4** (Sprint 27 carry, P0 격상) — Gemini timeout + tenacity retry + circuit breaker (1.5d)
3. **PERF-10** (Sprint 27 carry, P1 격상) — next/font local self-host (0.5d)

### 6.2 보통 (외부 진입 안전망) — 본 sprint 안 권고

4. **TEST-5** (Sprint 27 carry, P1) — invite accept happy-path e2e (1.5h)
5. **TEST-7** (Sprint 27 carry, P1) — upload mime real browser e2e (1h)
6. **BUG-S28-SEC-1** (Round A 신규, 보통) — CI `uv sync --frozen` (10분)
7. **BUG-S28-SEC-3** (Round A 신규, 보통) — JWT 검증 실패 `logger.warning` (10분 + pytest 4 case)
8. **BUG-S28-ARCH-3** (Round A 신규, 보통/안전) — directory-map.md 재작성 (20분)
9. **BUG-S28-ARCH-5** = BUG-S28-TEST-7 — architecture test gate 4건 (1h)

### 6.3 안전 (governance / cleanup) — 본 sprint 안 권고

10. **BUG-S28-SEC-2** (Round A 신규) — r2-cleanup.yml SHA pin (5분)
11. **BUG-S28-ARCH-6** (Round A 신규) — BL-S27e-A~F backlog 등재 (10분)
12. **BUG-S28-ARCH-7** (Round A 신규) — 토큰컷 측정 도구 표준화 (30분)

총 비용: 심각 ~ 1-2h + 보통 ~ 6-7h + 안전 ~ 1h. **본 sprint Step 4 ~ 8-10h 권고**.

---

*검사자: Round B (MCP Playwright runtime smoke + curl + pytest), 본 main agent sequential — sub-agent 폐기*
*baseline: `3e41893` · branch `sprint-28/dogfooding-stabilize`*
*환경: FE :3000 + BE :8000 + dev Clerk (creative-boxer-79) + Neon dev*
