# QA-Function — Happy Path 8 시나리오

> 페르소나: 시리즈 A QA Lead. PRD §5 user flow 기준. localhost (FE :3002, BE :8000) 진입. Account #1 (a@e.com).

## 결과 요약

| # | 시나리오 | 결과 | 비고 |
|---|---|---|---|
| 1 | 가입 (Clerk login) | ✅ PASS | Account #1 password reset 후 통과 (사전 차단 = F-AUTH-001) |
| 2 | lazy seed workspace | ✅ PASS / ⚠️ slow | personal `4cc7e508-...` 자동 생성. 단 첫 `/workspaces` GET = **8.2s** (P1 latency) |
| 3 | 회의 업로드 (R2 presigned + meeting POST 202) | ✅ PASS | test.m4a 77.8KB → `/meetings/{id}` redirect, R2 정상 |
| 4 | 회의 상세 (요약/트랜스크립트/액션) | ❌ FAIL — **P0** | status=`실패`. BE log: `GEMINI_API_KEY invalid` → AI pipeline 전체 폭발. 외부 사용자 핵심 가치 0 |
| 5 | Inbox 자동 분류 | ⛔ BLOCKED | meeting 처리 실패로 InboxItem 생성 안 됨. 코드는 정합 추정 |
| 6 | 액션 칸반 status | ⛔ BLOCKED | `/actions` route **404** (P2 — dedicated 진입점 없음). action items 는 meeting 내부에 표시될 예정 |
| 7 | RAG SSE 검색 (⌘K, ?) | ✅ partial | 질문 입력 + 응답 "제공된 소스에서 관련 정보를 찾지 못했습니다" (데이터 0 정상). citation 검증은 데이터 부재로 미가능. **GEMINI_API_KEY 의존이므로 production 에서도 폭발 가능** |
| 8 | Memory promote | ⏸ NOT_TESTED | Memory page UI 정상 (empty state OK). promote 동작은 데이터 의존 |

## 핵심 Findings

### P0-PROD-DEPLOY (production deploy stale 가능성)

**증상**: production `https://kairos-zeta-ebon.vercel.app/dashboard` 접근 시:
- `GET /api/v1/workspaces` → **500** "Internal Server Error"
- `GET /api/v1/workspaces/{id}/members` → **500**
- `GET /api/v1/workspaces/{id}/inbox` → **403** "워크스페이스 멤버가 아닙니다"

**진단**: 동일 main HEAD code 를 localhost 에서 띄우면 `GET /workspaces` 200 OK. → production Cloud Run revision 이 stale main HEAD 일 가능성 높음 (Sprint 24+ BL-052/053/054 대규모 refactor 머지 후 redeploy 부재).

**증거**: 
- `screenshots/qa-f/02-dashboard-workspace-paradox.png` (production broken)
- `screenshots/qa-f/03-dashboard-local-200ok.png` (localhost 정상)

**Verdict**: 외부 5명 진입 즉시 dashboard broken. **P0 ship-blocker**. 사용자 액션: Cloud Run 에 main HEAD `eb13a42` re-deploy 1회.

### P0-AI-PIPELINE (Gemini API key invalid)

**증상**: 회의 업로드 후 BE log:
```
ERROR src.meetings.pipeline_service: 파이프라인 실패 (meeting=4a581772-...): 400 INVALID_ARGUMENT.
{'error': {'code': 400, 'message': 'API key not valid. Please pass a valid API key.',
'status': 'INVALID_ARGUMENT', 'details': [{'@type': '...ErrorInfo',
'reason': 'API_KEY_INVALID', 'domain': 'googleapis.com',
'metadata': {'service': 'generativelanguage.googleapis.com'}}]}}
```

**진단**: `backend/.env` 의 `GEMINI_API_KEY` 가 invalid 또는 만료. Sprint 27a (ADR-019 Phase B) gemini-3.1-flash-lite swap 후 key access 불가 가능성.

**Verdict**: 외부 5명이 회의 업로드해도 자동 요약/액션 추출 0. **P0 ship-blocker**. 사용자 액션: AI Studio 또는 GCP console 에서 GEMINI_API_KEY 유효성 확인 + 재발급. production env (Cloud Run secret) 도 동일 갱신.

### P1-LATENCY (lazy seed 첫 호출 8.2s)

**증상**: 신규 가입자의 첫 `GET /workspaces` 호출이 8210ms. 

**진단**: lazy seed INSERT (user + workspace + workspace_member + onboarding) + `await session.commit()` 가 직렬. PostgreSQL Neon (pgvector + halfvec extension) cold connection 비용 추가 가능성.

**Verdict**: 외부 5명 첫 진입 인상 직접 영향. SNS 유입 사용자가 8초 기다림 → 이탈률 ↑. Sprint 24 Wave 2 BUG-MOBILE-005 fix 후에도 잔여. P1.

### P1-A11Y-PopoverTrigger (3 page 공통 BaseUI 경고)

**증상**: Dashboard / Projects / CmdK 진입 시 console error:
```
Base UI: A component that acts as a button expected a native <button>
because the `nativeButton` prop is true.
Rendering a non-<button> removes native button semantics, which can
impact forms and accessibility.
PopoverTrigger → OnboardingTooltip → {DashboardPage|ProjectsPage|CmdK}
```

**Verdict**: OnboardingTooltip 컴포넌트의 PopoverTrigger 사용이 jsx render slot 에 non-button 을 넣음 → screen reader/form 접근성 저하. SR 사용자 5명 가입 시 즉시 이슈. P1.

### P2-FAIL-NO-RETRY (Meeting 실패 후 retry 부재)

**증상**: meeting status=`실패` 표시되나 retry 버튼 없음. 사용자 액션 = 새로 업로드만 가능. R2 storage 의 stale audio file 도 정리 안 됨.

**Verdict**: 핵심 가치 fail 시 복구 경로 미명시. P2.

### P2-FAIL-COPY-MISMATCH (failed meeting 요약 탭 copy 모순)

**증상**: status=`실패` 인데 요약 탭 = "AI 분석이 **완료되면** 요약이 자동으로 생성됩니다" 표시. 사용자가 "completed → wait" 로 오해. 

**Verdict**: P2.

### P2-INBOX-EMPTY-MISSING (Inbox empty state 부재)

**증상**: `/inbox` 빈 상태에서 헤더만 표시. "아직 항목이 없어요 / AI 분류는 회의 업로드부터 시작됩니다" 같은 empty state 메시지 없음. Memory page (`/memory`) 와 Projects page (`/projects`) 는 정상 empty state. 일관성 부족.

**Verdict**: P2.

### P2-ACTIONS-NO-ROUTE (`/actions` 404)

**증상**: `/actions` URL 직접 진입 시 404. dashboard 빠른 접근 카드에도 진입점 없음.

**진단**: CONTEXT-MAP §4.3 의 FE features 에 `actions` 있으나 dedicated route 미구현. action items 는 meeting detail 내부에 표시될 예정.

**Verdict**: P2. 액션 아이템 전체 보기 진입점 부재 = PRD §1 "결정·아이디어가 조직 자산화" 약화.

### P2-CMD-K-OBN-04-WORKING (Onboarding tooltip 정상 발화)

**증상**: dashboard 첫 진입 시 "AI 검색은 ⌘K — 워크스페이스 회의/노트 전체 검색" tooltip. ⌘K palette 첫 진입 시 "검색 범위는 현재 워크스페이스 전체입니다" tooltip. Sprint 22 OBN-04 정상.

**Verdict**: ✅ Positive — onboarding 흐름 working.

## 평가 점수 (10점)

| 차원 | 점수 | 근거 |
|---|---|---|
| 동작 성공률 | 3/10 | 8 시나리오 중 4 PASS, 1 BLOCKED, 2 FAIL P0, 1 partial. 핵심 happy path (회의 업로드→요약) broken |
| 응답 시간 | 5/10 | 첫 workspace API 8.2s (P1). RAG SSE / dashboard 일반 호출은 정상 |
| 데이터 정합 | 7/10 | lazy seed workspace + members + onboarding 정상. cross-domain INSERT 정합 |
| 오류 메시지 | 4/10 | meeting "실패" 만 표시, root cause/retry 미안내. 외부 사용자가 무엇이 잘못됐는지 모름 |

**평균: 4.75/10**

## 외부 5명 진입 결정 input

**자동 verdict**: 🔴 NOT-READY — P0 2건 (production deploy stale + GEMINI_API_KEY invalid) → 외부 사용자 5명 첫 회의 업로드 즉시 broken.

사용자 액션 필수 (audit 외):
1. Cloud Run main HEAD `eb13a42` re-deploy
2. `GEMINI_API_KEY` 갱신 + Cloud Run secret 동기화
3. 재진입 audit (10분, 같은 시나리오 재현)
