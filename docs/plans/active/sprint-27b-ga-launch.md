# Sprint 27b — GA Launch (외부 dogfooding 5명)

> 3 도구 (codex + agy + Opus subagent) 2026-05-23 점검 후 합의 = "22 sprint 동안 외부 user 0명, 모든 우선순위 추측 기반. Sprint 27 = GA dogfooding 1순위." 본 plan 은 Sprint 27a (luminous-anchor) D-6 grill + 토큰컷 직후 진입.

## Context

Sprint 22 외부 1명 dogfooding spec 미실행 + Clerk Production 의도적 SKIP (ADR-022). Sprint 27a 에서 D-6 (개인-팀 경계 / RAG UX / 회의 소속 / admin 접근 / 지식 생명주기) 5건 lock-in 완료 (ADR-023) → 외부 user onboarding 시 5건 모두 명시화된 정책으로 안내 가능. agy 의 "데이터 누수/권한 침해 risk" 해소.

**의도된 결과**: 외부 5명 중 3명이 2주 내 반복 사용 + 1명+ 지불 의사 명시 (codex 권고). PMF 첫 signal.

## 사용자 액션 (AI 작업 불가)

1. **Clerk Production 인스턴스 발급** — Clerk Dashboard → Production Mode 활성화
2. **Svix webhook 등록** — Clerk → Webhooks → `https://<api-domain>/api/v1/users/sync` 추가
3. **GCP/Vercel 환경변수 갱신** — `CLERK_SECRET_KEY` / `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` Production 키 + `CLERK_WEBHOOK_SECRET` (Svix signing secret)
4. **외부 5명 dogfooder 모집** — Sprint 15 R8 outreach 80 채널 활용 (memory `project_sprint15_stage4_done`)
5. **onboarding 1:1 미팅 5건** — paid customer milestone 명시 (codex: "5명 중 3명 2주 재사용 + 1명+ 지불 의사")

## AI 액션 (Sprint 27b 진입 시)

### Wave 1 — Code 회수 (ADR-022 회수 옵션 5단계 적용)

1. `backend/src/auth/router.py` 의 `sync_user` endpoint 활성화 (Sprint 25 비활성화 코드 revert)
2. Svix 서명 검증 middleware 추가 (`backend/src/auth/svix.py` 신규 또는 `dependencies.py`)
3. `core/config.py` 에 `CLERK_WEBHOOK_SECRET: SecretStr` 추가
4. ADR-022 `Status: Superseded by ADR-024` 마크
5. 회귀 4 case (`tests/integration/test_user_sync_webhook.py`) — sprint 25 sentinel test 회복

### Wave 2 — Onboarding fixture

1. `frontend/src/features/onboarding/` 컴포넌트 dogfooding 5명 대응 (이미 OBN-01~04 구현됨)
2. `docs/development/onboarding-5-dogfooders.md` 신설 — 5명 1:1 미팅 sheet 템플릿 (CODE 흐름 walkthrough 12분)
3. Sentry FE/BE error tracking 활성화 확인 (이미 Sprint 22 ADR-021 구현)

### Wave 3 — 측정 + paid customer 시도

1. `MemoryEvent` + R7 metrics 활성화 확인 (Sprint 15 구현됨)
2. 5명 × 2주 재사용 metric 추적 (각자 capture 5+회 + recall 3+회 = 활성)
3. 1명+ 지불 의사 = Sprint 28 paid customer 1명 시도 (PMF signal)

## DoD (Sprint 27b 완료 기준)

- Clerk Production 발급 + Svix webhook 등록 + GCP/Vercel 키 갱신 ✓
- `sync_user` endpoint + Svix 검증 회복 (ADR-022 → ADR-024 supersede)
- 외부 5명 onboarding 완료 (계정 생성 + 첫 회의 업로드)
- 2주 후 measurement: 5명 중 3명+ 활성 / 1명+ 지불 의사

## 회수 옵션

- 5명 모두 2주 내 이탈 → Sprint 28 = product pivot 결정 (PRD v3.1 office-hours 진입)
- 1명 활성 + 0명 지불 의사 → Sprint 28 = onboarding UX 개선 후 재시도
- 3명+ 활성 + 1명+ 지불 의사 → Sprint 28 = paid customer onboarding + pricing 페이지 갱신

## 의존

- Sprint 27a 머지 완료 (D-6 + 토큰컷)
- ADR-024 GA readiness 신설 (본 plan 과 같은 commit)
- 사용자 Clerk Production 발급 결정 (ADR-022 회수 옵션 발동)

## 참조

- `docs/adr/022-clerk-webhook-skip.md` (Sprint 25 SKIP 결정 + 회수 옵션 5단계)
- `docs/adr/023-second-brain-context-boundaries.md` (D-6 lock-in)
- memory `project_sprint15_stage4_done` (R8 outreach 80 채널)
- memory `project_sprint26_glittery_tulip_done` (Sprint 27 GA dogfooding 합의)
