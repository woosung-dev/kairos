# BL-050 Simple 4 — Cross-workspace Composite FK Hardening (Sprint 21)

> 일자: 2026-05-18 · 영역: backend / SQLModel models / alembic · 우선순위: P2 hardening · 시간: ~8-12h

## Context

Sprint 19 PR #2 (`BUG-C01-EXT-FK`, merge `5789822`) 는 4 entity (action_items.project / notes.project / mpl / project_members) 의 project FK 만 composite FK 로 hardening. 단일-FK 로 남은 entity 가 `BL-050` 으로 등재 (`docs/REFACTORING-BACKLOG.md:1319-1342`). 본 spec 은 BL-050 의 **Simple 4 entity subset** — nullable FK + UNIQUE 선행 작업 없음 — 만 단일 PR 로 closure.

**Simple 4 subset 선정 근거**: 7+ entity 전수 진행은 ~24-32h (promotion_audit 분석 + 2 UNIQUE 신설 포함). dogfooding scale 에서 단계적 hardening 이 안전 + Codex review 게이트 명확. 잔여 3 entity (memory_items.embedding_chunk_id / memory_ai_calls.memory_id / promotion_audit) 는 BL-050 carry-over.

**의도된 결과**:
1. 4 entity 의 cross-workspace data row 가 DB constraint 로 차단 (defense-in-depth).
2. `compare_metadata` drift 0 유지 (BL-051 별도).
3. Sprint 19 PR #2 의 검증된 patterns (preflight DO $$, MATCH SIMPLE, single revision) 재사용.

## Scope (4 entity)

| entity | FK 컬럼 | target | UNIQUE 선행 (기존재) | composite FK 명 |
|---|---|---|---|---|
| `action_items` | `meeting_id` (nullable) | `meetings(id, workspace_id)` | `uq_meetings_id_workspace_id` (PR #2) | `fk_action_items_meeting_workspace` |
| `inbox` | `ai_suggested_project_id` (nullable) | `projects(id, workspace_id)` | `7ebd009f89a4` (PR #2 이전) | `fk_inbox_suggested_project_workspace` |
| `embedding_chunks` | `project_id` (nullable) | `projects(id, workspace_id)` | 동상 | `fk_embedding_chunks_project_workspace` |
| `semantic_caches` | `project_id` (nullable) | `projects(id, workspace_id)` | 동상 | `fk_semantic_caches_project_workspace` |

**MATCH SIMPLE**: 4 entity 모두 nullable → PostgreSQL 기본 MATCH SIMPLE 로 NULL 면제 자동. notes 패턴 (PR #2) 그대로.

## Out of scope (BL-050 carry-over)

- `memory_items.embedding_chunk_id` ↔ embedding_chunks.workspace_id — embedding_chunks UNIQUE 선행 작업 필요.
- `memory_ai_calls.memory_id` ↔ memory_items.workspace_id — memory_items UNIQUE 선행 작업 필요 + NOT NULL FK 면제 패턴 다름.
- `promotion_audit` (source_workspace_id + target_workspace_id) — **intentional cross-workspace**, 별도 분석.

## Architecture

**워크트리**: `../kairos-sprint-21` (별도 worktree) · **branch**: `sprint-21/bl-050-composite-fk-simple4`

**Codex review 게이트**:
- 1차 plan review (verdict 후 plan v2 patch)
- 2차 diff review (D4 직전, APPROVE 권장)

## Components — 4-commit stack (Sprint 19 PR #2 패턴)

### D1 — audit RED 확장 (~2h)

**파일**: `backend/tests/integration/test_workspace_integrity_audit.py` (+~80 lines)

**신규 함수 4**:
- `test_action_items_meeting_workspace_match`
- `test_inbox_suggested_project_workspace_match`
- `test_embedding_chunks_project_workspace_match`
- `test_semantic_caches_project_workspace_match`

각 함수 = `JOIN target ON id = FK WHERE source.workspace_id != target.workspace_id LIMIT 10` 패턴 (Sprint 19 PR #1 4 audit 와 동일). TestContainers 빈 DB → mismatch 0 → 4 PASS baseline GREEN.

**Gate**: `uv run pytest tests/integration/test_workspace_integrity_audit.py -v` → **8 PASS** (기존 4 + 신규 4).

### D2 — model `__table_args__` 4 patch (~2h)

**파일**:
- `backend/src/actions/models.py` — 기존 `__table_args__` 에 meeting composite FK 1 추가
- `backend/src/inbox/models.py` — `__table_args__` 신설 (1 FK)
- `backend/src/embeddings/models.py` — embedding_chunks/semantic_caches 각각 `__table_args__` 신설

**패턴** (PR #2 `actions/models.py:6,12-17` 그대로 — BL-052 cleanup 후 sqlmodel re-export):
```python
from sqlmodel import Field, ForeignKeyConstraint, SQLModel

__table_args__ = (
    ForeignKeyConstraint(
        ["workspace_id", "meeting_id"],
        ["meetings.workspace_id", "meetings.id"],
        name="fk_action_items_meeting_workspace",
    ),
    # ... 기존 project composite FK 유지
)
```

**Atomic Update §4 매트릭스**: model 변경 → `docs/architecture/erd.md` 동시 갱신 (composite FK 4 신설 명시 + ERD relationship 라인 dashed → solid 갱신).

### D3 — alembic single revision (~3h)

**파일**: `backend/alembic/versions/<rev>_bl050_simple4_composite_fk.py`

**구조** (PR #2 `e5f6g7h8i9ja_sprint19_pr2_composite_fk.py` 패턴):

```python
def upgrade():
    # 1. preflight DO $$ — 4 mismatch SELECT COUNT, RAISE EXCEPTION on > 0
    op.execute("""
    DO $$
    DECLARE cnt_ai_m INT; cnt_ib INT; cnt_ec INT; cnt_sc INT;
    BEGIN
        SELECT COUNT(*) INTO cnt_ai_m FROM action_items a
          JOIN meetings m ON m.id = a.meeting_id
          WHERE a.meeting_id IS NOT NULL AND a.workspace_id != m.workspace_id;
        IF cnt_ai_m > 0 THEN RAISE EXCEPTION 'BL-050 preflight: action_items.meeting mismatch=%', cnt_ai_m; END IF;
        -- ... 3 더 (inbox / embedding_chunks / semantic_caches)
    END $$;
    """)

    # 2. 4 composite FK
    op.create_foreign_key("fk_action_items_meeting_workspace", "action_items", "meetings",
                          ["workspace_id", "meeting_id"], ["workspace_id", "id"])
    op.create_foreign_key("fk_inbox_suggested_project_workspace", "inbox_items", "projects",
                          ["workspace_id", "ai_suggested_project_id"], ["workspace_id", "id"])
    op.create_foreign_key("fk_embedding_chunks_project_workspace", "embedding_chunks", "projects",
                          ["workspace_id", "project_id"], ["workspace_id", "id"])
    op.create_foreign_key("fk_semantic_caches_project_workspace", "semantic_caches", "projects",
                          ["workspace_id", "project_id"], ["workspace_id", "id"])

def downgrade():
    # 역순 drop
```

**production scale 가정**: dogfooding scale (~수십 row) → 단순 `ADD CONSTRAINT` ms 단위 lock. >1만 row 진입 시 BL-049 패턴 (NOT VALID + VALIDATE).

### D4 — closeout (~1h)

- `docs/REFACTORING-BACKLOG.md` BL-050 § Simple 4 ✅ 완료 마크 + 잔여 3 entity carry-over 명시
- `docs/dev-log/2026-05-18-bl050-simple4-composite-fk.md` 신설 (Nygard 포맷, Sprint 21 머지 일자 기준 갱신)
- 회귀: `pytest tests/` → **325 PASS + 1 skipped** (baseline 321 + 4 audit 신규)

## Data Flow

```
[D1 audit RED]
  pytest test_workspace_integrity_audit.py -v → 빈 TestContainers DB → 8 PASS (mismatch 0 baseline)
        │
        ▼
[D2 model __table_args__]
  4 model 의 composite ForeignKeyConstraint 선언 → drift "fk pending in revision" (D3 가 해소)
        │
        ▼
[D3 alembic upgrade]
  preflight DO $$ ──┬── mismatch = 0 ──→ CREATE FK x 4 ──→ upgrade head 완료
                    └── mismatch > 0 ──→ RAISE EXCEPTION (fail-fast) ──→ 수동 backfill 후 재시도
        │
        ▼
  pytest tests/ → 325 PASS / test_alembic_upgrade.py → drift 0 GREEN
        │
        ▼
[D4 closeout + Codex 2차 → APPROVE → PR squash 머지 (base=main 확인)]
```

**핵심 invariant**:
1. D1 audit 통과 = mismatch 0 fact → D3 preflight 도 0 (이중 안전망).
2. D3 alembic ↔ D2 model = drift 0 정합.
3. nullable FK = MATCH SIMPLE 자동 면제 (NULL row 정상 INSERT 가능).

## Error Handling

| 시나리오 | 처리 | 시점 |
|---|---|---|
| D3 preflight mismatch > 0 | `RAISE EXCEPTION` → alembic abort | alembic 첫 step |
| runtime cross-workspace INSERT | `ForeignKeyViolation` → 409 Conflict (기존 handler) | runtime |
| nullable FK 의 NULL row | MATCH SIMPLE 자동 면제 (FK check skip) | PostgreSQL 기본 |
| D2/D3 drift | `test_alembic_upgrade.py` compare_metadata fail | CI/로컬 회귀 |
| 머지 후 main 미도달 | `feedback_stack_pr_base_check` protocol — gh pr view 로 base=main 확인 | 머지 직전 |

## Testing

| 항목 | 결과 |
|---|---|
| `pytest tests/` | **325 PASS + 1 skipped** (321 baseline + 4 audit 추가) |
| `pytest tests/integration/test_alembic_upgrade.py` | 1 PASS (drift 0 유지) |
| `pyright` | **132 errors** (baseline 유지) |
| Service-level test 추가 | **NO** — Sprint 19 PR #1 matrix 가 이미 검증, 본 PR 는 DB-level defense-in-depth |
| Codex 1차 plan review | verdict 후 finding 100% 수락 → plan v2 patch |
| Codex 2차 diff review | D4 직전, APPROVE 권장 |

## Production Rollback

- `alembic downgrade -1` → 4 composite FK drop (역순). 즉시 (ms 단위).
- mismatch 데이터는 그대로 (downgrade ≠ 데이터 제거).

## 머지 직전 체크리스트 (feedback_stack_pr_base_check 준수)

- [ ] `gh pr view <N> --json baseRefName` → `main` 확인
- [ ] GitHub UI "base branch" = `main` 시각 확인
- [ ] draft → ready 전환
- [ ] squash 머지 + `--delete-branch`
- [ ] `git fetch origin && git log origin/main --oneline -3` → 본 PR squash commit 도달 확인

## Critical 파일

- `backend/src/actions/models.py` — 기존 `__table_args__` 확장
- `backend/src/inbox/models.py` — `__table_args__` 신설
- `backend/src/embeddings/models.py` — embedding_chunks + semantic_caches 각 `__table_args__` 신설
- `backend/alembic/versions/<rev>_bl050_simple4_composite_fk.py` — 신설
- `backend/tests/integration/test_workspace_integrity_audit.py` — 4 audit 함수 추가
- `docs/REFACTORING-BACKLOG.md` — BL-050 § Simple 4 ✅ 마크 + carry-over
- `docs/architecture/erd.md` — Atomic Update §4 매트릭스 동시 갱신
- `docs/dev-log/2026-05-18-bl050-simple4-composite-fk.md` — 신설 (머지 일자 기준 갱신)

## 다음 세션 인계 (Sprint 22 진입 후보)

BL-050 잔여 3 entity:
- `memory_items.embedding_chunk_id` (embedding_chunks UNIQUE 신설 + composite FK)
- `memory_ai_calls.memory_id` (memory_items UNIQUE 신설 + composite FK, NOT NULL 면제 패턴 다름)
- `promotion_audit` (intentional cross-workspace, 별도 분석 + audit SQL)

기타 carry-over:
- BL-048 matrix forward coverage 강화 (kwargs 통일)
- BL-049 production alembic guard (NOT VALID + CONCURRENTLY)
- BL-051 schema drift 정리 (compare_metadata 잔여 finding)
- G5 tests/ session.exec migration
- ADR-019 Phase B Gemini 3.1-flash-lite 코드 swap (메모리 예정일 2026-05-28)
