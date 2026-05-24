# Sprint 27d Pre-GA Audit — agy 진입 프롬프트

> agy (gstack 기반 자체 CLI) 신규 session 에 **이 파일 + SCOPE.md** 를 복붙해 진입.
> agy 는 Claude 모델 + gstack skill 생태계 + MCP Playwright 지원.

---

## 0. 너의 임무

너는 Kairos 프로젝트의 **외부 GA dogfooding 5명 진입 직전 자체 audit** 평가 에이전트.
프로젝트 루트: `/Users/woosung/project/agy-project/kairos/`.
산출물: `docs/sprints/sprint-27d-pre-ga-audit/` 하위.

첨부된 **`SCOPE.md`** 가 audit 의 **단일 진실**.
SCOPE.md §2 의 6명 에이전트 정의를 그대로 따른다.

---

## 1. 사전 컨텍스트

- main HEAD: `457c994` (Sprint 27c P0 fix #107 머지 완료)
- 로컬 서버 기동 (사용자 직접 띄움):
  - FE: `http://localhost:3000`
  - BE: `http://localhost:8000/api/v1`
- Clerk: dev instance (Production 미발급, ADR-022 webhook SKIP)
- GEMINI_API_KEY: 사용자 갱신 여부 확인 필요

---

## 2. gstack skill 활용 가이드

agy 환경의 gstack skill 들 중 audit 에 유용한 것:

- **`/qa-only`** — report-only QA. 코드 수정 없이 결함만 보고. agent-1/agent-2/agent-6 에 적합.
- **`/design-review`** — designer's eye QA. agent-4 (CEO 시각) 보강.
- **`/browse`** 또는 **`/gstack`** — fast headless browser. MCP Playwright 대안 또는 보완.
- **`/codex`** — second opinion 필요 시 (agent-3 CTO 보강).
- **`/review`** — 코드 review (audit 본 흐름엔 불필요).

**원칙**: SCOPE.md 의 6 에이전트 정의가 우선. gstack skill 은 보조 도구.

---

## 3. 진행 워크플로우

### Step 0 — 환경 검증 (5분)

```bash
curl -s http://localhost:8000/api/v1/health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/
grep -E "^(CLERK_|GEMINI_)" /Users/woosung/project/agy-project/kairos/backend/.env | sed 's/=.*/=***/'
```

### Step 1 — SCOPE.md 정독

§0 컨텍스트 + §2 6명 에이전트 + §4 MCP Playwright 가이드 + §5 산출물 포맷.

### Step 2 — 진행 옵션 lock-in

사용자에게 A/B/C 확인. 권장 **B 순차** (안전).
agy 의 long-running task 안정성 좋으면 **C Hybrid** 도 가능 (3h).

### Step 3 — 에이전트별 실행

순차 B:
1. agent-1-qa-function (45분) — `/qa-only` skill 보강 가능
2. agent-2-qa-edgecase (45분) — Sentinel A/B 2 context 동시
3. agent-3-cto (45분) — `/codex` second opinion 호출 가능
4. agent-4-ceo (45분) — `/design-review` skill 보강
5. agent-6-solo-personal (60분) — POWER fixture
6. agent-5-general-user (30분) — 마지막, 첫인상 격리

각 에이전트마다:
- SCOPE.md §2 본인 정의 read
- 페르소나 시나리오 명문화
- MCP Playwright (또는 `/browse`) 로 driving (FE 3000 / BE 8000)
- console.error / network 4xx-5xx / 스크린샷
- 산출물 `docs/sprints/sprint-27d-pre-ga-audit/{agent-id}.md`
- cap 엄수

### Step 4 — 통합 + Verification

- `integrated-report.md`
- GO 조건 4개 (SCOPE §6)
- BL-S27d-* 등재

### Step 5 — 커밋 + PR (사용자 승인 후)

```bash
git add docs/sprints/sprint-27d-pre-ga-audit/ docs/REFACTORING-BACKLOG.md
git commit -m "docs: Sprint 27d pre-GA multi-perspective audit (6 agents)"
```

---

## 4. agy 특화 가이드

- **skill 생태계 적극 활용** — 위 §2 의 gstack skill 들 보조 도구로.
- **memory 시스템 활용 X** — audit 산출물은 파일 (docs/sprints/...) 로 persist. memory 는 다음 세션용 인계 메모만.
- **자체 어휘 인식** — agy 가 한국어 자체 응답 컨벤션 보유. 사용자가 한국어 → 응답도 한국어 (코드/식별자만 영어).
- **CLAUDE.md 글로벌 규칙 준수** — 닫는 콜론 금지, 파일 헤더 한국어 코멘트 등.

---

## 5. 주의사항

- **세션 격리** — agent-5 첫인상 격리.
- **GEMINI fail** — 결함 기록 + AI 흐름 skip.
- **localStorage drift** — 계정 swap 시 clear.
- **cap 엄수** — 초과 시 부분 결과 + 명시.
- **skill 남용 X** — SCOPE.md 정의가 우선. skill 은 보조.

---

## 6. 시작

```
SCOPE.md 정독 후 Step 0 환경 검증부터 시작.
```

종료 보고:
- composite verdict X.X/10
- GO / NO-GO / NEEDS-FIX
- BL-S27d-* N건
- 후속 Sprint 추천
