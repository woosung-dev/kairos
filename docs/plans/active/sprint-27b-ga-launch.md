# Sprint 27b — Webhook endpoint 회복 (코드 회수만)

> **Scope 재정의 (2026-05-23 Wave 1 게이트 closeout)**: 본 sprint 의 원 의도 (외부 dogfooding 5명 GA launch) 는 운영 인프라 (Clerk Production / Sentry) 결정이 별도 sprint 로 분리되며 narrower scope 로 재정의. 본 sprint = `sync_user` endpoint + Svix 검증 + race-safe upsert 코드 회수 only. 외부 5명 모집 / 1:1 미팅 / 측정 / paid customer 시도 = 운영 sprint 신호 후 별도 sprint.

## Context

Sprint 22 외부 1명 dogfooding spec 미실행 + Clerk Production 의도적 SKIP (ADR-022). Sprint 27a 에서 D-6 (개인-팀 경계 / RAG UX / 회의 소속 / admin 접근 / 지식 생명주기) 5건 lock-in 완료 (ADR-023). Sprint 27b 진행 중 운영 인프라 (Clerk Production / Sentry) 사용자 의존 결정을 별도 sprint 로 분리 — 본 sprint 는 코드 회수만 sealed.

**의도된 결과 (재정의)**: ADR-022 비활성화한 webhook endpoint 의 코드 부분 복원 + Svix 검증 의무 + race-safe 보장. 운영 진입 시점에 즉시 사용 가능한 codebase 정합.

## AI 액션 (Sprint 27b 코드 회수)

### Wave 1 — Code 회수 (ADR-022 회수 옵션 5단계 적용, 완료)

1. ✅ `backend/src/auth/router.py` `sync_user` endpoint 활성화 (Sprint 25 d614214 revert) + event whitelist (Codex 1차 P2-1) + primary email + nullable name (Codex 2차 P2)
2. ✅ Svix 서명 검증 middleware (`backend/src/auth/svix_verify.py`)
3. ✅ `core/config.py` 의 `CLERK_WEBHOOK_SECRET: SecretStr` (Sprint 24~25 사전 추가)
4. ✅ ADR-022 `Status: Superseded by ADR-024` 마크 + Superseded 섹션 + endpoints.md / CONTEXT.md atomic update
5. ✅ 회귀 8 case (`tests/auth/test_user_sync.py`) — created/updated/bad-sig/stale + Codex 1차 P2 후속 deleted-ignored/missing-id + Codex 2차 P2 후속 primary-email/nullable-name
6. ✅ Race-safe upsert (`repository.upsert_by_clerk_id`, ON CONFLICT, Codex 1차 P2-2) + lazy seed try/except IntegrityError fallback (Codex 2차 P1)

### 운영 진입 (deferred, 본 sprint scope 외)

운영 sprint 신호 후 진입:
- Clerk Production 인스턴스 발급 + dashboard webhook 등록 + GCP/Vercel 환경변수 갱신 (`CLERK_SECRET_KEY` / `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` / `CLERK_WEBHOOK_SECRET`)
- Sentry FE/BE DSN 설정 (외부 user 운영 중 error 추적)
- 외부 5명 dogfooder 모집 + 1:1 onboarding 미팅 5건 (`docs/guides/onboarding-5-dogfooders.md` 가이드 활용)
- MemoryEvent + R7 metrics 5명 × 2주 측정 (`docs/guides/onboarding-5-dogfooders.md` 부록 SQL 사용)
- 활성 임계 (capture 5+ AND recall 3+ / 14일) + 지불 의사 청취 → Sprint 28 분기 결정

## DoD (Sprint 27b 코드 회수 완료 기준, 충족)

- ✅ sync_user endpoint + Svix 검증 + race-safe upsert 모두 복원
- ✅ ADR-022 코드 부분 supersede (운영 부분은 deferred)
- ✅ 회귀 8 case PASS + 전체 backend pytest 468/1skip PASS
- ✅ codex 3 round + agy 2 round cross-검증 100% 수락 (codex 3차 APPROVE)

## 의존

- Sprint 27a 머지 완료 (D-6 + 토큰컷)
- ADR-024 코드 회수 부분 (운영 진입은 deferred)

## 참조

- `docs/adr/022-clerk-webhook-skip.md` (Sprint 25 SKIP 결정 + Superseded 섹션)
- `docs/adr/023-second-brain-context-boundaries.md` (D-6 lock-in)
- `docs/adr/024-ga-readiness.md` (코드 회수 scope, 운영은 deferred)
- `docs/guides/onboarding-5-dogfooders.md` (운영 진입 시 활용)
- memory `project_sprint15_stage4_done` (R8 outreach 80 채널, 운영 진입 시 활용)
