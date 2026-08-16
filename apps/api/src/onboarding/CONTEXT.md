# Onboarding 도메인 CONTEXT

## 1. 책임

User.onboarding_step (0~4) lifecycle 관리. 다른 도메인이 핵심 이벤트 발생 시 `OnboardingService.increment_step(user_id, target)` 호출하여 funnel advance.

## 2. 엔티티

User 테이블 (`apps/api/src/auth/models.py`) 의 다음 컬럼 사용:
- `onboarding_step: int` (0~4, default 0)
- `onboarded_at: datetime | None` (step 4 도달 시 자동 set)

OnboardingStep IntEnum:
- 0 NOT_STARTED — 로그인만 한 상태
- 1 WORKSPACE_CREATED — personal workspace lazy seed 완료 (또는 team workspace 생성)
- 2 FIRST_PROJECT — 첫 프로젝트 생성
- 3 FIRST_MEETING — 첫 회의 AI distillation 완료 (`pipeline_service.process_meeting` 끝)
- 4 FIRST_RAG — 첫 RAG ask 성공 (`rag.service.ask()` 첫 응답)

## 3. 의존

- 호출자: workspaces / projects / meetings (pipeline_service) / rag / auth (lazy seed)
- 의존: auth (User table)
- Single-session: 호출자의 transaction 에 합류 — `commit`/`flush` 호출 없음

## 4. 엔드포인트

- `GET /api/v1/users/me/onboarding` → `OnboardingResponse { step, totalSteps, onboardedAt, isCompleted }`

## 5. Idempotency

- UPDATE 조건: `WHERE id = :user_id AND onboarding_step < :target` — target ≤ current 면 no-op
- target=4 일 때만 `onboarded_at = now()` set
- 다중 동시 호출 안전 (race-free, partial unique index 불필요 — column UPDATE)
