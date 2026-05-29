# Sprint 27e Round 2 Post-Merge — QA Dynamic Verify (MCP Playwright + browse)

> 본 sprint 의 진짜 dynamic verify gap 보강. Round 1/Round 2 가 모두 정적 분석 + dep audit + pytest 만 진행. browser 단위 실 동작 검증은 본 세션이 첫 sprint 안 처리.
>
> 환경: localhost (FE :3000 + BE :8000), 로그인 d@e.com (개인 Kairos workspace, lazy seed 정상), 검사 일시 2026-05-25 22:30~22:35 KST, baseline main HEAD `29427f2` (PR #110 머지)
>
> 도구: gstack browse (chromium launched) + curl + console/network log

## Executive Summary

**Verdict: NEEDS-FIX (dogfooding-blocker 2건)** — 외부 5명 진입 *전* fix 필수.

| 항목 | 결과 |
|---|---|
| 보안 헤더 4종 live verify (sign-in + / + BE /health) | ✅ 모두 PASS |
| Lazy seed (Personal workspace 자동 생성) | ✅ verified (workspace_id `e968c95f-…` 자동 매핑) |
| Middleware 미인증 redirect | ✅ verified (/dashboard → Clerk sign-in) |
| Round 2 SEC-3 fix runtime (JWT issuer 정합) | ✅ verified (JWT iss = `https://creative-boxer-79.clerk.accounts.dev`, settings default 와 일치) |
| Round 2 SEC-4 fix runtime (cron token) | ✅ verified (사용자 custom env, dev fallback 거부 정상) |
| dashboard 첫 진입 BE fanout | ❌ **7.5s critical path** (PERF-r2-4 실측 confirm) |
| /inbox 페이지 진입 안정성 | ❌ **JWT 1분 expiry + React Query no-retry-401 → 401 다발 → 빈 list → "워크스페이스 만들기" UI 강제** |
| RAG ⌘K 시연 | ⚠️ 추천 질문 click prefill only (Enter 명시 필요) |

## 발견 매트릭스

| ID | 영역 | 심각도 | 차단 | 증상 | Root cause | 권장 fix |
|---|---|:-:|:-:|---|---|---|
| **BUG-QA-1** | 성능 | **P0** | dogfooding-blocker | dashboard 첫 진입 BE 5 endpoint fanout **7.5s** (workspaces 7512ms / projects 5479ms / inbox 5434ms / members 5367ms / onboarding 4370ms). 사용자 LCP/TTI 직접 영향. | Round 2 PERF-r2-4 실측 confirm — `get_current_user` 가 매 request lazy seed 3 INSERT + commit. JWT cache hit 시점에도. | `auth/dependencies.py:174-249` — `users.onboarding_step >= 1` 사용자는 lazy seed SKIP (fast path SELECT 1만) |
| **BUG-QA-2** | 인증/안정성 | **P0** | dogfooding-blocker | 1분 머문 후 페이지 전환 (/inbox, /dashboard 재진입) 시 **모든 endpoint 401** → "데이터를 불러올 수 없습니다" 또는 "워크스페이스 만들어주세요" 강제 화면. 외부 5명 dogfooding 시 매 1분마다 발생. | Clerk JWT exp = 60s (dev). FE 의 `getToken()` 이 만료 직전 stale token return → BE 의 jwt.decode `ExpiredSignatureError` → 401. React Query default `retry: 1` 가 401 도 같은 stale token 으로 retry → 다시 401. | (a) BE `jwt.decode(..., leeway=10)` 추가 (1줄, 10s clock skew 허용) + (b) FE `apiClient` 에 401 detect 시 `getToken({ skipCache: true })` + 1회 retry interceptor |
| **BUG-QA-3** | UX | P3 | NO | 대시보드 추천 질문 4개 click 시 input prefill 만 → Enter 명시 필요. 사용자 좌절 가능성. | `dashboard/page.tsx` 의 RecommendedQuestions click handler 가 setValue 만 + form submit 미발동. Round 1 보고서 미언급 신규. | click handler 에 `form.submit()` 또는 `onSubmit` trigger 추가 |
| BUG-QA-4 | 보안 (carry) | P2 | NO | console `Content-Security-Policy: script-src was not explicitly set, so default-src is used as a fallback` warning. | BL-S27e-3 CSP 정책 carry — Clerk/R2/Next domain 정리 후 strict-dynamic 도입 예정. | BL-S27e-3 진행 |
| BUG-QA-5 | external | P3 | NO | Clerk dev instance 502 Bad gateway 1회 (Cloudflare). 30s 후 회복. | Clerk dev tier 외부 incident. 본 sprint 외. | Clerk Production 발급 (ADR-024) 시 회피 |
| BUG-QA-6 | external | P3 | NO | `https://clerk-telemetry.com/v1/event` CORS error. | Clerk infra side. dev only. | Clerk SDK / production 환경 자동 해소 |
| BUG-QA-7 | external | P3 | NO | `Clerk: Structural CSS detected — install @clerk/ui` warning. | Clerk 7.4.1 권고. 본 sprint 외. | `@clerk/ui` import 권고 (별도 sprint) |

## 핵심 path verify 결과

### ✅ 정상 동작
- 랜딩 페이지 (`/`) 로드 + 보안 헤더 4종
- `/dashboard` redirect (미인증 → Clerk sign-in)
- 로그인 후 자동 redirect → `/dashboard`
- 사이드바 navigation (홈 / Inbox / Memory / 빠른 메모 / + 추가)
- workspace switcher 표시 ("사용자의 개인 Kairos")
- Personal workspace lazy seed (workspace_id `e968c95f-…` 자동 매핑)
- 4개 빠른 접근 link (회의 추가 / 노트 / Inbox / 프로젝트)
- 4개 추천 질문 표시
- OnboardingTooltip ("AI 검색은 ⌘K") 표시 + 닫기
- 보안 헤더 4종 (X-Frame-Options=DENY / X-Content-Type-Options=nosniff / Referrer-Policy=strict-origin-when-cross-origin / Permissions-Policy=camera=(), microphone=(self), geolocation=()) — `/sign-in`, `/`, BE `/api/v1/health` 모두 live PASS

### ⚠️ 부분 동작
- 추천 질문 click → input prefill 만 (Enter 명시 필요) — BUG-QA-3
- RAG `/ask` 실 호출 = Enter 후 응답 panel 안 열림 (또는 UX 흐름 불명) — 추가 검증 필요

### ❌ 차단 (dogfooding-blocker)
- dashboard 첫 진입 7.5s — BUG-QA-1
- 1분 후 페이지 전환 시 401 다발 → 빈 상태 화면 — BUG-QA-2

## 외부 5명 dogfooding 진입 차단 정량

| 시나리오 | 영향 | 차단 |
|---|---|---|
| 외부 사용자 첫 dashboard 진입 | 7.5s 대기 — "느리다" 첫 인상 | **YES** (BUG-QA-1) |
| 1분 이상 페이지 머문 후 navigate | "워크스페이스 만들어주세요" 또는 "데이터 불러올 수 없습니다" 화면 — 실재 workspace 가 있는데 표시 안 됨 | **YES** (BUG-QA-2) |
| 회의 업로드 (Whisper) | 미검증 (시간 제약) | UNKNOWN |
| RAG ⌘K 검색 | 추천 질문 prefill UX 혼란 + RAG panel 동작 unknown | partial |
| 보안 헤더 회귀 | 4종 live PASS — Round 1 TEST-1 가드 정상 | NO |
| ADR-024 cutover hardening (SEC-r2-2/3/4) | JWT issuer 정합 + cron token validator runtime PASS | NO |

→ **차단 2건 fix 후 GO** 가능. 본 sprint Round 2 가 audit 시점에 발견 못 한 진짜 dynamic critical.

## 권장 fix 순서 (총 ~2h)

### Step 1: BUG-QA-2 (JWT leeway, 5분)

```python
# backend/src/auth/dependencies.py:129
claims = jwt.decode(
    token,
    signing_key.key,
    leeway=10,  # 신규 — 10s clock skew 허용. JWT exp 도달 직후 short window 통과.
    **decode_kwargs,
)
```

```typescript
// frontend/src/lib/api-client.ts — 401 retry interceptor (대안: FE 의 모든 fetch wrap)
// 또는 React Query 의 retry policy 를 401 에도 적용
```

회귀 가드: `tests/auth/test_jwt_verification.py` 에 leeway 검증 case 추가.

### Step 2: BUG-QA-1 (lazy seed fast path, 30분)

```python
# backend/src/auth/dependencies.py:174-249
async def get_current_user(...):
    # ...JWT 검증...
    user = await repo.find_by_clerk_id(clerk_id)
    if user and user.onboarding_step >= 1:
        # Fast path — 이미 seed 된 user. lazy seed SKIP.
        return user
    # 기존 lazy seed 로직 (raw text() INSERT 3건 + commit)
    ...
```

회귀 가드: `tests/auth/test_get_current_user_fast_path.py` 신설 — `onboarding_step >= 1` 시 SQL 1건만 실행 검증 (mock counter).

### Step 3: BUG-QA-3 (추천 질문 form submit, 10분)

```tsx
// frontend/src/features/home/components/recommended-questions.tsx (or 유사 위치)
<button onClick={() => { setValue(q); formRef.current?.requestSubmit(); }}>
```

회귀 가드: vitest unit — click 후 form onSubmit 호출 검증.

## 다음 단계

1. **사용자 fix 진입 결정** — 3건 (QA-1/2/3) 모두 본 세션 안 fix? 또는 QA-1/2 만 priority?
2. fix 적용 + 회귀 가드 + 회귀 검증
3. atomic commit + PR (또는 main 직접 push)
4. CI 통과 후 외부 5명 진입

## 산출물

- screenshots: `.gstack/qa-reports/screenshots/01-landing.png ~ 08-meetings.png` (8장)
- 본 보고서: `docs/sprints/sprint-27e-multi-review/qa-dynamic-verify.md`
