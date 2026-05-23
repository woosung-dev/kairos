# Sprint 27d Pre-GA Audit — **codex 후속 세션** 진입 프롬프트 (최종)

> opus + agy 세션이 audit 끝낸 직후. 이 세션은 **OpenAI Codex CLI** 가 같은 브랜치에서 최종 cross-check + 통합 보고.
> **순서**: opus (완료, commit `6d70eb2`) → agy (완료, agy/ 디렉토리) → **codex (현재, 마지막)**.

---

## 새 세션 진입 절차 (사용자 액션)

1. **로컬 서버 기동 확인**
   ```bash
   curl -s -o /dev/null -w "FE: %{http_code}\n" http://localhost:3000/
   curl -s -o /dev/null -w "BE: %{http_code}\n" http://localhost:8000/api/v1/health
   ```

2. **브랜치 + agy 결과 fetch**
   ```bash
   cd /Users/woosung/project/agy-project/kairos
   git fetch origin
   git checkout sprint-27d/pre-ga-audit-prompts
   git pull origin sprint-27d/pre-ga-audit-prompts
   ls docs/sprints/sprint-27d-pre-ga-audit/agy/  # agy 결과 확인
   ```

3. **codex CLI 새 세션 시작** 후 첫 메시지로 본 프롬프트 전체 복붙.

4. **goal 등록** (Stop hook 자동 보장):
   ```
   /goal sprint-27d/pre-ga-audit-prompts 브랜치에서 opus + agy 결과 모두 cross-check + DEFERRED 잔여 보강 + docs/sprints/sprint-27d-pre-ga-audit/codex/ 하위 산출물 작성 + codex-final-report.md + codex-final-report.html + final-integrated-report.md (3-세션 통합) + 동일 브랜치 commit + push (PR #108 최종 업데이트) + 최종 GO/NO-GO 판정까지 모두 완료
   ```

---

## 0. 너의 임무

너는 Kairos 프로젝트의 **외부 5명 dogfooding 진입 직전 자체 audit** 의 **codex 최종 세션** 평가 에이전트다.

opus + agy 가 audit 끝냄. 너는 **같은 브랜치 `sprint-27d/pre-ga-audit-prompts` 에 최종 commit** 으로:

1. **opus + agy 결과 모두 cross-check** — 두 세션의 verdict 가 일치하는지. 불일치 시 codex 가 tie-breaker.
2. **adversarial 시각** — codex 의 "200 IQ autistic developer" 패턴으로 BUG 위치 / 회귀 가드 / IDOR / edge case 다시 시도.
3. **DEFERRED 잔여 보강** — agy 가 못 끝낸 부분 (있다면).
4. **3-세션 통합** — `final-integrated-report.md` (opus + agy + codex 결과 종합)
5. **최종 GO/NO-GO** — 4 GO 조건 재검증 + 외부 5명 진입 최종 판정
6. **산출물**: `docs/sprints/sprint-27d-pre-ga-audit/codex/` 하위
   - `codex-cross-check.md` (opus + agy verdict 재평가)
   - `codex-adversarial.md` (adversarial 시각 신규 발견)
   - `codex-final-report.md`
   - `codex-final-report.html`
   - `screenshots/`
7. **루트 산출물**: `docs/sprints/sprint-27d-pre-ga-audit/final-integrated-report.md` + `final-report.html` (opus/agy/codex 3-세션 종합)
8. **commit + push** — 같은 브랜치 → PR #108 최종 업데이트

---

## 1. 사전 컨텍스트

### 환경 (opus + agy 동일)
- main HEAD: `457c994`
- 브랜치: `sprint-27d/pre-ga-audit-prompts`
- FE: `http://localhost:3000` / BE: `http://localhost:8000/api/v1`
- Clerk dev / GEMINI_API_KEY set / 계정 `d@e.com`
- Personal workspace `e968c95f-...` + Team `7f9f446d-...` ("QA Cycle C Team")
- production audit SKIP / Sentry SKIP (사용자 정책)

### opus 결과 (composite 7.53/10 GO)
- agent-1 7.2 / agent-2 8.0 / agent-3 6.5 / agent-4 7.5 / agent-5 7.8 / agent-6 8.2

### opus 발견 결함 7건
| ID | 우선순위 | 결함 |
|----|---------|------|
| BUG-S27d-1 | P1 회귀 | OnboardingTooltip PopoverTrigger (BL-S27c-8) |
| BUG-S27d-2 | P2 회귀 | /actions 404 |
| BUG-S27d-3 | P2 | File upload mime validation 부재 |
| BUG-S27d-4 | P1 | 보안 헤더 부재 |
| ~~BUG-S27d-5~~ | — | Sentry 정책 SKIP |
| BUG-S27d-6 | P3 | RAG latency dev avg 10.6s |
| BUG-S27d-7 | P3 | 사이드바 nav flicker |

### agy 결과 (read 필요)
- `docs/sprints/sprint-27d-pre-ga-audit/agy/` 하위 모든 .md
- 신규 결함 prefix `BUG-S27d-AGY-*` 가 있을 수 있음

---

## 2. 진행 워크플로우

### Step 0 — 환경 검증 (5분)
```bash
curl -s -o /dev/null -w "FE: %{http_code}\n" http://localhost:3000/
curl -s -o /dev/null -w "BE: %{http_code}\n" http://localhost:8000/api/v1/health
mkdir -p docs/sprints/sprint-27d-pre-ga-audit/codex/screenshots
```

### Step 1 — opus + agy 산출물 read (15분)
opus:
- `SCOPE.md`
- `agent-1-qa-function.md` ~ `agent-6-solo-personal.md`
- `integrated-report.md`
- `report.html`

agy:
- `agy/agy-cross-check.md`
- `agy/agy-deferred-scenarios.md`
- `agy/agy-integrated-report.md`
- `agy/agy-report.html`

### Step 2 — opus + agy verdict cross-check (15분)
| Agent | opus | agy | codex 재평가 | 최종 |
|-------|------|-----|------------|------|
| agent-1 | 7.2 | (agy 결과) | (codex 결과) | (3개 합의) |
| ... | ... | ... | ... | ... |

불일치 시 codex 가 tie-breaker. `codex/codex-cross-check.md`.

### Step 3 — Adversarial 시각 (30분, codex 강점)
- IDOR 5 endpoint 재시도 with creative payloads (SQL injection / 큰 payload / 특수 문자)
- File upload 추가 시도 (100MB+ / null byte filename / racey concurrent)
- RAG 질의 with prompt injection 시도
- Personal workspace 강제 변경 시도
- Project visibility race condition

→ `codex/codex-adversarial.md`

### Step 4 — DEFERRED 잔여 보강 (10분)
agy 가 못 끝낸 영역 마무리.

### Step 5 — 3-세션 통합 (15분)
- `final-integrated-report.md` — opus + agy + codex 결과 종합 표
- `final-report.html` — opus `report.html` 의 스타일 차용 + 3 세션 결과 통합

### Step 6 — 최종 GO/NO-GO 판정 (5분)
GO 조건 4개 재검증:
1. composite (3 세션 평균) ≥ 7.0/10
2. IDOR leak 0건 (cross-check 후)
3. 일반사용자 추천 YES (3 세션 모두)
4. Solo-A-to-Z FAIL ≤ 5 cells

→ 4/4 충족 → **외부 5명 진입 최종 GO**
→ 미달 → **NEEDS-FIX** 결함 list + BL-S27e-* 등재

### Step 7 — 커밋 + push (5분)
```bash
git add docs/sprints/sprint-27d-pre-ga-audit/codex/ docs/sprints/sprint-27d-pre-ga-audit/final-*.md docs/sprints/sprint-27d-pre-ga-audit/final-*.html
git commit -m "docs: Sprint 27d codex final audit — 3-세션 통합 + GO/NO-GO 최종

(상세 본문)

Co-Authored-By: OpenAI Codex <noreply@...>"
git push origin sprint-27d/pre-ga-audit-prompts
# PR #108 최종 업데이트
```

---

## 3. codex 특화 가이드

- **adversarial mode** — codex 의 challenge 패턴. "이게 안 깨질까?" 마음가짐.
- **200 IQ autistic developer** — opus 가 놓친 edge case 발굴.
- **Bash + curl 다수 사용** — Codex CLI 강점.
- **MCP Playwright integration** — 동일 도구 사용.
- **한국어 응답** — 사용자 한국어 → 응답도 한국어.

---

## 4. 산출물 매트릭스 포맷

### codex-cross-check.md
3 세션 verdict 매트릭스 + tie-breaker 판정.

### final-integrated-report.md
- 3 세션 composite (평균 또는 가중평균)
- 결함 list (opus BUG-S27d-* + agy BUG-S27d-AGY-* + codex BUG-S27d-CODEX-*)
- 회귀 가드 매트릭스 (3 세션 모두 통과 / 일부 통과 / 통과 안 함)
- 최종 GO/NO-GO + 진입 전 fix 권고

### final-report.html
- opus `report.html` 의 스타일 (dark mode, condition grid, bug card) 동일
- 3 세션 결과 비교 섹션 추가
- 최종 verdict 큰 글씨

---

## 5. 시작 신호

```
SCOPE.md + opus 산출물 + agy 산출물 모두 read 후 Step 0 환경 검증부터 시작해줘.
```

종료 보고 (사용자에게):
- 3-세션 composite 점수 X.X/10
- 최종 GO / NO-GO / NEEDS-FIX
- 새 결함 BUG-S27d-CODEX-* N건 (또는 BUG-S27d-AGY-* 확인)
- 외부 5명 진입 권고 사항
- PR #108 최종 update commit hash
