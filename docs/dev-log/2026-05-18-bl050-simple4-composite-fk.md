<!-- Sprint 21 BL-050 Simple 4 closeout ADR (Nygard 포맷) -->

# BL-050 Simple 4 — Cross-workspace Composite FK Hardening (Sprint 21)

> 일자: 2026-05-18 · PR #96 · 작성자: woo sung

## Context

Sprint 19 PR #2 (BUG-C01-EXT-FK, merge 5789822) 의 후속 hardening. 4 entity (action_items.meeting / inbox.suggested / embedding_chunks.project / semantic_caches.project) 의 cross-workspace single-FK 를 composite FK 로 강화.

BL-050 BACKLOG 의 7+ entity 중 nullable + UNIQUE 선행재 인 Simple 4 subset 만 본 PR scope. 잔여 3 entity (memory_items / memory_ai_calls / promotion_audit) 는 carry-over.

## Decision

Simple 4 subset 만 단일 PR (4 commit stack + 2 polish + 1 D0.5 patch):
- D0.5 plan v2 + drift gate allowlist (Codex 1차 MAJOR-1 수락) — 1bacce6
- D1 audit RED — 4 신규 audit (mismatch 0 baseline) — 989e86d + 1ef4a55
- D2 model `__table_args__` — 4 model composite ForeignKeyConstraint 선언 — 8e80151 + 70e4fab
- D3 alembic — preflight DO $$ + 4 composite FK single revision `cf903ab3dd37` — 12c9b82 + 68ac2d9
- D4 closeout — 본 doc + BACKLOG mark + ERD

잔여 3 entity 는 carry-over (별도 PR):
- memory_items.embedding_chunk_id (embedding_chunks UNIQUE 선행 작업)
- memory_ai_calls.memory_id (memory_items UNIQUE 선행 + NOT NULL 패턴)
- promotion_audit (intentional cross-workspace, 별도 분석)

## Consequences

### 긍정

- DB-level defense-in-depth: cross-workspace INSERT 가 PostgreSQL FK violation 으로 차단 (409 Conflict).
- nullable FK MATCH SIMPLE 면제 → NULL row 정상 (워크스페이스-level 임베딩/캐시/AI 추천 정상).
- Sprint 19 PR #2 patterns 재사용 (preflight DO $$, single revision, MATCH SIMPLE, dogfooding scale).
- drift gate allowlist 갱신 — 본 4 FK 의 D2/D3 정합성 false-green 차단.

### 부정 / trade-off

- production scale (>1만 row) 진입 시 BL-049 NOT VALID + VALIDATE 2단계 별도 적용 필요 (본 PR 는 dogfooding scale ms ADD CONSTRAINT 가정).
- BL-054 manifest G5 (tests/ session.exec migration) 영역 vs 본 PR audit 8 함수의 raw text execute 패턴 — G5 별도 cleanup BL carry-over (본 PR scope 외).

## Verification

| 항목 | 결과 |
|---|---|
| `pytest tests/` | 325 passed + 1 skipped |
| `pytest tests/integration/test_alembic_upgrade.py` | 1 passed (drift 0 GREEN) |
| `pytest tests/integration/test_workspace_integrity_audit.py` | 8 passed (기존 4 + 신규 4) |
| `pyright` | 132 errors (baseline 유지) |
| Codex 1차 plan review | REVISE (1 MAJOR finding) → 100% 수락 + D0.5 patch |
| Codex 2차 diff review | (Task 4 후 진행, controller 가 처리) |

## References

- Spec: `docs/superpowers/specs/2026-05-18-bl050-simple4-composite-fk-design.md`
- Plan: `docs/superpowers/plans/2026-05-18-bl050-simple4-composite-fk.md` (v2 — D0.5 patch 후)
- Sprint 19 PR #2: `5789822` (BUG-C01-EXT-FK base pattern, alembic revision `e5f6g7h8i9ja`)
- 본 PR alembic revision: `cf903ab3dd37` (down_revision: `e5f6g7h8i9ja`)
- Memory: [[feedback_stack_pr_base_check]] (머지 직전 base=main 확인 protocol)

## 머지 직전 체크리스트

- [ ] `gh pr view <N> --json baseRefName` → `main` 확인
- [ ] draft → ready 전환
- [ ] squash 머지 + `--delete-branch`
- [ ] `git fetch origin && git log origin/main --oneline -3` → squash commit 도달 확인
- [ ] 본 doc + BACKLOG 의 `#NN` placeholder PR 머지 후 정확 PR 번호로 갱신
