<!-- Sprint 28 Round A — Test-Coverage 정적 audit (본 main agent 직접 작성, sub-agent 폐기 후 sequential) -->

# Sprint 28 Round A — Test-Coverage 정적 audit

> baseline `3e41893` · branch `sprint-28/dogfooding-stabilize` · 본 main agent 가 시니어 엔지니어 + QA 마스터 페르소나로 sequential 진행.

## 0. 정량 baseline (실 측정)

### BE pytest

`cd backend && uv run pytest -q --tb=no` → **490 passed / 1 skipped / 1501 warnings (83.66s)**.

- Sprint 27e Round 1 baseline (482 PASS) → +8 신규 PASS (Round 2 PR #110 cutover hardening + PR #111 QA dynamic verify fix 회귀 가드 +6 + 기타 +2).
- 1 skip = pre-existing (transcription ffmpeg mock).
- 회귀 0건.

### FE vitest

`cd frontend && pnpm test` → **56 passed (6 files, 1.70s)**.

- Sprint 27e Round 1 baseline 동일 (변경 0).

### FE typecheck + build (Round A 정적 검증 추정 — 본 round B 가 실 빌드)

- vitest 통과 = TypeScript syntax OK
- Sprint 27e Round 2 의 tiptap dep fix (`@tiptap/* 3.23.6`) 후 build PASS 라고 가정 (`gh run list` 결과 main 가지 15/15 success → CI build PASS verified).

### e2e spec inventory

`frontend/e2e/tests/` 22 spec:
1. actions-redirect / auth / auth-relogin / first-project / home / inbox-dismiss
2. invite-page-regression / meeting-export / meeting-upload / mobile-responsive / note-detail
3. onboarding-tooltip-first-visit / projects-list / rag-citation / record-state-machine
4. security-headers / settings-audit / workspace-switch
5. QA: qa-extract-credentials / qa-regression / qa-sentinel-p0 / qa-sentinel-p1-token

### CI flake rate (main 가지, 최근 15 run)

`gh run list --workflow=test.yml --branch=main --limit=15` → **15/15 success (flake rate 0%)**.

- Sprint 27e Round 2 BL-S27e-4 재분류 (flake 가설 false → tiptap dep + Nightly GEMINI_API_KEY) 의 검증. 본 sprint 시점 main 가지 flake 0건 confirm.

### CI 게이트 활성 상태

`gh variable list` → **E2E_ENABLED=true** (2026-05-13 설정).
`.github/workflows/test.yml`:
- `backend-test` job: `uv sync` + `pytest --ignore=tests/services/test_transcription.py --ignore=tests/test_r2_cors_regression.py -v` (line 22-36). **`--frozen` 미사용** (Round A Security BUG-S28-SEC-1 의 진짜 발현 지점).
- `frontend-build` job: `pnpm install --frozen-lockfile` + `pnpm test` + `pnpm build` + **`security-headers.spec.ts` 단독 실행 (line 73-106, 항상 실행, secrets 불요)** ✅ — Sprint 27e Round 2 TEST-r2-1 fix RESOLVED-verified.
- `e2e` job: `if: vars.E2E_ENABLED == 'true'` (line 122) — 활성. Postgres + pgvector + backend uvicorn + Next.js + Playwright 전체 e2e 실행.

→ **CI 게이트 운영화 PASS** (Round 2 carry 모두 해소 + e2e 22 spec 실 CI 실행 중).

---

## 1. Sprint 27 carry list 자기 영역 verify

| ID | Sprint 27 분류 | Sprint 28 검증 file:line | severity | 결과 |
|---|---|---|:-:|---|
| **TEST-1** | P0 차단 fix (PR #109) — 보안 헤더 회귀 가드 | `backend/tests/test_security_hardening.py::TestSecurityHeadersRegression` 2 PASS + `frontend/e2e/tests/security-headers.spec.ts` 49 line CI 활성 (`test.yml:73-106`) | 안전 | ✅ **RESOLVED + CI gate 활성** |
| **TEST-2** | P0 차단 fix (PR #109) — lazy seed concurrent race | `backend/tests/auth/test_personal_workspace_race_concurrent.py` 2 PASS (testcontainers N=5/10) | 안전 | ✅ **RESOLVED** |
| **TEST-r2-1** | P1 conditional (PR #110) — FE CI 게이트 | `test.yml:73-106` security-headers.spec.ts 단독 실행 step. E2E_ENABLED 무관 항상 실행 | 안전 | ✅ **RESOLVED-verified** |
| **TEST-r2-2** | INFO (Round 2 errata) — FE 병렬 E2E flake 재분류 | 본 sprint 측정 main 가지 15/15 success (flake 0%). tiptap dep fix 2195c8b 적용 + Nightly key 는 사용자 task | 안전 | ✅ **재분류 정합 verified** |
| **TEST-5** | P1 carry — invite accept happy-path e2e | `frontend/e2e/tests/invite-page-regression.spec.ts` 68 lines — ISSUE-008 회귀 (Next.js error page + QueryClient mount) 만. **owner 발급 → user 수락 → role 부여 → cross-workspace switch 흐름 0 cover.** spec 신설 필요 | **보통** | ❌ **carry 유지 — 본 sprint 안 신설 권고** (1.5h) |
| **TEST-7** | P1 carry — upload mime real browser e2e | `frontend/e2e/tests/meeting-upload.spec.ts` 53 lines — STT 처리 완료 + 요약 렌더링 만. **proxy 경로 + 위장 .exe 거부 흐름 미 cover**. BE 단위 `backend/tests/upload/test_upload_validation.py` 는 9 case 존재 (mime + magic + 한도) — unit OK but **real browser proxy path 미검증** | **보통** | ❌ **carry 유지 — 본 sprint 안 신설 권고** (1h) |
| **TEST-3** | P1 carry — vitest.config coverage.include | `frontend/vitest.config.ts` 미 read 검증 — `coverage.include` 미설정 추정 (Round 1 측정 정합) | 안전 | ❌ carry (BL-S27e-E) |
| **TEST-4** | P1 carry — workspaces branch 4% | invite_service / member role branch coverage 부족 | 안전 | ❌ carry (BL-S27e-E) |
| **TEST-6** | P1 carry — 회의 retry e2e (M-3) | `frontend/e2e/tests/` 22 spec 중 `meeting-retry` 0 hit | 안전 | ❌ carry (BL-S27e-E) |
| **TEST-8/9/10** | P2 carry — 에지 unit | 큰 입력 / 유니코드 / Personal+Team 동시 통합 | 안전 | ❌ carry (BL-S27e-E) |

**carry verify summary**:
- 해소 = 4건 (TEST-1, TEST-2, TEST-r2-1, TEST-r2-2)
- 잔존 = 6건 (TEST-3, TEST-4, TEST-5, TEST-6, TEST-7, TEST-8/9/10)
- **본 sprint 안 처리 필수 = TEST-5 (1.5h) + TEST-7 (1h)** — 사용자 결정 (b) carry 범위 명시

---

## 2. 신규 발견 매트릭스 (Round 1/2 blind spot)

| ID | 영역 | severity | 차단 | file:line | 발견 | 권장 fix |
|---|---|:-:|:-:|---|---|---|
| **BUG-S28-TEST-1** | mutation test 도구 부재 | **보통** | NO | `backend/pyproject.toml` + `frontend/package.json` | Sprint 27e Round 2 가 main.py:103 X-Frame-Options 1줄 주석 수동 mutation (`100% kill`) 만 측정. **자동화 도구 (`mutmut` / `cosmic-ray` Python, `stryker` JS) 미설치**. 본 sprint 의 main.txt §"audit pattern 진화" 명시한 "mutation 3건" 측정에 사용할 도구 부재. 수동 시연만 가능 = sprint 마다 측정 부담 + 회귀 catch 불가능 | (a) `mutmut` 단순 도입 (`uv add mutmut --dev`), (b) backend critical path 3건 mutation 적용 (보안 헤더 / config validator / lazy seed fast path), (c) CI step 추가 (선택) |
| **BUG-S28-TEST-2** | dashboard fast path 회귀 가드 | **보통** | NO | `backend/tests/auth/test_get_current_user_fast_path.py:1-100` | PR #111 fast path fix 의 회귀 가드 2 PASS but **dashboard fanout 의 hidden 2s cost (Round B 측정)** 회귀 가드 없음. fast path 외 root cause 가 발견 시 다른 회귀 가드 필요 (find_by_clerk_id query plan 회귀, connection pool 부족 회귀 등) | mutation 권고 = `auth/dependencies.py:185` `>= 1` 을 `>= 999` 또는 `>= 0` 으로 mutation → fast path test 가 fail/pass 차이 catch verify |
| **BUG-S28-TEST-3** | TEST-5 invite accept happy-path 갭 | **보통** | NO (carry) | `frontend/e2e/tests/invite-accept-*.spec.ts` 부재 | Sprint 27e Round 1 TEST-5 carry 항목 — 본 sprint 안 신설 권고 (사용자 carry 범위 b 명시). owner 발급 → user 수락 → role 부여 → cross-workspace switch. ~1.5h | spec 신설: `frontend/e2e/tests/invite-accept-happy-path.spec.ts` (또는 invite-page-regression.spec.ts 확장) — `WorkspaceInvite.code` 발급 → 다른 user 가입 → role 확인 |
| **BUG-S28-TEST-4** | TEST-7 upload mime real browser 갭 | **보통** | NO (carry) | `frontend/e2e/tests/upload-mime-*.spec.ts` 부재 | Sprint 27e Round 1 TEST-7 carry — BE unit cover OK but FE proxy + 위장 .exe 차단 real browser 흐름 미 cover. ~1h | spec 신설: `frontend/e2e/tests/upload-mime-validation.spec.ts` — proxy 경로 + 위장 audio/.exe 업로드 → 422 거부 |
| **BUG-S28-TEST-5** | e2e CI gate 안 보안 헤더만 활성 | 안전 | NO | `.github/workflows/test.yml:73-106` | `frontend-build` job 의 e2e 단독 실행 step 은 `security-headers.spec.ts` 만 (public route only). 나머지 21 spec 은 `e2e` job 에 묶임 (`E2E_ENABLED=true` 활성). 이중 게이트 — frontend-build 가 unit + build + 보안 헤더, e2e 가 full e2e. 운영 OK | 현 구조 유지. 단 `security-headers` 가 `frontend-build` 안 inline 이라 PR 마다 항상 실행 → 빠른 회귀 catch |
| **BUG-S28-TEST-6** | BE pytest warnings 1501건 | 안전 | NO | `cd backend && uv run pytest` 출력 | 1501 warnings — 대부분 `session.execute → session.exec` deprecation (SQLModel 0.1.4 권고). Sprint 20 BL-054 cleanup 후에도 잔재 — typed exec 가 G3-keep-dialect 패턴에서 사용 안 함 (G1/G2 only). 본 sprint 영향 0, governance 항목 | warning filter 정렬 후 `filterwarnings = ["ignore::sqlmodel.exec.deprecated"]` 또는 `pytest.ini` 추가 권고 — sprint deepening 시 |
| **BUG-S28-TEST-7** | architecture test gate 1건만 | **보통** | NO | `backend/tests/architecture/` | S28-ARCH-5 와 정합 — I-1 (service AsyncSession) / ADR-014 (service.py cross-import) / common 역의존 (ARCH-3) / Demeter (self.<repo>.session) 회귀 가드 부재. 본 sprint BL-S27e-F 진입 *전* lock-in 권고 | architecture test 4건 추가 (S28-ARCH-5 fix 와 동일) |
| **BUG-S28-TEST-8** | Personal/Team 동시 운영 통합 e2e | 안전 | NO | TEST-10 carry | 22 spec 중 workspace-switch.spec.ts 가 일부 cover 하나 Personal + Team 격리 누출 시나리오 0 | BL-S27e-E carry — sprint deepening |

---

## 3. 차단 결함 상세

**차단 결함 = 0건**. 본 audit 의 모든 발견은 비차단 (보통 / 안전).

외부 5명 dogfooding 진입 차단 = **NO** (TEST-1/2 + TEST-r2-1 모두 RESOLVED, CI 게이트 활성).

본 sprint 안 처리 필수 (사용자 carry 범위 b):
- **TEST-5 invite accept happy-path e2e** (1.5h) — Team workspace 외부 진입 happy-path 회귀 가드
- **TEST-7 upload mime real browser e2e** (1h) — proxy 경로 + 위장 .exe 거부 회귀 가드

---

## 4. 비차단 carry

### 4.1 Sprint 27 carry (BL-S27e-E cluster)

| ID | 묶음 | 비용 |
|---|---|:-:|
| TEST-3 | vitest.config coverage.include | 30분 |
| TEST-4 | workspaces branch | 1h |
| TEST-6 | 회의 retry e2e | 1.5h |
| TEST-8/9/10 | 에지 unit (큰 입력 / 유니코드 / Personal+Team 통합) | 2-3h |

### 4.2 Sprint 28 신규 carry (BL-S28-TEST-*)

| ID | 묶음 |
|---|---|
| BUG-S28-TEST-1 | mutation 도구 표준화 (mutmut 도입) |
| BUG-S28-TEST-6 | pytest warning filter |
| BUG-S28-TEST-7 | architecture test gate 4건 (S28-ARCH-5 와 동일 — 본 sprint 안 권고) |
| BUG-S28-TEST-8 | Personal/Team 통합 e2e |

---

## 5. mutation test baseline (수동 시연)

main.txt 명시 "mutation 3건" 측정 — 본 Round A 가 baseline.

| ID | 대상 | baseline | 측정 방법 |
|---|---|---|---|
| MUT-1 (보안 헤더) | `main.py:103` `X-Frame-Options: DENY` → `X-Frame-Options-MUTATED` | Sprint 27e Round 2 100% kill verified | `tests/test_security_hardening.py::TestSecurityHeadersRegression` 2/2 FAIL catch |
| MUT-2 (config validator) | `core/config.py:91-98` `_no_dev_issuer_in_non_dev` validator `not_creative-boxer-79` mutation | Round 2 verify (PR #110) 정상 | `tests/test_config.py` 4 PASS / mutation 시 fail |
| MUT-3 (lazy seed fast path) | `auth/dependencies.py:185` `user.onboarding_step >= 1` → `>= 999` 또는 `>= 0` | 신규 — 본 sprint baseline | `tests/auth/test_get_current_user_fast_path.py` 2 PASS / mutation 시 fail expected |

**Step 4 fix 후 의무**: 모든 fix 의 회귀 가드는 mutation 100% kill rate verify. 본 round 는 baseline 만, Step 4 fix 적용 시 즉시 verify.

---

## 6. Summary

### 6.1 정량

| 항목 | 결과 |
|---|---|
| BE pytest | **490 PASS / 1 skip / 0 fail** (83.66s) |
| FE vitest | **56 PASS / 0 fail** (1.70s) |
| e2e spec | **22 spec** (security-headers 항상 + 21 spec E2E_ENABLED 활성) |
| main 가지 CI flake rate (15 run) | **0% (15/15 success)** |
| Sprint 27 carry 해소 | **4/10** (TEST-1/2 + r2-1/r2-2) |
| Sprint 27 carry 잔존 | **6** (TEST-3/4/5/6/7/8/9/10 묶음) |
| Sprint 28 신규 발견 | **8건** (BUG-S28-TEST-1~8) |
| 차단 결함 | **0건** |

### 6.2 본 sprint 안 처리 권고 (사용자 carry 범위 b)

1. **TEST-5 invite accept happy-path e2e** (1.5h, **보통**) — Team workspace 외부 진입 happy-path
2. **TEST-7 upload mime real browser e2e** (1h, **보통**) — proxy 경로 + 위장 .exe
3. **BUG-S28-TEST-7 (S28-ARCH-5)** architecture test gate 4건 (1h, **보통**) — BL-S27e-F 진입 전 회귀 가드 lock-in

### 6.3 외부 5명 dogfooding 진입 verdict (Test-Coverage only)

| 분기 | 판정 |
|---|---|
| **외부 5명 dogfooding 진입 (current main `3e41893`)** | **GO** — 차단 0건, BE+FE+e2e 회귀 가드 PASS, CI flake 0% |
| **본 sprint TEST-5/7 fix 적용 후** | **GO+** — Team workspace + upload mime 회귀 가드 회복 |

### 6.4 Round B 인계 (dynamic verify)

- mutation test 3건 실 적용 (MUT-1/2/3) — Step 4 fix 후 100% kill 검증
- e2e spec 실 실행 (CI 안 + 로컬) — TEST-5/7 신설 spec 의 실 PASS 확인
- coverage 정량 baseline (BE pytest --cov / FE vitest --coverage) — Sprint 27 cited 65.69%/41.08%/6% 정합 검증

---

*검사자: Test-Coverage Static Audit (Round A, 본 main agent, sequential)*
*baseline: `3e41893` · branch `sprint-28/dogfooding-stabilize`*
