Sprint 24 진입. ADR-019 Phase B (Gemini 3.1-flash-lite swap, **2026-05-28 데드라인**) + Sprint 23 carry-over (BL-063~067) 통합 sprint.

## 첫 read (순서 중요, 9 항목)

1. `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/MEMORY.md` — 인덱스
2. `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint23_cozy_crystal_done.md` — 직전 sprint closeout
3. `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint15_adr019_phase_a_done.md` — ADR-019 Phase A spike (5.76x speedup verify)
4. `/Users/woosung/project/agy-project/kairos/CONTEXT-MAP.md` — 헌법 (entity 19개, I-1~I-21 불변식)
5. `/Users/woosung/project/agy-project/kairos/.ai/templates/workflow.md` — Stage 0~6 운영
6. `/Users/woosung/project/agy-project/kairos/.ai/common/global.md` — Atomic Update §4 매트릭스
7. `/Users/woosung/project/agy-project/kairos/docs/REFACTORING-BACKLOG.md` — BL-063~067 detail
8. `/Users/woosung/project/agy-project/kairos/docs/TODO.md` — 현재 Sprint 24 Next Actions
9. git probe (한 답변에서 모두):
   ```bash
   cd /Users/woosung/project/agy-project/kairos
   git fetch && git log origin/main --oneline -3   # expected main = d659c03 (Sprint 23 squash)
   git stash list                                   # expected stash@{0} On main: 임시 디자인 요청...
   git worktree list                                # main + kairos-pgvector-opt (sprint-16) — sprint-23 제거됨
   ```

## Sprint 24 scope (사용자 결정 게이트)

| 우선순위 | 항목 | 추정 | 상태 |
|---|---|---|---|
| 🔴 **P0** | **ADR-019 Phase B** — `gemini-2.5-flash` → `gemini-3.1-flash-lite` 6 spots swap. spike validated (5.76x speedup / 20% cost 절감 / schema 3/3). 데드라인 2026-05-28 | 2-4h | 진입 필수 |
| 🟡 **P1** | **BL-066** D1/D3 dev server dogfood verify (Sprint 23 fix 실 효과 확인) | 1-2h | 진입 권장 |
| 🟡 P1 | **BL-063** ActionItem 도메인 promote 시 source actions 복제 (CO-15) | 3-5h | 사용자 결정 |
| 🟢 P2 | **BL-064** Note 임베딩 재계산 옵션 (Codex 6차 P2 carry, CO-16) | 4-6h | 사용자 결정 |
| 🟢 P2 | **BL-065** Member.last_active_at 필드 (Sprint 23 D2 carry CO-17) | 4-6h | 사용자 결정 |
| 🟢 P3 | **BL-067** pyright `_update().where()` false-positive 패턴 cleanup (CO-19) | 1-2h | 자율 |

**진입 직후 codename 결정** — Stage 0 grill 진행 직전에 사용자와 함께 결정 (Sprint 22 expressive-squirrel / Sprint 23 cozy-crystal 패턴 정합). ADR-019 Phase B 핵심 = 속도/효율 hint 적합 (`swift-falcon`, `lithe-otter` 같은).

## 워크플로우 강제 (`.ai/templates/workflow.md` Stage 0~6)

본 sprint 도 superpowers + workflow Stage 0~6 따름. **단축 금지** (Sprint 23 의 10 cycle Codex review 도 본 워크플로우 강제 결과).

| Stage | 도구 | 산출물 | 강제 |
|---|---|---|---|
| **0 grill** | `/grill-with-docs` 또는 직접 verify | 헌법 lock-in + 도메인 용어 정합 | ADR-019 의 경우 spike doc (memory) read + 6 spots grep verify |
| **1 spec** | `superpowers:brainstorming` | `docs/superpowers/specs/2026-05-22-sprint24-<codename>-design.md` | Architecture/Components/Data Flow/Error Handling/Testing 5 sections + Success Criteria |
| **2 plan** | `superpowers:writing-plans` | `docs/superpowers/plans/2026-05-22-sprint24-<codename>-tasks.md` | Task 0~N 의존성 + step list + Atomic Update §4 매트릭스 + Stage 4/5/6 closeout 절차 |
| **2.5 Codex 1차 plan review** | `codex review --base origin/main` (--base 만, PROMPT 없이) | Codex verdict | APPROVE 또는 REVISE 100% 수락 → plan v2 patch commit |
| **3 dev** | `superpowers:subagent-driven-development` 또는 controller 직접 | code commits | 큰 task = sub-agent 4 분할 dispatch (R2 mitigation). 진단 first (D1/D3 학습) |
| **4 Codex 2차 diff review (반복)** | `codex review --base origin/main` | Codex APPROVE 까지 cycle | **Sprint 23 의 10 cycle 패턴 그대로 — 아래 §"Codex iterative protocol" 참조** |
| **5 PR push** | `git push -u origin <branch>` + `gh pr create --draft` | PR url | `gh pr view <N> --json baseRefName` = "main" 확인 (R7) |
| **6 closeout** | controller | memory `project_sprint24_<codename>_done.md` + MEMORY.md 인덱스 + BL carry-over | atomic update §4 강제 |

## Codex iterative protocol (Stage 4 — Sprint 23 학습)

**Sprint 23 = 10 cycle 16 finding 100% 수락 → APPROVE**. 본 patten 그대로 적용:

```
loop:
    codex review --base origin/main      # PROMPT 없이, --base 만
    if verdict == "APPROVE" → break
    elif verdict == "REVISE":
        - finding 100% 수락 (fact-based 면 무조건). reject 사유 명시는 P3 만 허용
        - polish commit 1개 (atomic, recoverable)
        - commit message: "polish: Codex N차 M finding 100% 수락 (P1 X + P2 Y)"
        - git push (PR 자동 갱신)
    elif usage limit:
        - wait until reset 또는 새 session
```

**Codex finding 카테고리** (Sprint 23 학습):
- **P1**: blocker (memory alias / Suspense / RBAC bypass / personal info leak)
- **P2**: correctness/security (BE/FE field mismatch / non-terminal source / BG rollback / RAG cache / embedding race / admin gate)
- **P3**: detail (error_message preserve / action_item_count reset)

**fact-check 강제 (R1 mitigation)** — Stage 4 진입 직전 모든 plan/spec 의 함수명/모듈 위치/hook placement grep verify. Sprint 22 plan v1 의 7 finding 패턴 회피.

**Codex limit 회피 전략**:
- Phase 1 (limit 초기화 전, ~5-7h reset): dogfood verify, HTML 결과 보고서, PR description manual review
- Phase 2 (limit 후): Codex review cycle 재개. 새 session 권장 (context burn 분리).

## 핵심 강제 (R1~R8, Sprint 22/23 학습)

| Risk | Mitigation |
|---|---|
| **R1. Codex fact-mismatch** | Stage 4 직전 함수명/모듈/hook placement grep verify. 5 cycle 미만 종료 시 부족 → 10 cycle 까지 정상 (Sprint 23 사례) |
| **R2. Sub-agent stall** | 큰 task 분할 dispatch (도메인별 4분할). controller 가 git log progress verify. 단일 sub-agent ~1.5h limit, 그 이상 = 분할 권장 |
| **R3. 코드 외부 원인** | 진단 first (Playwright reproduce / curl) 환경 의존 시 carry-over BL 등재 (Sprint 23 BL-066 패턴) |
| **R4. BE/FE shape mismatch (snake/camel)** | response_model 의 alias_generator 또는 도메인별 alias 명시. 헌법 I-16 (DB snake ↔ API camel) 강제. Sprint 23 inbox D3 학습 |
| **R5. alembic migration scope** | 도메인 모델 변경 vs audit 테이블 신설 결정. drift gate (`backend/tests/integration/test_alembic_upgrade.py`) PR2_MANAGED_COLUMNS allowlist 검토 |
| **R6. scope overrun** | 30h 초과 시 사용자 보고 + 일부 carry-over. Sprint 23 = ~28h (10 Codex cycle 포함) |
| **R7. stack PR base** | 머지 직전 `gh pr view <N> --json baseRefName` → "main" 확인. PR #93 main 미도달 사고 재발 방지 |
| **R8. stash@{0} 보존** | **어떤 worktree 에서도 pop 금지**. 본 stash 는 design-review 잔재 (Sprint 22 R6). 어떤 lint/test 시 stash push + pop 필요한 경우 새로 만든 stash 만 pop |

## Atomic Update §4 매트릭스 (코드 변경 시 동시 갱신)

| 코드 변경 | 동시 갱신 docs |
|---|---|
| 도메인별 `models.py` 변경 | `<domain>/CONTEXT.md` §엔티티 + `docs/architecture/erd.md` |
| 도메인별 `router.py` endpoint 변경 | `<domain>/CONTEXT.md` §엔드포인트 + `docs/api/endpoints.md` |
| 헌법 §4.2 도메인 경계 변경 | `CONTEXT-MAP.md` §4 표/Mermaid + §7 부채 |
| `pipeline_service.py` 신설/변경 | `backend/CONTEXT.md` §4 도메인 표 + `docs/architecture/cross-domain-pipeline.md` |
| RAG 6-Layer 변경 | `docs/architecture/rag-pipeline.md` + `backend/src/rag/CONTEXT.md` |
| ADR-019 Phase B 적용 (본 sprint 핵심) | `backend/src/common/prompts.py` 또는 `core/config.py` (모델 상수) + `docs/dev-log/019-*.md` Phase B section + `backend/CONTEXT.md` B-4 invariant 확인 + 헌법 I-12 (AI 모델 고정) 검증 |
| alembic revision 신설 | `backend/alembic/env.py` import + drift gate allowlist (`PR2_MANAGED_COLUMNS`) + 헌법 §2 entity 표 |

PR 본문 "Docs sync" 섹션 필수 (`git diff --stat docs/ backend/**/CONTEXT.md CONTEXT-MAP.md` 결과 첨부).

## Sub-agent driven dev 패턴 (Stage 3, Sprint 23 학습)

Sprint 23 = 6 sub-agent dispatch (4 도메인 promote + Task 4 FE + foundation) 모두 stall 없이 완료. 패턴 그대로 적용:

**Sub-agent prompt 구조 (boilerplate)**:
```
Sprint 24 <codename> Task X — <도메인> <작업>.

## 컨텍스트
- 작업 디렉토리: /Users/woosung/project/agy-project/kairos-sprint-24 (worktree, branch sprint-24/<codename>)
- 이전 commits (reference): <SHA list>
- baseline pytest: <count> PASS

## Reference impl (반드시 read)
- <file path 1>: <purpose>
- <file path 2>: <purpose>

## 산출물 (모두 신설/추가)
1. <file>: <change>
2. ...

## 검증 (필수)
- pytest, typecheck, lint, alembic drift

## 제약 / 주의
1. 다른 도메인 건드리지 말 것
2. AsyncSession 은 repository 만 (헌법 B-1)
3. workspace_id 필터 강제 (헌법 B-2)
4. stash 건드리지 말 것 (R8) — stash@{0}: On main: 임시 디자인 요청 보존
5. fact-check 강제 — 함수명/모듈 위치 grep verify
6. commit 만들지 말고 controller 가 확인 후 commit

## 진입 직후 read 권장
<file list>

## 보고 형식
- git status -sb
- pytest 결과 + diff stat
- design 결정 + stall/blocker 명시
```

**worktree 1개 → 직렬 dispatch** (git race 회피). 한 sub-agent 결과 verify 후 다음 dispatch.

## Sprint 24 첫 action (Stage 0 진입 후)

1. **codename 결정** (사용자 게이트)
2. **worktree 생성**:
   ```bash
   cd /Users/woosung/project/agy-project/kairos
   git worktree add ../kairos-sprint-24 -b sprint-24/<codename>
   cp backend/.env ../kairos-sprint-24/backend/.env   # gitignored, 수동 복사
   cd ../kairos-sprint-24/backend && uv sync
   cd ../frontend && pnpm install --frozen-lockfile
   ```
3. **baseline pytest verify**:
   ```bash
   cd backend && uv run pytest tests/ -q
   # expected: 379 passed + 1 skipped (Sprint 23 closeout baseline)
   ```
4. **ADR-019 Phase B grep 6 spots verify**:
   ```bash
   cd /Users/woosung/project/agy-project/kairos-sprint-24
   grep -rn "gemini-2.5-flash\|gemini-3.1-flash-lite" backend/src/ | head -20
   ```
5. **Stage 1 진입** — `superpowers:brainstorming` spec doc 작성

## 진입 baseline (Sprint 24 시작 시점)

- main HEAD = `d659c03` (Sprint 23 cozy-crystal squash merge, 2026-05-19T13:06:47Z)
- pytest baseline = **379 passed + 1 skipped**
- FE typecheck 0 / lint 16 baseline (carry-over)
- alembic head = `9dd1a3b80431` (Sprint 23 item_promotion_audit)
- ADR-019 Phase A spike validated (5.76x speedup, 20% cost 절감, schema 3/3 verify) — Phase B = 코드 swap 만

## 사용자 잔여 (sprint 진행 독립)

- Clerk Production key (Sprint 14 carry)
- Sentry DSN (Sprint 22 carry, Cloud Run env 등록)
- 외부 user 1명 실 dogfooding (Sprint 22 doc walkthrough)

## 응답 모드

- 한국어 (CLAUDE.md §1)
- Senior Tech Lead + System Architect 역할 (`/Users/woosung/project/agy-project/kairos/.claude/CLAUDE.md` §2)
- Git Safety Protocol — 사용자 명시 승인 후 commit/push 진행 (단 본 prompt 가 "쭉 진행" 허용 명시 시 inline 진행 OK)

진행 시작.
