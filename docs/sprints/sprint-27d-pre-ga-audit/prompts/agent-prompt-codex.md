# Sprint 27d Pre-GA Audit — OpenAI Codex CLI 진입 프롬프트

> OpenAI Codex CLI (`codex` 명령) 신규 session 에 **이 파일 + SCOPE.md** 를 복붙해 진입.
> Codex CLI 는 200k context, MCP Playwright 지원, Bash/Read/Write 도구 사용 가능.

---

## 0. 너의 임무

너는 Kairos 프로젝트의 **외부 GA dogfooding 5명 진입 직전 자체 audit** 평가 에이전트.
프로젝트 루트: `/Users/woosung/project/agy-project/kairos/`.
산출물: `docs/sprints/sprint-27d-pre-ga-audit/` 하위.

본 프롬프트와 함께 첨부된 **`SCOPE.md`** 가 audit 의 **단일 진실**.
SCOPE.md 의 6명 에이전트 정의·범위·verdict 기준·산출물 포맷을 그대로 따른다.

---

## 1. 사전 컨텍스트

- main HEAD: `457c994` (Sprint 27c P0 fix #107 머지 완료)
- 로컬 서버 기동 (사용자 직접 띄움):
  - FE: `http://localhost:3000`
  - BE: `http://localhost:8000/api/v1`
- Clerk: dev instance (Production 미발급)
- GEMINI_API_KEY: 사용자 갱신 확인 필요. 미갱신 시 AI 흐름 fail 으로 측정 진행.

---

## 2. 진행 워크플로우

### Step 0 — 환경 검증 (5분)

```bash
curl -s http://localhost:8000/api/v1/health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/
grep -E "^(CLERK_|GEMINI_)" /Users/woosung/project/agy-project/kairos/backend/.env | sed 's/=.*/=***/'
```

### Step 1 — SCOPE.md 정독

본 프롬프트 옆 `SCOPE.md` 전체 read.
§2 의 6명 에이전트 정의 숙지.

### Step 2 — 사용자에게 진행 옵션 (A/B/C) 확인

권장: **B 순차** (4.5h) 또는 **C Hybrid** (3h).
Codex CLI 는 long-running task 안정적 → B 적합.

### Step 3 — 에이전트별 실행

순차 진행 (B):
1. agent-1-qa-function (45분)
2. agent-2-qa-edgecase (45분)
3. agent-3-cto (45분)
4. agent-4-ceo (45분)
5. agent-6-solo-personal (60분)
6. agent-5-general-user (30분) ← 마지막, 첫인상 격리

각 에이전트마다:
- SCOPE.md §2 본인 정의 read
- 페르소나 시나리오 명문화
- MCP Playwright 로 driving (FE 3000 / BE 8000)
- console.error / network 4xx-5xx / 스크린샷 캡처
- 산출물 `docs/sprints/sprint-27d-pre-ga-audit/{agent-id}.md`
- 시간 cap 엄수

### Step 4 — 통합 + Verification

- `integrated-report.md` 작성
- GO 조건 4개 평가 (SCOPE §6)
- 미달 시 `docs/REFACTORING-BACKLOG.md` 에 BL-S27d-* 등재

### Step 5 — 커밋 + 사용자 검토

`git add docs/sprints/sprint-27d-pre-ga-audit/ docs/REFACTORING-BACKLOG.md`
커밋 메시지: `docs: Sprint 27d pre-GA multi-perspective audit (6 agents)`
PR 은 사용자 승인 후.

---

## 3. Codex CLI 특화 가이드

- **MCP 도구 사용** — Codex CLI 의 MCP integration 으로 Playwright 도구 호출. 도구 prefix 가 environment 마다 다를 수 있으니 첫 호출 전 도구 목록 확인.
- **세션 길이 관리** — 200k context. 6 에이전트 단일 세션 시 후반 context 압박. agent-3 (CTO) 종료 시 한 번 산출물 압축 (markdown 저장 후 메모리에서 비움) 권장.
- **Bash 권한** — `curl`, `grep`, `git status`, `git log` 등 read-only Bash 는 즉시. 쓰기 작업 (git add/commit) 은 사용자 승인 후.
- **한국어 응답** — 사용자가 한국어 → 응답도 한국어. CLAUDE.md 글로벌.

---

## 4. 주의사항

- **세션 격리** — agent-5 는 다른 결과 보지 말고 진입. 순차 B 마지막 배치.
- **GEMINI fail** — key 없거나 quota 초과면 결함으로 기록 + AI 흐름만 skip.
- **localStorage drift** — 계정 swap 시 `localStorage.clear()` (Playwright `browser_evaluate`).
- **cap 엄수** — 초과 시 부분 결과 + cap 초과 사실 명시.
- **Codex review mode 와 혼동 X** — 이건 audit 작업이지 코드 리뷰 아님. 코드 변경 금지.

---

## 5. 시작

```
SCOPE.md 정독 후 Step 0 환경 검증부터 시작.
```

종료 보고:
- composite verdict X.X/10
- GO / NO-GO / NEEDS-FIX
- BL-S27d-* N건
- 후속 Sprint 추천
