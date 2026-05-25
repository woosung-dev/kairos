<!-- Sprint 28 통합 audit 보고서 (Round A + Round B). 시니어 엔지니어 + QA 마스터 페르소나, 4 영역 sequential audit. -->

# Sprint 28 dogfooding-stabilize — 통합 audit 보고서 (Round A + B)

> baseline `3e41893` (Sprint 27e Round 1 PR #109 + Round 2 PR #110 + QA dynamic verify PR #111 머지 직전 main HEAD) · branch `sprint-28/dogfooding-stabilize`
>
> audit 진행자: 본 main agent (시니어 엔지니어 + QA 마스터 페르소나, sequential). Round A 의 sub-agent 3건 polling 후 stop, security-findings.md 만 보존, 나머지 본 agent 직접 작성. Round B 는 MCP Playwright single browser 라 sub-agent 미사용 — 본 agent 만 sequential 측정.
>
> 검사 일시 2026-05-26 KST · 환경 FE:3000 + BE:8000 + dev Clerk + Neon dev.

---

## 0. Executive Summary

### 0.1 외부 5명 dogfooding 진입 verdict

| 분기 | 판정 | 차단 결함 |
|---|---|---|
| current main `3e41893` | **NEEDS-FIX** | 1건 (BUG-S28-PERF-RT-1 심각, Round B 신규) |
| 본 sprint Step 4 fix 적용 후 | **GO** | 0건 (전 영역) |

### 0.2 audit 결과 정량

| 영역 | Round A (정적) | Round B (dynamic) | severity (심각/보통/안전) |
|---|:-:|:-:|:-:|
| Security | carry 12/12 verify + 신규 7건 | 회귀 0 (보안 헤더 + IDOR + JWT) | 0 / 1 / 6 |
| Performance | carry 21 잔존 + 신규 12건 | dashboard 4.3s + RAG p95 13.5s + **authn 2s hidden** | **1** / 5 / 6 |
| Test-Coverage | carry 6 잔존 + 신규 8건 | CI flake 0%, TEST-r2-1 활성 | 0 / 3 / 5 |
| Architecture | carry 8 잔존 + 신규 7건 | runtime OK, cycle ImportError 0 | 0 / 2 / 5 |
| **합계 신규** | **34건** | **4 영역 cross-verify** | **1 / 11 / 22** |

→ 본 audit 신규 차단 = 1건 (Round B BUG-S28-PERF-RT-1). 나머지 33건 비차단 (보통 11 + 안전 22).

### 0.3 본 sprint Step 4 권고 fix 12건

| 분류 | ID | severity | 비용 |
|:-:|---|:-:|:-:|
| dogfooding-blocker | **BUG-S28-PERF-RT-1** (Round B 신규) — authn 2s hidden cost root cause | **심각** | 1-2h |
| 외부 진입 *전* | **PERF-4** (carry) — Gemini timeout + circuit breaker | **심각** (P0 격상) | 1.5d |
| 외부 진입 *전* | **PERF-10** (carry) — next/font local | **보통** (P1 격상) | 0.5d |
| 외부 안전망 | **TEST-5** (carry) — invite accept happy-path e2e | **보통** | 1.5h |
| 외부 안전망 | **TEST-7** (carry) — upload mime real browser e2e | **보통** | 1h |
| 보안 hygiene | **BUG-S28-SEC-1** (신규) — CI `uv sync --frozen` | **보통** | 10분 |
| 보안 hygiene | **BUG-S28-SEC-3** (신규) — JWT 검증 실패 `logger.warning` | **보통** | 10분 + pytest 4 case |
| 보안 hygiene | **BUG-S28-SEC-2** (신규) — r2-cleanup.yml SHA pin | 안전 | 5분 |
| governance | **BUG-S28-ARCH-3** (신규) — directory-map 재작성 | 안전 | 20분 |
| governance | **BUG-S28-ARCH-5/TEST-7** (신규) — architecture test gate 4건 | **보통** | 1h |
| governance | **BUG-S28-ARCH-6** (신규) — BL-S27e-A~F backlog 등재 | 안전 | 10분 |
| governance | **BUG-S28-ARCH-7** (신규) — 토큰컷 도구 표준화 + BL-S26-1 재검토 | 안전 | 30분 |

총 비용: 심각 ~ 1.5d (PERF-4 가 dominant) + 보통 ~ 4h + 안전 ~ 1h. **본 sprint Step 4 ~ 1.5d + 5h ≈ 1.5-2d**.

사용자 carry 범위 (b) 명시 = P0/P1 + 일부 BL-S27e-A/B/H. PERF-4/10/TEST-5/7 + BUG-S28-PERF-RT-1 + 보안/governance 묶음 모두 (b) 정합.

---

## 1. 4 영역 audit 결과 통합

### 1.1 Security (Round A + B)

**Round A 정적**: `round-a/security-findings.md` (116 line)
- carry 12/12 PASS verify (Clerk + Next CVE + JWT + cron token + 보안 헤더 + lazy seed race + cutover hardening + BUG-QA-1/2)
- 신규 7건 (BUG-S28-SEC-1~7) — 모두 비차단

**Round B dynamic**: `round-b/runtime-findings.md` §1
- 보안 헤더 4종 live 3 path PASS
- IDOR live 9 probe (cross-tenant 403 + SQLi 422 + protected 200)
- JWT tampered → 401 + Clerk auto re-issue 동작
- ADR-022 sync_user 비활성 verify

→ **Security verdict — 안전 (전 영역 GO)**. Round A 의 BUG-S28-SEC-1/3 가 보통 (CI hygiene + forensic), 본 sprint 안 처리.

### 1.2 Performance (Round A + B)

**Round A 정적**: `round-a/performance-findings.md`
- carry 21 잔존 (PERF-1/2/3/4/5 + PERF-r2-2/3/5~12 등)
- 신규 12건 (BUG-S28-PERF-1~12) — list endpoints 2 RTT / Whisper timeout / audio BG OOM 등

**Round B dynamic**: `round-b/runtime-findings.md` §2
- dashboard 5 endpoint fanout critical path **4286ms** (PR #111 fix 후 -45%, 외부 여전히 ~4s)
- isolated endpoint sequential — `/users/me` 단독 **2038ms** (authn 만)
- RAG p95 **13.5s** / p50 11.1s (KPI <15s 안)
- BE health 6ms (BE 자체 latency 0)

**Round B 신규 발견 — BUG-S28-PERF-RT-1 (심각)**:
- 증상: 모든 authn endpoint ~2s hidden cost (PR #111 fast path fix 적용 후에도 잔재)
- root cause 가설 (가장 가능성 순):
  1. JWKS fetch 매 request 또는 PyJWKClient cache miss (Clerk dev URL SSL handshake + JWKS response 1-1.5s)
  2. `find_by_clerk_id` Neon RTT + query (localhost→Neon US/EU region 100-200ms + 추가 cost)
  3. JWT verify cost (cache hit 시 sub-ms 이어야)
  4. connection pool contention (sequential 측정도 2s = pool 문제 X)
- 영향: 외부 5명 매 클릭 2s + dashboard 첫 인상 4s
- 본 sprint Step 4 root cause 분석 + 가능 시 fix

→ **Performance verdict — NEEDS-FIX (BUG-S28-PERF-RT-1 심각)**. PERF-4/10 carry 도 본 sprint 안.

### 1.3 Test-Coverage (Round A + B)

**Round A 정적**: `round-a/test-coverage-findings.md`
- BE pytest 490 PASS / 1 skip (Sprint 27e 482 → +8)
- FE vitest 56 PASS / 0 fail
- e2e spec 22 (CI 활성)
- main 가지 flake rate 0% (15/15 success)
- carry verify 4/10 해소 + 6 잔존 (TEST-3/4/5/6/7/8/9/10)
- 신규 8건 (BUG-S28-TEST-1~8)

**Round B dynamic**: `round-b/runtime-findings.md` §3
- TEST-r2-1 CI gate 활성 verify (`test.yml:73-106` 정합)
- mutation test 3건 baseline (Step 4 fix 후 verify 의무)

→ **Test-Coverage verdict — 안전 (GO)**. TEST-5/7 본 sprint 안 신설 권고.

### 1.4 Architecture (Round A + B)

**Round A 정적**: `round-a/architecture-findings.md`
- carry verify 4 해소 + 2 부분 해소 + 8 잔존
- 신규 7건 (S28-ARCH-1~7) — common 역의존 + Demeter 5번째 사이트 + directory-map stale + 11 쌍 양방향 cycle + test gate 부족 + BL 미등재 + 토큰컷 회귀

**Round B dynamic**: `round-b/runtime-findings.md` §4
- architecture test runtime 2/2 PASS
- runtime config (BE health 200)
- 의존성 cycle runtime ImportError 0건 (정적 cycle 존재해도 lazy import + model-only 회피)
- Sentry SKIP path forensic 활성 (ARCH-r2-4 fix verified)

→ **Architecture verdict — 안전 (PASS-with-carry)**. 본 sprint governance fix (S28-ARCH-3/5/6/7) 권고.

---

## 2. 신규 발견 매트릭스 (Round A + B 통합)

### 2.1 심각 (1건, dogfooding-blocker)

| ID | 영역 | round | file:line | 증상 |
|---|---|:-:|---|---|
| **BUG-S28-PERF-RT-1** | Performance | **B** | `auth/dependencies.py:115-186` + `common/database.py:20-27` | 모든 authn endpoint ~2s hidden cost. PR #111 fast path fix 후에도 잔재. JWKS fetch / find_by_clerk_id / connection pool 후보. |

### 2.2 보통 (11건, 외부 안전망 또는 hygiene)

| ID | 영역 | round | file:line | 증상 |
|---|---|:-:|---|---|
| BUG-S28-SEC-1 | Security CI | A | `.github/workflows/test.yml + nightly + r2-cleanup` | CI 4곳 `uv sync --frozen` 없음 — dep drift PR 가 CI 통과 가능 |
| BUG-S28-SEC-3 | Security forensic | A | `auth/dependencies.py:140-150` | JWT 검증 실패 4 except 분기 `logger.warning` 0 — Sentry SKIP path forensic 0 |
| BUG-S28-PERF-1 | Performance DB | A | `meetings/service.py:95-98` + 4 도메인 동일 | list endpoints `find_by_workspace + count_by_workspace` 2 sequential await |
| BUG-S28-PERF-2 | Performance Whisper | A | `services/transcription.py:118-123` + chunked | Whisper API timeout 0 / retry 0 (PERF-4 의 Whisper 잔재) |
| BUG-S28-PERF-3 | Performance audio BG | A | `meetings/pipeline_service.py:203` + `services/chunked_transcription.py:113` | BG audio 전체 메모리 적재 — 4hr 회의 OOM risk |
| BUG-S28-ARCH-2 | Architecture Demeter | A | `meetings/service.py:385,389,390` | Demeter 5번째 사이트 (`self.repo.session.add/flush` 직접) |
| BUG-S28-ARCH-4 | Architecture cycle | A | 의존성 그래프 11 쌍 | `core ↔ common` layered 최하위 cycle + auth ↔ onboarding cross-import |
| BUG-S28-ARCH-5 / S28-TEST-7 | Architecture test gate | A | `backend/tests/architecture/` 1건만 | I-1 / ADR-014 / common 역의존 / Demeter 회귀 가드 4건 부족 |
| BUG-S28-PERF-4 | Performance pool | A | `common/database.py + BG task` | BG pool 분리 부재, main pool 공유 |
| BUG-S28-PERF-5 | Performance RBAC | A | `auth/rbac.py` workspace_members SELECT 매 호출 | WorkspaceMember in-process cache 부재 |
| BUG-S28-PERF-6 | Performance FE | A | `lib/query-client.tsx:12` | refetchOnWindowFocus default true + 도메인 staleTime 미정합 |

### 2.3 안전 (22건, governance / cleanup)

| ID | 영역 | round | 비고 |
|---|---|:-:|---|
| BUG-S28-SEC-2 | Security supply chain | A | r2-cleanup.yml SHA pin |
| BUG-S28-SEC-4 | Security CORS | A | `cors_origins` field_validator 부재 |
| BUG-S28-SEC-5 | Security R2 URL | A | `get_download_url` ExpiresIn=3600 hardcode |
| BUG-S28-SEC-6 | Security Sentry scrub | A | `_scrub_pii_hook` URL query / breadcrumbs 미scrub |
| BUG-S28-SEC-7 | Security JWT cache | A | JWT cache revocation hook 부재 |
| BUG-S28-PERF-7~12 | Performance edge | A | `useActivityFeed` race / RAG limit / promote N+1 등 |
| BUG-S28-TEST-1 | Test mutation 도구 | A | mutmut 도입 권고 |
| BUG-S28-TEST-2 | Test fast path 보강 | A | mutation 시연 신규 |
| BUG-S28-TEST-3/4 | Test e2e gap | A | TEST-5/7 신설 권고 (위 보통과 중복) |
| BUG-S28-TEST-5 | Test CI 구조 | A | e2e 단독 step 안 |
| BUG-S28-TEST-6 | Test warning | A | pytest 1501 warnings |
| BUG-S28-TEST-8 | Test 통합 | A | Personal+Team 통합 |
| BUG-S28-ARCH-1 | Architecture common | A | promote_helpers actions 역의존 |
| BUG-S28-ARCH-3 | Architecture docs | A | directory-map FE 7→14 / BE common 5→10 stale |
| BUG-S28-ARCH-6 | Architecture BL | A | BL-S27e-A~F backlog 등재 0건 |
| BUG-S28-ARCH-7 | Architecture 토큰컷 | A | CONTEXT-MAP 8007 bytes (회귀 +47) |

---

## 3. Round A 와 Round B cross-verify

| Round A 정적 finding | Round B dynamic verify | 결과 |
|---|---|---|
| Security carry 12 + 신규 7 | 보안 헤더 + IDOR + JWT 회귀 0 | ✅ 일치 (모두 비차단) |
| Performance PERF-r2-4 lazy seed hidden cost | dashboard 4.3s + authn 2s | ⚠️ **Round B 추가 root cause** (fast path 외 hidden) — BUG-S28-PERF-RT-1 |
| Performance BUG-S28-PERF-1 list 2 RTT | dashboard fanout 4.3s — RTT 분포 측정 미 (BE log 필요) | △ 부분 verify, Step 4 정밀 측정 |
| Test-Coverage carry verify | CI flake 0% + TEST-r2-1 활성 | ✅ 일치 |
| Architecture S28-ARCH-4 cycle | runtime ImportError 0 (lazy import OK) | ✅ 정적 cycle but runtime OK |
| Architecture ARCH-r2-4 logger.exception | dev 환경 forensic 동작 | ✅ 일치 (Round 2 fix 정합) |

**Round B 의 신규성** = Round A 가 정적 분석으로 못 잡은 BUG-S28-PERF-RT-1 (authn 2s hidden cost). 외부 5명 dogfooding 진입 직접 영향. Sprint 28 의 핵심 신규 finding.

---

## 4. Step 4 fix 진행 plan (사용자 명시 패턴)

**branch 구조**:
- `sprint-28/dogfooding-stabilize` = audit branch (Round A + B + 통합 보고서, 본 commit)
- `sprint-28/fixes` = fix-only branch (audit branch 위 신설)

**fix 진행 순서** (severity 순):

1. **BUG-S28-PERF-RT-1** (심각, runtime 신규) — root cause 분석 + 가능 시 fix
2. **PERF-10** (보통/외부 LCP) — next/font local self-host
3. **PERF-4** (심각/Gemini 가용성) — timeout + tenacity retry + circuit breaker
4. **TEST-5** (보통) — invite accept happy-path e2e
5. **TEST-7** (보통) — upload mime real browser e2e
6. **BUG-S28-SEC-1** (보통) — CI `uv sync --frozen`
7. **BUG-S28-SEC-3** (보통) — JWT 검증 실패 logger.warning + pytest 4 case
8. **BUG-S28-SEC-2** (안전) — r2-cleanup.yml SHA pin
9. **BUG-S28-ARCH-3** (안전) — directory-map.md 재작성
10. **BUG-S28-ARCH-5** (보통) — architecture test gate 4건
11. **BUG-S28-ARCH-6** (안전) — BL-S27e-A~F backlog 등재
12. **BUG-S28-ARCH-7** (안전) — 토큰컷 도구 표준화 + BL-S26-1 재검토

각 fix 별 atomic commit + mutation test (해당 시) + pytest/vitest/typecheck 회귀.

**PR 머지 패턴**:
- `sprint-28/fixes` → `sprint-28/dogfooding-stabilize` PR (PR #112 예상)
- 사용자 review + 머지
- 후속: `sprint-28/dogfooding-stabilize` → `main` PR (PR #113 예상, 사용자 최종 머지)

---

## 5. 외부 5명 dogfooding 진입 최종 verdict

| GO 조건 | 기준 | Sprint 28 측정 | 판정 |
|---|---:|---:|:-:|
| Security 차단 0 | 0건 | 0건 (회귀 0) | **PASS** |
| Performance dashboard LCP | < 3s | 4.3s (PR #111 fix 후) | **NEEDS-FIX (BUG-S28-PERF-RT-1)** |
| Performance RAG p95 | < 15s | 13.5s | PASS (KPI 안) |
| Test 회귀 가드 | mutation kill ≥ 80% | 100% (X-Frame mutation) | PASS |
| Architecture 헌법 위반 차단 | 0건 | 0건 (carry only) | PASS |
| CI flake rate | 0% | 0% (15/15) | PASS |

→ **외부 5명 dogfooding 진입 = BUG-S28-PERF-RT-1 fix 후 GO**.

본 sprint Step 4 fix 12건 적용 시 모든 GO 조건 만족 예상. fix 완료 후 final-integrated-report.md 갱신 + sprint-28 PR 머지.

---

## 6. 산출물 인덱스

| 파일 | 내용 |
|---|---|
| `round-a/security-findings.md` | 11건 OWASP A01~A10 + 도메인, carry 12/12 verify |
| `round-a/performance-findings.md` | 12 신규 + 21 carry, BUG-S28-PERF-1~12 + BUG-QA-1 fix 측정 |
| `round-a/test-coverage-findings.md` | 8 신규 + 6 carry, BE 490 PASS + FE 56 + e2e 22 + CI flake 0% |
| `round-a/architecture-findings.md` | 7 신규 + 14 carry verify, 11 쌍 cycle + Demeter 5 사이트 + 토큰컷 |
| `round-b/runtime-findings.md` | 4 영역 dynamic verify 통합 (sequential MCP Playwright). BUG-S28-PERF-RT-1 신규 |
| `integrated-report.md` (본) | Round A + B 통합 + cross-verify + Step 4 fix plan |
| `final-integrated-report.md` (Step 4 후) | fix 적용 + verify 결과 + 최종 verdict |

---

*검사자: Claude Opus 4.7 (1M context, 본 main agent, 시니어 엔지니어 + QA 마스터 페르소나)*
*baseline: `3e41893` · branch `sprint-28/dogfooding-stabilize`*
