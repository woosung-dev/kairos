# Sprint 27e Round 2 — Cross-Check + Adversarial Verify 통합 보고서

> Round 1 (PR #109, main HEAD `b7e704e`) 의 fix 6건 RESOLVED 마크 검증 + 정적 분석 한계 보완 + 외부 5명 진입 직전 BL 우선순위 재평가.
>
> baseline: `b7e704e` (Round 1 merged) · branch: `sprint-27e/round2-cross-check` · 검사 일시: 2026-05-25 KST · 환경: FE/BE down → 정적 + pytest/vitest 실 실행 + dependency audit + commit-level verify · production/Sentry/Clerk Production audit SKIP (사용자 정책)

---

## 0. Executive Summary

### Round 2 Verdict — **PASS-with-carry (GO 유지)** + **production cutover hardening 필요**

| 차원 | Round 1 verdict | Round 2 verdict | Δ |
|---|---|---|---|
| 외부 5명 dogfooding 진입 | GO (차단 6건 fix 후) | **GO 유지** (차단 0건) | unchanged |
| ADR-024 Clerk Production cutover | (Round 1 SEC-3 lock-in) | **NEEDS-FIX** (SEC-r2-2/3/4 staging 우회) | regression 발견 |
| 헌법 정합성 | PASS-with-carry | **PASS-with-carry** (ARCH 추가 1건) | unchanged |
| 회귀 가드 efficacy | RESOLVED 6/6 | **BE 11/11 mutation kill 100%, FE CI 미게이트** | partial gap |

→ **외부 5명 dogfooding 진입 = GO 유지.** 단 **production cutover 직전 SEC-r2-2/3/4 fix 필수** + **FE e2e CI 게이트 활성화 권고 (30분, 본 sprint 안)**.

### Round 1 fix 6건 verify 결과

| Round 1 ID | 검증 방식 | 결과 |
|---|---|---|
| **BUG-S27e-SEC-1** (Clerk CVE) | `package.json:19` + `pnpm audit --json` | ✅ **RESOLVED-verified** — `^7.4.1`, GHSA-vqx2 사라짐 |
| **BUG-S27e-SEC-2** (Next CVE) | `package.json:33` + `pnpm audit --json` | ✅ **RESOLVED-verified** — `16.2.6`, middleware/SSRF advisory 사라짐 |
| **BUG-S27e-SEC-3** (JWT issuer/audience) | `dependencies.py:120-129` + `config.py:32-34,89-98` + pytest 4 case | ✅ **RESOLVED-verified** (edge case → r2-2 별도 등재) |
| **BUG-S27e-SEC-4** (cron token validator) | `config.py:77-86` + pytest 3 case | ✅ **RESOLVED-verified** (edge case → r2-3 별도 등재) |
| **BUG-S27e-TEST-1** (보안 헤더 회귀 가드) | BE 2/2 PASS + mutation test 100% kill + FE spec 49 line 정합 | ✅ **RESOLVED-verified (BE)** + ⚠️ **FE CI 미게이트** (→ TEST-r2-1) |
| **BUG-S27e-TEST-2** (lazy seed concurrent race) | testcontainers 2/2 PASS (N=5 + N=10) | ✅ **RESOLVED-verified** |

→ **6/6 RESOLVED-verified.** 단 SEC-3/4 의 staging 우회 edge case 2건 + TEST-1 의 FE CI 미게이트 1건 = Round 2 신규 등재.

### Round 2 신규 발견 총량

| Reviewer | 차단 (Blocking) | P1 (비차단) | P2 | P3 | errata/INFO | 합계 |
|---|---:|---:|---:|---:|---:|---:|
| Security | **3** (r2-2/3/4 — prod cutover 직전) | — | 5 | 2 | 1 (r2-1) | **11** |
| Performance | 0 | 5 (r2-1~5) | 6 (r2-6~11) | 1 (r2-12) | — | **12** |
| Test-Coverage | **1 conditional** (r2-1, CI 게이트) | — | 3 (r2-2~4) | 1 (r2-5) | — | **5** |
| Architecture | 0 | 1 (r2-1) | 1 (r2-3) | 4 (r2-2/4/5/7) | 1 (r2-6) | **7** |
| **합계** | **3 (cutover) + 1 (CI gate, conditional)** | **6** | **15** | **8** | **2** | **35** |

→ **외부 5명 dogfooding 진입을 차단하는 결함 = 0건.** 차단 3건 모두 "production cutover 직전" 발현 — current main (dev Clerk instance) 위 외부 5명 dogfooding 에서는 미발현.

### Round 1 BL escalation 권고 (Round 2 가 P 등급 갱신)

| Round 1 BL | Round 1 분류 | Round 2 재평가 | 사유 |
|---|---|---|---|
| BL-S27e-SEC-5 (audit_events) | P2 | **P1 escalate** | 외부 진입 시 role escalation 탐지 0 + Sentry SKIP — r2-6/r2-7 와 결합 forensic blind |
| BL-S27e-SEC-6 (rate-limit) | P2 | **P1 escalate** | r2-8 JWT cache DoS + Gemini 비용 abuse 3중 risk |
| BL-S27e-SEC-8 (prompt inj 1 prompt) | P3 | **P2 escalate (+ r2-9 확대)** | 3 prompt 모두 패턴 동일 — RAG 1개만이 아님 |
| BL-S27e-SEC-11 (Sentry SKIP) | P3 | **P1 escalate** | r2-6/r2-7 결합 시 JWT 실패/admin 호출/role 변경 모두 log 0 |
| BL-S27e-PERF-4 (Gemini timeout) | P1 | **P0 격상 권고** | vendor incident 1주에 1회 → 외부 5명 다중 다운 risk |
| BL-S27e-PERF-10 (font CDN) | P2 | **P1 격상 권고** | 외부 첫 인상 LCP 직접 |
| BL-S27e-PERF-15 (client lazy) | P3 | **P1 격상 권고** | RAG path 도 동일 패턴 (PERF-r2-2 와 결합) |
| BL-S27e-PERF-7/8/9 | P2 | **P3 강등 권고** | 외부 5명 1주 시나리오 영향 미미 |
| BL-S27e-ARCH-5 | P3 | **P2 격상 권고** | 1 곳 가정 → 실재 4 곳 산재 |

---

## 1. Round 1 fix 6건 verify 상세 (모든 file:line 증거)

### 1.1 SEC-1: `@clerk/nextjs` CVE 해소

- `frontend/package.json:19` — `"@clerk/nextjs": "^7.4.1"` (Round 1 권고 ≥7.2.1, 실 적용 7.4.1)
- `pnpm audit --audit-level critical` = **0 critical**
- GHSA-vqx2-fgx2-5wq9 advisory pnpm audit 결과 사라짐
- **verdict**: ✅ RESOLVED-verified

### 1.2 SEC-2: Next.js 16.2.2 → 16.2.6

- `frontend/package.json:33` — `"next": "16.2.6"` (≥16.2.5 patched)
- `eslint-config-next: 16.2.6` 동행
- middleware/Proxy bypass + SSRF + DoS + cache poisoning advisory 모두 pnpm audit 에서 사라짐
- **verdict**: ✅ RESOLVED-verified

### 1.3 SEC-3: JWT issuer + audience 명시

- `backend/src/auth/dependencies.py:117-129` — `decode_kwargs` 빌더 + `issuer=settings.clerk_jwt_issuer` 강제 + `audience=` 분기 + `InvalidIssuerError` 별도 catch (line 137-139)
- `backend/src/core/config.py:32-34` — `clerk_jwt_issuer` + `clerk_jwt_audience` Settings 신규
- `backend/src/core/config.py:89-98` — `_no_dev_issuer_in_prod` field_validator
- `backend/tests/test_jwt_verification.py` 4 PASS
- **verdict**: ✅ RESOLVED-verified — **단 edge case (staging 우회 + audience None default) = BUG-S27e-SEC-r2-2 별도 등재**

### 1.4 SEC-4: cron_secret_token field_validator

- `backend/src/core/config.py:8` — `_CRON_TOKEN_DEV_FALLBACK` 상수 추출
- `backend/src/core/config.py:77-86` — `_no_default_cron_in_prod` field_validator
- `backend/tests/test_config.py:62-100` 3 PASS
- **verdict**: ✅ RESOLVED-verified — **단 edge case (staging 우회 + 약한 token 통과) = BUG-S27e-SEC-r2-3 별도 등재**

### 1.5 TEST-1: 보안 헤더 4종 회귀 가드

- `backend/tests/test_security_hardening.py::TestSecurityHeadersRegression` 2 PASS (health + 404)
- **Mutation test 결과**: `backend/src/main.py:103` `X-Frame-Options` 1줄 주석 처리 → 2/2 FAIL 정확히 catch → **kill rate 100%**
- `frontend/e2e/tests/security-headers.spec.ts` 49 line 정합 (4 헤더 × 2 page = sign-in + home)
- **verdict**: ✅ RESOLVED-verified (BE) + ⚠️ **FE CI 미게이트** (`test.yml:78` `if: vars.E2E_ENABLED == 'true'` 미활성화 → BUG-S27e-TEST-r2-1 신규 등재, **30분 fix 권고**)

### 1.6 TEST-2: lazy seed concurrent race

- `backend/tests/auth/test_personal_workspace_race_concurrent.py` 2 PASS (N=5 + N=10, testcontainers postgres, 2.27s)
- `asyncio.Barrier(N)` 로 진정한 동시성 검증. 별개 connection 5/10 task → 최종 workspace 1개 + WorkspaceMember 1개 보장
- partial unique index `uq_workspaces_owner_personal ON workspaces (owner_id) WHERE type = 'personal'` fixture 명시 생성 (alembic 정합)
- **verdict**: ✅ RESOLVED-verified

### 1.7 Round 1 errata 1건 (Round 2 발견)

| 진술 | 실제 |
|---|---|
| `integrated-report.md:28` "fast-uri Sentry transitive — Sentry 도입 시 함께 해소" | **잘못** — fast-uri 의 real source = `shadcn@4.1.2 > @modelcontextprotocol/sdk@1.29.0 > ajv@8.18.0 > fast-uri@3.1.0`. Sentry 와 무관. 별도 해소 필요 (BUG-S27e-SEC-r2-5 = shadcn → devDependencies). |

→ BUG-S27e-SEC-r2-1 (errata).

---

## 2. Round 2 신규 발견 매트릭스 (Round 1 blind spot)

### 2.1 차단 결함 (Production cutover 직전 + CI 게이트)

| ID | Reviewer | OWASP/원칙 | 차단 시점 | file:line | 발견 요약 | 권장 fix | 본 sprint? |
|---|---|---|---|---|---|---|:-:|
| **BUG-S27e-SEC-r2-2** | Security | A02/A07 | ADR-024 cutover 직전 | `core/config.py:91-98` + `auth/dependencies.py:124-128` | SEC-3 fix 의 staging 우회 (`app_env == "production"` 만 차단, staging 통과) + `clerk_jwt_audience = None` default 가 `verify_aud: False` fallback (audience 검증 영구 skip) | validator → `app_env in {production, staging, stage, prod}` + audience non-dev validator 추가 | **YES (cutover 직전 fix 권고)** |
| **BUG-S27e-SEC-r2-3** | Security | A05 | ADR-024 cutover 직전 | `core/config.py:77-86` | SEC-4 fix 의 staging 우회 + 약한 token 통과 (`CRON_SECRET_TOKEN=x` 1글자도 production 통과 — validator 가 "fallback 문자열과 동일한지" 만 검사) | validator → `app_env != "development"` (staging 도 거부) + `len(val) >= 32` 강제 | **YES (cutover 직전 fix 권고)** |
| **BUG-S27e-SEC-r2-4** | Security | A05 | ADR-024 cutover 직전 | `main.py:75-78` vs `config.py:80,92` | production 판별 분기 inconsistency — `_is_production` 은 OR+lower, validator 는 `app_env == "production"` 단일. `ENVIRONMENT=production` + `APP_ENV` 미설정 시 docs 차단 정상 but validator skip → dev issuer + dev cron token 통과 | `is_production_env()` helper 추출 + main.py + 양 validator 공통 호출 | **YES (cutover 직전 fix 권고)** |
| **BUG-S27e-TEST-r2-1** | Test-Coverage | CI 게이트 | 외부 5명 진입 *전* | `.github/workflows/test.yml:78` + `frontend/e2e/tests/security-headers.spec.ts` | TEST-1 fix 의 FE e2e spec 이 `if: vars.E2E_ENABLED == 'true'` 미활성화로 CI 결코 실행 X. BE 한정 RESOLVED. next.config.ts 정리 시 CI 가드 0 → 사용자 도달 후 발견 risk | `test.yml` 에 `security-headers.spec.ts` 단독 실행 step 추가 (public route 만, secrets 불요) | **YES (30분, 본 sprint)** |

→ **차단 4건 = 모두 30분 ~ 1시간 fix 가능.** 외부 5명 dogfooding 진입 자체에는 미차단 (current main 위 dev Clerk).

### 2.2 P1 비차단 (Round 2 신규)

| ID | Reviewer | 영역 | file:line | 발견 |
|---|---|---|---|---|
| BUG-S27e-PERF-r2-1 | Performance | baseline 갭 | sprint infra | production p95 측정값 0건 — Sprint 27d localhost 5 sample (avg 10.6s) 만 cited |
| BUG-S27e-PERF-r2-2 | Performance | DI / 리소스 | `rag/dependencies.py:18-26` + `meetings/dependencies.py:41-50` | RAG/meetings AI client 매 request 신규 (`genai.Client()` + `AsyncOpenAI()` 매번) |
| BUG-S27e-PERF-r2-3 | Performance | DB / 알고리즘 | `rag/service.py:112-131` | RAG hybrid search vector + text sequential await (2× Neon RTT 100-200ms 추가) |
| BUG-S27e-PERF-r2-4 | Performance | auth hidden cost | `auth/dependencies.py:174-249` | `get_current_user` JWT cache hit 도 매 request 3 INSERT + commit. 5 API fanout = 20 statements = 500ms-1s hidden |
| BUG-S27e-PERF-r2-5 | Performance | connection pool | `common/database.py:20-27` | `pool_size=5 + overflow=10 = 15` max, Cloud Run max-concurrency=80 default 와 미정합 (burst 시 즉시 발현) |
| BUG-S27e-ARCH-r2-1 | Architecture | ADR-014 위반 | `workspaces/service.py:57-58`, `projects/service.py:81-82`, `meetings/pipeline_service.py:165-166`, `rag/service.py:37-38` | OnboardingService 가 4 service.py 에서 cross-import (Round 1 §5 "service.py 직접 import 0" false negative) |

### 2.3 P2/P3 비차단 (Round 2 신규, 요약)

| Reviewer | P2 | P3 |
|---|---|---|
| Security | r2-5 (shadcn devDeps — 14 audit 즉시 0), r2-6 (admin audit log), r2-7 (JWT 실패 log), r2-8 (JWT cache DoS), r2-9 (prompt injection 3 prompt 확대) | r2-10 (backend upper-bound), r2-11 (CORS 형식 검증) |
| Performance | r2-6 (lifespan cold start), r2-7 (BG task leak), r2-8 (EmbeddingService 신규), r2-9 (in-app cron 인프라), r2-10 (SemanticCache expires_at filter), r2-11 (Sentry trace 0) | r2-12 (save_cache ON CONFLICT) |
| Test-Coverage | r2-2 (flake 재분류), r2-3 (cross-spec 확장), r2-4 (mutation 도구 도입) | r2-5 (race 경계 시나리오) |
| Architecture | r2-3 (services DTO 일관성) | r2-2 (auth raw SQL), r2-4 (global handler 5xx unlogged), r2-5 (CONTEXT-MAP 카운트 13 vs list 14 vs 실재 15), r2-7 (BL-S26-1 토큰컷 회귀 3398→7960 bytes) |

---

## 3. 충돌 해결 (Round 1 vs Round 2 시각)

### 3.1 충돌 없음 (대부분 항목)

Round 2 는 Round 1 의 보강 (edge case carry, blind spot 추가) 위주 — 명시적 충돌 0건.

### 3.2 일부 진술 정정 (errata)

| Round 1 진술 | Round 2 정정 |
|---|---|
| `integrated-report.md:28` "fast-uri Sentry transitive" | `shadcn > MCP-SDK > ajv > fast-uri` (Sentry 와 무관) |
| `architecture-findings.md §5` "service.py 끼리 직접 import 0건" | OnboardingService 4 service.py cross-import (ARCH-r2-1) |
| `test-coverage-findings.md §6.4` "flake 2 spec (first-project + onboarding-tooltip)" | 실 fail = (a) tiptap useEditor overload type-check + (b) Nightly GEMINI_API_KEY=fake. flake 아닌 환경/dep 결함 (BL-S27e-4 재분류) |
| `performance-findings.md §0` "Sentry 도입 시 함께 해소" | Sentry 가 fast-uri 영향 0 (위와 동일) |

→ Round 1 의 결론 (GO 판정) 자체 영향 0. errata 4건은 Round 2 보고서에 명시 + Round 1 보고서는 historical record 로 유지.

### 3.3 우선순위 재평가 (Round 2 가 갱신 권고)

§0.4 의 BL escalation 권고 표 참조. 8건 P 등급 변경.

---

## 4. 외부 5명 진입 직전 fix 권고 (Round 1 + Round 2 통합)

### 4.1 본 sprint 안 fix (30분 ~ 1.5h)

| 우선순위 | ID | 작업 | 예상 |
|:-:|---|---|:-:|
| 1 | **BUG-S27e-SEC-r2-2/3/4** (Security cutover 묶음) | config.py `is_production_env()` helper + 양 validator staging 확장 + audience non-dev validator + cron token min length | **1h** |
| 2 | **BUG-S27e-TEST-r2-1** (FE CI 게이트) | `test.yml` 에 `security-headers.spec.ts` 단독 실행 step 추가 (secrets 불요) | **30분** |
| 3 | **BUG-S27e-ARCH-r2-4** (global handler 5xx log) | `main.py:132-139` `logger.exception("global 5xx", exc_info=_exc)` 1 line | **5분** |
| 4 | **BUG-S27e-ARCH-4 / r2-5 / r2-7** (governance) | CONTEXT-MAP §4.1/§4.3 모듈 수 정합 (15/14) + BL-005 closed 마크 + BL-S26-1 토큰컷 회귀 갱신 | **30분** |

**총 ~ 2h.** 본 Round 2 commit 묶음에 같이 포함 권고.

### 4.2 외부 진입 *전* 권고 (Sprint 28 head-of-line — Round 1 BL escalation)

| 우선순위 | ID | 작업 | 예상 |
|:-:|---|---|:-:|
| 1 | **PERF-4** (P0 격상) | Gemini timeout + tenacity retry + half-open circuit breaker | 1.5d |
| 2 | **PERF-10** (P1 격상) | next/font local self-host (Satoshi/Pretendard woff2) | 0.5d |
| 3 | **TEST-5** (P1 유지) | invite accept happy-path e2e | 1.5h |
| 4 | **TEST-7** (P1 유지) | upload mime real browser e2e | 1h |

**총 ~ 2-3d.** 외부 진입 시그널 (사용자 결정) 후 1 sprint 안 처리.

### 4.3 Sprint 28+ carry (BL-S27e-A~H 묶음)

- **BL-S27e-A 보강**: SEC-5 + r2-6 + r2-7 (audit log 표준화) + SEC-11 (Sentry 재검토)
- **BL-S27e-B 보강**: SEC-8 + r2-9 (3 prompt 구분자 통일)
- **BL-S27e-C cluster**: PERF-1/2/3/5 + PERF-r2-2/3/4/5 (외부 진입 *후* 우선순위)
- **BL-S27e-D cluster**: PERF-6/11/12 + PERF-r2-6~11 (외부 진입 *후*)
- **BL-S27e-E 보강**: TEST-3/4 + r2-3/4 + TEST-8/9/10
- **BL-S27e-F 보강**: ARCH-1/2/3/5/6 + ARCH-r2-1/2/3 (architecture deepening sprint ~5-6d)
- **BL-S27e-G (신규)**: production cutover hardening (SEC-r2-2/3/4) — *본 sprint 안에 해결 권고로 사라질 수 있음*
- **BL-S27e-H (신규)**: backend dep upper-bound (SEC-r2-10) 또는 `--frozen` 강제

---

## 5. 최종 verdict + 외부 5명 진입 판정

### 5.1 verdict 표

| 차원 | 기준 | 측정 | 판정 |
|---|---|---|---|
| 외부 5명 dogfooding 진입 (current main) | 차단 0 | **차단 0** | **GO** |
| ADR-024 Clerk Production cutover | SEC-r2-2/3/4 fix | **fix 권고 (본 sprint 안 1h)** | NEEDS-FIX |
| FE 회귀 가드 CI 운영화 | CI 게이트 활성 | **TEST-r2-1 fix 권고 (30분)** | NEEDS-FIX |
| Round 1 fix verify | 6/6 RESOLVED | **6/6 verified** + mutation kill 100% | PASS |
| 헌법 정합성 | 차단 0 | **차단 0** (ARCH 위반 P1~P3 비차단 carry) | PASS-with-carry |
| 성능 measurement baseline | production p95 ≥ 10 sample | **0 sample** (PERF-r2-1) | UNKNOWN |

### 5.2 최종 판정

**외부 5명 dogfooding 진입 — GO (Round 1 verdict 유지)**

- Round 1 fix 6/6 모두 RESOLVED-verified
- Round 2 신규 차단 4건 = 모두 30분~1h fix 가능 + production cutover/CI 게이트 한정 (current main+dogfooding 자체에는 미차단)
- 헌법/ADR 위반 차단 0건 (PASS-with-carry)
- mutation test 결과 BE 회귀 가드 efficacy 100%

**production cutover (ADR-024) 직전 — NEEDS-FIX (1h)**

- SEC-r2-2/3/4 = staging 우회 + audience None default + production 분기 inconsistency
- 본 Round 2 commit 에 묶어 fix 진행 권고

**FE 회귀 가드 CI 운영화 — NEEDS-FIX (30분)**

- TEST-r2-1 = `test.yml` CI 게이트 활성화
- 본 Round 2 commit 에 묶어 fix 진행 권고

---

## 6. Round 1 + Round 2 평균 점수 (Sprint 27d 형식 차용)

Round 1 의 product/UX 시각이 아닌 기술 deep audit 이라 6 reviewer 평균 점수 산정은 부적합. 대신 차원별 verdict.

| 차원 | Round 1 | Round 2 cross-check | 평균 |
|---|---|---|---|
| 보안 | NEEDS-FIX (P0×2 + P1×2) | PASS (Round 1 fix verified) + 3 cutover risk | **PASS-with-cutover-carry** |
| 성능 | PASS (차단 0) | PASS (차단 0) + 5 P1 추가 | **PASS-with-carry** |
| 테스트 | NEEDS-FIX (P0×2) | PASS (BE 100% mutation kill) + FE CI 미게이트 | **PASS-with-CI-gate-carry** |
| 아키텍처 | PASS-with-carry | PASS-with-carry (ARCH-r2-1 추가) | **PASS-with-carry** |

→ **종합: 외부 5명 dogfooding 진입 GO. production cutover 1h fix 후 GO. governance 1h fix 본 sprint 안.**

---

## 7. 산출물 인덱스

| 파일 | 내용 |
|---|---|
| `security-findings-r2.md` | 11건 (errata 1 + P1 3 + P2 5 + P3 2) |
| `performance-findings-r2.md` | 12건 (P1 5 + P2 6 + P3 1) + Round 1 priority 재분류 |
| `test-coverage-findings-r2.md` | 5건 (P1 1 conditional + P2 3 + P3 1) + BE 11/11 PASS + mutation 100% kill |
| `architecture-findings-r2.md` | 7건 (P1 1 + P2 1 + P3 4 + INFO 1) + 헌법 토큰컷 정량 |
| `integrated-report-r2.md` (본) | Round 1+2 통합 + fix verify 표 + 외부 5명 진입 final verdict |
| `final-integrated-report.md` | Sprint 27e 전체 (Round 1 + Round 2) 최종 통합 |
| `final-report.html` | 시각화 (Round 1 report.html 차용 + final verdict) |
