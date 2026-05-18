# Sprint 22 — 가상 외부 user "Alice" Dogfooding Walkthrough

> 2026-05-19, Sprint 22 expressive-squirrel
> 본 문서 = OBN-01~04 의 user journey 통합 검증 narrative
> 실행은 Stage 6 closeout 단계 (사용자가 직접 진행 또는 PR review 후 staging dogfooding)

## 시나리오 — 가상 외부 user "Alice" (1인 founder, 첫 가입)

### 진입 baseline
- 신규 Clerk dev key signup 계정
- workspace 0건, project 0건, meeting 0건
- User table 의 `onboarding_step = 0` (alembic backfill 적용 외 신규 user)

### 12분 압축 walkthrough

#### Step 1/4 — 가입 (00:00 ~ 00:30)

1. `localhost:3003` 진입 → Clerk SignUp page
2. Google OAuth 또는 email 가입
3. `/dashboard` 자동 redirect
4. **BE event hook**: `auth/dependencies.py:get_current_user()` lazy seed
   - personal workspace `"{Alice}의 개인 Kairos"` 자동 생성 (`ON CONFLICT DO NOTHING`)
   - WorkspaceMember(owner) seed
   - `OnboardingService.increment_step(user.id, 1)` ← **D8/Codex finding 1 lock-in**
5. **검증**: 사이드바에 personal workspace + 3 template project (🚀 시작하기 / 💡 아이디어 / 📋 회의록) 노출
6. **검증**: TodayFeed 영역 또는 OnboardingBanner 에 `Step 1/4` 또는 등가 progress 텍스트 visible
7. **검증**: `GET /api/v1/users/me/onboarding` → `{step: 1, totalSteps: 4, onboardedAt: null, isCompleted: false}`

#### Step 2/4 — 첫 프로젝트 생성 (00:30 ~ 02:00)

1. `/new` 진입 → "프로젝트 이름" 입력 (예: "Sprint 22 dogfooding")
2. 생성 버튼 클릭
3. **BE event hook**: `projects/service.py:create_project()` 끝부분에서 `OnboardingService.increment_step(user.id, 2)`
4. **FE invalidate**: `useCreateProject().onSuccess` → `queryClient.invalidateQueries({ queryKey: ['onboarding'] })` (E16)
5. **검증**: OnboardingBanner 가 `Step 2/4` 로 갱신 (React Query refetch)
6. **검증**: 사이드바에 신규 project + 자동 선택

#### Step 3/4 — 첫 회의 업로드 + AI Distillation (02:00 ~ 06:00)

1. `/meetings` 진입 → "회의 추가" 또는 마이크 녹음 버튼
2. 30초 mock audio upload (또는 actual 녹음)
3. STT (Whisper) → background pipeline → AI Distillation (Gemini)
4. **BE event hook**: `meetings/pipeline_service.py:process_meeting()` 의 method end 직전, `MeetingRepository.find_by_id(meeting_id, workspace_id)` → `meeting.created_by_id` 추출 → `OnboardingService.increment_step(meeting.created_by_id, 3)` ← **Codex finding 3 lock-in (workspace.owner_id 가 아님)**
5. **FE invalidate**: `useMeetingStatus` 의 `status === "completed"` transition (Task 4-6 E16 의 정확화 — `has_summary` 가 아님)
6. **검증**: 회의 detail 진입 → summary + action item + tag 자동 생성 확인
7. **검증**: OnboardingBanner `Step 3/4`
8. **G8 검증**: 회의 detail header 의 "내보내기" 라벨 + tooltip visible (BUG-C04 해소)
9. **G8 검증**: 내보내기 클릭 → dropdown → Markdown 선택 → `.md` 다운로드

#### Step 4/4 — 첫 RAG ask (06:00 ~ 09:00)

1. `/dashboard` 또는 RAG 진입점에서 "이번 회의 요약" 질문 입력
2. SSE streaming 시작 → answer tokens + citation badge [1][2]
3. **BE event hook**: `rag/service.py:ask()` 첫 성공 응답 후, `self.embedding_repo.session` 재사용 (Codex finding 7 lock-in — `_session` attribute 미존재) → `OnboardingService.increment_step(user_id, 4)`
4. SSE `done` event → **FE invalidate**: `useRagStream` 의 done callback → onboarding query invalidate (E16 정확화 — `useRagAsk.onSuccess` 가 아님, streaming 이라)
5. **검증**: `onboarded_at = now()` set
6. **검증**: OnboardingBanner 가 `isCompleted = true` → 자동 hide
7. **검증**: `GET /api/v1/users/me/onboarding` → `{step: 4, isCompleted: true, onboardedAt: ...}`

#### Step Logout → Re-login (09:00 ~ 10:00) — G7 검증

1. User menu → 로그아웃
2. `/sign-in` 진입
3. 재로그인
4. **검증**: `activeWorkspaceId` localStorage 동일 / workspace 자동 진입
5. **검증**: OnboardingBanner 가 `isCompleted` 로 hidden 유지 (server-side persistence 확인)

#### Step Sentry verification (10:00 ~ 12:00)

1. Sentry dashboard (production DSN 설정 시) 진입
2. 의도된 에러 1건 trigger (예: `throw new Error("Sprint 22 dogfooding test")` in dev console)
3. **검증**: Sentry 에 1건 등재, `before_send` PII scrub 으로 email/transcript redact
4. **검증**: 의도된 1건 외 production error 0건

## Pass 기준

- 7 단계 무중단
- 각 단계 < 3s response
- BE pytest 회귀 0건 (Task 1+2+3 신규 test 포함 ~352+ PASS)
- pyright 회귀 0건 (baseline 132 → +3 leftover `test_config.py` 무관)
- FE typecheck 0 error
- Sentry 의도된 1건 외 error 0

## 발견된 Carry-over (Sprint 23+)

- **CO-1**: OpenTelemetry full instrumentation (Sentry 위 layer)
- **CO-2**: Email reminder for stuck onboarding (step ≤ 2 + 24h 경과)
- **CO-3**: Onboarding step 5+ 확장 (collaboration: 첫 댓글 / 첫 share)
- **CO-4**: A/B test framework for OnboardingBanner copy
- **CO-5**: BL-050 잔여 3 entity (memory_items / memory_ai_calls / promotion_audit)
- **CO-6**: ADR-019 Phase B Gemini 3.1-flash-lite 코드 swap (2026-05-28 예정)
- **CO-7**: Clerk webhook (Sprint 19 PR #3 BUG-AUTH-WH) — lazy seed 교체 의도 시
- **CO-8**: BL-OBS-1 Sentry quota 모니터링 + production sampling 하향
- **CO-9**: BL-OBS-2 배포 체크리스트에 `SENTRY_DSN env injection` 명시
- **CO-10**: BL-OBS-3 PII 필드 자동 발견 linter
- **CO-11**: Playwright G3/G5/G6 progress N/4 assertion 보강 (runtime fixture 확보 후)
- **CO-12**: Playwright G4 SSE mock 디버깅 (skip 해제)
- **CO-13**: Sprint 22 의 `test_config.py` 3 pyright errors (본 sprint 무관 baseline)

## 회귀 회피 (R6) — stash@{0} 보존

- 본 sprint 어떤 worktree 에도 `git stash pop` 안 함
- main worktree 의 `stash@{0}: On main: 임시 디자인 요청을 통해서 변경한 부분` 그대로 유지
- Sprint 23 검토 보류
