# Sprint 27d Pre-GA Multi-Perspective Audit — 통합 보고

> opus 단일 세션 audit (~55분 진행). 6 agent 순차. localhost only. production audit SKIP (사용자 정책).

---

## Executive Summary

**verdict: 🟢 GO — 외부 5명 진입 권장**

| GO 조건 | 기준 | 결과 |
|---------|------|------|
| composite verdict ≥ 7.0/10 | 평균 | **7.53/10** ✅ |
| IDOR leak | 0건 | **0건** ✅ |
| 일반사용자 추천 | YES | **YES** ✅ |
| Solo-A-to-Z FAIL | ≤ 5 cells | **2 cells** ✅ |

→ **4/4 조건 모두 충족.** Sprint 27c (5.18/10 NOT-READY) 대비 **+2.35 개선** (Gemini key 갱신 + race fix 효과).

---

## Composite Score (6 agent)

| Agent | 점수 | Sprint 27c 대비 | verdict |
|-------|------|----------------|---------|
| agent-1 QA-Function | 7.2/10 | +2.45 | GO |
| agent-2 QA-EdgeCase | 8.0/10 | +3.00 | GO |
| agent-3 CTO | 6.5/10 | +0.90 | NEEDS-FIX (P1 1건) |
| agent-4 CEO | 7.5/10 | +2.10 | GO |
| agent-5 일반사용자 | 7.8/10 | +2.80 | GO |
| agent-6 Solo-A-to-Z | 8.2/10 | (신규) | GO |
| **Composite** | **7.53/10** | **+2.35** | **GO** |

---

## 발견 결함 (7건, Sentry 정책 SKIP 정정 후)

| ID | 우선순위 | 결함 요약 | 발견 agent | 회귀 여부 |
|----|---------|---------|-----------|-----------|
| **BUG-S27d-1** | P1 | OnboardingTooltip PopoverTrigger nativeButton — /dashboard + CmdK 2위치 | agent-1, 2, 6 | BL-S27c-8 회귀 |
| **BUG-S27d-2** | P2 | `/actions` 라우트 부재 → 404 next.js not-found | agent-1, 6 | Sprint 27c P2 carry-over 회귀 |
| **BUG-S27d-3** | P2 | File upload mime/extension validation 부재 (R2 abuse) | agent-2 | 신규 |
| **BUG-S27d-4** | P1 | 보안 헤더 부재 (CSP/X-Frame/Referrer/Permissions 모두) FE+BE | agent-3 | 신규 |
| ~~BUG-S27d-5~~ | — | Sentry DSN 미설정 → **사용자 정책 SKIP** | agent-3 | 정정 후 결함 아님 |
| **BUG-S27d-6** | P3 | RAG latency localhost dev avg 10.6s (Gemini API 지배) | agent-3 | 신규 |
| **BUG-S27d-7** | P3 | 사이드바 nav flicker (/notes 진입 시 일시 미표시) | agent-6 | 신규 |

### Sprint 27c BL 회귀 가드 (carry-over)
- ✅ I-9 cross-workspace 격리: 5/5 endpoint 403
- ✅ I-19 Personal 1인 격리: invite POST 403 with Korean message
- ✅ lazy seed race fix: 5 API 동시 호출 200 (`d@e.com` 신규 가입 lazy seed 정상)
- ✅ landing screenshot fix: 랜딩 SSR 200 + 5 H2 섹션
- ✅ Gemini key 갱신: 회의 요약 + RAG citation 모두 정상

---

## 강한 PASS 신호 (외부 5명 진입 GO)

### 🟢 보안 (agent-2)
- Cross-workspace IDOR 5/5 endpoint 403 ✅
- Personal workspace invite POST 403 ("개인 워크스페이스에는 초대을(를) 수행할 수 없습니다")
- 인증 누락 401 + UUID validation 422
- → **헌법 I-9 + I-19 모두 정합 검증**

### 🟢 핵심 가치 흐름 (agent-1)
- 회의 업로드 → AI 요약 (Gemini) → ~30초 완료 ✅
- 노트 생성 → 임베딩 즉시 활용 → RAG citation 정확 ✅
- Inbox 자동 분류 (count 1→2) ✅
- ⌘K SSE 스트리밍 + 출처 인용 ✅

### 🟢 사용자 경험 (agent-4 + agent-5)
- 랜딩 5 섹션 + "이미 동작하는 제품입니다" hero ✅
- sign-up CTA 3회 + "무료" 17회 ✅
- 모바일 viewport 정상 ✅
- 첫 5분 funnel: 2 클릭으로 가입, 3 클릭으로 회의 업로드 ✅
- 일반사용자 추천 의향 YES ✅

### 🟢 운영 readiness (agent-3, Sentry 정책 정정)
- lazy seed 부하 (5 API 동시) 모두 200 ✅
- API prefix 정합성 (헌법 I-13): 48 endpoint 중 41 (85%) /workspaces ✅

---

## 외부 5명 진입 전 즉시 fix 권고 (P1 2건)

### 1. BUG-S27d-1 — PopoverTrigger nativeButton (BL-S27c-8 회귀)
- 영향: console.error (사용자에게 직접 보이지 않음)
- fix: `OnboardingTooltip` 컴포넌트의 `PopoverTrigger` 에 `render={(props) => <button {...props} />}` 또는 `nativeButton={false}` 추가
- 작업 시간: 10-15분
- 위치: `frontend/src/components/onboarding/OnboardingTooltip.tsx` (추정)

### 2. BUG-S27d-4 — 보안 헤더 부재 (신규)
- 영향: 보안 baseline 부재 (clickjacking / MIME sniffing 등)
- fix:
  - FE: `next.config.ts` 의 `headers()` 함수에 CSP/X-Frame-Options/Referrer-Policy 추가
  - BE: FastAPI `secure-headers` middleware 또는 직접 ASGIMiddleware 작성
- 작업 시간: 30분
- 우선순위: 외부 5명 진입 전 권고 (BLOCK 아니지만 baseline)

### 3. BUG-S27d-2 — /actions 404 (선택)
- 영향: URL 직접 진입 시 이탈 trigger
- 사이드바 nav 에는 link 없으므로 발견 빈도 낮음
- fix: redirect `/actions` → `/inbox` 또는 신규 `/actions` 페이지 추가
- 작업 시간: 5-30분 (옵션에 따라)

---

## 후속 sprint 권고 (P2/P3)

| ID | 권고 | sprint |
|----|------|--------|
| BUG-S27d-3 | File upload mime/extension whitelist + 100MB cap | Sprint 28+ |
| BUG-S27d-6 | RAG latency 모니터링 + p95 < 5s 목표 | Sprint 28+ |
| BUG-S27d-7 | 사이드바 nav flicker fix | Sprint 28+ |

---

## DEFERRED 시나리오 (agy / codex 세션 위임)

| Agent | 시나리오 | 이유 |
|-------|---------|------|
| agent-2 E3 | Cross-tenant private RAG leak | Sentinel A/B 별도 로그인 필요 |
| agent-2 E5 | Project visibility 분기 (viewer/draft/private) | 별도 viewer 계정 필요 |
| agent-2 E7 | localStorage workspace drift | A/B logout/login 시퀀스 |

→ 위 3 시나리오는 다음 audit 사이클 (agy 또는 codex 세션) 에서 보강 검증.

---

## 최종 권고

1. **외부 5명 진입 GO** ✅
2. **진입 전 fix 권고** (60분 작업):
   - BUG-S27d-1 (OnboardingTooltip 회귀)
   - BUG-S27d-4 (보안 헤더 부재)
3. **진입 후 fix** (P2/P3):
   - BUG-S27d-3, -6, -7
4. **후속 audit**: agy 세션 + codex 세션에서 DEFERRED 시나리오 보강

---

## 메타 정보
- 시작: 2026-05-24 (Sprint 27c P0 fix `457c994` 머지 직후)
- 종료: 2026-05-24 (~55분)
- 세션: Claude Opus 4.7 (1M context)
- 브랜치: `sprint-27d/pre-ga-audit-prompts`
- 환경: localhost FE 3000 / BE 8000 (production audit SKIP)
- 정정 사항: Sentry 의도적 SKIP (2026-05-24 사용자 결정)
