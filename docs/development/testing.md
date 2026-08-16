# 테스트 가이드

## 0. 전제 — CI 가 죽어 있다

GitHub Actions 가 **결제 실패로 전면 중단** 상태다 (`docs/TODO.md` Blocked 최우선 항목).
워크플로가 시작조차 못 하고 `changes` job 이 4~8초 만에 실패하며 나머지가 전부 skip 된다.

> **그래서 로컬 게이트 출력이 유일한 머지 증거다.** PR body 에 붙인다 (`.github/PULL_REQUEST_TEMPLATE.md`).

## 1. 한 방에

```bash
just ci-local
```

`.github/workflows/test.yml` 의 `backend-test` + `frontend-build` + `contract-check` job 을
로컬에서 미러한다. **새 명령을 정의하지 않고 기존 recipe 를 조합만 한다** — ADR-027 D3 의
"로컬 게이트와 CI 게이트는 문자 그대로 같은 명령" 불변을 지키기 위해서다.

- 실패가 환경 문제로 의심되면 `just install` 을 먼저 돌린다.
- **clean tree 에서 실행한다.** `contracts-check` 는 `git diff --exit-code` 라 작업 트리가
  더러우면 계약과 무관한 변경까지 drift 로 잡는다(오탐).

## 2. 게이트 ↔ CI job 대응표

| 로컬 recipe | CI job / step | 검증하는 것 |
|---|---|---|
| `just be-test` | `backend-test` "Run tests" | pytest. `transcription` / `r2-cors` 2개 제외가 **정본** (외부 API·실 R2 의존) |
| `just fe-test` | `frontend-build` "Unit tests (vitest)" | 코드 옆 `__tests__/` 단위 테스트 |
| `just fe-build` | `frontend-build` "Build (includes type check)" | Next 빌드 = TS strict 타입 검사 |
| `just fe-security-headers` | `frontend-build` "Run security-headers spec only" | 보안 헤더 회귀 (public route, secrets 불요). **빌드 산출물(`pnpm start`)을 검증한다** — ↓ §2.1 |
| `just contracts-check` | `contract-check` | OpenAPI 재생성 + `git diff --exit-code` drift 차단 (ADR-027 D2) |
| `just e2e` | `e2e` job (`vars.E2E_ENABLED`, **현재 미활성**) | Playwright |

CI 가 복구되면 이 표가 대조표가 된다 — 로컬만 green 이고 CI 가 red 이면 차이는 이 표의 행에 있다.

### 2.1 ★ 보안 헤더는 dev 서버로 검증하면 안 된다

`playwright.config.ts` 의 `webServer` 는 **비-CI 에서 `pnpm dev` 를 띄운다.** 반면 CI 는
`pnpm start`(빌드 산출물)를 검증한다. 이 차이를 방치하면 **프로덕션에서만 나는 헤더·기동 회귀가
로컬 게이트를 통과한다** (2026-08-16 codex 리뷰 P2 지적).

그래서 `just fe-security-headers` 는 직접 `pnpm start -p 3005` 를 띄우고 그 서버를 검증한다
(`reuseExistingServer: true` 라 playwright 가 dev 서버를 새로 띄우지 않는다).

- 포트 **3005** 고정 — dev(`:3000`) / playwright 기본(`:3003`) 과 겹치지 않게 한다
- 이미 점유돼 있으면 **중단한다.** 남의 서버를 검증하면 게이트가 거짓 green 이 된다
- `.next` 가 최신이어야 한다. `ci-local` 이 `fe-build` → `fe-security-headers` 순서를 보장한다
- 헤더 단언은 포트에 의존하지 않으므로 CI(`:3000`)와 동치다

## 3. 백엔드 테스트 지형 (`apps/api/tests/`)

| 위치 | 성격 |
|---|---|
| 도메인 미러 16 디렉터리 (`actions/` `auth/` `meetings/` …) | 사실상의 unit. `unit/` 디렉터리를 따로 두지 않는다 |
| `architecture/` | **arch gate** — 아래 §3.1 |
| `integration/` | TestContainers 실 PostgreSQL. IDOR·멀티테넌시·alembic drift |
| `qa_edge/` | 스프린트 QA 엣지 케이스 |
| `llm/` | LLM 계약 fixture |
| `fixtures/` | composite FK · visibility SQL 골든파일 |

계약 테스트는 디렉터리가 아니라 **파일명 규약**으로 표시한다 —
`test_list_count_contract.py` / `test_sync_contract.py` / `test_adr019_phase_b_contract.py`.
실질 계약 게이트는 `just contracts-check` 이고, 이 파일들은 그 하위 계약(목록/카운트 필터 일치 등)을 지킨다.

### 3.1 arch gate — 규칙을 코드로 강제하는 테스트

`tests/architecture/` 는 리뷰가 놓치는 구조 위반을 CI 에서 막는다.

| 파일 | 막는 것 |
|---|---|
| `test_visibility_single_source.py` | visibility 규칙 사본 재발 (`common/visibility.py` SSOT, B-15) |
| `test_visibility_characterization.py` | 그 SSOT 의 동작 특성 고정 |
| `test_prompts_centralized.py` | 인라인 프롬프트 (B-6 — `common/prompts.py` 만) |
| `test_service_no_asyncsession_instance.py` | service 가 `AsyncSession` 을 보유 (B-1) |
| `test_no_memory_to_embeddings_lazy_import.py` | cross-domain 직접 호출 (헌법 §4.2, BL-006 회귀) |
| `test_core_common_import_allowlist.py` | `core ↔ common` 레이어 cycle |

**arch gate 가 실패하면 테스트를 고치지 말고 코드를 고친다.** 이 테스트들이 곧 헌법의 집행부다.

## 4. 프론트엔드 테스트 지형

- **단위**: 코드 옆 `__tests__/` (`src/**/__tests__/*.test.tsx`). 별도 top-level `tests/` 없음
- **e2e**: `apps/web/e2e/` (`playwright.config.ts` `testDir: "./e2e"`)
  - project `chromium` — 일반 spec
  - project `public-only` — 보안 헤더. public route 만이라 secrets·BE 불요
  - project `team` — 멀티테넌시/RBAC 회귀 T1~T23 (조건부)

★신규 page/component 를 만들면 **영향받는 spec 의 selector 도 같은 PR 에서** 갱신한다.
`data-testid` 를 우선한다 — `getByRole` + regex + `.first()` 는 같은 라벨이 2개일 때 조용히 오작동한다.

## 5. team 스위트 (T1~T23) 실행법

owner + member 2-토큰으로 실 RBAC 를 관통하는 회귀 스위트다. 헌법 I-9/I-13/I-17/I-19 +
visibility + RBAC 4-cell + RAG private 누수 0 을 여기서 영구 고정한다.

```bash
# BE 는 단일 프로세스로 :8000 (--reload 금지 — in-process RBAC 캐시 단일성)
just be-dev

E2E_RUN_TEAM=true E2E_API_URL=http://localhost:8000 \
  pnpm --dir apps/web exec playwright test --project=team --workers=1
```

- `apps/api/.env` 의 `CORS_ORIGINS` 에 `:3003` 이 포함돼야 한다 (없으면 preflight 400 노이즈)
- `--workers=1` 필수 — 병렬 실행은 공유 워크스페이스 상태를 서로 깬다
- 시드는 `assertLocalSeedTarget()` 이 비-로컬 대상을 거부한다 (프로덕션 오염 방지)

## 6. e2e 실패 디버깅 순서

**코드를 추측하기 전에 trace 의 page snapshot 을 먼저 읽는다.** 이 순서를 건너뛰어 헛다리를 짚은 전례가 있다.

```bash
gh run download <run-id> --dir /tmp/ci-artifacts   # CI 실패 시
find /tmp/ci-artifacts -name error-context.md
```

로컬은 `apps/web/playwright-report/` + `test-results/` 에 같은 산출물이 남는다.

## 7. 증거 남기기 (AGENTS.md §4)

| 변경 유형 | 필요한 증거 |
|---|---|
| BE | pytest 결과 요약 + alembic dry-run 출력 |
| FE | 스크린샷 1장 + `console.error` **0건** 로그 |
| API 시그니처 | `just contracts-check` + Playwright smoke — **한쪽만 통과하면 차단** |

`console.error` 0건의 합격 대상은 **앱 집계**다 — 앱 코드 `console.error` + `pageerror` +
앱 BE `/api/v1/*` 4xx/5xx. 브라우저 generic `Failed to load resource …` 는 같은 실패의 중복
집계라 합격선에서 제외하되 **함께 보고**한다. 안 셌으면 "미집계" 라고 쓴다 (추정치 금지).
