# Sprint 24 Wave 2 — Multi-Agent QA P0/P1 Fix Bundle (kickoff prompt)

Sprint 24 Wave 2 진입. Wave 1 (BL-063/064/066 promote 정합성) + ADR-019 Phase B Gemini swap 은 **Phase 0 closure 로 main 적용 완료**. 본 sprint = **Multi-Agent QA 가 발견한 P0/P1 dogfood-blocking 결함 fix bundle (16 tasks, ~24.5h)**.

데드라인 2026-05-28 — Phase B swap 자체는 충족 (T-2 측정만 잔여).

## Pre-Sprint Closure (이미 main 적용, 본 sprint 진입 baseline)

| 작업 | Commit | 산출물 |
|---|---|---|
| **Phase B Gemini swap** (T-1, 3h) | `003908a` 2026-05-15 PR #32 | `gemini-3.1-flash-lite` 6 spots ✓ |
| **Wave 1 promote 정합성** (BL-063/064/066) | `b1c777b` 2026-05-20 PR #99 | 387 pytest PASS + Codex 4 cycle APPROVE + Gemini review 100% 수락 |
| **Multi-Agent QA 산출물** (5 페르소나 + sprint-24-plan v2) | `f46a075` 2026-05-20 PR #100 | 20 BUG + 11 BL + 17 tasks (16 잔여, v2 patch `1487fdb`) |

**main HEAD = `f46a075`** / pytest baseline = **387 passed + 1 skipped** / FE typecheck 0 / vitest 50 PASS.

## 첫 read (순서 중요, 13 항목)

1. `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/MEMORY.md` — 인덱스
2. `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint24_diligent_beaver_done.md` — Wave 1 closeout
3. `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint15_adr019_phase_a_done.md` — Phase B spike (5.76x speedup verify)
4. `/Users/woosung/project/agy-project/kairos/CONTEXT-MAP.md` — 헌법 (entity + I-1~I-21 불변식 + §4.2 도메인 경계)
5. `/Users/woosung/project/agy-project/kairos/.ai/templates/workflow.md` — Stage 0~6 운영
6. `/Users/woosung/project/agy-project/kairos/.ai/common/global.md` — Atomic Update §2 매트릭스
7. `/Users/woosung/project/agy-project/kairos/docs/TODO.md` — 현재 Next Actions
8. `/Users/woosung/project/agy-project/kairos/docs/dev-log/qa/2026-05-19-sprint24-qa-multi-agent/README.md` — QA report 인덱스
9. `/Users/woosung/project/agy-project/kairos/docs/dev-log/qa/2026-05-19-sprint24-qa-multi-agent/sprint-24-plan.md` — **Wave 2 plan v2 (Phase 0 closure + 16 tasks 잔여)**
10. `/Users/woosung/project/agy-project/kairos/docs/dev-log/qa/2026-05-19-sprint24-qa-multi-agent/evidence-matrix.md` — 17 tasks T-N 매트릭스
11. `/Users/woosung/project/agy-project/kairos/docs/dev-log/qa/2026-05-19-sprint24-qa-multi-agent/post-swap-delta-stub.md` — T-2 측정 5 시나리오 정의
12. `/Users/woosung/project/agy-project/kairos/docs/REFACTORING-BACKLOG.md` — BL-T2-001~007 / BL-MOB-001~003 / BL-006 detail
13. git probe (한 답변에서 모두):
    ```bash
    cd /Users/woosung/project/agy-project/kairos
    git fetch && git log origin/main --oneline -3   # expected: f46a075 / b1c777b / d659c03
    git stash list                                   # expected: stash@{0} On main: 임시 디자인 요청...
    git worktree list                                # main + kairos-pgvector-opt + kairos-sprint-24 (머지됨) + kairos-sprint24-qa-multi-agent (머지됨)
    ```

페르소나 detail 은 진입한 task 별로 lazy read:
- T-AI-DATE → `docs/dev-log/qa/2026-05-19-sprint24-qa-multi-agent/curious/report.md` + `casual/report.md` (BUG-CURIOUS-001 hallucinate 진단)
- T-RAG-MOCK-REMOVE → `power/MISSION.md` (BUG-POW-005 reproduce + screenshots)
- T-OBN-05 → `curious/report.md` (BUG-CURIOUS-003 Sprint 22 OBN-01~04 회귀)
- T-MOBILE-HEADER + T-BE-PERF → `mobile/MISSION.md` + `mobile/screenshots/`
- T-N+1 BL-006 → `qa-sentinel/MISSION-tier2.md` (헌법 §4.2 위반 3 cross-domain import)
- T-2 Delta → `post-swap-delta-stub.md` 5 시나리오 baseline + ttfv-gap-analysis.md (Curious gemini F2)

## Wave 2 scope (16 tasks, sprint-24-plan v2 §3 Phase 순서)

| Phase | Task | 시간 | BUG/BL | 우선 |
|---|---|---|---|---|
| **1** | **T-2 Post-Swap Delta 측정** (Phase B swap `003908a` 품질 회귀 검증) | 2h | post-swap-delta-stub 5 시나리오 | **P0 (first)** |
| 2 | T-AI-DATE — Gemini prompt 현재 연도 컨텍스트 + `assert deadline_date.year >= current_year` 안전망 | 1.5h | BUG-CURIOUS-001 | **P0 Critical** |
| 2 | T-RAG-MOCK-REMOVE — `search-scope.tsx:31-37` MOCK 제거 + 실 API 또는 empty state | 1h | BUG-POW-005 | **P0 Critical** |
| 3 | T-OBN-05 — Sprint 22 OBN-01~04 FE UI 발화 fix (신규 가입 dashboard 진입 시) | 2h | BUG-CURIOUS-003 | **P0 High** |
| 3 | T-MOBILE-HEADER — 모바일 헤더 우측 잘림 fix (3 viewport 일관) | 0.5-1h | BUG-MOBILE-001 | **P0 High UX** |
| 4 | T-PROJ-LIST — `frontend/src/app/(app)/projects/page.tsx` 신설 | 2h | BUG-CASUAL-001 | P1 High |
| 4 | T-NOTE-DETAIL — `frontend/src/app/(app)/notes/[id]/page.tsx` 신설 | 3h | BUG-POW-003 | P1 High |
| 4 | T-CMD-K-FIX — dashboard 추천 질문 dead-click → ⌘K 호출 | 1h | BUG-CURIOUS-002 | P1 High |
| 5 | T-RAG-TIME-FILTER — `embeddings/repository.py` search() time_range SQL clause | 2h | BUG-POW-006 | P1 High |
| 5 | T-AUDIT-VIEW — ItemPromotionAudit read endpoint + Settings audit 탭 (admin only) | 4h | BUG-POW-008 | P1 (compliance) |
| 6 | T-BE-PERF spike — dashboard 첫 진입 3-4s (Clerk JWT verify + DB 직렬 의심) | 4-6h | BUG-MOBILE-005 | **P1 Performance** |
| 7 | T-N+1 BL-006 — `memory→embeddings` 직접 import 제거 + pipeline_service 위임 | 3h | BL-006 헌법 §4.2 | **P0 (헌법)** |
| 8 | T-N+4 BL-T2-003 — Whisper 4hr+ chunk 분할 (ffmpeg duration + 병렬 + offset 보존) | 4h | BL-T2-003 production 차단 | P1 (production) |
| 9 | T-N+2 — composite FK regression fixture 자동화 (SCN-FK-01~12 + CI 통합) | 2h | SCN-FK-01~12 | P1 |
| (carry) | P2 묶음 — T-VOCAB / MOBILE-NAV / A11Y-SKIP / A11Y-CC / CMD-K-SEQ / NAV-BADGE / INBOX-COPY | 6.5h | BUG-CASUAL-002~006 / a11y | P2 |
| (carry) | Sprint 25 — T-LAND-01/02 마케팅 + BL-T2 P2 5건 + Power P2 3건 (Inbox bulk/PAT/zip) | ~25h | — | — |

**총 Wave 2 P0+P1 = 24.5h** (T-1 3h closed 제외) / 8일 가용 (~32-64h working day) = 충분.

## Sprint 24 Wave 2 codename 결정 (사용자 게이트)

Stage 0 grill 직전 사용자와 함께 결정. 본 sprint 핵심 = **AI 신뢰 회복 + dogfood 차단 해소 + 헌법 정합**. hint: 회복/신뢰/탄력 (`resilient-otter`, `trusty-heron`, `mending-koala`, `sturdy-pelican` 등).

기존 Sprint 24 진입 시 codename `diligent-beaver` 는 Wave 1 (promote 정합성) 으로 closure. Wave 2 는 새 codename.

## Wave 2 진입 첫 action (Stage 0 진입 후)

### Step 1. 사전 cleanup (사용자 확인 권장)

1. **stash@{0} 결정** — "임시 디자인 요청을 통해서 변경한 부분" 의 적용 / branch 화 / drop. 본 sprint 시작 전 명확히. **R8 보존 룰 = pop 금지 (어떤 워크트리에서도)**.
2. **머지된 워크트리 정리** (PR #99 / PR #100 squash merge 후 잔재):
   ```bash
   git worktree remove /Users/woosung/project/agy-project/kairos-sprint-24
   git worktree remove /Users/woosung/project/agy-project/kairos-sprint24-qa-multi-agent
   git branch -D sprint-24/diligent-beaver sprint-24/multi-agent-qa-mongoose-orbit
   ```

### Step 2. Wave 2 worktree 생성

```bash
cd /Users/woosung/project/agy-project/kairos
git worktree add ../kairos-sprint-24-wave2 -b sprint-24/<codename>
cp backend/.env ../kairos-sprint-24-wave2/backend/.env   # gitignored, 수동 복사
cd ../kairos-sprint-24-wave2/backend && uv sync
cd ../frontend && pnpm install --frozen-lockfile
```

### Step 3. baseline verify

```bash
cd backend && uv run pytest tests/ -q
# expected: 387 passed + 1 skipped (Wave 1 closeout baseline)
cd ../frontend && pnpm typecheck && pnpm test
# expected: typecheck 0 / vitest 50 PASS
```

### Step 4. Phase 0 closure grep verify

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2

# ADR-019 Phase B (003908a) 6 spots
grep -rn "gemini-3.1-flash-lite" backend/src/ | head -10
# expected: backend/src/services/ai_processing.py:18, backend/src/memory/service.py:68 등

# Wave 1 산출물 (b1c777b)
grep -rn "clone_action_items_for_promote\|_bg_regenerate_embed_with_audit" backend/src/
# expected: backend/src/common/promote_helpers.py, backend/src/notes/service.py
```

### Step 5. Phase 1 — T-2 Post-Swap Delta 측정 first

`post-swap-delta-stub.md` 의 5 시나리오 baseline 수집 (swap 직전 = `003908a^`) → swap 후 (현재 main) 재실행 → delta report 작성. fixture audio 또는 캐시된 prompt 결과 비교.

**기준 위반 시 즉시 사용자 보고 + revert PR 옵션 검토**:
- DELTA-1 worse 1건+ (품질 회귀)
- DELTA-3 precision/recall -10% 초과
- DELTA-2/4/5 ±20% 초과 (latency / cost / schema)

T-2 결과 OK 면 Phase 2 (P0 Critical) 진입.

### Step 6. Stage 1 진입 (T-2 결과 OK 가정)

`superpowers:brainstorming` → Wave 2 spec doc `docs/superpowers/specs/2026-05-20-sprint24-wave2-<codename>-design.md`. P0 Critical (T-AI-DATE + T-RAG-MOCK-REMOVE) 부터 분해. 5 sections (Architecture / Components / Data Flow / Error Handling / Testing) + Success Criteria.

## 워크플로우 강제 (`.ai/templates/workflow.md` Stage 0~6) — Sprint 23/24 패턴 정합

| Stage | 도구 | 산출물 / 강제 |
|---|---|---|
| 0 grill | `/grill-with-docs` 또는 직접 verify | 헌법 lock-in (특히 T-N+1 BL-006 의 §4.2 위반 정합) |
| 1 spec | `superpowers:brainstorming` | spec doc 5 sections + Success Criteria |
| 2 plan | `superpowers:writing-plans` | task plan + Atomic Update §2 매트릭스 적용 + Stage 4/5/6 closeout 절차 |
| 2.5 Codex 1차 plan review | `codex review --base origin/main` | APPROVE 또는 REVISE 100% 수락 → plan v2 patch commit |
| 3 dev | `superpowers:subagent-driven-development` (큰 task 분할) 또는 controller 직접 | code commits |
| 4 Codex 2차 diff review (iter) | `codex review --base origin/main` | Codex APPROVE 까지 cycle (Sprint 23 = 10 cycle 패턴) |
| 5 PR push | `git push -u origin <branch>` + `gh pr create --draft` | PR url, `gh pr view <N> --json baseRefName = main` (R7) |
| 6 closeout | controller | memory `project_sprint24_wave2_<codename>_done.md` + MEMORY.md 인덱스 + BL carry-over |

**단축 금지** — Sprint 23 의 10 cycle Codex review 도 본 워크플로우 강제 결과. 본 sprint 도 동일 cycle 적용.

## §19/§20 sub-agent 보호 gate (PR #100 plan v2 룰 — Wave 2 에도 적용)

- **§19 sub-agent 코드 수정 금지** — sub-agent dispatch 시 read-only / write 산출물만. 코드 변경 + git commit 은 main session controller 만.
- **§20 critical 발견 시 STOP + Decision Required** — sub-agent 가 P0 critical 발견 시 작업 중단 + 사용자 보고. 즉시 수정 금지 (baseline 정합 유지).

## Codex iterative protocol (Stage 4 — Sprint 23 = 10 cycle 16 finding 100% 수락 → APPROVE)

```
loop:
    codex review --base origin/main   # PROMPT 없이, --base 만
    if APPROVE → break
    elif REVISE:
        - finding 100% 수락 (fact-based 면 무조건). reject 사유 명시는 P3 만 허용
        - polish commit 1개 (atomic, recoverable)
        - commit message: "polish: Codex N차 M finding 100% 수락 (P1 X + P2 Y)"
        - git push (PR 자동 갱신)
    elif usage limit:
        - wait until reset (~5-7h) 또는 새 session (context burn 분리)
```

**Codex finding 카테고리** (Sprint 23 학습):
- **P1**: blocker (memory alias / Suspense / RBAC bypass / personal info leak)
- **P2**: correctness/security (BE/FE field mismatch / non-terminal source / BG rollback / RAG cache / embedding race / admin gate)
- **P3**: detail (error_message preserve / count reset)

**fact-check 강제 (R1 mitigation)** — Stage 4 진입 직전 모든 plan/spec 의 함수명 / 모듈 위치 / hook placement grep verify.

## R1~R8 risk + mitigation (Sprint 22/23 학습 누적)

| Risk | Mitigation |
|---|---|
| R1. Codex fact-mismatch | Stage 4 직전 함수명 / 모듈 / hook placement grep verify |
| R2. Sub-agent stall | 큰 task 분할 dispatch (도메인별 4분할). controller 가 git log progress verify. 단일 sub-agent ~1.5h limit |
| R3. 코드 외부 원인 | 진단 first (Playwright reproduce / curl). 환경 의존 시 carry-over BL 등재 (BL-068/069 패턴) |
| R4. BE/FE shape mismatch | response_model alias_generator 또는 도메인별 alias. 헌법 I-16 강제 |
| R5. alembic migration scope | 도메인 모델 변경 vs audit 테이블 신설 결정. drift gate `PR2_MANAGED_COLUMNS` allowlist 검토 |
| R6. scope overrun | 30h 초과 시 사용자 보고 + 일부 carry. 본 sprint = ~24.5h 여유 |
| R7. stack PR base | 머지 직전 `gh pr view <N> --json baseRefName` → "main" 확인 (PR #93 사고 재발 방지) |
| R8. **stash@{0} 보존** | 어떤 worktree 에서도 pop 금지. design-review 잔재. 새 stash 만 pop. |

## Atomic Update §2 매트릭스 (Wave 2 특이 row)

| 코드 변경 | 동시 갱신 docs |
|---|---|
| AI 액션 prompt 변경 (T-AI-DATE) | `backend/src/common/prompts.py` + `backend/src/services/ai_processing.py` + `backend/CONTEXT.md` AI 모듈 § + `docs/architecture/ai-pipeline.md` |
| FE search-scope MOCK 제거 (T-RAG-MOCK-REMOVE) | `frontend/src/features/rag/components/search-scope.tsx` + `frontend/CONTEXT.md` (있다면) — 사실상 FE 만 |
| Onboarding step UI fix (T-OBN-05) | `backend/src/onboarding/CONTEXT.md` (있다면) + `frontend/src/components/onboarding/` |
| FE list/detail page 신설 (T-PROJ-LIST / T-NOTE-DETAIL) | `frontend/src/app/(app)/projects/page.tsx` + `frontend/src/app/(app)/notes/[id]/page.tsx` — `frontend` 일관성 + `DESIGN.md` 참조 |
| RAG SQL clause 추가 (T-RAG-TIME-FILTER) | `backend/src/embeddings/repository.py` + `backend/src/embeddings/CONTEXT.md` + `docs/architecture/rag-pipeline.md` Layer 3 (Hybrid Search) |
| Audit endpoint + Settings UI (T-AUDIT-VIEW) | `backend/src/<도메인>/router.py` + `<도메인>/CONTEXT.md` §엔드포인트 + `docs/api/endpoints.md` + `frontend/src/app/(app)/settings/` |
| BL-006 cross-domain import 해소 (T-N+1) | **헌법 §4.2** — `CONTEXT-MAP.md` §4 + §7 부채 갱신 + `backend/CONTEXT.md` §의존 + `backend/src/memory/CONTEXT.md` + `backend/src/embeddings/CONTEXT.md` + `docs/architecture/cross-domain-pipeline.md` §위반 해소 section |
| Whisper chunk 분할 (T-N+4) | `backend/src/services/stt_service.py` (또는 해당 모듈) + `backend/CONTEXT.md` STT § + `docs/architecture/ai-pipeline.md` STT 단계 |
| composite FK fixture (T-N+2) | `backend/tests/conftest.py` 또는 `backend/tests/fixtures/composite_fk.py` + BL-024 cross-link |
| BE perf spike (T-BE-PERF) | profiling 결과 doc `docs/dev-log/sprints/2026-05-NN-be-perf-spike.md` + 변경 시 도메인별 CONTEXT.md |

PR 본문 "Docs sync" 섹션 필수 — `git diff --stat docs/ backend/**/CONTEXT.md frontend/**/CONTEXT.md CONTEXT-MAP.md` 결과 첨부.

## Sub-agent driven dev 패턴 (Stage 3, Sprint 23/24 학습)

큰 task 4분할 + 직렬 dispatch (worktree 1개, git race 회피). T-AUDIT-VIEW (BE endpoint + FE 탭) / T-BE-PERF (profiling spike) 가 분할 후보. Sub-agent prompt boilerplate:

```
Sprint 24 Wave 2 <codename> Task X — <도메인> <작업>.

## 컨텍스트
- 작업 디렉토리: /Users/woosung/project/agy-project/kairos-sprint-24-wave2 (worktree, branch sprint-24/<codename>)
- 이전 commits (reference): <SHA list>
- baseline pytest: 387 passed + 1 skipped

## Reference impl (반드시 read)
- <file path 1>: <purpose>
- <file path 2>: <purpose>

## 산출물 (모두 신설/추가)
1. <file>: <change>
2. ...

## 검증 (필수)
- pytest, typecheck, lint, alembic drift

## 제약 / 주의
1. §19 코드 수정만 — git commit 금지 (controller 가 한꺼번에)
2. AsyncSession 은 repository 만 (헌법 B-1)
3. workspace_id 필터 강제 (헌법 B-2)
4. stash 건드리지 말 것 (R8 — stash@{0}: On main: 임시 디자인 요청 보존)
5. fact-check 강제 — 함수명 / 모듈 위치 grep verify
6. §4.2 cross-domain import 금지 (T-N+1 BL-006 진행 중일 때 특히)

## 진입 직후 read 권장
<file list>

## 보고 형식
- git status -sb
- pytest 결과 + diff stat
- design 결정 + stall/blocker 명시
```

## PR 분할 전략 (사용자 결정 게이트)

- **옵션 A — 단일 sprint-24/wave2-`<codename>` 브랜치 + multi-commit** (Sprint 23 cozy-crystal 패턴 정합, **추천**)
- **옵션 B — Phase 별 분할 PR** (P0 Critical PR + P0 High PR + P1 PR + 헌법 PR + production PR)

Sprint 23 cozy-crystal = 19 commit 단일 PR + 10 Codex cycle = 검증된 패턴. **옵션 A 추천**. 단 T-AUDIT-VIEW (4h, BE+FE 양쪽) 또는 T-BE-PERF spike (4-6h, profiling) 가 별도 작업 분리 후보 — Stage 1 spec 시 사용자 결정.

## Dogfood mini-redo 가이드 (P0/P1 fix 후 회귀 검증)

Wave 2 closeout 직전 또는 P0 묶음 fix 후 dogfood mini-redo 1회:

- **시나리오**: Curious 페르소나 mini-redo (신규 가입 → AI 요약 → RAG /ask)
- **검증 대상**: BUG-CURIOUS-001 (AI 날짜) / BUG-CURIOUS-002 (dead-click) / BUG-CURIOUS-003 (onboarding) 모두 회귀 없음
- **방법** (sprint-24-plan v2 §6 [확인 필요] — 사용자 결정):
  - 옵션 1: Curious 원본 계정 reuse (storageState clear)
  - 옵션 2: incognito 새 Clerk 계정 (가장 깨끗하지만 셋업 5분)
- **Phase B Delta**: Sentry Gemini API latency 5.76x 검증 (Phase A spike 일치 — `project_sprint15_adr019_phase_a_done` 참조)

## 사용자 잔여 (sprint 진행 독립)

- Clerk Production key (Sprint 14 carry, `pk_live_*` / `sk_live_*` 발급 후 Vercel env 등록)
- Sentry DSN (Sprint 22 carry, Cloud Run + Vercel env 등록 + 알람 verify)
- 외부 user 1명 실 dogfooding (Sprint 22 `docs/dev-log/sprints/2026-05-19-sprint22-dogfooding.md` 12분 walkthrough)
- **stash@{0} "임시 디자인 요청" 적용/branch/drop 결정** (본 sprint 진입 전 명확화 권장)

## 응답 모드

- 한국어 (CLAUDE.md §1)
- Senior Tech Lead + System Architect 역할 (`.claude/CLAUDE.md` §2)
- Git Safety Protocol — 사용자 명시 승인 후 commit / push 진행
- Fact vs Assumption 라벨링 (`[가정]` / `[확인 필요]`)
- workflow.md Stage 0~6 단축 금지

진행 시작.
