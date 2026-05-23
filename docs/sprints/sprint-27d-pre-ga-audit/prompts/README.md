# Sprint 27d Pre-GA Audit — 진입 프롬프트 사용 안내

> 외부 GA dogfooding 5명 진입 직전 6명 평가 에이전트가 MCP Playwright 로 로컬 환경 audit.
> 본 디렉토리의 프롬프트 1개 + 상위의 `SCOPE.md` 를 함께 복붙해 audit 세션에 진입.

---

## 디렉토리 구조

```
docs/sprints/sprint-27d-pre-ga-audit/
├── SCOPE.md                      ← 단일 진실 (6 에이전트 정의 + 워크플로우)
├── prompts/
│   ├── README.md                 ← 본 파일
│   ├── agent-prompt-opus.md      ← Claude Opus 4.7 (1M context)
│   ├── agent-prompt-codex.md     ← OpenAI Codex CLI (200k)
│   └── agent-prompt-agy.md       ← agy / gstack CLI
├── {agent-id}.md                 ← audit 산출물 (실행 후 생성)
├── screenshots/                  ← 캡처 모음
└── integrated-report.md          ← 6명 통합 보고 (실행 후 생성)
```

---

## 3 프롬프트 비교

| 항목 | opus | codex | agy |
|------|------|-------|-----|
| 모델/엔진 | Claude Opus 4.7 | OpenAI Codex CLI | agy (gstack) |
| context | 1M tokens | ~200k | Claude 모델 의존 |
| MCP Playwright | ✅ native | ✅ MCP integration | ✅ + `/browse` skill 대안 |
| 강점 | 단일 세션 6명 모두 가능, 긴 산출물 | 안정적 long-running, Bash 다수 | gstack skill (`/qa-only`, `/design-review`, `/codex`) 보강 |
| 적합 시나리오 | **순차 B 단일 세션 권장** | 순차 B (안정) | Hybrid C (skill 보강) |

---

## 사용 방법

### 1. 환경 준비 (사용자)

```bash
# 1) 로컬 서버 기동 (이미 띄워져 있다면 skip)
cd backend && uv run alembic upgrade head && uv run uvicorn src.main:app --port 8000 &
cd frontend && npm run dev -- -p 3000 &

# 2) GEMINI_API_KEY 갱신 권고 (없으면 AI 흐름 fail 으로 진행 가능)
# backend/.env 에서 GEMINI_API_KEY=... 갱신

# 3) seed fixture (필요 시)
cd backend && uv run python scripts/seed_qa_fixtures.py --env ~/.kairos-qa-secrets/seed-credentials.env --out /tmp/fixtures.json
```

### 2. 모델 선택 → 프롬프트 복붙

선택한 모델의 프롬프트 파일 + `SCOPE.md` **두 파일 전체를 통째로** 새 세션에 복붙.

권장 조합:
- **단독 운영** → opus (1M context, 세션 분할 불필요)
- **gstack 사용자** → agy (`/qa-only` 등 skill 보강)
- **빠른 실행** → codex (안정성 + 짧은 cap)

### 3. 진행 옵션 lock-in

세션 진입 직후 사용자에게 묻는 질문:

> 진행 옵션 A (동시 6개, 1.5h) / B (순차 6개, 4.5h, 권장) / C (Hybrid, 3h) 중 선택?

대부분의 경우 **B** 또는 **C** 권장.

### 4. 실행 → 통합 보고

각 에이전트가 자체 산출물 생성 (`{agent-id}.md`) → 마지막에 `integrated-report.md` 통합 → GO/NO-GO 판정.

### 5. 커밋

사용자 승인 후:
```bash
git add docs/sprints/sprint-27d-pre-ga-audit/
git commit -m "docs: Sprint 27d pre-GA multi-perspective audit (6 agents)"
```

---

## 사용자 액션 잔여 (audit 실행 전 ideally)

- [ ] BE/FE 로컬 서버 기동 확인
- [ ] GEMINI_API_KEY 갱신 (또는 fail 으로 진행 동의)
- [ ] seed fixture 또는 5계정 직접 가입 결정
- [ ] 3 프롬프트 중 1개 선택
- [ ] 진행 옵션 (A/B/C) 결정

---

## GO 조건 (audit 종료 후)

| # | 조건 | 측정 |
|---|------|------|
| 1 | composite verdict ≥ 7.0/10 | 6 에이전트 평균 |
| 2 | IDOR leak 0건 | agent-2 결과 |
| 3 | 일반사용자 추천 yes | agent-5 결과 |
| 4 | Solo-A-to-Z FAIL ≤ 5 cells | agent-6 결과 |

4개 모두 충족 → **외부 5명 진입 GO**.
미달 → `docs/REFACTORING-BACKLOG.md` BL-S27d-* 등재 → Sprint 27d 진입.

---

## 🔁 후속 세션 (opus 1차 audit 종료 후, 같은 브랜치 이어서)

opus 가 1차 audit 끝낸 후 (PR #108, commit `6d70eb2`) **같은 브랜치 `sprint-27d/pre-ga-audit-prompts` 에서 이어서** agy → codex 순차 진행.

| 순서 | 세션 | 프롬프트 파일 | 목적 |
|------|------|--------------|------|
| 1 | opus | ✅ 완료 (이 directory 의 SCOPE + agent-1~6 + report.html) | 1차 audit |
| 2 | **agy** | `agent-followup-agy.md` | cross-check + DEFERRED 3건 보강 |
| 3 | **codex** | `agent-followup-codex.md` | 3-세션 통합 + 최종 GO/NO-GO + adversarial |

### 진입 절차 (각 세션 공통)

1. 로컬 서버 기동 확인 (FE :3000 / BE :8000)
2. 브랜치 fetch + checkout: `git checkout sprint-27d/pre-ga-audit-prompts && git pull`
3. 해당 CLI (agy 또는 codex) 새 세션 시작
4. **followup 프롬프트 본문 통째로 복붙**
5. **goal 등록** — Stop hook 자동 보장 (각 프롬프트 §"새 세션 진입 절차" §4 의 goal condition 사용)
6. 세션이 alle 작업 자동 진행 → PR #108 push 까지

### 산출물 디렉토리

```
docs/sprints/sprint-27d-pre-ga-audit/
├── (opus 산출물 — 이미 commit)
├── agy/             ← agy 세션 산출물
│   ├── agy-cross-check.md
│   ├── agy-deferred-scenarios.md
│   ├── agy-integrated-report.md
│   ├── agy-report.html
│   └── screenshots/
├── codex/           ← codex 세션 산출물
│   ├── codex-cross-check.md
│   ├── codex-adversarial.md
│   ├── codex-final-report.md
│   ├── codex-final-report.html
│   └── screenshots/
├── final-integrated-report.md  ← 3-세션 통합 (codex 작성)
└── final-report.html           ← 3-세션 통합 HTML (codex 작성)
```

### 결함 prefix 컨벤션

| 세션 | prefix | 예 |
|------|--------|-----|
| opus | `BUG-S27d-*` | BUG-S27d-1 ~ BUG-S27d-7 |
| agy | `BUG-S27d-AGY-*` | BUG-S27d-AGY-1 ... |
| codex | `BUG-S27d-CODEX-*` | BUG-S27d-CODEX-1 ... |

→ 3 세션 결함 모두 prefix 로 출처 추적 가능.
