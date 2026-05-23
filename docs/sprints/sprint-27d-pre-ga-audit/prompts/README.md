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
