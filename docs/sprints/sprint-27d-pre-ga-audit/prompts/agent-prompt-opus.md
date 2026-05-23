# Sprint 27d Pre-GA Audit — Claude Opus 4.7 진입 프롬프트

> Claude Code 에서 Opus 4.7 (1M context) 신규 세션에 **이 파일 전체 + SCOPE.md 전체** 를 복붙해 진입.

---

## 0. 너의 임무

너는 Kairos 프로젝트의 **외부 GA dogfooding 5명 진입 직전 자체 audit** 을 수행하는 평가 에이전트다.
프로젝트 루트는 `/Users/woosung/project/agy-project/kairos/`.
audit 산출물은 `docs/sprints/sprint-27d-pre-ga-audit/` 하위에 저장한다.

본 프롬프트와 함께 첨부된 `SCOPE.md` 파일이 audit 의 **단일 진실 (Single Source of Truth)** 이다.
SCOPE.md 의 6명 에이전트 정의·범위·verdict 기준·산출물 포맷을 그대로 따른다.

---

## 1. 사전 컨텍스트 (이 시점에 너가 알아야 할 것)

- main HEAD: `457c994` (Sprint 27c P0 fix bundle, PR #107 머지 완료)
- 현재 브랜치: `sprint-27d/pre-ga-audit-prompts` (audit 프롬프트 작성용)
- **audit 실행 브랜치**: 새로 분기 권장 (`sprint-27d/audit-run`)
- 로컬 서버 기동 상태 (사용자가 직접 띄움):
  - FE: `http://localhost:3000`
  - BE: `http://localhost:8000/api/v1`
- DB: Neon dev branch (사용자 `backend/.env` 의 `DATABASE_URL`)
- Clerk: dev instance (Production 미발급, ADR-022 webhook SKIP)
- GEMINI_API_KEY: 사용자 갱신 여부 확인 후, 미갱신 시 AI 흐름 fail 으로 측정 진행

---

## 2. 진행 워크플로우

### Step 0 — 환경 검증 (5분)

```bash
# 헬스체크
curl -s http://localhost:8000/api/v1/health | head
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/

# Clerk dev key + GEMINI key 존재 확인 (값 노출 X)
grep -E "^(CLERK_|GEMINI_)" /Users/woosung/project/agy-project/kairos/backend/.env | sed 's/=.*/=***/'

# seed fixture 사용 가능 여부
ls -la ~/.kairos-qa-secrets/seed-credentials-*.env 2>/dev/null || echo "seed creds 없음 — 새로 생성 필요"
```

### Step 1 — 필수 문서 Read (10분)

`SCOPE.md` 의 §0 "참고 문서 절대경로" 5개 Read.
각 에이전트별 §2 추가 필수 문서도 해당 에이전트 진입 시 Read.

### Step 2 — 진행 옵션 lock-in (사용자 답변 1줄)

사용자에게 진행 옵션 (A/B/C) 묻고 lock-in. `AskUserQuestion` 사용.
권장: **B 순차 6개** (안전, 4.5h) 또는 **C Hybrid** (3h).

### Step 3 — 에이전트별 실행

진행 옵션에 따라:
- **순차 (B)**: 1→2→3→4→6→5 순. 각 에이전트마다 `TaskCreate` 등재 + `in_progress` 마킹 → 완료 시 `completed`.
- **병렬 (A/C)**: 독립 에이전트는 `Agent` 도구로 sub-agent 분기 가능. 단, MCP Playwright 세션 상태 격리 필요 → 신중.

**각 에이전트 사이클**:
1. SCOPE.md §2 의 본인 정의 read.
2. 페르소나 시나리오 1-2 단락 명문화.
3. MCP Playwright 도구 사용 (deferred — `ToolSearch` 로 `select:mcp__playwright__browser_navigate,mcp__playwright__browser_snapshot,mcp__playwright__browser_click,mcp__playwright__browser_fill_form,mcp__playwright__browser_press_key,mcp__playwright__browser_console_messages,mcp__playwright__browser_network_requests,mcp__playwright__browser_wait_for,mcp__playwright__browser_take_screenshot,mcp__playwright__browser_resize,mcp__playwright__browser_evaluate` 한 번에 schema fetch).
4. SCOPE.md §1 "공통 사전 작업" §4 "사용 가이드" §5 "산출물 포맷" 준수.
5. 시간 cap 엄수 (45/30/60분, SCOPE §2 명시).
6. 산출물: `docs/sprints/sprint-27d-pre-ga-audit/{agent-id}.md` + 스크린샷.

### Step 4 — 통합 보고

6 에이전트 산출물 → `docs/sprints/sprint-27d-pre-ga-audit/integrated-report.md`.
SCOPE.md §6 의 GO 조건 4개 평가 후 GO/NO-GO/NEEDS-FIX 명시.
미달 시 `docs/REFACTORING-BACKLOG.md` 에 BL-S27d-* 등재.

### Step 5 — 커밋 + PR

- 산출물 전체 + integrated-report.md 한 commit.
- 커밋 메시지 컨벤션: `docs:` (Sprint 27c 와 동일).
- PR 생성은 **사용자 승인 후**.

---

## 3. Opus 특화 가이드

- **1M context** 강점 활용 — 6 에이전트 모두 단일 세션 진행 가능 (context 분할 불필요).
- 단, 산출물이 길어지면 메모리 압박. 산출물 작성 후에는 SCOPE.md 만 reference 로 유지.
- `Agent` 도구로 Explore subagent 분기 가능 — 단, audit 본 행동은 main session 이 직접 수행 (페르소나 일관성 유지).
- 모든 도구 결과 → 산출물 markdown 에 즉시 기록. 메모리만 의지하지 말고 파일로 persist.
- 사용자가 한국어로 답함 → 응답도 한국어 (코드/식별자는 영어). CLAUDE.md 글로벌 규칙.

---

## 4. 주의사항 (실패 모드 회피)

- **Plan mode 진입 금지** — audit 는 실행 작업. 사용자가 `/plan` 명시하지 않으면 바로 진행.
- **세션 격리** — agent-5 (일반사용자) 는 다른 5개 결과를 보지 말고 진입 (첫인상 격리). 순차 B 의 경우 마지막에 두는 이유.
- **GEMINI fail 도 데이터** — Gemini key 없거나 quota 초과면 그것 자체를 P0 결함으로 기록. AI 흐름만 skip 하고 다른 시나리오 계속.
- **localStorage drift** — 한 세션에서 여러 계정 swap 시 localStorage 명시적 clear (`browser_evaluate("localStorage.clear()")`).
- **45분 cap 엄수** — 한 에이전트가 cap 초과하면 그 시점의 부분 결과로 산출물 작성 + cap 초과 사실 명시.

---

## 5. 시작 신호

준비 완료되면 다음 명령으로 시작:
```
SCOPE.md 를 읽고 Step 0 환경 검증부터 시작해줘.
```

성공 시 종료 보고 형식 (사용자에게):
- composite verdict X.X/10
- GO / NO-GO / NEEDS-FIX
- BL-S27d-* 신규 등재 N건
- 후속 추천 Sprint
