# ADR-024 — Webhook endpoint 회복 (Svix 검증 의무 + race-safe upsert)

**Status**: Accepted (Sprint 27a 결정, Sprint 27b 코드 회수 완료 2026-05-23)
**Date**: 2026-05-23
**Sprint**: 27a (luminous-anchor) 결정 / 27b (코드 회수 closeout)
**Supersedes**: ADR-022 (Clerk webhook SKIP)
**관련**: ADR-016 (Personal/Team IA) · ADR-023 (D-6 lock-in)

> **Scope 재정의 (2026-05-23 Wave 1 게이트 closeout)**: 본 ADR 의 사용자 액션 §1~3 (Clerk Production 발급 / Svix webhook 등록 / GCP+Vercel 환경변수 갱신) + Sentry 관련 사용자 결정은 본 sprint 에서 분리. Wave 1 코드 회수 (Svix 검증 + sync_user endpoint + race-safe upsert + 회귀 8 case) 만 sprint scope. 외부 5명 모집 + 1:1 미팅 + 운영 진입은 별도 운영 sprint 신호 시점에 본 ADR 재진입 또는 신규 ADR.

## Context

22 sprint 동안 외부 user 0명 (3 도구 점검 Sprint 26 합의). PRD Phase 4 "시기 미정" (Sprint 4 완료 후 office-hours 재검토 명시되었으나 미실행). Sprint 15 personal wedge pivot + Sprint 25 Clerk Production SKIP (ADR-022, 단독 founder 기능 검증 중 단계로 의도) → Sprint 27a D-6 grill 완료 후 외부 dogfooding 진입 가능 상태로 보였으나, 본 sprint 진행 중 운영 인프라 (Clerk Production / Sentry) 결정은 별도 sprint 로 분리하기로 재결정 (2026-05-23 reshape).

## Decision

**Sprint 27b = Webhook endpoint 회복 sprint** (코드 회수만). ADR-022 SKIP 의 코드 부분 supersede:
- sync_user endpoint 활성화 + Svix 검증 의무 + race-safe upsert + 회귀 8 case

운영 부분 (Clerk Production 발급 / webhook 등록 / 환경변수 / Sentry / 외부 5명) 은 본 sprint scope 외. 운영 진입 결정 시점에 별도 ADR 또는 본 ADR 재진입.

### 종료 기준 (Sprint 27b — 본 sprint scope)

- ✅ sync_user endpoint 복원 + Svix 검증 강제 (Depends)
- ✅ race-safe upsert (`repository.upsert_by_clerk_id`, ON CONFLICT) + lazy seed try/except IntegrityError fallback
- ✅ 회귀 8 case PASS (`tests/auth/test_user_sync.py`)
- ✅ ADR-022 Superseded 마크 + endpoints.md 응답 표 + auth/CONTEXT.md §5/§6 갱신
- ✅ codex 3 round + agy 2 round cross 검증 100% 수락 (codex 3차 APPROVE)

### 운영 진입 기준 (별도 sprint, 본 ADR scope 외)

Wave 2/3 (외부 5명 onboarding + 측정 + paid customer) 는 운영 sprint 신호 후 재진입. 그 시점에 필요한 사용자 액션 + 종료 기준은 신규 ADR (또는 본 ADR §"운영 진입 (deferred)" 부록) 에서 lock-in.

### AI 액션 (Sprint 27b 코드 회수, 완료)

Plan: `docs/plans/active/sprint-27b-ga-launch.md` Wave 1 (코드 회수, 완료).
Wave 2/3 (운영) 는 본 sprint scope 외.

## Consequences

### 즉시 효과 (Sprint 27b 코드 회수)
- ADR-022 SKIP 의 코드 부분 종결. sync_user endpoint + Svix 검증 + race-safe upsert 복원.
- D-6 (ADR-023) 5건 명시화 = 운영 진입 시 외부 user 안내 readiness 보존.
- 회귀 가드 8 case — Svix middleware / event whitelist / race-safe upsert / primary email / nullable name 모두 cover.

### Risk + Mitigation (Sprint 27b 코드 회수)
- **Risk A**: Svix middleware 회귀 — **Mitigation**: codex 3 round + agy 2 round 100% 수락 + 회귀 8 case integration with mock service
- **Risk B**: race-safe upsert 의 ON CONFLICT 가 personal workspace lazy seed 패턴 (dependencies.py:175) 와 동등 race-safe — **Mitigation**: codex 2차 P1 fix 의 try/except IntegrityError fallback 으로 lazy seed 경로도 보호

### 운영 진입 (deferred, 본 ADR scope 외)
운영 sprint 신호 시점에 다음 항목 lock-in 신규 ADR 또는 본 ADR 부록:
- Clerk Production 인스턴스 발급 절차 + GCP/Vercel 환경변수 갱신
- Svix webhook 등록 (`<api>/api/v1/users/sync`) + signing secret
- Sentry FE/BE DSN 설정 (외부 5명 운영 중 error 추적)
- 외부 5명 dogfooder 모집 + 1:1 onboarding 미팅 (12분 walkthrough)
- 활성 임계 (capture 5+ AND recall 3+ / 14일) + 지불 의사 측정
- Sprint 28 분기 (3+ 활성 / 1~2 / 0)

### Trade-off
- 보안 (Svix 강제) vs 1인 founder 인프라 부담 — 본 sprint 는 코드 측만 sealed. 운영 인프라는 별도 결정 시점.

## 회수 옵션 (운영 진입 후, deferred)

운영 sprint 신호 후 외부 5명 dogfooding measurement 종료 시 결정 분기 (본 ADR 또는 신규 ADR 에서 lock-in):
1. **3+ 활성 + 1+ 지불 의사** → paid customer onboarding (ADR-025 pricing 신설)
2. **1~2 활성** → onboarding UX 개선 + 재시도
3. **0 활성** → product pivot (PRD v3.1 retrofit, office-hours 진입)

## References

- ADR-022 (Clerk webhook SKIP, Sprint 25 — 본 ADR 가 코드 부분만 supersede)
- ADR-016 (Personal/Team IA, Sprint 15)
- ADR-023 (D-6 second-brain §8 lock-in, Sprint 27a)
- `docs/plans/active/sprint-27b-ga-launch.md` (Sprint 27b 코드 회수 plan)
- memory `project_sprint26_glittery_tulip_done` (Sprint 26 거버넌스 + 3 도구 합의 historical)
- Sprint 27a 점검 결과 (3 도구 합의, historical — 본 ADR 의 Scope 재정의 후 운영 진입은 별도 결정)
