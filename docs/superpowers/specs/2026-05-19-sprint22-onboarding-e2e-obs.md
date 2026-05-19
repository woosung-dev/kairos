# Sprint 22 — Onboarding + Playwright G1~G8 + Sentry Observability Design

> 코드네임: **expressive-squirrel**
> 기간: 2026-05-19 ~ ETA (단일 세션 22-28h 목표, 단일 PR)
> 진입 baseline: main HEAD `1a83af6` (Sprint 21 BL-050 Simple 4 closeout, 325 PASS + 1 skipped, pyright 132)
> Plan 참조: `~/.claude/plans/sprint-22-expressive-squirrel.md`

---

## 1. Context (왜)

**한 줄 목표**: 첫 외부 user 가 회원가입에서 첫 RAG 응답까지 24시간 내 도달, 그 여정을 production-observable 하게.

**문제 발견 (Phase 1 탐색 결과)**:

1. **OnboardingBanner = local useState only** — `frontend/src/features/home/components/today-feed.tsx` line 23-117 의 `isDismissed` state 가 새로고침마다 재출현. progress indicator (1/4 → 4/4) 부재. server-side persistence 0. BE event hook 0.
2. **Playwright E2E 11개 spec 이미 존재** — brief 의 "현재 2개" 진술은 outdated. 실제 GAP = NEW 3건 (G2/G7/G8) + G4 skip 해제 + G1/G3/G5/G6 progress assertion 보강.
3. **Production observability 전무** — `grep -r "sentry\|otel\|structlog" backend/src` 결과 0건. 첫 외부 user 의 silent failure 를 알 방법 없음.
4. **ISSUE-OBN-01~04 정의 미상** — `docs/TODO.md` line 34 한 줄 언급, 어디에도 정의 부재.
5. **Personal workspace race fix = Sprint 15 에서 부분 해결** — `backend/src/auth/dependencies.py` line 79-120 의 lazy seed + `uq_workspaces_owner_personal` partial unique index + `ON CONFLICT DO NOTHING`. DB-level race-safe. 회귀 test 누락.
6. **Export UI 이미 구현됨** — `frontend/src/features/meetings/components/export-button.tsx` + `notes/components/export-button.tsx` (Markdown + JSON dropdown). BUG-C04 의 실제 문제 = **discoverability** (Power 페르소나가 못 찾음).

**의도된 outcome**:
- User table `onboarding_step` (0~4) + `onboarded_at` 으로 funnel 측정 가능
- OnboardingBanner 가 server state 기반 progress 표시 (모든 device 일관)
- Playwright G1~G8 8 시나리오 PASS (NEW 3 + 보강 4 + G4 fix)
- Sentry FE+BE wired — 첫 user crash 시 즉시 알람
- Export discoverability 개선 (UI 신설 X, 노출 위치 정렬)
- 외부 user 1명 가상 dogfooding walkthrough 통과

---

## 2. 사용자 결정 (lock-in)

| # | 결정 | 값 | 근거 |
|---|---|---|---|
| D1 | Sprint 축 | Brief 전체 (G1~G8 + UX + obs) | dogfooding readiness 우선 |
| D2 | E2E 환경 | Local dev (pnpm dev + uvicorn) | baseURL=localhost:3003, Clerk Production key 미발급 우회 |
| D3 | Onboarding state | Server-side User column | funnel 분석 + device 일관성 + BE event 자연 hook + Clerk webhook 부재 |
| D4 | OBN-01~04 정의 | Brief 추측대로 lock-in | (§3 참조) |
| D5 | PR 전략 | 단일 PR (Sprint 21 패턴) | Atomic Update 자연 + 한 워크트리 |
| D6 | Observability | Sentry FE+BE | 3-5h, 첫 user crash 즉시 알람, FE+BE 둘 다 |
| D7 | Alembic backfill | 기존 user 전원 step=4 + `onboarded_at=created_at` | 외부 user 1명 dogfooding = 신규 가입자, 기존 user banner 노출 회피 |
| D8 | step=3 trigger 시점 | **AI Distillation 완료 시점** | user 가 실제 가치 (요약 · 액션) 받은 시점. STT 만 끝난 시점은 너무 이름 |
| D9 | personal workspace race fix scope | 회귀 test 만 추가 | Sprint 15 의 lazy seed + partial unique index 가 DB-level race-safe. Clerk webhook 신설 (PR #3 BUG-AUTH-WH) 은 Sprint 23 carry-over |
| D10 | Export UI scope | Discoverability fix only | UI 자체는 이미 구현됨 (Markdown+JSON dropdown). BUG-C04 실제 문제 = 노출 위치 |

---

## 3. ISSUE-OBN-01~04 정의 (lock-in)

- **OBN-01**: personal workspace 자동 시드 검증 + 회귀 test (Sprint 15 lazy seed 안정성 확인). race fix 자체는 Sprint 15 완료, S15-T1 personal seed 작업도 dependencies.py 에 구현됨.
- **OBN-02**: progress indicator 1/4~4/4 + state persistence (server-side User column)
- **OBN-03**: 첫 회의 업로드 가이드 토스트 + 빈 state copy 강화
- **OBN-04**: 모바일 onboarding 최적화 (BL-017 Mobile FAB collision 동반)

---

## 4. Architecture

### 4.1 도메인 경계 (헌법 §4 준수)

**신규 도메인**: `backend/src/onboarding/` — 단일 책임 = onboarding step lifecycle 관리

```
backend/src/onboarding/
├── __init__.py
├── CONTEXT.md          # 도메인 문서 (Atomic §4)
├── dependencies.py     # OnboardingService DI provider
├── models.py           # Pydantic schemas (User column 자체는 auth/models.py)
├── repository.py       # OnboardingRepository (UPDATE idempotent)
├── router.py           # GET /api/v1/users/me/onboarding
├── schemas.py          # API Request/Response models
└── service.py          # OnboardingService.increment_step()
```

**의존 방향** (단방향, orchestrator 패턴 불필요):
```
workspaces ─┐
projects ───┼─→ onboarding (호출)
meetings ───┤
rag ────────┘
```

**중요**: `onboarding` 도메인은 다른 도메인을 import 안 함. 다른 service 가 `OnboardingService.increment_step(user_id, target_step)` 만 호출 (one-way fan-in).

### 4.2 Race safety 보존 (Sprint 15 구조 유지)

- `auth/dependencies.py` line 79-120 의 lazy seed 구조 **변경 0**
- `uq_workspaces_owner_personal` partial unique index 변경 0
- 본 sprint 작업 = 회귀 test 추가 (S11) + WorkspaceMember(owner) seed assert 명시화 (S12)

### 4.3 Sentry layer (cross-cutting)

- **BE**: `main.py` 의 `sentry_sdk.init()` 1줄 + `core/config.py` 의 `SENTRY_DSN` env. 도메인 layer 변경 0.
- **FE**: `sentry.client.config.ts` + `sentry.server.config.ts` (Next.js 16 `@sentry/nextjs` 표준)
- PII scrub `before_send` hook 으로 transcript / email field redact

---

## 5. Components

### 5.1 BE 신설 (5 파일)

| 파일 | 책임 |
|---|---|
| `backend/src/onboarding/models.py` | Pydantic schemas — `OnboardingResponse { step: int, totalSteps: 4, onboardedAt: datetime \| None, isCompleted: bool }`, `OnboardingStep` enum (NOT_STARTED=0, WORKSPACE_CREATED=1, FIRST_PROJECT=2, FIRST_MEETING=3, FIRST_RAG=4) |
| `backend/src/onboarding/repository.py` | `OnboardingRepository.increment(user_id, target_step)` — idempotent UPDATE |
| `backend/src/onboarding/service.py` | `OnboardingService.increment_step(user_id, target_step)` — transaction-safe, same-session |
| `backend/src/onboarding/router.py` | `GET /api/v1/users/me/onboarding` |
| `backend/src/onboarding/dependencies.py` | DI provider (`get_onboarding_service`) |
| `backend/src/onboarding/CONTEXT.md` | 도메인 문서 (Atomic §4) |

### 5.2 BE 수정 (6 파일)

| 파일 | 변경 |
|---|---|
| `backend/src/auth/models.py` | User column 2개 추가: `onboarding_step: int = 0`, `onboarded_at: datetime \| None = None` |
| `backend/src/auth/schemas.py` | `UserResponse` 에 `onboardingStep`, `onboardedAt` alias 필드 추가 |
| `backend/src/auth/dependencies.py:get_current_user()` | lazy seed 직후 `OnboardingService.increment_step(user.id, 1)` 호출 — **signup path 의 primary step=1 hook** (Codex 1차 finding 1) |
| `backend/src/workspaces/service.py:create_workspace()` | `commit()` 직전 `OnboardingService.increment_step(owner_id, 1)` 호출 — team workspace path 보조 hook. **commit 직전** 위치 필수 (Codex 1차 finding 2 — commit 후 placement 는 UPDATE rollback 됨) |
| `backend/src/projects/service.py:create_project()` | endpoint 끝부분에 `OnboardingService.increment_step(user_id, 2)` 호출 |
| `backend/src/meetings/pipeline_service.py:process_meeting()` | **AI Distillation 완료 시점** — line 67 `save_summary` + line 79+ ActionItem 저장 후 method end 직전에 `OnboardingService.increment_step(meeting.created_by_id, 3)` 호출. **`meeting.created_by_id` 사용** (workspace.owner_id 아님 — Codex 1차 finding 3, non-owner 멤버 회의 시 owner 의 funnel 잘못 advance 방지) |
| `backend/src/rag/service.py:ask()` | 첫 성공 응답 후 `OnboardingService.increment_step(user_id, 4)` 호출. **session = `self.embedding_repo.session` 재사용** (RagService 에 `_session` 없음 — Codex 1차 finding 7). `ask()` 시그니처에 `user_id` 파라미터 추가 (router update 동반) |
| `backend/main.py` | router include + `sentry_sdk.init()` conditional |
| `backend/src/core/config.py` | `SENTRY_DSN: SecretStr \| None = None` env |

### 5.3 BE Alembic (1 revision)

`backend/alembic/versions/<rev>_sprint22_user_onboarding.py`:
- `op.add_column('users', sa.Column('onboarding_step', sa.Integer(), nullable=False, server_default='0'))`
- `op.add_column('users', sa.Column('onboarded_at', sa.DateTime(timezone=True), nullable=True))`
- backfill: `op.execute("UPDATE users SET onboarding_step = 4, onboarded_at = created_at WHERE onboarding_step = 0")` — D7 lock-in
- downgrade: `op.drop_column('users', 'onboarded_at')` + `op.drop_column('users', 'onboarding_step')`
- 주석 형식: `<rev> (sprint22_user_onboarding)` — Sprint 21 D2.1 polish 학습

### 5.4 BE Drift gate 갱신

`backend/tests/integration/test_alembic_upgrade.py` 의 `PR2_MANAGED_CONSTRAINTS` 에 `users.onboarding_step`, `users.onboarded_at` 등록 — Sprint 21 BL-050 패턴

### 5.5 FE 신설 (1 모듈)

```
frontend/src/features/onboarding/
├── api.ts        # exportOnboardingApi (getOnboarding(token, wid))
├── hooks.ts      # useOnboarding() React Query hook (polling 없음, mutation invalidate only)
└── schemas.ts    # Zod schema (OnboardingResponse z.infer)
```

### 5.6 FE 수정 (8 위치)

| 파일 | 변경 |
|---|---|
| `frontend/src/features/home/components/today-feed.tsx` | OnboardingBanner refactor — server state 연결 (`useOnboarding`), `Step N/4` progress UI, 4/4 = 자동 hide, 모바일 flex-wrap (OBN-02 + OBN-04) |
| `frontend/src/features/meetings/components/meeting-detail-header.tsx` | Export button discoverability — header 우측 prominent 위치, tooltip "내보내기 (Markdown / JSON)" (G8 / BUG-C04) |
| `frontend/src/features/notes/components/note-detail-header.tsx` | 동일 패턴 |
| `frontend/src/components/empty-state.tsx` | onboarding-aware copy — `onboardingStep` prop 받아 "첫 회의를 업로드해 보세요" 같은 가이드 표시 (OBN-03) |
| `frontend/src/features/meetings/components/meeting-list.tsx` (또는 meetings/page) | EmptyState 진입 시 step ≤ 2 면 강조 토스트 (OBN-03) |
| `frontend/src/features/projects/hooks.ts` | `useCreateProject().onSuccess` 에 `queryClient.invalidateQueries({ queryKey: ['onboarding'] })` 추가 |
| `frontend/src/features/meetings/hooks.ts` | `useMeetingPolling().onSuccess` (distillation 완료 polling) 에 invalidate |
| `frontend/src/features/rag/hooks.ts` | `useRagAsk().onSuccess` 에 invalidate |

### 5.7 FE Mobile (BL-017 동반)

`frontend/src/components/{floating-action,fab}/...` (위치 확인 필요) — onboarding banner 와 FAB 충돌 검사 + z-index 정리 + 모바일 viewport `flex-wrap`

### 5.8 FE Sentry config

```
frontend/sentry.client.config.ts
frontend/sentry.server.config.ts
frontend/sentry.edge.config.ts        # Next.js 16 표준
frontend/instrumentation.ts            # Next.js 16 Sentry hook
```

### 5.9 Playwright E2E (8 시나리오)

| Spec | 작업 | NEW or 보강 |
|---|---|---|
| `home.spec.ts` | G1 — `Step 1/4` assertion 추가 | 보강 |
| `first-project.spec.ts` | G2 — signup → /new → 프로젝트 생성 → `Step 2/4` | **NEW** |
| `meeting-upload.spec.ts` | G3 — distillation 완료 후 `Step 3/4` assertion (E2E_RUN_HEAVY 의존성 유지) | 보강 |
| `rag-citation.spec.ts` | G4 — skip 해제, SSE mock 정합성 디버깅, `Step 4/4` 후 banner hide | **fix** |
| `qa-sentinel-p0.spec.ts` | G5 — action 완료 후 통계 갱신 verify | 보강 |
| `invite-page-regression.spec.ts` + `qa-sentinel-p0.spec.ts` | G6 — multi-user IDOR + invite flow | 보강 |
| `auth-relogin.spec.ts` | G7 — login → logout → login → workspace state 보존 (localStorage activeWorkspaceId) | **NEW** |
| `actions-export.spec.ts` (또는 `meeting-export.spec.ts`) | G8 — meeting detail 진입 → export button visible → dropdown → markdown 다운로드 verify | **NEW** |
| `mobile-responsive.spec.ts` | OBN-04 — onboarding banner mobile viewport case 추가 | 보강 |

---

## 6. Data Flow

### 6.1 Onboarding step lifecycle

```
[가입] Clerk sign-up
  ↓ FE: useUser() 후 protected endpoint 첫 호출
  ↓ BE: auth/dependencies.py:get_current_user() lazy seed
  ↓       → ON CONFLICT DO NOTHING personal workspace 시드
  ↓       → WorkspaceMember(owner) seed
  ↓       → OnboardingService.increment_step(user.id, 1)   ← signup path primary hook (D8/Codex finding 1)
  → User.onboarding_step = 1

[team workspace 생성 — 별도 path] FE: POST /api/v1/workspaces
  ↓ BE: workspaces/service.py:create_workspace() — commit() 직전 (Codex finding 2)
  ↓       → OnboardingService.increment_step(workspace.owner_id, 1)
  → User.onboarding_step = max(current, 1)   ← idempotent

[첫 project] FE: POST /api/v1/projects (사용자 입력)
  ↓ BE: projects/service.py:create_project()
  ↓       → OnboardingService.increment_step(user_id, 2)
  → User.onboarding_step = 2

[첫 meeting] FE: POST /api/v1/meetings (audio file upload)
  ↓ BE: BackgroundTasks → pipeline_service.process_meeting()
  ↓       → STT (Whisper)
  ↓       → AI Distillation (Gemini gemini-3.1-flash-lite)
  ↓             → summary + action item + tag 생성
  ↓             → OnboardingService.increment_step(user_id, 3)  ← D8 lock-in
  → User.onboarding_step = 3

[첫 RAG ask] FE: POST /api/v1/rag/ask (SSE stream)
  ↓ BE: rag/service.py:ask() (첫 성공 응답 후)
  ↓       → OnboardingService.increment_step(user_id, 4)
  ↓       → onboarded_at = now()
  → User.onboarding_step = 4
  → FE: useRagAsk().onSuccess → invalidate('onboarding') → banner 자동 hide
```

### 6.2 Idempotency 보장

```sql
-- OnboardingRepository.increment 의 SQL
UPDATE users
SET onboarding_step = :target_step,
    onboarded_at = CASE WHEN :target_step = 4 THEN now() ELSE onboarded_at END
WHERE id = :user_id
  AND onboarding_step < :target_step
```

- step=1 도달 후 새 workspace 생성 → `onboarding_step < 1` false → no-op
- step=4 도달 후 새 RAG ask → no-op (onboarded_at 변경 X)

### 6.3 FE invalidation

- `useCreateProject().onSuccess` → `queryClient.invalidateQueries({ queryKey: ['onboarding'] })`
- 동일 패턴: `useMeetingPolling` (distillation 완료 detection — `has_summary === true` transition 시점에 invalidate, STT 완료 시점 아님), `useRagAsk`
- `useOnboarding()` query 가 새로 fetch → banner 갱신

### 6.4 Sentry event flow

```
[BE 예외] FastAPI handler → sentry_sdk.capture_exception()
  ↓ before_send hook → PII scrub (email, transcript field redact)
  ↓ → sentry.io
  → Alarm (이메일 / Slack)

[FE 예외] React ErrorBoundary → Sentry.captureException()
  ↓ Sentry.init beforeSend → Clerk user.email redact + request body 차단
  ↓ → sentry.io
  → Alarm
```

---

## 7. Error Handling

### 7.1 Alembic backfill rollback safety (R1)

- upgrade: `UPDATE users SET onboarding_step=4, onboarded_at=created_at WHERE onboarding_step=0` (D7)
- downgrade: column drop (data 손실 의도된 정책)
- 본 sprint 는 production user 0명 → 안전. CO carry-over (production-scale) 별도 BL.

### 7.2 Sentry PII leak prevention (R5)

```python
# BE: backend/main.py
def scrub_pii_hook(event, hint):
    # request.data.transcript / email / password redact
    if "request" in event and "data" in event["request"]:
        for field in ("transcript", "email", "password", "audio_url"):
            event["request"]["data"].pop(field, None)
    return event

sentry_sdk.init(
    dsn=str(settings.SENTRY_DSN) if settings.SENTRY_DSN else None,
    send_default_pii=False,
    before_send=scrub_pii_hook,
    traces_sample_rate=0.1,
    environment=settings.ENVIRONMENT,
)
```

```typescript
// FE: frontend/sentry.client.config.ts
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  sendDefaultPii: false,
  beforeSend(event) {
    // Clerk user.email redact
    if (event.user) delete event.user.email;
    return event;
  },
  tracesSampleRate: 0.1,
});
```

- `.env.local` 에 `SENTRY_DSN` 미설정 시 init 안 함 (개발 모드 안전)
- staging / production env 분리

### 7.3 Race condition (R2 — 기존 lazy seed 의존)

- `auth/dependencies.py` 의 lazy seed 가 `ON CONFLICT DO NOTHING` 이므로 race-safe
- S11 = `asyncio.gather` 로 같은 user_id 동시 2회 `auth/sync` 호출 시 personal workspace **1개만** 생성 됨을 assert
- S12 = WorkspaceMember(owner) seed 라인 (dependencies.py:113-120) 의 SQL 결과 검증

### 7.4 Stack PR 회피 + stash@{0} 보존 (R6)

- 본 worktree `kairos-sprint-22` 는 stash@{0} 와 격리 (별개 worktree). pop 안 함.
- 단일 PR 패턴 (Sprint 21) 따름. commit message granular (S1~S28 으로 분리).
- 머지 직전 `gh pr view <N> --json baseRefName` → "main" 확인 (feedback_stack_pr_base_check)

### 7.5 Playwright flakiness (R4)

- G3 STT mock = `frontend/e2e/fixtures/` audio fixture 재사용
- G4 SSE mock = MSW 또는 `page.route` 로 통제
- `playwright.config.ts` retries (CI 1회, local 0회) 그대로

---

## 8. Testing

### 8.1 BE pytest (신규 +10~12 test)

| Test 파일 | 범위 |
|---|---|
| `backend/tests/onboarding/test_service.py` | increment_step idempotency (4 step transitions, target < current → no-op) |
| `backend/tests/onboarding/test_repository.py` | UPDATE WHERE clause 정확성 |
| `backend/tests/onboarding/test_router.py` | `GET /api/v1/users/me/onboarding` response shape |
| `backend/tests/auth/test_personal_workspace_race.py` | S11 — `asyncio.gather` 동시 2회 sync race → personal workspace 1개만 생성 + WorkspaceMember 1개만 생성 |
| `backend/tests/integration/test_onboarding_funnel.py` | workspace 생성 → step=1 / project → step=2 / meeting distillation → step=3 / RAG ask → step=4 end-to-end |

### 8.2 BE Alembic drift gate

- `backend/tests/integration/test_alembic_upgrade.py` 의 `PR2_MANAGED_CONSTRAINTS` 에 `users.onboarding_step`, `users.onboarded_at` 추가 → PASS

### 8.3 Playwright E2E (8 시나리오, 8/8 PASS 목표)

- G1 보강: `home.spec.ts` 에 `await expect(page.getByText('Step 1/4')).toBeVisible()`
- G2 NEW: `first-project.spec.ts`
- G3 보강: `meeting-upload.spec.ts` 에 distillation 완료 후 `Step 3/4` assertion + `E2E_RUN_HEAVY` 의존성 유지
- G4 fix: `rag-citation.spec.ts` skip 해제 — SSE mock 정합성 디버깅, citation + SourceViewer + `Step 4/4` 후 banner hide
- G5 보강: `qa-sentinel-p0.spec.ts` action 완료 후 통계 갱신
- G6 보강: `invite-page-regression.spec.ts` + `qa-sentinel-p0.spec.ts` multi-user IDOR
- G7 NEW: `auth-relogin.spec.ts`
- G8 NEW: `actions-export.spec.ts` — export button discoverability + Markdown download verify

### 8.4 수동 dogfooding (S28)

가상 외부 user "Alice" 12분 walkthrough:

1. `localhost:3003` → sign up → workspace 자동 생성 + `OnboardingBanner: Step 1/4`
2. `/new` → 첫 project 생성 → `Step 2/4`
3. `/meetings` → 30s 회의 mock upload → STT + Distillation 완료 → `Step 3/4`
4. RAG ask "이번 회의 요약" → 응답 + citation → `Step 4/4` + `onboarded_at` set → banner 자동 hide
5. Logout → Login → state 보존 확인 (G7)
6. `/meetings/<id>` export 클릭 → Markdown 다운로드 (G8)
7. Sentry dashboard 에 의도된 1건 외 error 0

Pass 기준: 7 단계 무중단, 각 단계 < 3s, Sentry 의도된 1건 외 error 0

### 8.5 Baseline 회귀

```bash
cd backend
uv run pytest tests/ -q                    # 325 + 신규 ≈ 335+ PASS, 1 skipped
uv run pyright                              # 132 baseline 유지
uv run alembic upgrade head                 # success
uv run pytest tests/integration/test_alembic_upgrade.py  # PASS (drift gate)

cd frontend
pnpm typecheck                              # 0 error
pnpm lint                                   # 0 error
pnpm test                                   # unit test PASS
pnpm exec playwright test                   # 8/8 PASS, 0 skip
```

---

## 9. Atomic Update §4 매트릭스 (PR 본문 "Docs sync" 섹션 필수)

| 코드 변경 | 동시 갱신 docs |
|---|---|
| `backend/src/auth/models.py` (User column 2개) | `backend/src/auth/CONTEXT.md` §엔티티 + `docs/architecture/erd.md` + `CONTEXT-MAP.md` §2 entity row |
| `backend/alembic/versions/<rev>_sprint22_user_onboarding.py` | drift gate 갱신 (`PR2_MANAGED_CONSTRAINTS`) |
| `backend/src/onboarding/` 신설 (새 도메인) | `backend/CONTEXT.md` §4 도메인 표 + `docs/architecture/directory-map.md` 백엔드 트리 |
| `backend/src/onboarding/router.py` endpoint 신설 | `backend/src/onboarding/CONTEXT.md` §6 + `docs/api/endpoints.md` |
| `backend/src/workspaces/service.py` (step=1 hook) | `backend/src/workspaces/CONTEXT.md` §의존 |
| `backend/src/projects/service.py` (step=2 hook) | `backend/src/projects/CONTEXT.md` §의존 |
| `backend/src/services/pipeline_service.py` (step=3 hook) | `docs/architecture/cross-domain-pipeline.md` + 해당 도메인 CONTEXT.md §5 의존 |
| `backend/src/rag/service.py` (step=4 hook) | `backend/src/rag/CONTEXT.md` §의존 |
| `frontend/src/features/onboarding/` 신설 | (FE CONTEXT.md 미존재 — skip 또는 자유 형식 등재) |
| Sentry 도입 | `docs/dev-log/021-sentry-observability.md` (신설 ADR Nygard 포맷) + `.env.example` `SENTRY_DSN` + `NEXT_PUBLIC_SENTRY_DSN` |

검증: PR 본문에 "Docs sync" 별도 섹션 + `git diff --stat docs/ backend/**/CONTEXT.md CONTEXT-MAP.md` 결과 첨부

---

## 10. Risk + Mitigation

| Risk | 영향 | Mitigation |
|---|---|---|
| **R1. Alembic backfill** | 기존 user 의 banner 노출 / funnel 오염 | D7: `step=4` + `onboarded_at=created_at` 일괄 backfill. production user 0명 → 안전 |
| **R2. Clerk webhook idempotency** | personal workspace 중복 시드 | Sprint 15 의 lazy seed + `ON CONFLICT DO NOTHING` 이미 race-safe (D9). 회귀 test 추가만 |
| **R3. 단일 PR review 부담** | 22-28h diff 한 번에 review → stash 사고 (PR #91) 재발 가능 | (a) sub-agent 단계 reviewer 2단계 통과 후 Codex 게이트, (b) stash@{0} 본 worktree 어디서도 pop 안 함, (c) commit message granular |
| **R4. E2E flakiness (G3 STT, G4 SSE)** | mock 정합성 깨질 위험 | STT mock = fixture 분리, SSE mock = `page.route` 통제. real LLM 호출 0건 |
| **R5. Sentry PII leak** | user email, transcript 가 error context 송신 | `before_send` PII scrub, `send_default_pii=False`, request body 차단 |
| **R6. stash@{0} 손실** | Sprint 21 이전 디자인 변경 손실 (PR #91 사례) | 본 sprint 어떤 worktree 에도 pop 안 함. Sprint 23 검토 보류 |
| **R7. AI Distillation 완료 시점 정의** | step=3 trigger 가 STT 완료 vs Distillation 완료 mix | D8 + §5.2: `backend/src/meetings/pipeline_service.py:process_meeting()` method end 직전 (line 67 `save_summary` + line 79+ ActionItem 저장 모두 완료 후). `has_summary` flag 가 True 로 set 된 시점이 user-facing distillation 완료 |

---

## 11. Carry-over 후보 (Sprint 23+)

- **CO-1**: OpenTelemetry full instrumentation (Sentry 위 layer, traces + RAG p50/p95)
- **CO-2**: Email reminder for stuck onboarding (step ≤ 2 + 24h 경과)
- **CO-3**: Onboarding step 5+ 확장 (collaboration: 첫 댓글 / 첫 share)
- **CO-4**: A/B test framework for OnboardingBanner copy
- **CO-5**: BL-050 잔여 3 entity (memory_items / memory_ai_calls / promotion_audit)
- **CO-6**: ADR-019 Phase B Gemini 3.1-flash-lite 코드 swap (예정 2026-05-28)
- **CO-7**: Clerk webhook (Sprint 19 PR #3 BUG-AUTH-WH) — lazy seed 교체 의도 시
- **CO-8**: BL-048 / BL-049 / BL-051 / BL-054 G5 잔여
- **CO-9**: Actions 도메인 export 신설 (CSV) — Q3 의 옵션 B carry-over
- **CO-10**: BUG-PROJ-DEL cascade 정책 (Sprint 19 PR #5 carry-over)

---

## 12. References

- Plan: `~/.claude/plans/sprint-22-expressive-squirrel.md`
- 진입 baseline: main HEAD `1a83af6` (Sprint 21 BL-050 Simple 4)
- 헌법: `/Users/woosung/project/agy-project/kairos/CONTEXT-MAP.md`
- Atomic Update 규정: `.ai/common/global.md` §2
- 직전 sprint spec: `docs/superpowers/specs/2026-05-18-bl050-simple4-composite-fk-design.md`
- Phase 1 탐색 결과 (코드 위치):
  - `backend/src/auth/dependencies.py` line 79-120 (Sprint 15 personal workspace lazy seed)
  - `backend/src/workspaces/service.py` line 26-54 (create_workspace)
  - `backend/src/workspaces/templates.py` (TEMPLATE_PROJECTS 3개)
  - `backend/src/meetings/router.py` line 90+ (export endpoint)
  - `frontend/src/features/home/components/today-feed.tsx` line 23-117 (OnboardingBanner)
  - `frontend/src/features/meetings/components/export-button.tsx` (export UI 기존)
  - `frontend/e2e/tests/*.spec.ts` (11개 spec)

---

**다음 단계**: 사용자 spec review → `/superpowers:writing-plans` 진입 → task plan 작성.
