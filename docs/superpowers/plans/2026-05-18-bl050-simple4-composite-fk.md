# BL-050 Simple 4 Composite FK Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 4 composite FK constraints (action_items.meeting / inbox.ai_suggested_project / embedding_chunks.project / semantic_caches.project) as DB-level defense-in-depth against cross-workspace data integrity violations.

**Architecture:** Sprint 19 PR #2 (`BUG-C01-EXT-FK`, merge `5789822`) stack pattern — 4 commits in sequence: D1 audit RED → D2 model `__table_args__` → D3 alembic preflight + composite FK → D4 closeout. 4 entity all have nullable FK → MATCH SIMPLE auto-skip NULL rows. Target table UNIQUE constraints already exist (no preflight UNIQUE setup needed).

**Tech Stack:** FastAPI · SQLModel (sqlmodel `ForeignKeyConstraint` re-export) · Alembic · PostgreSQL · pytest + TestContainers.

**Spec:** `docs/superpowers/specs/2026-05-18-bl050-simple4-composite-fk-design.md`

---

## File Structure

| 파일 | 작업 | Task |
|---|---|---|
| `backend/tests/integration/test_workspace_integrity_audit.py` | modify (+4 함수, ~80 lines) | Task 1 |
| `backend/src/actions/models.py` | modify (`__table_args__` 에 1 FK 추가) | Task 2.1 |
| `backend/src/inbox/models.py` | modify (`__table_args__` 신설 + import) | Task 2.2 |
| `backend/src/embeddings/models.py` | modify (EmbeddingChunk + SemanticCache 각 `__table_args__` 신설 + import) | Task 2.3 |
| `backend/alembic/versions/<rev>_bl050_simple4_composite_fk.py` | create | Task 3 |
| `docs/REFACTORING-BACKLOG.md` | modify (BL-050 § Simple 4 ✅ mark) | Task 4.1 |
| `docs/dev-log/2026-05-18-bl050-simple4-composite-fk.md` | create | Task 4.2 |
| `docs/architecture/erd.md` | modify (4 composite FK relationship 갱신) | Task 4.3 |

---

## Task 0: Setup — worktree + branch (~5min)

**Goal:** isolate Sprint 21 작업 in `../kairos-sprint-21` worktree.

- [ ] **Step 0.1: 새 worktree + branch 생성**

```bash
cd /Users/woosung/project/agy-project/kairos
git fetch origin
git status -sb  # main HEAD = cc17dd8 (spec commit) 확인
git worktree add ../kairos-sprint-21 -b sprint-21/bl-050-composite-fk-simple4
cd ../kairos-sprint-21
git log --oneline -3  # cc17dd8 → aae7e3d → c1b29c1 확인
```

- [ ] **Step 0.2: backend deps 동기화**

```bash
cd backend
uv sync
uv run pytest tests/ -q 2>&1 | tail -3
```

Expected: 321 passed + 1 skipped (BL-054 후 baseline).

- [ ] **Step 0.3: alembic head + drift baseline 확인**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-21
cd backend && uv run alembic heads
```

Expected: `e5f6g7h8i9ja (head)` (Sprint 19 PR #2).

---

## Task 1: D1 audit RED — 4 신규 audit 함수 (~2h)

**Goal:** schema 변경 없이 4 audit SQL 신설. TestContainers 빈 DB → mismatch 0 → 4 PASS baseline.

**Files:**
- Modify: `backend/tests/integration/test_workspace_integrity_audit.py:88-` (기존 4 함수 뒤에 추가)

### Step 1.1: action_items.meeting audit 함수 추가

- [ ] **Write the failing test (RED 의도, 본 DB 는 baseline GREEN)**

`backend/tests/integration/test_workspace_integrity_audit.py` 끝에 추가 (기존 `test_project_members_project_workspace_match` 다음):

```python
@pytest.mark.asyncio
async def test_action_items_meeting_workspace_match(
    integration_session: AsyncSession,
):
    """action_items.meeting_id 가 다른 workspace 의 meeting 을 가리키지 않는다.

    BL-050 Simple 4 — composite FK 신설 직전 mismatch 0 확인용 baseline audit.
    """
    result = await integration_session.execute(text("""
        SELECT a.id, a.workspace_id AS a_ws, m.workspace_id AS m_ws
        FROM action_items a
        JOIN meetings m ON m.id = a.meeting_id
        WHERE a.meeting_id IS NOT NULL AND a.workspace_id != m.workspace_id
        LIMIT 10
    """))
    mismatched = result.fetchall()
    assert len(mismatched) == 0, (
        f"BL-050 audit: action_items 의 {len(mismatched)} 행이 cross-workspace meeting 참조. "
        f"sample={mismatched[:3]}. composite FK 신설 + backfill 은 본 PR 의 D3 alembic."
    )
```

- [ ] **Run test to verify it passes (mismatch 0 fact 확인)**

```bash
cd backend
uv run pytest tests/integration/test_workspace_integrity_audit.py::test_action_items_meeting_workspace_match -v
```

Expected: 1 passed.

### Step 1.2: inbox.ai_suggested_project audit 함수 추가

- [ ] **Add test 2**

```python
@pytest.mark.asyncio
async def test_inbox_suggested_project_workspace_match(
    integration_session: AsyncSession,
):
    """inbox.ai_suggested_project_id 가 다른 workspace 의 project 를 가리키지 않는다."""
    result = await integration_session.execute(text("""
        SELECT i.id, i.workspace_id AS i_ws, p.workspace_id AS p_ws
        FROM inbox_items i
        JOIN projects p ON p.id = i.ai_suggested_project_id
        WHERE i.ai_suggested_project_id IS NOT NULL AND i.workspace_id != p.workspace_id
        LIMIT 10
    """))
    mismatched = result.fetchall()
    assert len(mismatched) == 0, (
        f"BL-050 audit: inbox_items 의 {len(mismatched)} 행이 cross-workspace project 추천. "
        f"sample={mismatched[:3]}. composite FK 신설 + backfill 은 본 PR 의 D3 alembic."
    )
```

- [ ] **Run**: `uv run pytest tests/integration/test_workspace_integrity_audit.py::test_inbox_suggested_project_workspace_match -v` → Expected: 1 passed.

### Step 1.3: embedding_chunks.project audit 함수 추가

- [ ] **Add test 3**

```python
@pytest.mark.asyncio
async def test_embedding_chunks_project_workspace_match(
    integration_session: AsyncSession,
):
    """embedding_chunks.project_id 가 다른 workspace 의 project 를 가리키지 않는다."""
    result = await integration_session.execute(text("""
        SELECT ec.id, ec.workspace_id AS ec_ws, p.workspace_id AS p_ws
        FROM embedding_chunks ec
        JOIN projects p ON p.id = ec.project_id
        WHERE ec.project_id IS NOT NULL AND ec.workspace_id != p.workspace_id
        LIMIT 10
    """))
    mismatched = result.fetchall()
    assert len(mismatched) == 0, (
        f"BL-050 audit: embedding_chunks 의 {len(mismatched)} 행이 cross-workspace project 참조. "
        f"sample={mismatched[:3]}. composite FK 신설 + backfill 은 본 PR 의 D3 alembic."
    )
```

- [ ] **Run**: `uv run pytest tests/integration/test_workspace_integrity_audit.py::test_embedding_chunks_project_workspace_match -v` → Expected: 1 passed.

### Step 1.4: semantic_caches.project audit 함수 추가

- [ ] **Add test 4**

```python
@pytest.mark.asyncio
async def test_semantic_caches_project_workspace_match(
    integration_session: AsyncSession,
):
    """semantic_caches.project_id 가 다른 workspace 의 project 를 가리키지 않는다."""
    result = await integration_session.execute(text("""
        SELECT sc.id, sc.workspace_id AS sc_ws, p.workspace_id AS p_ws
        FROM semantic_caches sc
        JOIN projects p ON p.id = sc.project_id
        WHERE sc.project_id IS NOT NULL AND sc.workspace_id != p.workspace_id
        LIMIT 10
    """))
    mismatched = result.fetchall()
    assert len(mismatched) == 0, (
        f"BL-050 audit: semantic_caches 의 {len(mismatched)} 행이 cross-workspace project 참조. "
        f"sample={mismatched[:3]}. composite FK 신설 + backfill 은 본 PR 의 D3 alembic."
    )
```

- [ ] **Run**: `uv run pytest tests/integration/test_workspace_integrity_audit.py::test_semantic_caches_project_workspace_match -v` → Expected: 1 passed.

### Step 1.5: D1 회귀 + commit

- [ ] **회귀: audit 8 PASS + 전체 회귀**

```bash
cd backend
uv run pytest tests/integration/test_workspace_integrity_audit.py -v 2>&1 | tail -15
```

Expected: 8 passed (기존 4 + 신규 4).

```bash
uv run pytest tests/ -q 2>&1 | tail -3
```

Expected: 325 passed + 1 skipped (baseline 321 + 4 신규).

- [ ] **Commit D1**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-21
git add backend/tests/integration/test_workspace_integrity_audit.py
git commit -m "$(cat <<'EOF'
test(bl-050): D1 audit RED 확장 — 4 신규 cross-workspace audit 함수

Sprint 19 PR #1 4 audit (project_workspace_match 패턴) 위에 4 entity 추가:
- action_items.meeting_id ↔ meetings.workspace_id
- inbox.ai_suggested_project_id ↔ projects.workspace_id
- embedding_chunks.project_id ↔ projects.workspace_id
- semantic_caches.project_id ↔ projects.workspace_id

TestContainers 빈 DB → mismatch 0 → 8 PASS (기존 4 + 신규 4) baseline GREEN.
D3 alembic preflight 와 이중 안전망.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Codex 1차 plan review gate (Task 1 이후, ~30min)

Sprint 19 PR #2 패턴 — D1 직후 plan + 첫 commit 으로 Codex review 진입. Codex finding 100% 수락 → plan v2 patch.

- [ ] **Codex review 호출**

```bash
# kairos-sprint-21 worktree
cd /Users/woosung/project/agy-project/kairos-sprint-21
# /codex review skill — diff vs origin/main + spec doc 동봉
```

또는 main 세션의 Skill 도구로 `codex` 호출. plan + D1 diff + spec 첨부.

- [ ] **Codex finding 평가**

verdict = APPROVE / REVISE / BLOCK 중 하나. REVISE 시 finding 100% 수락 → plan 갱신 → 본 plan 파일 inline patch + 재 commit. BLOCK 시 immediate stop.

---

## Task 2: D2 model `__table_args__` 4 patch (~2h)

**Goal:** 4 model 에 composite ForeignKeyConstraint 선언. import 추가 + table_args 신설/확장.

**Files:**
- Modify: `backend/src/actions/models.py:11-19` (기존 `__table_args__` 확장)
- Modify: `backend/src/inbox/models.py` (import + `__table_args__` 신설)
- Modify: `backend/src/embeddings/models.py` (import + 2 model 의 `__table_args__` 신설)

### Step 2.1: actions/models.py 확장

- [ ] **Edit `backend/src/actions/models.py:11-19` — meeting composite FK 추가**

기존 `__table_args__`:

```python
    __table_args__ = (
        # Sprint 19 PR #2 D4 (BUG-C01-EXT-FK / 헌법 I-9 (9)): cross-workspace project_id insert 차단.
        # 기존 single-FK (workspace_id → workspaces.id, project_id → projects.id) 유지 — defense-in-depth.
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_action_items_project_workspace",
        ),
    )
```

→ 확장:

```python
    __table_args__ = (
        # Sprint 19 PR #2 D4 (BUG-C01-EXT-FK / 헌법 I-9 (9)): cross-workspace project_id insert 차단.
        # 기존 single-FK (workspace_id → workspaces.id, project_id → projects.id) 유지 — defense-in-depth.
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_action_items_project_workspace",
        ),
        # Sprint 21 BL-050 Simple 4: cross-workspace meeting_id insert 차단.
        # meetings(id, workspace_id) UNIQUE 는 PR #2 e5f6g7h8i9ja 에서 신설됨.
        # nullable FK → MATCH SIMPLE NULL row 면제.
        ForeignKeyConstraint(
            ["workspace_id", "meeting_id"],
            ["meetings.workspace_id", "meetings.id"],
            name="fk_action_items_meeting_workspace",
        ),
    )
```

### Step 2.2: inbox/models.py `__table_args__` 신설

- [ ] **Edit `backend/src/inbox/models.py` — import + `__table_args__` 신설**

`from sqlmodel import JSON, Field, SQLModel` 를:

```python
from sqlmodel import JSON, Field, ForeignKeyConstraint, SQLModel
```

`class InboxItem(SQLModel, table=True):` 의 `__tablename__` 다음, field 선언 전 삽입:

```python
class InboxItem(SQLModel, table=True):
    __tablename__ = "inbox_items"
    __table_args__ = (
        # Sprint 21 BL-050 Simple 4: cross-workspace ai_suggested_project_id 차단.
        # nullable FK → MATCH SIMPLE NULL row 면제 (AI 추천 없는 inbox 정상).
        ForeignKeyConstraint(
            ["workspace_id", "ai_suggested_project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_inbox_suggested_project_workspace",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # ... 기존 field 유지
```

### Step 2.3: embeddings/models.py 2 model 의 `__table_args__` 신설

- [ ] **Edit `backend/src/embeddings/models.py` — import + 2 model __table_args__**

`from sqlmodel import JSON, Column, Field, SQLModel, Text` 를:

```python
from sqlmodel import JSON, Column, Field, ForeignKeyConstraint, SQLModel, Text
```

`class EmbeddingChunk(SQLModel, table=True):` 의 `__tablename__ = "embedding_chunks"` 다음 삽입:

```python
class EmbeddingChunk(SQLModel, table=True):
    """계층적 임베딩 청크. Level 2(문단)가 검색 대상."""

    __tablename__ = "embedding_chunks"
    __table_args__ = (
        # Sprint 21 BL-050 Simple 4: cross-workspace project_id 차단.
        # nullable FK → MATCH SIMPLE NULL row 면제 (workspace-level 임베딩 정상).
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_embedding_chunks_project_workspace",
        ),
    )
    # ... 기존 field 유지
```

`class SemanticCache(SQLModel, table=True):` 의 `__tablename__ = "semantic_caches"` 다음 삽입:

```python
class SemanticCache(SQLModel, table=True):
    """시맨틱 캐시. 유사 질문 → 캐시 답변 반환."""

    __tablename__ = "semantic_caches"
    __table_args__ = (
        # Sprint 21 BL-050 Simple 4: cross-workspace project_id 차단.
        # nullable FK → MATCH SIMPLE NULL row 면제 (workspace-level 캐시 정상).
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_semantic_caches_project_workspace",
        ),
    )
    # ... 기존 field 유지
```

### Step 2.4: D2 회귀 + commit

- [ ] **회귀: pytest + pyright**

```bash
cd backend
uv run pytest tests/ -q 2>&1 | tail -3
```

Expected: 325 passed + 1 skipped (model 변경 = test 영향 0).

```bash
uv run pyright 2>&1 | tail -3
```

Expected: 132 errors (baseline 유지, ForeignKeyConstraint 는 type-safe).

- [ ] **alembic drift 의도 확인**

```bash
cd backend
uv run pytest tests/integration/test_alembic_upgrade.py -v 2>&1 | tail -10
```

Expected: **FAIL** with drift "fk constraint pending in revision" (D2 model 과 alembic head `e5f6g7h8i9ja` 불일치 — 의도된 상태, D3 가 해소).

> drift FAIL 이 의도된 RED. D3 에서 GREEN 으로 전환.

- [ ] **Commit D2**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-21
git add backend/src/actions/models.py backend/src/inbox/models.py backend/src/embeddings/models.py
git commit -m "$(cat <<'EOF'
refactor(bl-050): D2 4 model __table_args__ — composite FK 선언

Sprint 21 BL-050 Simple 4 — model layer composite FK 선언:
- action_items.meeting_id ↔ meetings(workspace_id, id) (기존 project FK 옆 추가)
- inbox_items.ai_suggested_project_id ↔ projects(workspace_id, id) (__table_args__ 신설)
- embedding_chunks.project_id ↔ projects(workspace_id, id) (__table_args__ 신설)
- semantic_caches.project_id ↔ projects(workspace_id, id) (__table_args__ 신설)

nullable FK → MATCH SIMPLE NULL row 자동 면제 (Sprint 19 PR #2 notes 패턴).
ForeignKeyConstraint import = sqlmodel re-export (BL-052 cleanup 후).

alembic drift = 의도된 RED (D3 alembic 으로 해소).
회귀: pytest 325 PASS / pyright 132 baseline 유지.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: D3 alembic migration (~3h)

**Goal:** preflight DO $$ + 4 composite FK upgrade in single revision. alembic head `e5f6g7h8i9ja` 위.

**Files:**
- Create: `backend/alembic/versions/f6g7h8i9jakb_bl050_simple4_composite_fk.py` (혹은 alembic 자동 ID)

### Step 3.1: alembic revision 생성

- [ ] **Manual revision 생성 (autogenerate 가 preflight + RAISE 미생성)**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-21/backend
uv run alembic revision -m "bl050_simple4_composite_fk"
```

Output: `Generating <path>/<rev>_bl050_simple4_composite_fk.py`. revision 파일명의 `<rev>` 부분 확인.

### Step 3.2: revision 파일 content 작성

- [ ] **Edit 새 revision 파일** — 전체 content 교체:

```python
"""BL-050 Simple 4 — composite FK (action_items.meeting + inbox.suggested + embedding_chunks.project + semantic_caches.project).

Revision ID: <auto-generated>
Revises: e5f6g7h8i9ja
Create Date: 2026-05-18

배경:
- Sprint 19 PR #2 (BUG-C01-EXT-FK) 의 후속 hardening.
- 4 entity 의 cross-workspace single-FK 패턴을 composite FK 로 강화.
- 4 entity 모두 nullable → MATCH SIMPLE NULL row 자동 면제.

scope (4 composite FK):
1. action_items (workspace_id, meeting_id) → meetings(workspace_id, id)
2. inbox_items (workspace_id, ai_suggested_project_id) → projects(workspace_id, id)
3. embedding_chunks (workspace_id, project_id) → projects(workspace_id, id)
4. semantic_caches (workspace_id, project_id) → projects(workspace_id, id)

scale trade-off (Sprint 19 PR #2 와 동일):
- dogfooding scale (~수십 row) = 단순 ADD CONSTRAINT ms 단위 lock. 본 revision 단순 패턴.
- production scale (>1만 row) 진입 시 BL-049 NOT VALID + VALIDATE 2단계 권장.
- Cloud Run 컨테이너 startup = 트래픽 받기 전 자연 maintenance window.

preflight 안전성 (D1 audit 4 PASS 기반):
- D1 audit 가 이미 mismatch 0 확인.
- 본 preflight DO $$ 는 production 데이터 mismatch 대비 이중 안전망.
- RAISE EXCEPTION on mismatch > 0 → alembic abort + 명확한 메시지.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '<auto-generated>'  # alembic revision 자동 생성된 값으로 교체 (Step 3.1)
down_revision: Union[str, Sequence[str], None] = 'e5f6g7h8i9ja'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """4 entity composite FK 일괄 추가.

    preflight (PR #2 패턴): mismatch row 가 있으면 RAISE EXCEPTION 으로 fail-fast.
    """
    # 0. preflight — 4 mismatch check
    op.execute(
        """
        DO $$
        DECLARE
            cnt_ai_m INT;
            cnt_ib INT;
            cnt_ec INT;
            cnt_sc INT;
        BEGIN
            SELECT COUNT(*) INTO cnt_ai_m FROM action_items a
              JOIN meetings m ON m.id = a.meeting_id
              WHERE a.meeting_id IS NOT NULL AND a.workspace_id != m.workspace_id;
            IF cnt_ai_m > 0 THEN
                RAISE EXCEPTION 'BL-050 preflight: action_items.meeting mismatch=% (composite FK 추가 불가, fix 후 재실행)', cnt_ai_m;
            END IF;

            SELECT COUNT(*) INTO cnt_ib FROM inbox_items i
              JOIN projects p ON p.id = i.ai_suggested_project_id
              WHERE i.ai_suggested_project_id IS NOT NULL AND i.workspace_id != p.workspace_id;
            IF cnt_ib > 0 THEN
                RAISE EXCEPTION 'BL-050 preflight: inbox_items.suggested mismatch=% (composite FK 추가 불가)', cnt_ib;
            END IF;

            SELECT COUNT(*) INTO cnt_ec FROM embedding_chunks ec
              JOIN projects p ON p.id = ec.project_id
              WHERE ec.project_id IS NOT NULL AND ec.workspace_id != p.workspace_id;
            IF cnt_ec > 0 THEN
                RAISE EXCEPTION 'BL-050 preflight: embedding_chunks.project mismatch=% (composite FK 추가 불가)', cnt_ec;
            END IF;

            SELECT COUNT(*) INTO cnt_sc FROM semantic_caches sc
              JOIN projects p ON p.id = sc.project_id
              WHERE sc.project_id IS NOT NULL AND sc.workspace_id != p.workspace_id;
            IF cnt_sc > 0 THEN
                RAISE EXCEPTION 'BL-050 preflight: semantic_caches.project mismatch=% (composite FK 추가 불가)', cnt_sc;
            END IF;
        END $$;
        """
    )

    # 1. action_items meeting composite FK
    op.create_foreign_key(
        "fk_action_items_meeting_workspace",
        "action_items",
        "meetings",
        ["workspace_id", "meeting_id"],
        ["workspace_id", "id"],
    )

    # 2. inbox suggested project composite FK
    op.create_foreign_key(
        "fk_inbox_suggested_project_workspace",
        "inbox_items",
        "projects",
        ["workspace_id", "ai_suggested_project_id"],
        ["workspace_id", "id"],
    )

    # 3. embedding_chunks project composite FK
    op.create_foreign_key(
        "fk_embedding_chunks_project_workspace",
        "embedding_chunks",
        "projects",
        ["workspace_id", "project_id"],
        ["workspace_id", "id"],
    )

    # 4. semantic_caches project composite FK
    op.create_foreign_key(
        "fk_semantic_caches_project_workspace",
        "semantic_caches",
        "projects",
        ["workspace_id", "project_id"],
        ["workspace_id", "id"],
    )


def downgrade() -> None:
    """역순 drop. 데이터 영향 0 (constraint drop 만)."""
    op.drop_constraint("fk_semantic_caches_project_workspace", "semantic_caches", type_="foreignkey")
    op.drop_constraint("fk_embedding_chunks_project_workspace", "embedding_chunks", type_="foreignkey")
    op.drop_constraint("fk_inbox_suggested_project_workspace", "inbox_items", type_="foreignkey")
    op.drop_constraint("fk_action_items_meeting_workspace", "action_items", type_="foreignkey")
```

> **Important**: Step 3.1 의 alembic 자동 revision ID (예: `f6g7h8i9jakb`) 를 `revision: str` 필드에 정확히 복사 (`<auto-generated>` placeholder 제거).

### Step 3.3: alembic upgrade head + drift 검증

- [ ] **local DB 에 적용**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-21/backend
uv run alembic upgrade head 2>&1 | tail -10
```

Expected: `Running upgrade e5f6g7h8i9ja -> <new-rev>` (preflight 통과 + 4 FK 생성).

mismatch 발견 시 alembic 이 RAISE EXCEPTION 으로 abort → mismatch row 수동 fix 후 재시도.

- [ ] **drift 검증**

```bash
uv run pytest tests/integration/test_alembic_upgrade.py -v 2>&1 | tail -10
```

Expected: 1 passed (drift 0, D2 model ↔ D3 alembic 정합).

### Step 3.4: D3 회귀 + commit

- [ ] **회귀**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-21/backend
uv run pytest tests/ -q 2>&1 | tail -3
```

Expected: 325 passed + 1 skipped (audit 4 + alembic 1 + 기존 320).

```bash
uv run pyright 2>&1 | tail -3
```

Expected: 132 errors (baseline 유지).

- [ ] **Commit D3**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-21
git add backend/alembic/versions/<rev>_bl050_simple4_composite_fk.py
git commit -m "$(cat <<'EOF'
feat(bl-050): D3 alembic — 4 composite FK + preflight DO $$ (single revision)

Sprint 21 BL-050 Simple 4 — DB-level composite FK 신설:
- fk_action_items_meeting_workspace
- fk_inbox_suggested_project_workspace
- fk_embedding_chunks_project_workspace
- fk_semantic_caches_project_workspace

preflight: 4 mismatch SELECT COUNT → RAISE EXCEPTION on > 0 (fail-fast).
D1 audit 8 PASS + 본 preflight 이중 안전망.

scale: dogfooding (~수십 row) 단순 ADD CONSTRAINT ms 단위 lock.
production (>1만 row) 진입 시 BL-049 NOT VALID + VALIDATE 별도.

회귀: pytest 325 PASS / alembic drift 0 / pyright 132 baseline.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: D4 closeout (~1h)

**Goal:** BACKLOG ✅ + dev-log 신설 + ERD 갱신 + 최종 회귀.

### Step 4.1: REFACTORING-BACKLOG.md BL-050 mark

- [ ] **Edit `docs/REFACTORING-BACKLOG.md` BL-050 § (`docs/REFACTORING-BACKLOG.md:1319-1342`)**

기존 BL-050 헤더:

```markdown
## BL-050 — 잔여 cross-workspace single-FK entity audit + composite FK 신설 (BUG-C01-EXT-FK 잔여)
```

→

```markdown
## BL-050 — 잔여 cross-workspace single-FK entity audit + composite FK 신설 (BUG-C01-EXT-FK 잔여) 🟡 **PARTIAL (Simple 4 완료, 2026-05-18 Sprint 21 PR #NN)**
```

(`#NN` 은 PR 생성 후 갱신)

기존 항목 끝 `**근거**: Sprint 19 PR #2 plan agent §D scope omission, Codex 1차 F-8.` 직전에 추가:

```markdown
### Simple 4 완료 (Sprint 21 PR #NN, 2026-05-18)

- ✅ action_items.meeting_id (composite FK + audit)
- ✅ inbox.ai_suggested_project_id (composite FK + audit)
- ✅ embedding_chunks.project_id (composite FK + audit)
- ✅ semantic_caches.project_id (composite FK + audit)

### Carry-over (Sprint 22+)

- memory_items.embedding_chunk_id — embedding_chunks(id, workspace_id) UNIQUE 선행 작업 필요
- memory_ai_calls.memory_id — memory_items(id, workspace_id) UNIQUE 선행 + NOT NULL FK 패턴 다름
- promotion_audit (source/target workspace_id) — intentional cross-workspace, 별도 분석
```

### Step 4.2: dev-log 신설

- [ ] **Create `docs/dev-log/2026-05-18-bl050-simple4-composite-fk.md` (Nygard 포맷)**

```markdown
# BL-050 Simple 4 — Cross-workspace Composite FK Hardening (Sprint 21)

> 일자: 2026-05-18 · PR #NN · 작성자: woo sung

## Context

Sprint 19 PR #2 (BUG-C01-EXT-FK, merge 5789822) 의 후속 hardening. 4 entity (action_items.meeting / inbox.suggested / embedding_chunks.project / semantic_caches.project) 의 cross-workspace single-FK 를 composite FK 로 강화.

## Decision

Simple 4 subset 만 단일 PR (4 commit stack):
- D1 audit RED — 4 신규 audit (mismatch 0 baseline)
- D2 model `__table_args__` — 4 model 의 composite ForeignKeyConstraint 선언
- D3 alembic — preflight DO $$ + 4 composite FK single revision
- D4 closeout — 본 doc + BACKLOG mark

잔여 3 entity (memory_items / memory_ai_calls / promotion_audit) 는 carry-over.

## Consequences

- DB-level defense-in-depth: cross-workspace INSERT 가 PostgreSQL FK violation 으로 차단 (409 Conflict).
- nullable FK MATCH SIMPLE 면제 → NULL row 정상 (워크스페이스-level 임베딩/캐시/AI 추천 정상).
- Sprint 19 PR #2 patterns 재사용 (preflight DO $$, single revision, MATCH SIMPLE, dogfooding scale).
- production scale (>1만 row) 진입 시 BL-049 NOT VALID + VALIDATE 별도 적용.

## Verification

- `pytest tests/` → 325 passed + 1 skipped (baseline 321 + 4 audit)
- `pytest tests/integration/test_alembic_upgrade.py` → 1 passed (drift 0)
- `pytest tests/integration/test_workspace_integrity_audit.py` → 8 passed (기존 4 + 신규 4)
- `pyright` → 132 errors (baseline 유지)
- Codex 1차 plan review + 2차 diff review → APPROVE

## References

- Spec: `docs/superpowers/specs/2026-05-18-bl050-simple4-composite-fk-design.md`
- Plan: `docs/superpowers/plans/2026-05-18-bl050-simple4-composite-fk.md`
- Sprint 19 PR #2: `5789822` (BUG-C01-EXT-FK base pattern)
- Feedback: `[[feedback_stack_pr_base_check]]` (머지 직전 base=main 확인 protocol)
```

### Step 4.3: ERD 갱신 (Atomic Update §4)

- [ ] **Edit `docs/architecture/erd.md`** — composite FK 4 relationship 갱신

기존 ERD 의 dashed (single FK) → solid (composite FK) 라인 갱신. 또는 별도 §"BL-050 Simple 4 composite FK" 섹션 추가:

```markdown
### BL-050 Simple 4 composite FK (Sprint 21, 2026-05-18)

| 출발 entity | 컬럼 | 도착 entity | composite FK 명 |
|---|---|---|---|
| action_items | (workspace_id, meeting_id) | meetings | fk_action_items_meeting_workspace |
| inbox_items | (workspace_id, ai_suggested_project_id) | projects | fk_inbox_suggested_project_workspace |
| embedding_chunks | (workspace_id, project_id) | projects | fk_embedding_chunks_project_workspace |
| semantic_caches | (workspace_id, project_id) | projects | fk_semantic_caches_project_workspace |

모두 nullable FK → MATCH SIMPLE NULL row 자동 면제.
```

> erd.md 의 정확한 patch 위치는 file 의 기존 구조 (Mermaid diagram + 표 등) 에 맞춰 결정. ERD 의 일관성을 우선.

### Step 4.4: 최종 회귀

- [ ] **회귀 final**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-21/backend
uv run pytest tests/ -q 2>&1 | tail -3
uv run pytest tests/integration/test_workspace_integrity_audit.py -v 2>&1 | tail -15
uv run pytest tests/integration/test_alembic_upgrade.py -v 2>&1 | tail -5
uv run pyright 2>&1 | tail -3
```

Expected:
- pytest tests/ → 325 passed + 1 skipped
- audit 8 passed
- alembic 1 passed (drift 0)
- pyright 132 errors

### Step 4.5: Codex 2차 diff review gate

- [ ] **Codex 호출 (D1~D4 전체 diff)**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-21
# /codex review skill — diff vs origin/main
```

verdict = APPROVE 권장. REVISE 시 finding 100% 수락 → patch 추가 commit.

### Step 4.6: D4 closeout commit

- [ ] **Commit D4**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-21
git add docs/REFACTORING-BACKLOG.md docs/dev-log/2026-05-18-bl050-simple4-composite-fk.md docs/architecture/erd.md
git commit -m "$(cat <<'EOF'
docs(bl-050): D4 closeout — BACKLOG 🟡 PARTIAL mark + dev-log + ERD 갱신

Sprint 21 BL-050 Simple 4 closeout:
- docs/REFACTORING-BACKLOG.md BL-050 § 🟡 PARTIAL mark + Simple 4 ✅ + Sprint 22 carry-over
- docs/dev-log/2026-05-18-bl050-simple4-composite-fk.md (Nygard 포맷, PR #NN reference)
- docs/architecture/erd.md composite FK 4 relationship 갱신

Atomic Update §4 매트릭스 준수 (model 변경 + alembic + ERD 동시 commit).

회귀 최종:
- pytest tests/ → 325 passed + 1 skipped
- audit 8 PASS / alembic drift 0 / pyright 132 baseline

Codex 2차 diff review → APPROVE.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: PR 생성 + 머지 (사용자 승인 게이트)

### Step 5.1: push + draft PR 생성

- [ ] **Git Safety Protocol §3 푸쉬 승인 필요**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-21
git push -u origin sprint-21/bl-050-composite-fk-simple4
gh pr create --base main --draft \
  --title "Sprint 21 BL-050 Simple 4: cross-workspace composite FK hardening (4 commits)" \
  --body "$(cat <<'EOF'
## Summary

Sprint 19 PR #2 (BUG-C01-EXT-FK, 5789822) 의 후속 hardening — BL-050 의 7+ entity 중
**Simple 4 subset** (nullable + UNIQUE 선행재) 만 단일 PR 로 closure.

## Scope (4 composite FK)

- action_items.meeting_id ↔ meetings(workspace_id, id)
- inbox.ai_suggested_project_id ↔ projects(workspace_id, id)
- embedding_chunks.project_id ↔ projects(workspace_id, id)
- semantic_caches.project_id ↔ projects(workspace_id, id)

## Commits (4-stack)

- D1 test(bl-050): audit RED 확장 — 4 신규 audit
- D2 refactor(bl-050): 4 model __table_args__ composite FK 선언
- D3 feat(bl-050): alembic preflight + 4 composite FK single revision
- D4 docs(bl-050): closeout — BACKLOG mark + dev-log + ERD

## Test plan

- [x] `pytest tests/` → 325 passed + 1 skipped (baseline 321 + 4 audit)
- [x] `pytest tests/integration/test_alembic_upgrade.py` → drift 0
- [x] `pytest tests/integration/test_workspace_integrity_audit.py` → 8 PASS
- [x] `pyright` → 132 errors (baseline 유지)
- [x] Codex 1차 plan review + 2차 diff review → APPROVE

## Carry-over (Sprint 22+)

- memory_items.embedding_chunk_id (UNIQUE 신설 필요)
- memory_ai_calls.memory_id (UNIQUE 신설 + NOT NULL 패턴)
- promotion_audit (intentional cross-workspace, 별도 분석)

## 머지 직전 체크리스트 (feedback_stack_pr_base_check 준수)

- [ ] `gh pr view <N> --json baseRefName` → `main` 확인
- [ ] draft → ready 전환
- [ ] squash 머지 + `--delete-branch`
- [ ] `git fetch origin && git log origin/main --oneline -3` → squash commit 도달 확인

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### Step 5.2: BACKLOG 와 dev-log 의 `#NN` placeholder 갱신

- [ ] **PR 번호 확정 후 1 commit**

```bash
gh pr view --json number
# 출력된 번호로 docs/REFACTORING-BACKLOG.md 와 docs/dev-log/2026-05-18-bl050-simple4-composite-fk.md 의 "#NN" 일괄 치환
git add docs/REFACTORING-BACKLOG.md docs/dev-log/2026-05-18-bl050-simple4-composite-fk.md
git commit -m "docs(bl-050): PR 번호 #<N> 확정 갱신"
git push
```

### Step 5.3: 머지 (사용자 승인 게이트)

- [ ] **base=main 확인 + ready + 머지**

```bash
gh pr view <N> --json baseRefName  # → "main" 확인 (feedback_stack_pr_base_check)
gh pr ready <N>
# 사용자 승인 후
gh pr merge <N> --squash --delete-branch
```

- [ ] **main 도달 검증**

```bash
cd /Users/woosung/project/agy-project/kairos
git fetch origin
git log origin/main --oneline -3
# 본 PR squash commit 이 HEAD 인지 확인
```

### Step 5.4: worktree 정리

- [ ] **사용자 승인 후 worktree 제거**

```bash
cd /Users/woosung/project/agy-project/kairos
git worktree remove ../kairos-sprint-21
git branch -D sprint-21/bl-050-composite-fk-simple4
```

---

## Verification Summary

| 단계 | 검증 | 기대 결과 |
|---|---|---|
| D1 commit | `pytest tests/` | 325 passed + 1 skipped |
| D2 commit | `pytest tests/` + `pyright` | 325 / 132 errors / alembic drift FAIL (의도) |
| D3 commit | 위 + `alembic upgrade head` | 325 / 132 / drift 0 |
| D4 commit | 모든 위 + Codex 2차 | APPROVE |
| 머지 후 | `git log origin/main --oneline -3` | 본 PR squash commit 도달 |

---

## Memory 갱신 (closeout 후 별도 commit 또는 main 직접)

- [ ] **`project_sprint21_bl050_simple4_done.md` 신설** in `/Users/woosung/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/`

- [ ] **`MEMORY.md` 인덱스 1줄 추가**

---

## Critical 파일 (실제 작업 시)

- `backend/tests/integration/test_workspace_integrity_audit.py` (D1)
- `backend/src/{actions,inbox,embeddings}/models.py` (D2)
- `backend/alembic/versions/<rev>_bl050_simple4_composite_fk.py` (D3 신설)
- `docs/REFACTORING-BACKLOG.md` (D4)
- `docs/dev-log/2026-05-18-bl050-simple4-composite-fk.md` (D4 신설)
- `docs/architecture/erd.md` (D4)

---

## 다음 세션 인계

머지 후 잔여:
- BL-050 Sprint 22 진입 (memory_items / memory_ai_calls / promotion_audit 3 entity)
- 또는 ADR-019 Phase B Gemini 3.1-flash-lite 코드 swap (2026-05-28 예정)
- 또는 BL-048 matrix forward coverage 강화
