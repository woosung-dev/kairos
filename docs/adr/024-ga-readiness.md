# ADR-024 — GA readiness (Clerk Production + Svix + 외부 dogfooding 5명)

**Status**: Accepted (Sprint 27a 결정, Sprint 27b 실행)  
**Date**: 2026-05-23  
**Sprint**: 27a (luminous-anchor) 결정 / 27b 실행  
**Supersedes**: ADR-022 (Clerk webhook SKIP)  
**관련**: ADR-016 (Personal/Team IA) · ADR-023 (D-6 lock-in)

## Context

22 sprint 동안 외부 user 0명 (3 도구 점검 Sprint 26 합의). PRD Phase 4 "시기 미정" (Sprint 4 완료 후 office-hours 재검토 명시되었으나 미실행). Sprint 15 personal wedge pivot + Sprint 25 Clerk Production SKIP (ADR-022, 단독 founder 기능 검증 중 단계로 의도) → Sprint 27a D-6 grill 완료 후 외부 dogfooding 진입 가능 상태.

## Decision

**Sprint 27b = GA dogfooding sprint**. ADR-022 SKIP 결정 supersede. 회수 옵션 5단계 실행 (sync_user endpoint 활성화 + Svix 검증 + 회귀 test 회복 + Clerk Production 키 + webhook 등록).

### 종료 기준 (3 도구 합의)

GA launch 는 **milestone, 종료 신호 아님**. 진짜 종료 = **paid customer 1명** (PMF signal).

구체 measurement (codex):
- 외부 5명 중 **3명 이상이 2주 내 반복 사용** (capture 5+회 + recall 3+회 = 활성)
- **1명 이상이 지불 의사 명시** (Sprint 28 paid customer 1명 시도 base)

### 사용자 액션 (AI 작업 외)

1. Clerk Production 인스턴스 발급 (Dashboard)
2. Svix webhook 등록 (`<api>/api/v1/users/sync`)
3. GCP/Vercel `CLERK_SECRET_KEY` / `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` / `CLERK_WEBHOOK_SECRET` 갱신
4. 외부 5명 모집 (Sprint 15 R8 outreach 80 채널 활용)
5. 1:1 onboarding 미팅 5건 (12분 CODE walkthrough)

### AI 액션 (Sprint 27b)

Plan: `docs/plans/active/sprint-27b-ga-launch.md` Wave 1~3.

## Consequences

### 즉시 효과
- ADR-022 SKIP 종결. sync_user endpoint + Svix 검증 회복.
- D-6 (ADR-023) 5건 명시화 + GA dogfooding = 외부 user 안내 가능.
- BL-CUR-001/002/003 (마케팅) + R8 outreach 80 활용.

### Risk + Mitigation
- **Risk A**: Clerk Production 발급 지연 (사용자 액션 의존) — **Mitigation**: 발급 전엔 Sprint 27a 머지만 진행, 27b 는 사용자 신호 후 진입
- **Risk B**: 5명 모집 실패 (R8 outreach 80 응답률 X) — **Mitigation**: 마케팅 BL-CUR-001 (15초 비디오) + 002 (ROI 계산기) 병행
- **Risk C**: 5명 중 0명 활성 → product pivot (PRD v3.1 office-hours 진입) — Sprint 28 evidence base 명확
- **Risk D**: Svix middleware 회귀 (sprint 25 sentinel test 회복) — **Mitigation**: 회귀 4 case 코드 review

### Trade-off
- enterprise 보안 (Clerk webhook signing 강제) vs 1인 founder 인프라 부담 — Sprint 28 정도까지 운영 단순성 유지 (paid 시점부터 enterprise 옵션 검토).

### 후속 결정 (Sprint 28+)
- paid customer 1명 도달 시 → ADR-025 pricing 결정
- 5명 모두 이탈 시 → PRD v3.1 office-hours (Opus subagent 권고 보존)

## 회수 옵션

Sprint 27b 결과 measurement 후 결정 분기:
1. **3+ 활성 + 1+ 지불 의사** → Sprint 28 paid customer onboarding
2. **1~2 활성** → Sprint 28 onboarding UX 개선 + 재시도
3. **0 활성** → Sprint 28 product pivot (PRD v3.1 retrofit)

## References

- ADR-022 (Clerk webhook SKIP, Sprint 25)
- ADR-016 (Personal/Team IA, Sprint 15)
- ADR-023 (D-6 second-brain §8 lock-in, Sprint 27a)
- `docs/plans/active/sprint-27b-ga-launch.md` (실행 plan)
- memory `project_sprint26_glittery_tulip_done` (Sprint 26 거버넌스 + 3 도구 합의)
- Sprint 27a 점검 결과 (3 도구 합의 = B GA launch + 종료 = paid customer 1명)
