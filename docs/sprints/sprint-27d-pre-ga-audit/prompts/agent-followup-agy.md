# Sprint 27d Pre-GA Audit — **agy 후속 세션** 진입 프롬프트

> opus 세션이 1차 audit 끝낸 직후. 이 세션은 **agy (gstack 기반 CLI)** 가 같은 브랜치에서 이어서 진행.
> **순서**: opus (완료, PR #108) → **agy (현재)** → codex (마지막).

---

## 새 세션 진입 절차 (사용자 액션)

1. **로컬 서버 기동 확인**
   ```bash
   curl -s -o /dev/null -w "FE: %{http_code}\n" http://localhost:3000/
   curl -s -o /dev/null -w "BE: %{http_code}\n" http://localhost:8000/api/v1/health
   # 둘 다 200 이어야 함. 아니면 backend/frontend 띄우기
   ```

2. **브랜치 확인** (이미 sprint-27d/pre-ga-audit-prompts 일 것)
   ```bash
   cd /Users/woosung/project/agy-project/kairos
   git fetch origin
   git checkout sprint-27d/pre-ga-audit-prompts
   git pull origin sprint-27d/pre-ga-audit-prompts
   ```

3. **agy CLI 새 세션 시작** 후 첫 메시지로 본 프롬프트 전체 복붙.

4. **goal 등록** (Stop hook 자동 보장) — 세션 안에서 다음 명령:
   ```
   /goal sprint-27d/pre-ga-audit-prompts 브랜치에서 opus 1차 audit 결과 cross-check + DEFERRED 시나리오 3건 보강 + docs/sprints/sprint-27d-pre-ga-audit/agy/ 하위 산출물 작성 + agy-integrated-report.md + agy-report.html + 동일 브랜치 commit + push (PR #108 업데이트)까지 모두 완료
   ```

---

## 0. 너의 임무

너는 Kairos 프로젝트의 **외부 5명 dogfooding 진입 직전 자체 audit** 의 **agy 후속 세션** 평가 에이전트다.

opus 가 1차 audit 끝냄 (composite 7.53/10 GO, PR #108). 너는 **같은 브랜치 `sprint-27d/pre-ga-audit-prompts` 에 추가 commit** 으로 다음 임무 수행:

1. **opus 결과 cross-check** — 6 agent 산출물의 verdict 검증. 동일 시나리오 다른 시각으로 재평가. 불일치 시 BUG-S27d-AGY-* 신규 등재.
2. **DEFERRED 시나리오 3건 보강** (opus 가 실행 어려웠던 영역):
   - agent-2 E3: Cross-tenant private RAG leak
   - agent-2 E5: Project visibility 분기 (viewer/draft/private)
   - agent-2 E7: localStorage workspace drift (A logout → B login → stale workspace_id)
3. **gstack skill 적극 활용** — `/qa-only`, `/design-review`, `/codex` second opinion
4. **신규 결함 발견 시 prefix `BUG-S27d-AGY-*`** (opus 의 BUG-S27d-* 와 구분)
5. **산출물**: `docs/sprints/sprint-27d-pre-ga-audit/agy/` 하위
   - `agy-cross-check.md` (opus 6 agent verdict 재평가)
   - `agy-deferred-scenarios.md` (E3/E5/E7 보강)
   - `agy-integrated-report.md` (agy 결과 통합)
   - `agy-report.html` (단일 self-contained HTML)
   - `screenshots/` (캡처 모음)
6. **commit + push** — 같은 브랜치 `sprint-27d/pre-ga-audit-prompts` → PR #108 자동 업데이트

---

## 1. 사전 컨텍스트 (opus 결과 요약)

### 환경
- main HEAD: `457c994` (Sprint 27c P0 fix #107 머지 완료)
- 브랜치: `sprint-27d/pre-ga-audit-prompts` (opus commit `6d70eb2` 머지 후 추가 작업)
- FE: `http://localhost:3000`
- BE: `http://localhost:8000/api/v1`
- Clerk: dev instance `creative-boxer-79.clerk.accounts.dev` (Production 미발급, ADR-022 SKIP)
- GEMINI_API_KEY: set ✅ (사용자 갱신 직후)
- 로그인 계정: `d@e.com` (dummy, Personal workspace `e968c95f-4bbe-4f12-9468-2741c047e142` + Team "QA Cycle C Team" `7f9f446d-9b7f-4ae7-aa9b-ac861fb81b11`)
- seed credentials: `~/.kairos-qa-secrets/seed-credentials-2026-05-17.env` (SENTINEL A/B/CASUAL/MOBILE/POWER, JWT expired → 재로그인 필요)
- **production audit SKIP** (사용자 정책)
- **Sentry 의도적 SKIP** (사용자 정책)

### opus 1차 audit 결과 (composite 7.53/10 GO)
| Agent | 점수 | verdict |
|-------|------|---------|
| agent-1 QA-Function | 7.2/10 | GO |
| agent-2 QA-EdgeCase | 8.0/10 | GO |
| agent-3 CTO | 6.5/10 | NEEDS-FIX (P1 1건) |
| agent-4 CEO | 7.5/10 | GO |
| agent-5 일반사용자 | 7.8/10 | GO |
| agent-6 Solo-A-to-Z | 8.2/10 | GO |
| **Composite** | **7.53** | **GO** |

### opus 발견 결함 7건
1. **BUG-S27d-1 P1**: OnboardingTooltip PopoverTrigger nativeButton 회귀 (BL-S27c-8) — /dashboard + CmdK 2위치
2. **BUG-S27d-2 P2**: /actions 404 (Sprint 27c carry-over 회귀)
3. **BUG-S27d-3 P2**: File upload mime/extension validation 부재 (R2 에 .exe 업로드 가능)
4. **BUG-S27d-4 P1**: 보안 헤더 부재 (CSP/X-Frame/등 FE+BE)
5. ~~BUG-S27d-5~~ Sentry 정책 SKIP (사용자 정정)
6. **BUG-S27d-6 P3**: RAG latency dev 환경 avg 10.6s
7. **BUG-S27d-7 P3**: 사이드바 nav flicker

### opus 강한 PASS 신호
- IDOR 5/5 endpoint 403 + Personal invite 403 (헌법 I-9/I-19 정합)
- 회의 업로드 → 30초 AI 요약 + RAG citation 정확 (Gemini 작동)
- 모바일 viewport 정상

---

## 2. 진행 워크플로우

### Step 0 — 환경 검증 (5분)
```bash
# 헬스체크 (둘 다 200 기대)
curl -s -o /dev/null -w "FE: %{http_code}\n" http://localhost:3000/
curl -s -o /dev/null -w "BE: %{http_code}\n" http://localhost:8000/api/v1/health

# 디렉토리 생성
mkdir -p docs/sprints/sprint-27d-pre-ga-audit/agy/screenshots
```

### Step 1 — opus 산출물 read (10분, 필수)
다음 6개 파일 모두 read:
- `docs/sprints/sprint-27d-pre-ga-audit/SCOPE.md` (단일 진실)
- `docs/sprints/sprint-27d-pre-ga-audit/agent-1-qa-function.md`
- `docs/sprints/sprint-27d-pre-ga-audit/agent-2-qa-edgecase.md`
- `docs/sprints/sprint-27d-pre-ga-audit/agent-3-cto.md`
- `docs/sprints/sprint-27d-pre-ga-audit/agent-4-ceo.md`
- `docs/sprints/sprint-27d-pre-ga-audit/agent-5-general-user.md`
- `docs/sprints/sprint-27d-pre-ga-audit/agent-6-solo-personal.md`
- `docs/sprints/sprint-27d-pre-ga-audit/integrated-report.md`

### Step 2 — Cross-check 6 agent (20분)
각 agent verdict 를 본인 시각에서 재평가:
- agent-1 PASS 시나리오 (회의 업로드 / RAG citation 등) 재실행 → 동일 결과 확인
- agent-2 IDOR 5 endpoint 재검증 (다른 random UUID, 다른 method)
- agent-3 보안 헤더 재확인 + RAG latency 재측정
- agent-4 랜딩 SSR 추가 분석 (모바일 카피)
- agent-5 일반사용자 첫 인상 본인 평가
- agent-6 78 cells 중 FAIL 2 확인 + 추가 페이지 인터액션

→ 산출물: `agy/agy-cross-check.md` (verdict 재평가 표 + 일치/불일치 명시)

### Step 3 — DEFERRED 시나리오 보강 (30분, 가장 중요)

#### E3 — Cross-tenant private RAG leak
- 사용자가 두 번째 Personal workspace 또는 다른 사용자 계정 보유 시: 다른 workspace 의 private note → 본인이 RAG 질의해도 인용되지 않는지 검증
- 또는 backend SQL 직접 query: `SELECT visibility FROM project WHERE ...` → RAG 검색 결과에 private/draft 가 인용되는지 cross-check
- 산출물: `agy/agy-deferred-scenarios.md` 의 E3 섹션

#### E5 — Project visibility 분기
- Personal workspace 에 project 생성 시 visibility 옵션 (public/draft/private) UI 노출 확인
- 각 visibility 별 RAG 인용 정합 검증

#### E7 — localStorage workspace drift
- 사용자 d@e.com 로그아웃 → 사용자 본인 (또는 Sentinel A) 로 재로그인
- localStorage `kairos-workspace.activeWorkspaceId` 가 stale 값 유지하는지
- stale workspace_id 로 API 호출 시 403 graceful 여부

### Step 4 — 통합 보고 + HTML (10분)
- `agy/agy-integrated-report.md` — agy 결과 (cross-check + DEFERRED 보강 + 신규 결함)
- `agy/agy-report.html` — opus `report.html` 의 스타일 차용 + agy 결과 섹션

### Step 5 — 커밋 + push (5분)
```bash
git add docs/sprints/sprint-27d-pre-ga-audit/agy/
git commit -m "docs: Sprint 27d agy follow-up audit — cross-check + DEFERRED 보강

(상세 본문)

Co-Authored-By: <agy 모델명> <noreply@...>"
git push origin sprint-27d/pre-ga-audit-prompts
# PR #108 자동 업데이트
```

---

## 3. agy 특화 가이드

- **gstack skill 활용**:
  - `/qa-only` — report-only QA (cross-check 에 적합)
  - `/codex` — second opinion (opus verdict 불일치 시)
  - `/design-review` — agent-4 CEO 시각 보강
  - `/browse` — MCP Playwright 대안
- **MCP Playwright** — opus 와 동일 사용 (browser_navigate, snapshot, evaluate, file_upload 등)
- **한국어 응답** — CLAUDE.md 글로벌 규칙
- **memory 시스템** — audit 산출물은 파일로 persist, memory 는 다음 세션용 인계만

---

## 4. 산출물 매트릭스 포맷

각 agent cross-check 결과 (`agy-cross-check.md`):

```markdown
### agent-1 QA-Function 재평가
| 시나리오 | opus | agy | 일치? |
|---------|------|-----|-------|
| #2 회의 업로드 | PASS | (재실행) | ✅/⚠️/🔴 |
| #6 RAG citation | PASS | (재실행) | ... |

agy 추가 발견:
- (있다면 BUG-S27d-AGY-* 등재)
```

---

## 5. 시작 신호

준비 완료되면:
```
SCOPE.md + opus 산출물 6개를 read 하고 Step 0 환경 검증부터 시작해줘.
```

종료 보고 형식:
- agy composite cross-check verdict X.X/10
- opus 와 일치율 N/6 agent
- DEFERRED 3건 결과 (E3/E5/E7)
- 신규 발견 BUG-S27d-AGY-* N건
- 다음 세션 (codex) 진입 가이드

---

## 6. 다음 세션 (codex) 진입 가이드

agy 세션 종료 후 사용자가 codex 세션 시작 시 `docs/sprints/sprint-27d-pre-ga-audit/prompts/agent-followup-codex.md` 참고.
codex 세션은 opus + agy 결과 모두 cross-check + 최종 통합.
