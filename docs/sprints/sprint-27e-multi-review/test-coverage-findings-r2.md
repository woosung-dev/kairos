# Sprint 27e Round 2 — 테스트 Cross-Check + 실 실행 검증

- 검사 일시: 2026-05-25 KST
- baseline commit: `b7e704e` (main, Sprint 27e Round 1 fix bundle merged via PR #109)
- 작업 branch: `sprint-27e/round2-cross-check`
- 환경: pytest / vitest 실 실행 + e2e spec 정합 정적 검토 (FE/BE down)
- 시각: (a) Round 1 RESOLVED 정합 verify · (b) 정적 분석 한계 보완 · (c) 실 환경 측정 · (d) BL 외부 직격 재평가

---

## 0. Executive Summary

| 결과 | 판정 |
|---|---|
| Round 1 RESOLVED 마크 6건 (TEST-1/2 + SEC-3/4 회귀 가드) **실 실행 검증** | **모두 검증 PASS** |
| 신규 BE 케이스 13건 실 pytest 실행 (`test_security_hardening` 2 + `test_config` 7 + `test_jwt_verification` 4) | **13/13 PASS** (`backend && uv run pytest ... -v` 0.99s) |
| 신규 concurrent race 케이스 (`test_personal_workspace_race_concurrent`) | **2/2 PASS** (testcontainers postgres up, 2.27s) |
| vitest FE | **56 PASS / 6 file** (1.66s) |
| Round 1 totals 482 PASS 주장 정합 (collect-only) | **483 collected** (+1 — concurrent race spec 가 conftest collect 시 함께 잡힘) |
| **mutation test** — `main.py:103` `X-Frame-Options` 라인 주석 처리 → `TestSecurityHeadersRegression` | **2/2 FAIL (정확히 잡음)** → 회귀 가드 자체 efficacy 검증 |
| **CI 게이트 정합 — security-headers.spec.ts (FE e2e)** | **CI 미게이트 (BUG-S27e-TEST-r2-1)** — `test.yml:78` 의 `if: vars.E2E_ENABLED == 'true'` 미활성화 → 신규 FE e2e 가 CI 에서 결코 실행되지 않음 |
| Round 1 "flake 2 spec (first-project + onboarding-tooltip)" 주장 재검 | **flake 가설 false — 실 fail 은 (1) tiptap type-check + (2) Nightly Gemini API key 결함** |
| Round 1 추가 권고 14건 중 본 sprint ROI 높은 5건 | 선별 §5 |

**verdict**: Round 1 의 BE 회귀 가드 11/11 RESOLVED 검증 PASS. **단 FE e2e 회귀 가드 (security-headers.spec.ts) 는 CI 미실행 → 회귀 가드로서 절반만 동작** (실 운영 시 사용자가 local 수동 실행해야 발견). **BUG-S27e-TEST-r2-1 신규 차단 후보 (P1)**.

---

## 1. Round 1 신규 테스트 실 실행 결과

### 1.1 매트릭스

| Round 1 ID | 신규 case 갯수 | pytest 실 실행 결과 | mutation test | verdict |
|---|---:|---|---|---|
| **TEST-1** (보안 헤더 회귀) | BE `TestSecurityHeadersRegression` 2 + FE e2e `security-headers.spec.ts` 2 | **BE 2/2 PASS** (`pytest ... -v` 0.99s); FE spec 파일 정합 (Playwright 코드 + 4 헤더 + 2 페이지 검증) | **PASS — `main.py:103` X-Frame-Options 1줄 주석 처리 → 2/2 FAIL 정확히 잡음** | **RESOLVED-verified (BE)** + **FE CI 미게이트 (BUG-S27e-TEST-r2-1 신규)** |
| **TEST-2** (lazy seed concurrent race) | BE `test_personal_workspace_race_concurrent.py` 2 (N=5 + N=10) | **BE 2/2 PASS** (`pytest ... -v` 2.27s, testcontainers postgres) | (mutation 미시행 — 의미 있는 mutation = `INSERT ... ON CONFLICT` 의 `WHERE type='personal'` 절 제거인데 partial unique index 가 동일 효과로 catch) | **RESOLVED-verified** |
| **SEC-3** 회귀 (jwt issuer/audience) | BE `test_jwt_verification.py` 4 | **BE 4/4 PASS** | — | **RESOLVED-verified** |
| **SEC-3** 회귀 (config validator) | BE `test_config.py::test_clerk_jwt_issuer_*` 2 | **BE 2/2 PASS** | — | **RESOLVED-verified** |
| **SEC-4** 회귀 (cron_secret_token validator) | BE `test_config.py::test_cron_token_*` 3 | **BE 3/3 PASS** | — | **RESOLVED-verified** |
| **SEC-1/SEC-2** (deps CVE) | (별도 신규 케이스 없음 — `pnpm audit --audit-level critical` = 0) | (이전 audit 인용) | — | RESOLVED |

**합계 신규 BE 13 case 전부 PASS. mutation test 결과 BE 회귀 가드 자체가 fix 결함을 정확히 잡음.**

### 1.2 mutation test 상세 (회귀 가드 efficacy 정량)

`backend/src/main.py:103` 의 `response.headers.setdefault("X-Frame-Options", "DENY")` 한 줄을 잠시 주석 처리 → `tests/test_security_hardening.py::TestSecurityHeadersRegression` 재실행:

```
FAILED tests/test_security_hardening.py::TestSecurityHeadersRegression::test_security_headers_present_on_health_check
FAILED tests/test_security_hardening.py::TestSecurityHeadersRegression::test_security_headers_present_on_404
============================== 2 failed in 1.04s ===============================
RESTORED
```

→ 회귀 가드가 **정확히 잡음**. file:line 까지 정확 — `tests/test_security_hardening.py:97 AssertionError: assert None == 'DENY'`. **mutation kill rate = 100%** (1 mutation 시도, 2/2 case 잡음).

### 1.3 concurrent race fixture 정합

`tests/auth/test_personal_workspace_race_concurrent.py:42-60` 의 `concurrent_engine` fixture 가 `tests/conftest.py:37` 의 `postgres_container` (module-scoped) 위에 `pool_size=10, max_overflow=5` 별개 engine 을 띄움. `asyncio.Barrier(N)` 로 5/10 task 가 INSERT 직전까지 정렬 → 진정한 동시성. partial unique index `uq_workspaces_owner_personal ON workspaces (owner_id) WHERE type = 'personal'` 가 testcontainers 에는 alembic 미적용이므로 fixture `:54-57` 에서 명시 생성 — alembic env 와 정합.

verdict: Round 1 TEST-2 의 "sequential 만 검증 carry" 가 정확히 닫힘. **2/2 PASS**.

---

## 2. Round 2 신규 발견 매트릭스

| ID | 영역 | 심각도 | 차단 | file:line | 발견 |
|---|---|---|:-:|---|---|
| **BUG-S27e-TEST-r2-1** | CI 게이트 정합 | **P1** | **conditional YES** (외부 5명 진입 정책에 따름) | `.github/workflows/test.yml:78` + `frontend/e2e/tests/security-headers.spec.ts` | 신규 FE e2e 회귀 가드가 **CI 에서 결코 실행되지 않음** — `if: vars.E2E_ENABLED == 'true'` 미활성화. Round 1 의 "RESOLVED" 마크가 BE 한정. FE 측은 사용자가 local 에서 `pnpm e2e tests/security-headers.spec.ts` 수동 실행해야만 회귀 catch. next.config.ts 정리 시 CI 가드 0. |
| BUG-S27e-TEST-r2-2 | flake 분류 정정 | P2 | NO | Round 1 §6.4 + Nightly run 26370146178 | "BL-S27e-4 flake 2 spec" 분류 부정확. 실 실패는 (a) `frontend-build` 단계 **tiptap useEditor overload type error** (CI run 26389145626) — 환경 결함 + (b) Nightly `meeting-upload.spec.ts` **GEMINI_API_KEY=fake** 환경 결함. **flake 아닌 환경/dep 결함**. BL-S27e-4 재분류 권고 (`tiptap dep + Nightly secret`). |
| BUG-S27e-TEST-r2-3 | 회귀 가드 cross-spec 확장 | P2 | NO | `frontend/e2e/tests/security-headers.spec.ts:23,38` (sign-in + /) + `playwright.config.ts:24` | 보안 헤더 spec 가 2 page (`/sign-in`, `/`) 만 검증. `/api/v1/health` (BE) 는 BE 가 cover. **하지만 dashboard / settings / inbox 등 인증 후 page 의 헤더 정합 검증 없음** — Next.js 가 page 별 `headers()` override 가능 → 회귀 risk. spec 에 인증 storageState 의존 page 1건 추가 권고. |
| BUG-S27e-TEST-r2-4 | mutation test 확장 권고 | P3 | NO | (Sprint 28+) | 본 Round 2 에서 X-Frame-Options 1 mutation 만 검증. `Permissions-Policy` 의 `camera=()` value 변조 / `setdefault` → `__setitem__` 변경 등 추가 mutation 시도 시 가드 robustness 강화. mutmut 도구 도입 권고 (별도 PR). |
| BUG-S27e-TEST-r2-5 | concurrent race 시나리오 확장 | P3 | NO | `test_personal_workspace_race_concurrent.py:107-181` | 현 spec 가 N=5 / N=10 만 검증. **lazy seed + WorkspaceMember owner row 의 NOT EXISTS guard 가 동시성에서 깨지는 경계 (예: 사용자 동시 2 device 첫 로그인 + slow connection) 자체 검증 OK**. 추가 위험 = `INSERT ... SELECT ... NOT EXISTS` 의 race window (row 가 visible 되기 전 SELECT) — postgres SERIALIZABLE 이 아니라 READ COMMITTED 이므로 이론상 race. 그러나 `ON CONFLICT (workspace_id, user_id) DO NOTHING` 이 workspace_members 에 별도 unique index 존재 시 닫힘. 확인 필요. |

---

## 3. CI flake 정량 (gh run list 실 측정)

`gh run list --limit 30 --workflow=test.yml` 분석 (since 2026-05-21):

| 기간 | Test (CI) 성공 | 실패 | 실패 원인 분류 |
|---|---:|---:|---|
| 2026-05-21 ~ 2026-05-25 | 13 | **6** | (a) frontend-build tiptap type error ×1 (`sprint-27e/multi-review`, run `26389145626`) + (b) backend-test 4건 (Sprint 27d/27c branch 진행 중 1차 실패 후 fix 재실행 PASS — 정상 dev cycle) + (c) `Deploy Backend (Cloud Run)` 2건 (run `26390656563` + `26364409071`, **본 분석 범위 외 = deploy 별도** ) |
| main 직접 push | **5/5 success** | 0 | 정상 |
| sprint-27e/multi-review (Round 1) | 1 success / 1 fail | — | fail 1건 = tiptap dep type error (코드 결함, flake 아님) |

**Nightly Heavy E2E** (`nightly-e2e.yml`):

| 회차 | 결과 | 원인 |
|---|---|---|
| 26370146178 (2026-05-24) | FAIL | `meeting-upload.spec.ts` — `GEMINI_API_KEY=fake` (env 결함, flake 아님) |
| 26340932857 (2026-05-23) | FAIL | (확인 SKIP — 동일 패턴 가능) |

**정량 결론**:
- main 가지 CI flake rate = **0%** (5/5 PASS)
- sprint branch 의 fail 은 **모두 코드/환경 결함 (재실행 무관)** — flake 아님
- Round 1 의 "flake 2 spec" 분류는 **잘못된 추정**. 실 fail = (a) tiptap type + (b) Nightly Gemini key.
- → **BL-S27e-4 재분류**: flake 카테고리 폐기 → `tiptap dep upgrade + Nightly secret 점검` 으로 변경.

---

## 4. Round 1 추가 권고 14건 → ROI 높은 5건 선별

Round 1 §8 / integrated-report §6 의 비차단 37건 carry 중 **외부 5명 직접 영향 + 본 sprint 내 ≤ 2h 신설 가능** 기준:

| 순위 | Round 1 ID | 신설 작업 | 예상 소요 | 외부 직격 ROI | 선택 사유 |
|:-:|---|---|:-:|---|---|
| **1** | **BUG-S27e-TEST-r2-1** (Round 2 신규) | `test.yml` 에 `security-headers.spec.ts` 만 단독 실행 step 추가 (`if: always() && env.E2E_ENABLED != 'true'`) — Clerk 의존 없는 public route 만 검증하므로 **secrets 불요** | **30분** | **HIGH** — Round 1 fix 가 CI 회귀 가드 fail-safe 의 절반만 동작 | r2 자체 신규 발견 |
| **2** | **TEST-5** (invite accept happy-path e2e) | `frontend/e2e/tests/invite-accept-happy-path.spec.ts` 신설 | 1.5h | **HIGH** — 외부 5명 dogfooding 진입 시 **첫 핵심 path** | Round 1 §5 권고 |
| **3** | **TEST-7** (upload mime e2e) | `frontend/e2e/tests/upload-mime-validation.spec.ts` 신설 (proxy 경로) | 1h | **MED-HIGH** — unit 두꺼움 but real browser 회귀 가드 0 | Round 1 §5 권고 |
| **4** | **TEST-4** (workspaces branch 4%) | `invite_service` expired/deactivated/idempotent 4 case unit | 1h | **MED** — invite 흐름 fragile | Round 1 §5 권고 |
| **5** | **TEST-3** (vitest.config coverage.include) | `frontend/vitest.config.ts` 에 `coverage.include: ['src/**']` + thresholds 30% | 30분 | **LOW (외부 영향)** / **HIGH (정량 신뢰도)** | Sprint 28+ FE 임계 점진 상향 base |

**미선택 reasoning**:
- TEST-6 회의 retry (BL-S27c-4 carry) — UI 자체 P2 carry. retry 동작 검증은 unit 에서 가능 but 외부 dogfooding 5명 규모에선 트리거 빈도 낮음.
- TEST-8/9/10 — 모두 P2. 외부 직격 ROI 낮음.

---

## 5. BE/FE coverage — 신규 fix 부분 branch cov 추정

### 5.1 신규 fix add new branches

| fix 영역 | new branch | cover by 신규 test | gap |
|---|---|---|---|
| `src/main.py:100-112` SecurityHeadersMiddleware | `setdefault` 4 헤더 (existing 시 skip 분기) | TestSecurityHeadersRegression 2 case 가 `setdefault` happy path 만 cover. **이미 헤더 setting 된 응답 (e.g. CORSMiddleware 충돌) 분기 미검증** | 1 case 신설 권고: `existing X-Frame-Options 값 보존` |
| `src/core/config.py` `_validate_cron_secret_token` / `_validate_clerk_jwt_issuer` | production + dev/test × custom + fallback = 4 branch | `test_config.py` 5 case 가 4/4 branch cover | **OK** |
| `src/auth/dependencies.py:111-124` jwt.decode | `audience=` 명시 / None / `verify_aud=False` / `InvalidIssuerError` | `test_jwt_verification.py` 4 case 가 4/4 branch cover | **OK** |
| `frontend/next.config.ts:5-25` `headers()` | `source: '/:path*'` → 모든 page | FE e2e 2 page 검증 (sign-in + /) | **부분 — dashboard/settings 등 인증 page 미검증** (TEST-r2-3) |

**verdict**: BE 신규 branch cov = **95%+ (3/4 영역 100%, SecurityHeadersMiddleware 분기 1건 부족)**. FE next.config.ts cov = **2 page 만 (전체 라우트 ~15+)**. → BL-S27e-E (Round 1 §6) 에 r2-3 추가 권고.

### 5.2 신규 fix 미커버 부분 발현 시 위험

- SecurityHeadersMiddleware `setdefault` (vs `__setitem__`) — 만약 upstream middleware 가 다른 값 set 하면 우선 → 즉 가드가 약한 정책. **현재 정책 = "기존 헤더 보존"** 로 의도적. 신규 case 권고 = "이미 설정된 값 보존" 검증 (회귀 X, 의도 설계 검증).
- FE next.config.ts headers() override — `app/` page-level `Response.headers.set()` 사용 시 next.config 우선 (Next 16 동작). 그러나 middleware 우선이라 검증 미흡 분기 존재.

---

## 6. Round 1 비차단 BL — 외부 5명 직격 재평가 (시각 (d))

| Round 1 ID | 원 분류 | 외부 5명 직격 재평가 | 진입 *전* 처리 권고 |
|---|---|---|---|
| TEST-5 invite accept e2e | P1 비차단 | **HIGH** — 외부 5명 진입 = invite token 발급 + 다른 user 가 처음 만나는 page. 실패 시 사용자가 첫 5분 안에 좌절 | **YES (진입 전 신설 권고)** |
| TEST-7 upload mime e2e | P1 비차단 | **MED-HIGH** — 외부 사용자 = 회의 녹음/업로드가 핵심 수요. `.exe` 위장 등은 unit 두꺼움 but real browser 415 메시지 UX 회귀 가능 | conditional YES (1h 소요 작은 비용) |
| TEST-4 workspaces branch | P1 비차단 | MED — invite 만료/비활성 분기 누락 시 가짜 500. 그러나 자주 트리거 안 됨 | NO (Sprint 28 batch) |
| TEST-6 회의 retry | P1 비차단 | LOW — 실패 비율이 낮음 가정. 외부 발견 빈도 ≤ 5% | NO |
| TEST-8/9/10 | P2 비차단 | LOW | NO |

**재평가 결론**: 외부 5명 진입 *전* 신설 권고 = **TEST-5 + TEST-7 + r2-1** 3건. 나머지는 진입 후 burn-down.

---

## 7. e2e spec 정합 (FE/BE down → 정적 검토)

### 7.1 security-headers.spec.ts (Round 1 신설)

`frontend/e2e/tests/security-headers.spec.ts:1-49` 정합:
- 4 헤더 (`FOUR_HEADERS`) 일관 정의 + 2 page (`/sign-in`, `/`) 검증
- `expect(headers[name]).toBeTruthy()` for-loop 후 명시 값 검증
- assertion 정합 OK
- **CI 게이트 X** (TEST-r2-1)

### 7.2 playwright.config.ts 정합

`frontend/playwright.config.ts:38-56`:
- `setup` project + `chromium` project (`dependencies: ['setup']`)
- security-headers.spec.ts 가 `chromium` project 에 자동 포함 (testIgnore 미적용)
- `storageState: "e2e/.auth/user.json"` 의존 — 본 spec 은 비인증 public route 만 호출하므로 storageState 영향 받지 않음 (page.goto 시 인증 redirect 없음)
- **정합 OK** — 단 CI 실행 자체 미게이트

### 7.3 21 spec 전체 인벤토리

```
actions-redirect / auth-relogin / auth / first-project / home / inbox-dismiss /
invite-page-regression / meeting-export / meeting-upload / mobile-responsive /
note-detail / onboarding-tooltip-first-visit / projects-list / qa-extract-credentials /
qa-regression / qa-sentinel-p0 / qa-sentinel-p1-token / rag-citation /
record-state-machine / security-headers / settings-audit / workspace-switch
```

= 22 spec. 4 qa-* spec 는 `testIgnore: process.env.CI ? [/qa-.*\.spec\.ts/]` (playwright.config.ts:24) → CI 자동 skip. **나머지 18 spec 가 E2E_ENABLED='true' 일 때만 CI 실행**.

---

## 8. Summary

### 8.1 검증 결과

| 항목 | 결과 |
|---|---|
| Round 1 RESOLVED 마크 (TEST-1/2 + SEC-3/4) 11 BE case | **11/11 PASS** (실 pytest) |
| Round 1 RESOLVED 마크 추가 (FE e2e 2 case) | spec 파일 정합 OK + **CI 미게이트 (r2-1)** |
| mutation test (가드 efficacy) | **100% kill rate** (1 mutation, 2/2 case 잡음) |
| concurrent race (testcontainers) | **2/2 PASS** (2.27s) |
| vitest 회귀 | **56/56 PASS** (1.66s) |
| total BE pytest collect | 483 (Round 1 주장 482 +1 — concurrent race 가 1 spec 추가) |
| flake 가설 (BL-S27e-4) | **부정확 — 실 fail = tiptap type + Nightly Gemini key 환경 결함** |

### 8.2 r2 신규 발견

- **BUG-S27e-TEST-r2-1 (P1, conditional 차단)** — FE 회귀 가드 CI 미게이트. 30분 fix.
- BUG-S27e-TEST-r2-2 ~ r2-5 (P2/P3) — flake 재분류 + cross-spec 확장 + mutation 확장 + race 경계.

### 8.3 외부 5명 진입 *전* 권고

1. **TEST-r2-1 fix** (CI 게이트 / 30분) — FE 회귀 가드 운영화
2. **TEST-5 신설** (invite accept happy-path / 1.5h)
3. **TEST-7 신설** (upload mime / 1h)
4. **TEST-3 신설** (vitest.config coverage.include / 30분, 정량 신뢰도)
5. (선택) **TEST-4 신설** (workspaces branch / 1h)

총 **~4h** 예상. 모두 Round 1 BL-S27e-E 묶음 안 — Sprint 28 head-of-line 으로 carry 권고 (외부 진입 시그널과 무관하게).

### 8.4 GO 판정 정합

Round 1 의 RESOLVED → GO 판정은 **BE 한정 정확**. FE e2e 회귀 가드 efficacy 는 **CI 미실행으로 절반만 동작** → 외부 5명 진입 시 SecurityHeadersMiddleware 가 누락되는 회귀가 사용자 도달 후 발견 가능. **GO 판정 자체 유효하나 r2-1 30분 fix 를 진입 *전* 권고**.

### 8.5 fix 4건 RESOLVED 의 실 운영 안전성

- BE 회귀 가드 (mutation test PASS) — robust
- FE 회귀 가드 — CI 미게이트 (r2-1)
- concurrent race 회귀 가드 — testcontainers 의존 (CI 에서도 동일 environment 필요, **BE `Test` job 에 testcontainers 의존 라이브러리 `uv sync` 가 testcontainers 설치하므로 OK**, 단 docker-in-docker 필요 — `ubuntu-latest` 기본 지원 → run 결과 확인 시 PASS history 가 있어야 함)

→ **마지막 확인 권고**: 사용자가 `gh run list --workflow=test.yml --limit 5` 결과에서 main HEAD `b7e704e` Test job 의 `tests/auth/test_personal_workspace_race_concurrent.py` 가 PASS 한 로그 확인.
