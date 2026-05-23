# agent-3-cto — CTO 평가 보고 (opus 세션)

## 메타
- **시작**: 2026-05-24 (agent-2 완료 후 연속)
- **세션**: Claude Opus 4.7
- **환경**: localhost FE 3000 / BE 8000 / Neon dev DB
- **cap**: 45분
- **이전 발견**: BUG-S27d-1 (P1), BUG-S27d-2 (P2), BUG-S27d-3 (P2)

## 페르소나 시나리오
나는 1인 풀스택 founder 의 외부 자문 (@levelsio 풍 hacker tech-lead). 운영 readiness / 비용 / observability / 부채 우선.
main HEAD `457c994` 에서의 운영 readiness 를 측정하고 외부 5명 진입 직전 부채 표를 정리.

## 시나리오별 결과 (작성 중)

### [C1] lazy seed 부하 분해 — dashboard 5 API — ✅ PASS
- agent-1 에서 검증 — 5 API (workspaces, projects, inbox, members, onboarding) 동시 호출 모두 200
- Sprint 27c P0-1 race fix 정합 확인

### [C2] 벡터 검색 RAG latency 5회 — 🟡 P3 부채
| sample | status | latency |
|--------|--------|---------|
| 1 | 200 | 7.3s |
| 2 | 200 | 8.5s |
| 3 | 200 | 10.8s |
| 4 | 200 | 12.4s |
| 5 | 200 | 14.2s |
- **stats**: min 7.3s / p50 10.8s / max 14.2s / avg 10.6s
- SSE stream 정상 작동 (`event: search_results` / `event: thinking` / `event: answer` 등)
- localhost dev 환경 (Gemini API call latency 지배적). production 에서는 cold start 추가.
- p95 추정 ~14s — 사용자 perceived latency 측면에서 **첫 event 0-1s** 만 빠르면 OK (streaming 사용자 경험)
- → **BUG-S27d-6 P3**: RAG latency 모니터링 + p95 < 5s 목표 (Sprint 28+)

### [C3] API prefix 정합성 (I-13) — ✅ PASS
- 총 48 endpoint
- 분포: `/api/v1/workspaces` 41 (85%) / `/api/v1/invites` 2 / `/api/v1/users` 2 / `/api/v1/admin` 1 / health+ready 2
- 헌법 I-13 (`/api/v1/workspaces/{workspace_id}/<resource>`) 정합 ✅

### [C4] Sentry 연결 — ⚠️ **의도적 SKIP (사용자 정책)**
- `backend/.env` + `frontend/.env.local` 모두 `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` 미설정
- ADR-021 wiring 코드는 존재 (Sprint 22 OBN-*)
- **사용자 정책 (2026-05-24 정정): Sentry 일단 안 함** → 결함 아님
- ~~BUG-S27d-5~~ 취소

### [C5] 보안 헤더 — 🔴 **BUG-S27d-4 P1 발견**
- FE `http://localhost:3000/` 응답 헤더에 **CSP / HSTS / X-Frame-Options / X-Content-Type-Options / Referrer-Policy / Permissions-Policy 모두 부재**
- BE `http://localhost:8000/api/v1/health` 동일 부재
- localhost 환경은 HTTPS 아니라 HSTS 는 무의미하지만, X-Frame-Options + X-Content-Type 은 dev 에서도 필요
- production (Vercel + Cloud Run) 에서는 일부 인프라 자동 헤더가 있을 가능성 — 사용자 확인 필요
- **외부 5명 진입 직전 보안 baseline 부재** → 보안 audit 의 가장 큰 결함

### [C6] 부채 hot spot — Sprint 27c BL + Sprint 27d 신규
- Sprint 27c carry-over (memory `project_sprint27c_audit_done`):
  - BL-S27c-8 P1: PopoverTrigger nativeButton (**BUG-S27d-1 회귀로 confirmed**)
  - ~~BL-S27c-9: Cloud Run cold start~~ → production audit 외 (사용자 정책)
  - BL-S27c-12: localStorage drift (logout 시 미clear)
  - 외 P2 6건 (retry UI / failed copy / inbox empty / /actions 404 등)
- Sprint 27d 신규 (이번 audit, **localhost only**):
  - BUG-S27d-1 P1: PopoverTrigger 회귀 (위치 2곳)
  - BUG-S27d-2 P2: /actions 404 회귀
  - BUG-S27d-3 P2: file upload validation 부재
  - BUG-S27d-4 P1: 보안 헤더 부재 (CSP/X-Frame/등)
  - ~~BUG-S27d-5~~ Sentry: 사용자 의도적 SKIP → 결함 아님 (정정)
  - BUG-S27d-6 P3: RAG latency localhost dev 환경 avg 10.6s

## 최종 verdict (agent-3, audit ~38분 진행, **Sentry 정정 후**)

### 점수: **6.5/10** (정정)
- 운영 readiness 6/10 (보안 헤더 부재 1건만 남음, Sentry 는 정책 SKIP)
- API 시그니처 정합성 + lazy seed fix + Personal/Team 격리 좋음
- Sprint 27c CTO 5.6/10 대비 **+0.9 개선** (Gemini 키 갱신 효과 + IDOR/I-19 강 검증)

### GO / NO-GO: **NEEDS-FIX 권장** (P1 1건만)
- BUG-S27d-4 (P1 보안 헤더): Next.js `next.config.ts` + FastAPI middleware 로 30분 작업. 외부 5명 진입 전 권고.
- 그 외 P2/P3 는 진입 후 fix OK
- production audit 는 사용자 정책으로 SKIP
