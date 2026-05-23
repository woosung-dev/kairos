# Session Inputs — 새 세션 복붙용 단일 메시지 (B 안 — fix 와 audit 분리)

각 `.txt` 파일은 **새 CLI 세션 첫 메시지로 그대로 복붙** 가능한 self-contained 프롬프트.
각 파일에 `[GOAL ...]` 블록 포함 — Stop hook 으로 자동 등록 (또는 사용자가 `/goal <copy-from-prompt>` 명시 등록).

## 진행 순서 (3 세션 순차)

| 순서 | 세션 | CLI | 파일 | 목적 |
|------|------|-----|------|------|
| 1 | **opus-fix** | Claude Code (Opus 4.7) | `opus-fix.txt` | opus 가 발견한 결함 4건 fix + 검증 루프 + push |
| 2 | **agy** | Antigravity CLI | `agy.txt` | opus fix 회귀 가드 + opus cross-check + DEFERRED 3건 보강 |
| 3 | **codex** | OpenAI Codex CLI | `codex.txt` | 3-세션 회귀 + adversarial + 최종 통합 + GO/NO-GO |

> 1차 opus audit (composite 7.53/10 GO, 결함 7건 발견) 는 이미 완료 (PR #108 commit `6d70eb2`).
> 이 디렉토리의 .txt 는 그 **후속 3 세션** 용.

---

## 사용 절차 (각 세션 공통)

### 1. 환경 준비 (사용자 액션, 매 세션 시작 전 1회)

```bash
cd /Users/woosung/project/agy-project/kairos
git fetch origin
git checkout sprint-27d/pre-ga-audit-prompts
git pull origin sprint-27d/pre-ga-audit-prompts

# 로컬 서버 기동 확인
curl -s -o /dev/null -w "FE: %{http_code} BE: " http://localhost:3000/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/health
# 둘 다 200 이어야 함
```

### 2. 새 CLI 세션 시작 + 복붙

```bash
# 해당 세션 input 파일 내용 출력
cat docs/sprints/sprint-27d-pre-ga-audit/session-inputs/opus-fix.txt
# 또는 agy.txt 또는 codex.txt
```

위 출력 내용을 **통째로 복사** → 해당 CLI (Claude Code / Antigravity / OpenAI Codex) 새 세션 첫 메시지로 붙여넣기.

### 3. goal 등록 확인

각 .txt 의 `[GOAL ...]` 블록이 자동으로 Stop hook 으로 작동.
CLI 가 `/goal` slash command 별도 지원 시 사용자가 명시 등록:

```
/goal sprint-27d/pre-ga-audit-prompts 브랜치에서 (해당 .txt 의 [GOAL ...] 블록 본문 복붙)
```

### 4. 세션 자동 진행 + 종료 보고 수신

세션이 모든 Step 끝까지 자동 진행. 종료 시 사용자에게 보고 (commit hash, GO/NO-GO 등). 다음 세션 진입 결정.

---

## 워크플로우 (B 안 — fix 와 audit 분리)

```
opus 1차 audit (완료, composite 7.53/10 GO, 결함 7건)
  ↓
[1] opus-fix.txt 세션 — Claude Code (Opus 4.7)
    Step 1: BUG-S27d-1 OnboardingTooltip PopoverTrigger nativeButton fix
    Step 2: BUG-S27d-2 /actions 404 → /inbox redirect
    Step 3: BUG-S27d-3 file upload mime/extension whitelist (415)
    Step 4: BUG-S27d-4 보안 헤더 (FE next.config + BE middleware)
    Step 5: BUG-S27d-6/7 → BL-S27e-1/2 등재
    Step 6: 통합 검증 (pytest + typecheck + vitest + MCP Playwright 회귀)
    Step 7: commit + push (PR #108)
  ↓
[2] agy.txt 세션 — Antigravity CLI
    Step 1: opus fix 4건 회귀 가드 (독립 시각 검증)
    Step 2: opus 6 agent cross-check (verdict 재평가)
    Step 3: DEFERRED 3건 보강 (E3 RAG leak / E5 visibility / E7 drift)
    Step 4: agy-* 산출물 + agy-report.html
    Step 5: commit + push (PR #108 업데이트)
  ↓
[3] codex.txt 세션 — OpenAI Codex CLI
    Step 1: opus fix + agy 결과 3중 회귀 가드
    Step 2: opus + agy cross-check (tie-breaker)
    Step 3: adversarial (SQL injection / prompt injection / racey upload 등)
    Step 4: 3-세션 통합 + final-integrated-report.md + final-report.html
    Step 5: 최종 GO/NO-GO + commit + push (PR #108 최종)
```

**fix 작성자 = opus / fix reviewer = agy + codex** → 독립적 cross-check 신뢰도 ↑.

---

## 산출물 디렉토리

```
docs/sprints/sprint-27d-pre-ga-audit/
├── (opus 1차 산출물 — 이미 commit 됨)
│   ├── SCOPE.md
│   ├── agent-1~6.md
│   ├── integrated-report.md
│   └── report.html
│
├── session-inputs/         ← 본 디렉토리 (3 세션 진입용)
│   ├── README.md (본 파일)
│   ├── opus-fix.txt
│   ├── agy.txt
│   └── codex.txt
│
├── agy/                    ← agy 세션 산출물
│   ├── agy-fix-regression.md
│   ├── agy-cross-check.md
│   ├── agy-deferred-scenarios.md
│   ├── agy-integrated-report.md
│   ├── agy-report.html
│   └── screenshots/
│
├── codex/                  ← codex 세션 산출물
│   ├── codex-regression.md
│   ├── codex-cross-check.md
│   ├── codex-adversarial.md
│   ├── codex-final-report.html
│   └── screenshots/
│
├── final-integrated-report.md  ← 3-세션 통합 (codex 작성)
└── final-report.html           ← 3-세션 통합 HTML (codex 작성)
```

---

## 결함 prefix 컨벤션

| 세션 | prefix | 의미 |
|------|--------|------|
| opus 1차 | `BUG-S27d-1 ~ 7` | 이미 발견 (Sentry 5번은 SKIP) |
| opus-fix | (수정 작업) | fix log 만 추가, 신규 결함 발견 시 BUG-S27d-OPUS-* |
| agy | `BUG-S27d-AGY-*` | agy cross-check + DEFERRED 보강 중 신규 |
| codex | `BUG-S27d-CODEX-*` | codex adversarial 신규 |

→ 3 세션 종료 시 `final-integrated-report.md` 에 모든 결함 종합.

---

## 주의사항

- **opus-fix 세션이 fix 끝까지 못 한 경우 (예: pytest fail)** — agy 세션은 진입 전 git log 로 opus fix commit 확인. fix 가 partial 이면 agy 가 회귀 가드 → 부분 PASS 만 인정 + codex 에 인계.
- **MCP Playwright 도구** — 세 CLI 모두 동일하게 사용 가능 (브라우저 자동화 표준).
- **commit/push** — 본 goal 안에 사전 승인되어 있으므로 세션이 자동 진행. CLAUDE.md Git Safety Protocol 의 사용자 승인 step 은 본 goal 진입 시 한 번에 묶여 인정.
- **응답 언어** — 모두 한국어 (CLAUDE.md 글로벌, 코드/식별자만 영어).
- **DB / 계정 공유** — 3 세션이 같은 로컬 DB + d@e.com 계정 사용. 시간 분리 (순차) 권장 — IDOR audit noise 회피.

---

## 비교: 기존 followup vs 본 session-inputs

| 항목 | followup-*.md (이전) | session-inputs/*.txt (현재) |
|------|---------------------|---------------------------|
| 형식 | 가이드 + 사용자 액션 + 본문 섞임 | 복붙 즉시 사용 단일 메시지 |
| fix 위치 | agy 가 fix + audit | opus-fix 가 fix, agy/codex 가 audit only (B 안) |
| 세션 수 | 2 (agy + codex) | 3 (opus-fix + agy + codex) |
| 신뢰도 | agy self-fix + self-audit (conflict) | fix 작성자 ≠ reviewer (독립적) |
