# Sprint 28 — dogfooding stabilize (외부 5명 진입 후 첫 sprint)

> Sprint 27d audit GO (composite 8.02/10) + PR #108 merge 후. 외부 5명 dogfooding 운영 중 발견한 결함 + Sprint 27d BL-S27e-1~4 처리 + 피드백 수집 인프라 셋업.
> 예상 기간: 2-3주 (외부 5명 응답 수집 시간 포함).

## Context

Sprint 27d 가 외부 5명 진입 *직전* audit 까지 완료. 본 sprint 는 **진입 후 운영**:

1. **dogfooding 피드백 수집 인프라** — Sprint 27c/27d 는 인앱 피드백 채널 미구현. 5명 응답이 ad-hoc 으로 흩어지면 인사이트 누락.
2. **BL-S27e-1~4** — Sprint 27d 가 carry 한 P3 4건. 외부 사용자 노출 위험은 낮지만, dogfooding 중 인지도 + RAG latency 는 직접 UX 영향.
3. **외부 사용자 발생 가능한 신규 결함** — Sprint 27d audit 이 본인 1계정 기반. 실 외부 사용자가 만드는 corner case (조직명/이름 한글-영문 혼용, 회의 길이 30분+, multilingual transcript 등) 의 회귀 가드 미흡.

production / Sentry audit 재진입 조건은 본 sprint 끝에 별도 분리 평가 (사용자 정책 SKIP 유지 여부 reconsideration).

---

## Wave 1 — 피드백 수집 인프라 (P0, ~1주)

dogfooding 5명 응답을 받는 채널이 인프라적으로 없는 상태. 1순위.

### W1-T1: 인앱 피드백 button (P0)

**위치**: `frontend/src/features/feedback/` 신설

- 우측 하단 floating button (모바일/데스크탑 공통)
- 클릭 → modal → free text + 별점 (1-5) + screenshot 자동 첨부 옵션
- POST `/api/v1/feedback` → BE 신규 table `feedback_entries`
- 사용자 ID + workspace_id + URL + user_agent 자동 capture
- 익명 옵션 (체크박스 — 그래도 user_id 는 internal 저장)

### W1-T2: 피드백 BE endpoint + storage (P0)

- `backend/src/feedback/` 모듈 신설 (router + service + models)
- alembic migration: `feedback_entries` table (id / user_id / workspace_id / rating / body / metadata jsonb / created_at)
- Sentry 통합 (정책 SKIP 해제 시) 또는 BE 로그 + Slack webhook 으로 라우팅 (sentry SKIP 유지 시)

### W1-T3: 주간 설문 + retention dashboard (P1)

- Typeform/Google Form 1개 셋업 — 5문항 (사용 빈도 / 가장 좋은 기능 / 가장 막힌 곳 / 추천 의사 / free text)
- 주 1회 ad-hoc 발송 (Sprint 28 첫 주는 진입 5일 후)
- BE `/admin/dogfooding-stats` endpoint — DAU/WAU + 회의 업로드 수 + RAG 질의 수

---

## Wave 2 — Sprint 27d BL carry (P1-P3, ~3-5일)

dogfooding 운영 중 인지도/UX 영향이 큰 순.

### W2-T1: BL-S27e-1 RAG latency 모니터링 + p95 < 5s 목표 (P1 승격)

dev avg 10.6s 는 운영에서 즉시 UX 임계. founder dogfooding 시기 (Sprint 15-22) 는 본인 인내심 + caching warm 으로 견뎠으나 외부 사용자는 즉시 이탈 신호.

- Sentry performance monitoring 활성 (정책 SKIP 해제 검토)
- 또는 BE 자체 metrics: `backend/src/rag/service.py` 에 timing log + 캐시 hit/miss + Gemini API call duration
- p95 < 5s 미달 시 캐시 우선 (`MemoryQueryEmbeddingCache` 의 hit률 분석 → BL-010 동반)

### W2-T2: BL-S27e-2 사이드바 nav flicker (P3, 디버깅)

- `/notes` 진입 시 일부 nav link 일시 미표시
- useEffect dependency 또는 SWR cache hydration timing 분석
- Fix 후보: nav skeleton + SSR-hydration 동기화

### W2-T3: BL-S27e-3 CSP 정책 도입 (P3, 시간 여유 시)

- Clerk + R2 + Sentry + Vercel + Cloud Run 도메인 inventory
- `strict-dynamic` + nonce 기반 CSP
- 본 sprint 시간 부족 시 Sprint 29+ carry

### W2-T4: BL-S27e-4 FE 병렬 E2E flake (P3)

- `e2e/.auth/user.json` storageState 단일 공유 → worker 별 분리
- 또는 onboarding localStorage 마크 prefix 에 worker index
- Sprint 28 후반 CI 게이트 강화 전 정리

---

## Wave 3 — 외부 사용자 corner case 회귀 가드 (P1-P2, ~3-5일)

dogfooding 5명 응답 후 발견 패턴 + 미리 가드해야 할 corner case.

### W3-T1: multilingual transcript 회귀 (P2)

- Whisper 가 한국어/영어 mixed transcript 생성 시 Gemini summary 가 일관되게 한국어 출력?
- pytest fixture 1개 + integration test

### W3-T2: 회의 길이 30분+ 안정성 (P2)

- 현재 BackgroundTask 가 30분+ 회의 (~50MB audio) 처리 시 timeout/메모리 안전?
- Cloud Run instance 의 메모리 제한 확인 + 청크 단위 처리 옵션

### W3-T3: 조직명/사용자명 한글 처리 (P3)

- 한글 workspace name + 한글 user display name 의 UI/검색/RAG 정합
- 한자 + emoji 혼용 edge case

---

## Wave 4 — production audit 재진입 조건 평가 (Sprint 28 끝, 0.5-1일)

본 sprint 마무리에서 다음 sprint 진입 조건 평가:

- Sentry FE+BE 활성 결정 (사용자 정책 reconsideration — dogfooding 응답에서 "오류 보고가 안 됨" 신호 있을 시)
- Clerk Production 키 발급 결정 (사용자 정책 reconsideration — 외부 5명 → 20명+ 확장 신호 있을 시)
- production 환경 audit 진입 결정 (dev → production 전환 시점)

산출물: `docs/sprints/sprint-28-dogfooding-stabilize/exit-evaluation.md`

---

## 성공 조건 (Sprint 28 closeout)

- [ ] 피드백 수집 인프라 운영 중 (W1-T1/T2 완료)
- [ ] dogfooding 5명 중 N≥3 명이 첫 7일 retain (W1-T3 dashboard 로 측정)
- [ ] BL-S27e-1 RAG p95 < 5s 또는 명시적 BL carry (Gemini 의존성 한계 명시)
- [ ] BL-S27e-2/3/4 처리 또는 명시적 carry (각 항목 reasoning)
- [ ] 외부 사용자 발생 신규 결함 0 → Sprint 29 진입 가능
- [ ] production audit 재진입 조건 명시 (Wave 4 산출물)

## 후속 가능성 (Sprint 29+)

- Sentry / Clerk Production / production audit 정책 재평가 결과에 따라
- dogfooding 응답 기반 PMF signal (paid user 1명 시도 = Sprint 28 GTM agent 권고)
- 다음 5명 → 20명 모집 진입 (외부 모집 채널 셋업)
