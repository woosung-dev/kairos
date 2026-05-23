# Sprint 27c Integrated Audit Report — 외부 5명 dogfooding 진입 readiness

> 6 페르소나 (QA-Function · QA-EdgeCase · CTO · CEO · General-User · Mobile-First) 합의. plan `~/.claude/plans/sprint-27c-fuzzy-map.md` §5 진입 결정 정책 자동 적용.

## TL;DR

**진입 결정**: 🔴 **NOT-READY** — P0 3건 (3+ agent 합의) + General-User 이탈 ≥ 3건 (critical BLOCK trigger).

audit 평균 점수: **5.20/10** (>=5 hard stop 회피, 단 critical BLOCK trigger 1건 적용).

**사용자 액션** (~30-60분):
1. Cloud Run main HEAD `eb13a42` redeploy
2. `GEMINI_API_KEY` 재발급 + production secret 동기화
3. landing screenshot 3건 fix (`frontend/public/landing/screenshots/`)
4. 위 3건 fix 후 **재진입 audit 10-15분** (같은 시나리오 #1~#4 재현)
5. **재진입 audit P0 0건 확인 시** → 1주 안 외부 5명 모집 시작 (plan §6 hard cap)

---

## 1. 평균 점수 종합

| Agent | 평균 점수 | 핵심 verdict |
|---|---|---|
| QA-Function | 4.75/10 | 회의 업로드 → 자동 요약 broken (P0) |
| QA-EdgeCase | 5.0/10 | sentinel ADR-022 회귀 0 ✅ / IDOR 미검증 |
| CTO | 5.6/10 | 운영 readiness 3/10 BLOCK 한계 |
| CEO | 5.4/10 | 차별점 6/10, broken screenshot trust 직격 |
| General-User | 5.0/10 | 이탈 3건 (BLOCK trigger) |
| Mobile-First | 5.3/10 | bottom nav 양호, P0 inherit |
| **Average** | **5.18/10** | hard stop (<5) 회피, critical BLOCK 1건 trigger |

## 2. P0 Findings (3+ agent 합의 = ship-blocker)

### P0-S27c-1 — Production deploy stale (dashboard 500)

**합의 agents**: QA-Function ✅ · CTO ✅ · General-User ✅ · Mobile-First ✅ (4/6)

**증상**:
- `GET https://kairos-api-imrsiyibaa-du.a.run.app/api/v1/workspaces` → 500 "Internal Server Error"
- `/workspaces/{id}/members` → 500
- `/workspaces/{id}/inbox` → 403 "워크스페이스 멤버가 아닙니다"

**진단**: 동일 main HEAD code 가 localhost 200 OK (8.2s) / production 500 = Cloud Run revision 이 stale main HEAD. Sprint 24 Wave 2 (PR #101) 머지 후 redeploy 부재 추정.

**영향**: 외부 5명 진입 즉시 dashboard broken. 핵심 가치 도달 불가.

**증거**: `screenshots/qa-f/02-dashboard-workspace-paradox.png` + `03-dashboard-local-200ok.png`

**Fix 절차**:
1. GCP Console → jetaime-dev → Cloud Run → kairos-api → 최신 revision = main HEAD `eb13a42` 인지 확인
2. mismatch 시 GitHub Actions deploy workflow 수동 trigger 또는 `gcloud run deploy`

### P0-S27c-2 — GEMINI_API_KEY invalid (AI pipeline fail)

**합의 agents**: QA-Function ✅ · CTO ✅ · General-User ✅ (3/6)

**증상** (localhost BE log):
```
ERROR src.meetings.pipeline_service: 파이프라인 실패: 400 INVALID_ARGUMENT.
'API key not valid. Please pass a valid API key.' (reason: API_KEY_INVALID,
service: generativelanguage.googleapis.com)
```

**진단**: `backend/.env` 의 `GEMINI_API_KEY` invalid 또는 만료. Sprint 27a ADR-019 Phase B (gemini-3.1-flash-lite) swap 후 key 권한 부재 가능성.

**영향**: 회의 업로드 후 자동 요약/액션 추출 0건 = Kairos 핵심 가치 0. PRD §0 "AI memory layer" identity 무력화.

**증거**: `screenshots/qa-f/08-meeting-failed-status.png`

**Fix 절차**:
1. Google AI Studio (`https://aistudio.google.com`) 에서 API key 검증 / 새 key 발급
2. local `backend/.env` 갱신
3. Cloud Run secret manager 동일 갱신 + revision 재배포

### P0-S27c-3 — General-User 이탈 ≥ 3건 (critical BLOCK)

**합의 agents**: General-User ✅ · Mobile-First ✅ (inherit) (2/6, 단 plan §5 의 critical 1건 BLOCK trigger 자동 적용)

**증상**: 30대 PM 페르소나의 critical path 에서 이탈 지점 3건:
1. Clerk sign-up form 의 "Development mode" 표시 + dev 도메인 노출
2. Production dashboard 500 즉시
3. Meeting status="실패" (P0-S27c-2 결과)

**영향**: 외부 5명 모집 → 60-80% 즉시 이탈 추정.

**Verdict**: P0-S27c-1 + P0-S27c-2 fix 시 이탈 1-2건 미만 추정 → BLOCK trigger 해소.

## 3. P1 Findings (2-3 agent 합의 또는 single agent critical)

### P1-S27c-1 — landing screenshot 3건 broken (`/landing/screenshots/*.png` 400)

**Agents**: CEO ✅ · General-User ✅

**Verdict**: source code bug (localhost + production 동일 400). 파일 자체는 disk 에 존재. Next.js Image config / format issue.

### P1-S27c-2 — lazy seed 첫 GET /workspaces 8.2s latency

**Agents**: QA-Function ✅ · Mobile-First (cold start inherit)

**Verdict**: 외부 5명 첫 인상 직접 영향. Cloud Run min instance 1 (USD ~$10-15/month) 권고.

### P1-S27c-3 — A11Y PopoverTrigger nativeButton 3 page 공통

**Agents**: QA-Function ✅

**Verdict**: OnboardingTooltip 컴포넌트의 PopoverTrigger render prop 에 non-button. screen reader 사용자 5명 가입 시 즉시 이슈.

### P1-S27c-4 — "Development mode" / Clerk dev 도메인 production 노출

**Agents**: CEO ✅ · General-User ✅ · Mobile-First (inherit)

**Verdict**: 외부 5명 trust ↓. 단 ADR-022 SKIP 정합성 (Clerk Production 발급 SKIP) 결정 archeology 정합. paid customer 1명 도달 후 ADR-025 검토 시 ADR-022 supersede 될 수 있음.

## 4. P2 Findings (BL 등재 carry-over)

| ID | 항목 | Agent |
|---|---|---|
| P2-S27c-1 | Meeting 실패 후 retry 버튼 부재 | QA-Function |
| P2-S27c-2 | Failed meeting "AI 완료되면" copy mismatch | QA-Function |
| P2-S27c-3 | Inbox `/inbox` empty state 부재 | QA-Function · General-User |
| P2-S27c-4 | `/actions` route 404 (진입점 부재) | QA-Function |
| P2-S27c-5 | Mobile `/dashboard` 의 AI 검색 `?` hint 약함 | Mobile-First |
| P2-S27c-6 | pricing 페이지 paid plan 가격 안내 부재 | CEO |
| P2-S27c-7 | OG image / Twitter card meta 미검증 | CEO · Mobile-First |
| P2-S27c-8 | Real IDOR (Account #2 valid token) 미검증 | QA-EdgeCase |
| P2-S27c-9 | Production 403 message workspace 존재 leak 가능성 | QA-EdgeCase |
| P2-S27c-10 | Cloud Run secret rotation 정책 부재 | CTO |
| P2-S27c-11 | Docker Desktop 3000/3001 점유 (개발 환경 stale) | (audit-internal) |

## 5. Positive Findings (✅ working)

- ADR-022 sentinel 회귀 가드 통과 (`POST /api/v1/users/sync` → 404)
- Invalid JWT 차단 (401 "유효하지 않은 토큰입니다")
- Sprint 22 OBN-04 onboarding tooltip 정상 (dashboard / CmdK)
- Mobile bottom nav 5탭 정상 (홈/프로젝트/추가/Inbox/메모)
- workspace lazy seed (user + workspace + workspace_member + onboarding) atomic 정합
- Memory page empty state 잘 설계됨
- Projects page empty state 잘 설계됨
- localhost dashboard 8.2s 후 정상 동작 (production deploy 만 stale)

## 6. Decision Matrix (plan §5 자동 적용)

| 조건 | 충족 여부 | trigger |
|---|---|---|
| P0 ≥ 1건 (3+ agent 합의) | ✅ 3건 (S27c-1, S27c-2, S27c-3) | 🟡 P0 fix 후 진입 |
| CTO 보안 < 5 | ❌ 7/10 | — |
| CTO 운영 < 3 | ❌ 3/10 (BLOCK 한계) | 🟡 P0 fix 권고 |
| CEO 차별점 < 5 | ❌ 6/10 | — |
| General-User 이탈 ≥ 3 | ✅ 3건 | 🔴 critical BLOCK trigger |
| 평균 점수 < 5 | ❌ 5.18/10 | — |

**최종 verdict (audit 우선순위)**: 🔴 **BLOCK** (General-User 이탈 critical) > 🟡 (P0 3건 fix) → 외부 5명 진입 보류 + P0 fix prerequisite.

## 7. 외부 5명 진입 절차 (P0 fix 후)

```
[1] Cloud Run main HEAD redeploy (15min)
   ↓
[2] GEMINI_API_KEY 갱신 + Cloud Run secret 동기화 (10min)
   ↓
[3] landing screenshot 3건 fix (15min, P1 but critical CEO trust)
   ↓
[4] 재진입 audit 10-15min — 같은 시나리오 (QA-F #1~#4)
   ↓
[5] P0 0건 confirm
   ↓
[6] 외부 5명 모집 시작 (1주 hard cap, R8 outreach 80 활용)
   ↓
[7] Sprint 28 진입 — paid customer 1명 추진 (PMF signal)
```

## 8. BL 등재 (`docs/REFACTORING-BACKLOG.md`)

본 audit 산출 BL-S27c-1 ~ BL-S27c-11. P0 3건 은 별도 sprint plan (`docs/plans/active/sprint-27c-p0-fix.md`, 본 audit 가 작성 X — 사용자 fix 후 follow-up).

## 9. 본 audit 의 메타 한계

- **MCP Playwright single browser** — 6 agent 가 진정한 병렬 X. 단 산출물 (.md 6 파일) 충돌 0
- **Account #2/#3/#4 미사용** — Account #1 단일 verify. Real IDOR + 첫 가입 마찰 (Account #3 incognito) 부재
- **production timeout 간헐적** — Cloud Run 자체 instability 가 audit 시점에 영향
- **GEMINI_API_KEY invalid** — RAG injection / Inbox 분류 / Action 추출 등 AI 의존 시나리오 verify 불가
- **Founder bias** — 1인 dogfooding 22 sprint 의 observer bias 가 본 audit 의 페르소나 emulation 으로 보완되었으나 진짜 외부인 X

## 10. 후속

본 audit 산출:
- 7 파일 (`{agent}.md` × 6 + `integrated-report.md`) — `docs/audits/2026-05-23-sprint27c-audit/`
- 스크린샷 8건 — `screenshots/{qa-f|qa-e|cto|ceo|general|mobile}/`
- fixture archeology — `fixtures/account-1-state.json`
- BL 등재 — `docs/REFACTORING-BACKLOG.md` 신규 BL-S27c-1~11 (별도 사용자 승인 후 등재)
- memory `project_sprint27c_audit_done` 신설 (별도 사용자 승인 후)

본 audit 는 **decision gate 아님** (plan §0 원칙) — 외부 5명 진입은 P0 fix 후 1주 hard cap. audit 의 finding 9건 (P0 3 + P1 4 + P2 11) 은 외부 5명에게 미리 알릴 known issue list = 그대로 사용 가능.
