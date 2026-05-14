<!-- Sprint 15 Recall-first prototype 구현 plan — R1~R8 task spec. Stage 3 Q3 산출. -->

# Sprint 15 Recall-first Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Sprint 15 Recall-first wedge prototype 구현. `/memory` route + voice/text capture + Gemini distill + vector + keyword-fallback recall + 1-button promote + R7 metrics + R8 PERSONA outreach.

> **FIX iter 1 patch applied (2026-05-14)**: `/docs/dev-log/2026-05-14-sprint15-plan-patch.md` 참조 — codex 적대적 검토 (Q4) 20 finding 중 15 must-fix를 patch doc에 inline. Stage 4 진입 시 본 plan + patch doc 함께 참조. **R1 진입 전 first task = T-1 fixtures + ffmpeg Dockerfile** (patch §2).

**Architecture:** 신규 `backend/src/memory/` 도메인 모듈 (Router/Service/Repository/Schemas/Models). 신규 alembic migration (memory_items + workspaces.type). 신규 `frontend/src/features/memory/` (FSD). 헌법 I-9 patch + I-19 코드 R3/R5 commit과 atomic.

**Tech Stack:** FastAPI + SQLModel + asyncpg + pgvector + Gemini gemini-2.5-flash + OpenAI text-embedding-3-small + Whisper API + aioboto3 R2 + Next.js 16 + React Query + shadcn/ui v4 + Tailwind v4.

---

## §0. Context (Stage 0+1+2 요약)

### 0.1 Recall-first wedge (Stage 1 lock-in)

Codex 2nd opinion 수용 — "10명/7일/3명 unprompted/1명 paying" evidence pattern. Capture (voice+text) → AI distill → top-3 recall = wedge. Promotion = retention/expansion ghost feature (Sprint 17+ 정식). 외부 5명 PERSONA testing + founder dogfooding으로 검증.

### 0.2 Stage 0 헌법 patch 본문 (atomic with code)

- **I-9 강화** (4-C inline patch on `CONTEXT-MAP.md`, R3 commit과 atomic):
  > 모든 Repository는 `workspace_id` 필터 강제. 신규 EmbeddingChunk insert 시 `workspace_id`는 신규 entity owner workspace와 매칭 (service layer assertion).
- **I-19 신설** (서비스 코드 invariant, R5 commit과 atomic. **CONTEXT-MAP 본문 등재는 Sprint 17+ 정식 신설 시 defer**):
  > 모든 Workspace는 `type: 'personal' | 'team'`. Personal은 (a) owner 1명 강제 (DB UNIQUE partial index `(owner_id) WHERE type='personal'`), (b) 멤버 추가/초대 차단, (c) 삭제 차단 (계정 cascade 외), (d) 모든 user 자동 보유 (lazy seed on first login).
- **I-18** (Promotion 불변식 본문 등재) = Sprint 17+ 정식 build 시. R6 prototype은 코드 atomic만.

### 0.3 Stage 2 DESIGN.md patch + Stage 3 Q1 approved variants

- A1 personal-first switcher / B3 search-first FAB / C1 promote dropdown.
- `DESIGN.md §132~219` 정합. 색상 신규 0 (1 accent #3ECFB4 + neutrals).
- Recall result card spec (DESIGN.md §176~187), Promote ghost button (§190~200), Promote modal (§202~211).

### 0.4 Stage 3 Q2 brainstorm 5 Open Q lock-in

- O-A: **Top 3** source memo / O-B: **token overlap count** / O-C: **인터뷰 only** (in-app modal 0) / O-D: **인디해커즈→X DM→HN-Show** / O-E: **R2 store + 30일 TTL**.

---

## §1. Schedule (Day 1~14 stagger)

| Day | 활동 | 결과 |
|-----|------|------|
| **Day 0** | (1) R8 outreach 3 채널 동시 시작 (founder ~1h) (2) Whisper+Gemini 10 sample spike (codex 입력) | outreach posts live + cost spike report |
| **Day 1** | T0 ADR-016 AD-41 reframe commit + R2 alembic migration | migration committed |
| **Day 2** | R1 BE memory API (capture + distill) + R5 personal seed (병행) | POST /memory 작동 |
| **Day 3** | R3 BE recall + I-9 patch atomic commit + R4 FE start | GET /memory/recall 작동 |
| **Day 3 end** | **Quality gate**: founder dogfooding capture ≥ 5, recall thumbs-up ≥ 3 | gate pass → R6/R7 진입 / fail → R3 fix |
| **Day 4-5** | R4 FE 완성 + R6 BE+FE promote + R7 metrics | /memory page e2e |
| **Day 5** | 1st PERSONA 인터뷰 (R8 outreach 결과로) | persona feedback log |
| **Day 6-12** | PERSONA 5명 7일 testing window + founder 병행 dogfooding | usage telemetry |
| **Day 13-14** | 인터뷰 5명 종합 + Sprint 16 결정 | retrospective + go/no-go |

> **R8 SLA**: Day 3 0/5 응답 시 cold expansion (LinkedIn / Reddit r/SaaS / 본인 X 친구). Day 7 ≤1명 응답 시 Success criteria = Minimum (founder + 1) 자동 전환.

---

## §2. R1~R8 Task Spec

### Task T0: ADR-016 AD-41 reframe inline (atomic 단일 commit, R1 진입 직전)

**Files:**
- Modify: `docs/dev-log/016-personal-team-ia.md` (AD-41 본문)
- Modify: `docs/TODO.md` Sprint 17+ candidates 섹션 (S17-T-PROMOTION-REFRAME 추가)

- [ ] **Step 1: ADR-016 AD-41 inline reframe**

`docs/dev-log/016-personal-team-ia.md`의 AD-41 본문 끝에 추가:

```markdown
> **[2026-05-14 reframe note]** Promotion = post-Recall-validation feature. v1 wedge 아니며 Sprint 17+ 정식 implementation. Recall demand 검증 (Sprint 15 R8 success criteria 충족) 통과 시 진입. Sprint 15에서는 S15-R6 1-button promote prototype만 (audit row 1개, multi-team/chain/review queue 모두 후순위). 근거: Stage 1 design doc `~/.gstack/projects/woosung-dev-kairos/woosung-sprint-15-personal-workspace-design-20260514-090026.md` §Premise 5 revision.
```

- [ ] **Step 2: Commit**

```bash
git add docs/dev-log/016-personal-team-ia.md docs/TODO.md
git commit -m "docs(adr-016): AD-41 reframe — Promotion = post-Recall-validation feature, Sprint 17+ 정식 implementation"
```

---

### Task R2: alembic migration — memory_items + workspaces.type (R1 dependency, build 먼저)

**Files:**
- Create: `backend/alembic/versions/<hash>_add_memory_items_workspace_type.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_alembic_memory.py`:

```python
"""memory_items table + workspaces.type 컬럼 스키마 검증."""
import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_memory_items_table_exists(integration_session):
    result = await integration_session.execute(
        text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'memory_items' ORDER BY ordinal_position"
        )
    )
    columns = {row[0]: row[1] for row in result.all()}
    assert "id" in columns
    assert "user_id" in columns
    assert "workspace_id" in columns
    assert "type" in columns  # voice | text
    assert "raw_content" in columns
    assert "distilled_json" in columns
    assert "r2_audio_key" in columns
    assert "embedding_chunk_id" in columns
    assert "status" in columns
    assert "created_at" in columns
    assert "deleted_at" in columns


@pytest.mark.asyncio
async def test_workspaces_type_column(integration_session):
    result = await integration_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'workspaces' AND column_name = 'type'"
        )
    )
    assert result.scalar_one_or_none() == "type"


@pytest.mark.asyncio
async def test_workspaces_personal_unique_index(integration_session):
    result = await integration_session.execute(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'workspaces' AND indexname = 'uq_workspaces_owner_personal'"
        )
    )
    assert result.scalar_one_or_none() is not None
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd backend && pytest tests/test_alembic_memory.py -v
# Expected: 3 FAIL — table/columns 미존재
```

- [ ] **Step 3: 생성 alembic migration**

```bash
cd backend && alembic revision -m "add memory_items table + workspaces type column"
```

`backend/alembic/versions/<hash>_add_memory_items_workspaces_type_column.py`에 다음 작성:

```python
"""add memory_items table + workspaces type column

Revision ID: <hash>
Revises: 7ebd009f89a4
Create Date: 2026-05-14 ...

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = '<hash>'
down_revision: Union[str, Sequence[str], None] = '7ebd009f89a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. workspaces.type 컬럼 추가 — 기본값 'team', 기존 row 보존
    op.add_column(
        "workspaces",
        sa.Column("type", sa.String(), nullable=False, server_default="team"),
    )
    op.create_index(
        "uq_workspaces_owner_personal",
        "workspaces",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text("type = 'personal'"),
    )

    # 2. memory_items 신설
    op.create_table(
        "memory_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),  # 'voice' | 'text'
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("distilled_json", JSONB, nullable=True),
        sa.Column("r2_audio_key", sa.String(), nullable=True),
        sa.Column("embedding_chunk_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        # active | transcription_pending | embedding_pending | promoted
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_memory_items_user_created", "memory_items", ["user_id", "created_at"])
    op.create_index("ix_memory_items_workspace_status", "memory_items", ["workspace_id", "status"])

    # 3. promotion_audit (Sprint 17+ 정식 schema simplified for R6 prototype)
    op.create_table(
        "promotion_audit",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_memory_id", UUID(as_uuid=True), sa.ForeignKey("memory_items.id"), nullable=False),
        sa.Column("target_workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("promoted_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("promoted_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("embedding_status", sa.String(), nullable=False, server_default="pending"),
        # pending | processing | completed | failed
        sa.Column("embedding_error_message", sa.Text(), nullable=True),
        sa.UniqueConstraint("source_memory_id", "target_workspace_id", name="uq_promotion_source_target"),
    )


def downgrade() -> None:
    op.drop_table("promotion_audit")
    op.drop_index("ix_memory_items_workspace_status", table_name="memory_items")
    op.drop_index("ix_memory_items_user_created", table_name="memory_items")
    op.drop_table("memory_items")
    op.drop_index("uq_workspaces_owner_personal", table_name="workspaces")
    op.drop_column("workspaces", "type")
```

- [ ] **Step 4: Run test — expect PASS**

```bash
cd backend && pytest tests/test_alembic_memory.py -v
# Expected: 3 PASS
```

- [ ] **Step 5: Commit (R2)**

```bash
git add backend/alembic/versions/<hash>_add_memory_items_workspaces_type_column.py backend/tests/test_alembic_memory.py
git commit -m "feat(memory): R2 alembic migration — memory_items + workspaces.type + promotion_audit"
```

---

### Task R1: BE memory API — capture (voice + text) → distill → store

**Files:**
- Create: `backend/src/memory/__init__.py`
- Create: `backend/src/memory/models.py`
- Create: `backend/src/memory/schemas.py`
- Create: `backend/src/memory/repository.py`
- Create: `backend/src/memory/service.py`
- Create: `backend/src/memory/router.py`
- Create: `backend/src/memory/dependencies.py`
- Create: `backend/src/memory/exceptions.py`
- Modify: `backend/src/common/prompts.py` (DISTILL_PROMPT 추가)
- Modify: `backend/src/main.py` (router 등록)
- Modify: `backend/tests/conftest.py` (memory import)
- Create: `backend/tests/memory/__init__.py`
- Create: `backend/tests/memory/test_api.py`
- Create: `backend/tests/memory/test_service.py`

#### R1.1 — DISTILL_PROMPT 상수 추가

- [ ] **Step 1: prompts.py 추가**

`backend/src/common/prompts.py` 끝에 추가:

```python
# ── Memory distill 프롬프트 (Sprint 15 R1 신설) ──
MEMORY_DISTILL_PROMPT = """당신은 사용자가 흘려쓴 생각을 구조화된 메모리로 변환하는 AI입니다.

## 입력
{raw_content}

## 출력 JSON 스키마
{{
  "title": "string (50자 이내, 메모 핵심을 짧게 압축)",
  "atomic_notes": ["string (각 1문장, 동의어/다양한 표현 포함하여 recall 검색 hit률 ↑)"],
  "open_loops": ["string (미해결 질문이나 후속 작업, 없으면 빈 배열)"],
  "people": ["@username (멘션된 사람, 없으면 빈 배열)"],
  "projects": ["#tagname (관련 프로젝트 태그, 없으면 빈 배열)"],
  "suggested_visibility": "personal 또는 team (개인 메모인지 팀에 공유될 만한 내용인지)"
}}

## 규칙
1. atomic_notes는 1개 이상 5개 이하. 각 항목은 자체완결성 있는 단문.
2. atomic_notes에 검색어 다양화 — 동의어 / 영어 / 다른 표현 일부 포함 (recall 정확도 ↑).
3. 사람 이름은 `@`, 프로젝트는 `#` 접두사.
4. visibility 추천: 개인 생각/메모 = personal. 팀에 공유될 결정/회의 내용 = team.
5. 다른 텍스트 없이 JSON만 출력."""


class MemoryDistillResult(BaseModel):
    title: str
    atomic_notes: list[str] = []
    open_loops: list[str] = []
    people: list[str] = []
    projects: list[str] = []
    suggested_visibility: str = "personal"
```

- [ ] **Step 2: Commit (R1.1)**

```bash
git add backend/src/common/prompts.py
git commit -m "feat(prompts): R1.1 add MEMORY_DISTILL_PROMPT for Sprint 15 capture distillation"
```

#### R1.2 — memory models / schemas / exceptions

- [ ] **Step 1: 신규 디렉토리 + __init__**

```bash
mkdir -p backend/src/memory backend/tests/memory
touch backend/src/memory/__init__.py backend/tests/memory/__init__.py
```

- [ ] **Step 2: Write `backend/src/memory/exceptions.py`**

```python
# backend/src/memory/exceptions.py
"""Memory 도메인 예외."""
from fastapi import HTTPException


class MemoryNotFoundError(HTTPException):
    def __init__(self, memory_id: str) -> None:
        super().__init__(status_code=404, detail=f"Memory {memory_id} not found")


class AudioTooLargeError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=413, detail="오디오 파일이 25MB를 초과합니다. 5분 이내 메모로 줄여주세요.")


class WhisperUnavailableError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            detail="음성 변환 서비스가 일시 사용 불가입니다. 텍스트는 임시 저장되었습니다.",
        )


class GeminiDistillError(Exception):
    """Gemini distill 실패 — service 내부에서 fallback으로 처리."""
```

- [ ] **Step 3: Write `backend/src/memory/models.py`**

```python
# backend/src/memory/models.py
"""SQLModel — memory_items + promotion_audit (R6에서 사용)."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class MemoryItem(SQLModel, table=True):
    __tablename__ = "memory_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", nullable=False)
    type: str = Field(nullable=False)  # 'voice' | 'text'
    raw_content: str = Field(nullable=False)
    distilled_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    r2_audio_key: str | None = Field(default=None)
    embedding_chunk_id: uuid.UUID | None = Field(default=None)
    status: str = Field(default="active")
    # active | transcription_pending | embedding_pending | promoted
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = Field(default=None)


class PromotionAudit(SQLModel, table=True):
    __tablename__ = "promotion_audit"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_memory_id: uuid.UUID = Field(foreign_key="memory_items.id", nullable=False)
    target_workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", nullable=False)
    promoted_by_user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    promoted_at: datetime = Field(default_factory=datetime.utcnow)
    embedding_status: str = Field(default="pending")
    embedding_error_message: str | None = Field(default=None)
```

- [ ] **Step 4: Write `backend/src/memory/schemas.py`**

```python
# backend/src/memory/schemas.py
"""Pydantic V2 입출력 스키마."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DistilledJson(BaseModel):
    title: str
    atomic_notes: list[str] = []
    open_loops: list[str] = []
    people: list[str] = []
    projects: list[str] = []
    suggested_visibility: Literal["personal", "team"] = "personal"


class MemoryCreateOut(BaseModel):
    memory_id: uuid.UUID
    distilled_json: DistilledJson | None = None
    status: str
    created_at: datetime


class MemoryRecallSource(BaseModel):
    memory_id: uuid.UUID
    title: str
    atomic_notes_excerpt: str
    score: float = Field(ge=0.0, le=1.0)
    match_type: Literal["vector", "keyword"] = "vector"
    created_at: datetime


class MemoryRecallOut(BaseModel):
    query: str
    sources: list[MemoryRecallSource] = []
    fallback_used: bool = False


class MemoryMetricsOut(BaseModel):
    capture_count: int
    recall_count: int
    promote_count: int
    recall_p50_ms: int | None = None
    recall_p95_ms: int | None = None
```

- [ ] **Step 5: Update `backend/tests/conftest.py`**

추가 import (line ~23 다음에):

```python
import src.memory.models  # noqa: F401 — memory_items, promotion_audit
```

- [ ] **Step 6: Commit (R1.2)**

```bash
git add backend/src/memory/__init__.py backend/src/memory/exceptions.py backend/src/memory/models.py backend/src/memory/schemas.py backend/tests/conftest.py backend/tests/memory/__init__.py
git commit -m "feat(memory): R1.2 models + schemas + exceptions + conftest import"
```

#### R1.3 — repository + service (capture + distill)

- [ ] **Step 1: Write `backend/src/memory/repository.py` — workspace_id 필터 강제 (I-9 정합)**

```python
# backend/src/memory/repository.py
"""DB 접근 전담. AsyncSession 유일 보유. workspace_id 필터 모든 query에 강제 (I-9)."""
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.memory.exceptions import MemoryNotFoundError
from src.memory.models import MemoryItem, PromotionAudit


class MemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, item: MemoryItem) -> MemoryItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def commit(self) -> None:
        await self.session.commit()

    async def get_by_id(self, memory_id: uuid.UUID, workspace_id: uuid.UUID) -> MemoryItem:
        """workspace_id 필터 강제 — I-9."""
        result = await self.session.execute(
            select(MemoryItem).where(
                MemoryItem.id == memory_id,
                MemoryItem.workspace_id == workspace_id,
                MemoryItem.deleted_at.is_(None),
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise MemoryNotFoundError(str(memory_id))
        return item

    async def list_recent(self, workspace_id: uuid.UUID, limit: int = 20) -> list[MemoryItem]:
        result = await self.session.execute(
            select(MemoryItem)
            .where(
                MemoryItem.workspace_id == workspace_id,
                MemoryItem.deleted_at.is_(None),
            )
            .order_by(MemoryItem.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_keyword(
        self, workspace_id: uuid.UUID, tokens: list[str], limit: int = 3
    ) -> list[tuple[MemoryItem, int]]:
        """Token overlap count rank (O-B lock-in). distilled_json->atomic_notes ∩ query_tokens 개수."""
        if not tokens:
            return []
        # Postgres: jsonb_array_elements_text(distilled_json->'atomic_notes')의 각 항목과 token match
        # 간단화: atomic_notes를 string으로 concat한 후 case-insensitive count
        # SQL inline (security: tokens 사전 sanitize — 영문/한국어/숫자만 허용)
        sanitized = [t for t in tokens if t.replace("_", "").isalnum() and len(t) >= 2]
        if not sanitized:
            return []
        # raw SQL for token overlap count
        from sqlalchemy import text
        # ?p 파라미터 인덱싱 위해 dict 사용
        params: dict[str, Any] = {"workspace_id": str(workspace_id), "limit": limit}
        count_clauses = []
        for i, tok in enumerate(sanitized):
            params[f"tok{i}"] = f"%{tok.lower()}%"
            count_clauses.append(
                f"(CASE WHEN lower(coalesce(distilled_json->>'title', raw_content)) LIKE :tok{i} THEN 1 ELSE 0 END)"
                f" + (CASE WHEN lower(distilled_json::text) LIKE :tok{i} THEN 1 ELSE 0 END)"
            )
        query_text = f"""
        SELECT id, ({' + '.join(count_clauses)}) AS overlap_count
        FROM memory_items
        WHERE workspace_id = :workspace_id
          AND deleted_at IS NULL
          AND distilled_json IS NOT NULL
        ORDER BY overlap_count DESC
        LIMIT :limit
        """
        result = await self.session.execute(text(query_text), params)
        rows = [(uuid.UUID(str(r[0])), int(r[1])) for r in result.all() if int(r[1]) > 0]
        if not rows:
            return []
        # ID로 MemoryItem fetch
        ids = [r[0] for r in rows]
        items_result = await self.session.execute(
            select(MemoryItem).where(MemoryItem.id.in_(ids))
        )
        items_by_id = {item.id: item for item in items_result.scalars().all()}
        return [(items_by_id[mid], cnt) for mid, cnt in rows if mid in items_by_id]

    async def save_promotion_audit(self, audit: PromotionAudit) -> PromotionAudit:
        self.session.add(audit)
        await self.session.flush()
        return audit

    async def count_by_workspace(self, workspace_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(MemoryItem.id)).where(
                MemoryItem.workspace_id == workspace_id,
                MemoryItem.deleted_at.is_(None),
            )
        )
        return int(result.scalar() or 0)

    async def count_promotions_by_workspace(self, workspace_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(PromotionAudit.id)).where(
                PromotionAudit.target_workspace_id == workspace_id
            )
        )
        return int(result.scalar() or 0)
```

- [ ] **Step 2: Write `backend/src/memory/service.py` — Whisper + Gemini distill + R2 upload**

```python
# backend/src/memory/service.py
"""비즈니스 로직 — Whisper transcribe + Gemini distill + R2 audio upload. AsyncSession import 금지."""
import asyncio
import uuid
from typing import Any

import aioboto3
from google import genai

from src.common.prompts import (
    MEMORY_DISTILL_PROMPT,
    MemoryDistillResult,
    parse_json_response,
)
from src.core.config import get_settings
from src.memory.exceptions import (
    AudioTooLargeError,
    GeminiDistillError,
    WhisperUnavailableError,
)
from src.memory.models import MemoryItem
from src.memory.repository import MemoryRepository
from src.memory.schemas import DistilledJson, MemoryCreateOut

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # Whisper API hard limit


class MemoryService:
    def __init__(self, repo: MemoryRepository) -> None:
        self.repo = repo
        self.settings = get_settings()

    async def capture_text(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        text: str,
    ) -> MemoryCreateOut:
        item = MemoryItem(
            user_id=user_id,
            workspace_id=workspace_id,
            type="text",
            raw_content=text,
            status="embedding_pending",
        )
        # distill (Gemini)
        try:
            distilled = await self._distill_with_gemini(text)
            item.distilled_json = distilled.model_dump()
        except GeminiDistillError:
            item.distilled_json = self._fallback_distill(text).model_dump()
        await self.repo.save(item)
        await self.repo.commit()
        return MemoryCreateOut(
            memory_id=item.id,
            distilled_json=DistilledJson(**item.distilled_json) if item.distilled_json else None,
            status=item.status,
            created_at=item.created_at,
        )

    async def capture_voice(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        audio_bytes: bytes,
        filename: str,
    ) -> MemoryCreateOut:
        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise AudioTooLargeError()
        # 1. Whisper transcribe
        try:
            transcript = await self._transcribe_with_whisper(audio_bytes, filename)
        except Exception as e:
            raise WhisperUnavailableError() from e
        # 2. R2 upload (O-E: store + 30d TTL — TTL은 cron job 별도 구현)
        r2_key = f"memory/{workspace_id}/{uuid.uuid4()}-{filename}"
        await self._upload_to_r2(audio_bytes, r2_key)
        # 3. Gemini distill
        try:
            distilled = await self._distill_with_gemini(transcript)
            distilled_json = distilled.model_dump()
        except GeminiDistillError:
            distilled_json = self._fallback_distill(transcript).model_dump()
        # 4. save
        item = MemoryItem(
            user_id=user_id,
            workspace_id=workspace_id,
            type="voice",
            raw_content=transcript,
            distilled_json=distilled_json,
            r2_audio_key=r2_key,
            status="embedding_pending",
        )
        await self.repo.save(item)
        await self.repo.commit()
        return MemoryCreateOut(
            memory_id=item.id,
            distilled_json=DistilledJson(**distilled_json),
            status=item.status,
            created_at=item.created_at,
        )

    async def _distill_with_gemini(self, raw_text: str) -> MemoryDistillResult:
        client = genai.Client(api_key=self.settings.google_api_key.get_secret_value())
        prompt = MEMORY_DISTILL_PROMPT.format(raw_content=raw_text)
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
            )
            parsed = parse_json_response(response.text)
            return MemoryDistillResult.model_validate(parsed)
        except Exception as e:
            raise GeminiDistillError(f"Gemini distill 실패: {e}") from e

    def _fallback_distill(self, raw_text: str) -> MemoryDistillResult:
        """Gemini fail 시 fallback — first 120 chars + raw chunk."""
        chunks: list[str] = []
        for i in range(0, len(raw_text), 512):
            chunks.append(raw_text[i : i + 512])
        return MemoryDistillResult(
            title=raw_text[:120],
            atomic_notes=chunks[:5],
            open_loops=[],
            people=[],
            projects=[],
            suggested_visibility="personal",
        )

    async def _transcribe_with_whisper(self, audio_bytes: bytes, filename: str) -> str:
        # OpenAI Whisper API (현 코드베이스에 services/embedding.py 있으므로 OpenAI SDK 재사용)
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.settings.openai_api_key.get_secret_value())
        # SDK는 file-like object를 받음
        import io
        bio = io.BytesIO(audio_bytes)
        bio.name = filename
        result = await client.audio.transcriptions.create(
            model="whisper-1",
            file=bio,
        )
        return result.text

    async def _upload_to_r2(self, data: bytes, key: str) -> None:
        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=f"https://{self.settings.r2_account_id.get_secret_value()}.r2.cloudflarestorage.com",
            aws_access_key_id=self.settings.r2_access_key_id.get_secret_value(),
            aws_secret_access_key=self.settings.r2_secret_access_key.get_secret_value(),
            region_name="auto",
        ) as client:
            await client.put_object(
                Bucket=self.settings.r2_bucket_name,
                Key=key,
                Body=data,
            )
```

- [ ] **Step 3: Write tests `backend/tests/memory/test_service.py`**

```python
"""Service layer 단위 테스트 — Gemini/Whisper mock."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.memory.exceptions import AudioTooLargeError
from src.memory.schemas import DistilledJson
from src.memory.service import MAX_AUDIO_BYTES, MemoryService


@pytest.mark.asyncio
async def test_capture_text_success_with_distill(integration_session):
    from src.memory.repository import MemoryRepository
    repo = MemoryRepository(integration_session)
    service = MemoryService(repo)

    mock_distill = DistilledJson(
        title="Sprint 15 결정",
        atomic_notes=["wedge = Recall-first"],
        suggested_visibility="personal",
    )
    with patch.object(service, "_distill_with_gemini", return_value=mock_distill):
        result = await service.capture_text(
            user_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            text="Sprint 15 wedge 결정 사항",
        )
    assert result.memory_id is not None
    assert result.distilled_json.title == "Sprint 15 결정"
    assert result.status == "embedding_pending"


@pytest.mark.asyncio
async def test_capture_text_gemini_fail_uses_fallback(integration_session):
    from src.memory.exceptions import GeminiDistillError
    from src.memory.repository import MemoryRepository
    repo = MemoryRepository(integration_session)
    service = MemoryService(repo)

    with patch.object(service, "_distill_with_gemini", side_effect=GeminiDistillError("rate limit")):
        result = await service.capture_text(
            user_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            text="긴 raw text " * 50,
        )
    # fallback: title = first 120 chars
    assert result.distilled_json.title.startswith("긴 raw text")


@pytest.mark.asyncio
async def test_capture_voice_oversize_raises():
    from src.memory.repository import MemoryRepository
    service = MemoryService(repo=MagicMock())
    huge = b"x" * (MAX_AUDIO_BYTES + 1)
    with pytest.raises(AudioTooLargeError):
        await service.capture_voice(
            user_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            audio_bytes=huge,
            filename="test.webm",
        )
```

- [ ] **Step 4: Run service tests — expect PASS**

```bash
cd backend && pytest tests/memory/test_service.py -v
# Expected: 3 PASS
```

- [ ] **Step 5: Commit (R1.3)**

```bash
git add backend/src/memory/repository.py backend/src/memory/service.py backend/tests/memory/test_service.py
git commit -m "feat(memory): R1.3 repository + service — Whisper + Gemini distill + R2 upload"
```

#### R1.4 — router + dependencies + e2e test

- [ ] **Step 1: Write `backend/src/memory/dependencies.py`**

```python
# backend/src/memory/dependencies.py
"""Depends() 조립. service.py/repository.py에 Depends import 금지."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.memory.repository import MemoryRepository
from src.memory.service import MemoryService


async def get_memory_repository(
    session: AsyncSession = Depends(get_async_session),
) -> MemoryRepository:
    return MemoryRepository(session)


async def get_memory_service(
    repo: MemoryRepository = Depends(get_memory_repository),
) -> MemoryService:
    return MemoryService(repo)
```

- [ ] **Step 2: Write `backend/src/memory/router.py`**

```python
# backend/src/memory/router.py
"""HTTP 라우터 — POST capture + GET recall + POST promote + GET metrics."""
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.memory.dependencies import get_memory_service
from src.memory.schemas import MemoryCreateOut
from src.memory.service import MemoryService

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/memory", tags=["memory"])


@router.post("", response_model=MemoryCreateOut, status_code=202)
async def capture_memory(
    workspace_id: uuid.UUID,
    text: str | None = Form(default=None),
    audio: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryCreateOut:
    if audio is not None:
        audio_bytes = await audio.read()
        return await service.capture_voice(
            user_id=user.id,
            workspace_id=workspace_id,
            audio_bytes=audio_bytes,
            filename=audio.filename or "voice.webm",
        )
    if not text or not text.strip():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="text 또는 audio 둘 중 하나 필수")
    return await service.capture_text(
        user_id=user.id,
        workspace_id=workspace_id,
        text=text.strip(),
    )
```

- [ ] **Step 3: Update `backend/src/main.py` — router 등록**

기존 router include 옆에 추가 (정확한 line은 read 후 결정):

```python
from src.memory.router import router as memory_router
# ...
app.include_router(memory_router)
```

- [ ] **Step 4: Write e2e test `backend/tests/memory/test_api.py`**

```python
"""POST /memory e2e — fake Gemini/Whisper."""
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.memory.schemas import DistilledJson


@pytest.fixture
def memory_client(test_app, auth_user):
    return TestClient(test_app)


def test_post_memory_text_returns_distilled_json(memory_client, auth_user, test_workspace):
    fake_distill = DistilledJson(
        title="Test thought",
        atomic_notes=["atomic 1"],
        suggested_visibility="personal",
    )
    with patch("src.memory.service.MemoryService._distill_with_gemini", return_value=fake_distill):
        response = memory_client.post(
            f"/api/v1/workspaces/{test_workspace.id}/memory",
            data={"text": "Sprint 15 wedge 결정"},
            headers=auth_user.bearer_header,
        )
    assert response.status_code == 202
    body = response.json()
    assert body["distilled_json"]["title"] == "Test thought"
    assert body["status"] == "embedding_pending"


def test_post_memory_no_input_returns_400(memory_client, auth_user, test_workspace):
    response = memory_client.post(
        f"/api/v1/workspaces/{test_workspace.id}/memory",
        data={},
        headers=auth_user.bearer_header,
    )
    assert response.status_code == 400


def test_post_memory_audio_oversize_returns_413(memory_client, auth_user, test_workspace):
    huge = ("x" * (26 * 1024 * 1024)).encode()
    response = memory_client.post(
        f"/api/v1/workspaces/{test_workspace.id}/memory",
        files={"audio": ("big.webm", huge, "audio/webm")},
        headers=auth_user.bearer_header,
    )
    assert response.status_code == 413
```

> **Note**: 위 fixture (`test_app`, `auth_user`, `test_workspace`)는 기존 conftest 패턴 따라 작성. fixture 미존재 시 `backend/tests/conftest.py` 확장 (기존 `integration_session` + Clerk JWT mock helper 추가).

- [ ] **Step 5: Run e2e — expect PASS**

```bash
cd backend && pytest tests/memory/test_api.py -v
# Expected: 3 PASS
```

- [ ] **Step 6: Commit (R1.4)**

```bash
git add backend/src/memory/dependencies.py backend/src/memory/router.py backend/src/main.py backend/tests/memory/test_api.py
git commit -m "feat(memory): R1.4 router + dependencies + e2e — POST /memory capture endpoint"
```

---

### Task R3: BE recall endpoint — vector + keyword fallback + I-9 atomic patch

**Files:**
- Modify: `backend/src/memory/router.py` (GET /recall 추가)
- Modify: `backend/src/memory/service.py` (recall logic 추가)
- Modify: `backend/src/embeddings/service.py` (create_chunk workspace_id assertion — I-9 강화)
- Modify: `CONTEXT-MAP.md` (I-9 inline patch — atomic)
- Create: `backend/tests/memory/test_recall.py`

#### R3.1 — embeddings 서비스 I-9 assertion

- [ ] **Step 1: Read embeddings/service.py — create_chunk 함수 위치 파악**

```bash
grep -n "def create_chunk\|class.*EmbeddingService" backend/src/embeddings/service.py | head -5
```

- [ ] **Step 2: create_chunk 진입부에 workspace_id assertion 추가**

`backend/src/embeddings/service.py` `create_chunk` 함수 진입부에:

```python
async def create_chunk(
    self,
    *,
    workspace_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    source_workspace_id: uuid.UUID,  # 신규 — caller가 entity owner workspace 명시
    content: str,
    embedding: list[float],
) -> EmbeddingChunk:
    # I-9 4-C: 신규 EmbeddingChunk insert 시 workspace_id는 신규 entity owner workspace와 매칭
    assert (
        workspace_id == source_workspace_id
    ), f"I-9 violation: chunk workspace_id ({workspace_id}) != source workspace_id ({source_workspace_id})"
    # ... 기존 로직
```

기존 caller 모두 source_workspace_id 추가하도록 patch (notes, meetings, inbox 등). caller 검색:

```bash
grep -rn "create_chunk(" backend/src/ --include="*.py" | grep -v "_test.py"
```

각 caller 위치에 source_workspace_id 인자 추가 (notes/meetings/inbox 각 service).

- [ ] **Step 3: Write `CONTEXT-MAP.md` I-9 inline patch**

`/CONTEXT-MAP.md`에서 I-9 row 찾아서 본문 교체:

```markdown
| I-9 | **멀티테넌시 격리**: 모든 Repository는 `workspace_id` 필터 강제. 신규 EmbeddingChunk insert 시 `workspace_id`는 신규 entity owner workspace와 매칭 (service layer assertion). | `<domain>/repository.py` `.where(... .workspace_id == workspace_id)`, `backend/src/embeddings/service.py:create_chunk` |
```

#### R3.2 — recall logic in service + router

- [ ] **Step 1: Write failing recall tests `backend/tests/memory/test_recall.py`**

```python
"""Recall endpoint — vector + keyword fallback + I-9 workspace_id 강제."""
import uuid
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_recall_returns_top_3_vector_results(memory_client, auth_user, test_workspace, seed_memories):
    # seed_memories fixture가 3개 vector-matchable memory_items 삽입
    response = memory_client.get(
        f"/api/v1/workspaces/{test_workspace.id}/memory/recall",
        params={"q": "Sprint wedge 결정"},
        headers=auth_user.bearer_header,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["sources"]) <= 3
    assert body["fallback_used"] is False


@pytest.mark.asyncio
async def test_recall_keyword_fallback_when_vector_empty(memory_client, auth_user, test_workspace, seed_memories):
    with patch("src.memory.service.MemoryService._vector_search", return_value=[]):
        response = memory_client.get(
            f"/api/v1/workspaces/{test_workspace.id}/memory/recall",
            params={"q": "atomic_notes_keyword"},
            headers=auth_user.bearer_header,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["fallback_used"] is True


@pytest.mark.asyncio
async def test_recall_workspace_id_filter_enforced(memory_client, auth_user, test_workspace, foreign_workspace_memory):
    """I-9: 다른 workspace의 memory는 절대 반환 안 됨."""
    response = memory_client.get(
        f"/api/v1/workspaces/{test_workspace.id}/memory/recall",
        params={"q": "foreign workspace content"},
        headers=auth_user.bearer_header,
    )
    body = response.json()
    foreign_id = str(foreign_workspace_memory.id)
    assert all(s["memory_id"] != foreign_id for s in body["sources"])
```

- [ ] **Step 2: Run test — expect FAIL (endpoint 미존재)**

```bash
cd backend && pytest tests/memory/test_recall.py -v
# Expected: 3 FAIL — endpoint not registered
```

- [ ] **Step 3: Add `recall` to MemoryService**

`backend/src/memory/service.py`에 추가:

```python
import re

class MemoryService:
    # ... existing __init__, capture_text, capture_voice ...

    async def recall(
        self,
        workspace_id: uuid.UUID,
        query: str,
        top_k: int = 3,  # O-A: Top 3 lock-in
    ) -> "MemoryRecallOut":
        """Vector search + keyword fallback. I-9 workspace_id filter 강제."""
        from src.memory.schemas import MemoryRecallOut, MemoryRecallSource

        # 1. Vector search
        vector_sources = await self._vector_search(workspace_id, query, top_k)
        if vector_sources:
            return MemoryRecallOut(query=query, sources=vector_sources, fallback_used=False)

        # 2. Keyword fallback (O-B: token overlap count)
        tokens = self._tokenize_query(query)
        rows = await self.repo.search_keyword(workspace_id, tokens, limit=top_k)
        keyword_sources = [
            MemoryRecallSource(
                memory_id=item.id,
                title=(item.distilled_json or {}).get("title", item.raw_content[:60]),
                atomic_notes_excerpt=" / ".join((item.distilled_json or {}).get("atomic_notes", [])[:2]),
                score=min(1.0, cnt / max(len(tokens), 1)),
                match_type="keyword",
                created_at=item.created_at,
            )
            for item, cnt in rows
        ]
        return MemoryRecallOut(query=query, sources=keyword_sources, fallback_used=True)

    async def _vector_search(
        self, workspace_id: uuid.UUID, query: str, top_k: int
    ) -> list["MemoryRecallSource"]:
        """OpenAI embedding → pgvector cosine sim filter by workspace_id (I-9)."""
        from src.memory.schemas import MemoryRecallSource
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.openai_api_key.get_secret_value())
        embed_resp = await client.embeddings.create(
            model="text-embedding-3-small", input=query
        )
        query_vec = embed_resp.data[0].embedding

        # pgvector cosine similarity query — EmbeddingChunk 필터 workspace_id
        from sqlalchemy import text
        result = await self.repo.session.execute(
            text("""
                SELECT mi.id, mi.distilled_json, mi.raw_content, mi.created_at,
                       1 - (ec.embedding <=> CAST(:qvec AS vector)) AS score
                FROM embedding_chunks ec
                JOIN memory_items mi ON ec.source_id = mi.id
                WHERE ec.workspace_id = :wid
                  AND ec.source_type = 'memory'
                  AND mi.deleted_at IS NULL
                ORDER BY score DESC
                LIMIT :limit
            """),
            {"qvec": str(query_vec), "wid": str(workspace_id), "limit": top_k},
        )
        sources: list[MemoryRecallSource] = []
        for row in result.all():
            distilled = row[1] or {}
            sources.append(MemoryRecallSource(
                memory_id=uuid.UUID(str(row[0])),
                title=distilled.get("title") or str(row[2])[:60],
                atomic_notes_excerpt=" / ".join(distilled.get("atomic_notes", [])[:2]),
                score=float(row[4]),
                match_type="vector",
                created_at=row[3],
            ))
        return sources

    def _tokenize_query(self, query: str) -> list[str]:
        """한국어 어절 + 영문 단어 단위 split. 대소문자 normalize."""
        tokens = re.findall(r"[가-힣]+|[A-Za-z][A-Za-z0-9_]*", query.lower())
        return [t for t in tokens if len(t) >= 2]
```

- [ ] **Step 4: Add `GET /recall` to router**

`backend/src/memory/router.py` 끝에 추가:

```python
from fastapi import Query
from src.memory.schemas import MemoryRecallOut


@router.get("/recall", response_model=MemoryRecallOut)
async def recall_memory(
    workspace_id: uuid.UUID,
    q: str = Query(..., min_length=2),
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryRecallOut:
    return await service.recall(workspace_id=workspace_id, query=q, top_k=3)
```

- [ ] **Step 5: Run test — expect PASS**

```bash
cd backend && pytest tests/memory/test_recall.py -v
# Expected: 3 PASS
```

- [ ] **Step 6: Commit R3 (BE recall + I-9 patch atomic)**

```bash
git add backend/src/memory/service.py backend/src/memory/router.py backend/src/embeddings/service.py backend/tests/memory/test_recall.py CONTEXT-MAP.md
# 기존 caller (notes/meetings/inbox) 변경된 파일도 같이
git commit -m "feat(memory): R3 recall endpoint + I-9 atomic patch — vector + keyword fallback + workspace_id assertion"
```

---

### Task R5: BE Personal workspace lazy seed + UNIQUE partial index + I-19 invariant 코드 atomic

**Files:**
- Modify: `backend/src/auth/dependencies.py` (get_current_user 내부 lazy seed)
- Modify: `backend/src/workspaces/service.py` (member-add 차단 invariant 검증)
- Modify: `backend/src/workspaces/exceptions.py` (PersonalWorkspaceProtected 신설)
- Create: `backend/tests/auth/test_personal_seed.py`
- Create: `backend/tests/workspaces/test_personal_invariants.py`

#### R5.1 — Personal workspace lazy seed

- [ ] **Step 1: Write failing test `backend/tests/auth/test_personal_seed.py`**

```python
"""Personal workspace lazy seed — first login + idempotent."""
import uuid
import pytest

from sqlmodel import select


@pytest.mark.asyncio
async def test_get_current_user_seeds_personal_ws_on_first_login(integration_session):
    """첫 로그인 user에게 personal workspace 자동 생성."""
    from src.auth.dependencies import get_current_user
    from src.workspaces.models import Workspace

    fake_claims = {"sub": "clerk_user_xyz", "name": "테스터", "email": "t@example.com"}
    user = await get_current_user(claims=fake_claims, session=integration_session)

    result = await integration_session.execute(
        select(Workspace).where(
            Workspace.owner_id == user.id, Workspace.type == "personal"
        )
    )
    ws = result.scalar_one_or_none()
    assert ws is not None
    assert ws.name.endswith("의 개인 Kairos")


@pytest.mark.asyncio
async def test_personal_seed_idempotent_on_relogin(integration_session):
    """재로그인 시 personal ws 중복 생성 안 됨."""
    from src.auth.dependencies import get_current_user
    from src.workspaces.models import Workspace
    from sqlalchemy import func

    fake_claims = {"sub": "clerk_user_xyz", "name": "테스터", "email": "t@example.com"}
    await get_current_user(claims=fake_claims, session=integration_session)
    await get_current_user(claims=fake_claims, session=integration_session)

    result = await integration_session.execute(
        select(func.count(Workspace.id)).where(Workspace.type == "personal")
    )
    assert result.scalar() == 1
```

- [ ] **Step 2: Run — expect FAIL (lazy seed 미구현)**

```bash
cd backend && pytest tests/auth/test_personal_seed.py -v
# Expected: 2 FAIL
```

- [ ] **Step 3: Update `backend/src/auth/dependencies.py`**

`get_current_user` 함수를 다음으로 교체:

```python
from src.workspaces.models import Workspace, WorkspaceMember
from sqlmodel import select


async def get_current_user(
    claims: dict = Depends(verify_clerk_token),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """현재 인증된 사용자 + Personal workspace lazy seed (I-19 invariant code)."""
    repo = UserRepository(session)
    user = await repo.find_by_clerk_id(claims["sub"])
    if user is None:
        user = User(
            clerk_id=claims["sub"],
            display_name=claims.get("name", "사용자"),
            email=claims.get("email", ""),
        )
        user = await repo.save(user)
    # I-19: lazy seed personal workspace (idempotent via UNIQUE partial index)
    result = await session.execute(
        select(Workspace).where(
            Workspace.owner_id == user.id, Workspace.type == "personal"
        )
    )
    if result.scalar_one_or_none() is None:
        from sqlalchemy.exc import IntegrityError
        ws = Workspace(
            name=f"{user.display_name}의 개인 Kairos",
            owner_id=user.id,
            type="personal",
        )
        session.add(ws)
        try:
            await session.flush()
            session.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner"))
        except IntegrityError:
            # 동시 요청 race condition — UNIQUE 위반 시 idempotent skip
            await session.rollback()
    await session.commit()
    return user
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && pytest tests/auth/test_personal_seed.py -v
# Expected: 2 PASS
```

#### R5.2 — Personal workspace invariant (member 추가/초대 차단)

- [ ] **Step 1: Write failing test `backend/tests/workspaces/test_personal_invariants.py`**

```python
import uuid
import pytest


@pytest.mark.asyncio
async def test_add_member_to_personal_ws_returns_403(integration_session):
    from src.workspaces.exceptions import PersonalWorkspaceProtected
    from src.workspaces.service import WorkspaceService
    from src.workspaces.repository import WorkspaceRepository
    from src.workspaces.models import Workspace
    from src.auth.models import User

    repo = WorkspaceRepository(integration_session)
    service = WorkspaceService(repo)

    owner = User(clerk_id="o1", display_name="o", email="o@test")
    integration_session.add(owner)
    await integration_session.flush()
    ws = Workspace(name="test personal", owner_id=owner.id, type="personal")
    integration_session.add(ws)
    await integration_session.flush()

    other = User(clerk_id="o2", display_name="x", email="x@test")
    integration_session.add(other)
    await integration_session.flush()

    with pytest.raises(PersonalWorkspaceProtected):
        await service.add_member(ws.id, other.id, role="member")
```

- [ ] **Step 2: Run — expect FAIL (exception 미존재)**

```bash
cd backend && pytest tests/workspaces/test_personal_invariants.py -v
```

- [ ] **Step 3: Add `PersonalWorkspaceProtected` to `backend/src/workspaces/exceptions.py`**

```python
class PersonalWorkspaceProtected(HTTPException):
    def __init__(self, action: str = "modify") -> None:
        super().__init__(
            status_code=403,
            detail=f"Personal workspace cannot be {action}d. (I-19 invariant)",
        )
```

- [ ] **Step 4: Update `WorkspaceService.add_member`**

기존 `add_member`/`add_invite` method 진입부에:

```python
async def add_member(self, workspace_id: uuid.UUID, user_id: uuid.UUID, role: str) -> WorkspaceMember:
    ws = await self.repo.get_by_id(workspace_id)
    if ws.type == "personal":
        # I-19: Personal workspace는 멤버 추가 차단
        raise PersonalWorkspaceProtected("add_member")
    # ... 기존 로직
```

`delete_workspace` (있다면)도 동일 가드.

- [ ] **Step 5: Run — expect PASS**

```bash
cd backend && pytest tests/workspaces/test_personal_invariants.py -v
```

- [ ] **Step 6: Commit R5 (lazy seed + I-19 invariant 코드 atomic)**

```bash
git add backend/src/auth/dependencies.py backend/src/workspaces/exceptions.py backend/src/workspaces/service.py backend/tests/auth/test_personal_seed.py backend/tests/workspaces/test_personal_invariants.py
git commit -m "feat(workspaces): R5 personal lazy seed + I-19 invariant code — add_member 차단 + UNIQUE partial index 정합"
```

> **Note**: CONTEXT-MAP.md I-19 본문 등재는 **Sprint 17+ 정식 신설 시 defer** (Stage 1 design doc §4 명시). R5 commit에는 코드만 atomic — CONTEXT-MAP edit 없음.

---

### Task R4: FE `/memory` page — B3 search-first FAB layout + Personal/Team tab

**Files:**
- Create: `frontend/src/features/memory/api.ts`
- Create: `frontend/src/features/memory/types.ts`
- Create: `frontend/src/features/memory/hooks.ts`
- Create: `frontend/src/features/memory/components/capture-sheet.tsx`
- Create: `frontend/src/features/memory/components/recall-result-card.tsx`
- Create: `frontend/src/features/memory/components/workspace-type-badge.tsx`
- Create: `frontend/src/app/(app)/memory/page.tsx`
- Modify: `frontend/src/components/layout/sidebar.tsx` (`/memory` 항목 + NEW pill + feature flag 분기)
- Modify: `frontend/.env.example` (`NEXT_PUBLIC_RECALL_ENABLED`)
- Create: `frontend/src/features/memory/__tests__/memory-page.test.tsx`

#### R4.1 — Feature flag + sidebar

- [ ] **Step 1: Add env**

`frontend/.env.example`에 추가:

```
NEXT_PUBLIC_RECALL_ENABLED=false
```

- [ ] **Step 2: Update sidebar.tsx**

`frontend/src/components/layout/sidebar.tsx`에서 navigation array에 조건부 추가:

```tsx
import { Mic } from "lucide-react";

// 기존 nav items 다음에
const recallEnabled = process.env.NEXT_PUBLIC_RECALL_ENABLED === "true";

const navItems = [
  // ... 기존 items
  ...(recallEnabled
    ? [{ href: "/memory", label: "Memory", icon: Mic, isNew: true }]
    : []),
];
```

기존 nav item 렌더 부분에 isNew 처리:

```tsx
{item.isNew && (
  <span className="ml-auto text-[10px] font-mono uppercase bg-accent/10 text-accent px-1.5 py-0.5 rounded-full">
    NEW
  </span>
)}
```

#### R4.2 — Memory features

- [ ] **Step 1: Write `types.ts`**

```ts
// frontend/src/features/memory/types.ts
// memory 도메인 타입 정의
export type WorkspaceType = "personal" | "team";

export interface DistilledJson {
  title: string;
  atomic_notes: string[];
  open_loops: string[];
  people: string[];
  projects: string[];
  suggested_visibility: WorkspaceType;
}

export interface MemoryCreateOut {
  memory_id: string;
  distilled_json: DistilledJson | null;
  status: string;
  created_at: string;
}

export interface MemoryRecallSource {
  memory_id: string;
  title: string;
  atomic_notes_excerpt: string;
  score: number;
  match_type: "vector" | "keyword";
  created_at: string;
}

export interface MemoryRecallOut {
  query: string;
  sources: MemoryRecallSource[];
  fallback_used: boolean;
}
```

- [ ] **Step 2: Write `api.ts` — React Query key factory**

```ts
// frontend/src/features/memory/api.ts
// memory API 래퍼 + React Query keys
import { apiFetch } from "@/lib/api";
import type { MemoryCreateOut, MemoryRecallOut } from "./types";

export const memoryKeys = {
  all: (workspaceId: string) => ["memory", workspaceId] as const,
  recall: (workspaceId: string, query: string) =>
    ["memory", workspaceId, "recall", query] as const,
};

export async function captureText(workspaceId: string, text: string): Promise<MemoryCreateOut> {
  const fd = new FormData();
  fd.append("text", text);
  return apiFetch(`/api/v1/workspaces/${workspaceId}/memory`, { method: "POST", body: fd });
}

export async function captureVoice(
  workspaceId: string,
  audio: Blob,
  filename = "voice.webm"
): Promise<MemoryCreateOut> {
  const fd = new FormData();
  fd.append("audio", audio, filename);
  return apiFetch(`/api/v1/workspaces/${workspaceId}/memory`, { method: "POST", body: fd });
}

export async function recall(workspaceId: string, q: string): Promise<MemoryRecallOut> {
  const params = new URLSearchParams({ q });
  return apiFetch(`/api/v1/workspaces/${workspaceId}/memory/recall?${params}`);
}
```

- [ ] **Step 3: Write `hooks.ts` — MediaRecorder + useQuery + useMutation**

```ts
// frontend/src/features/memory/hooks.ts
// MediaRecorder 캡처 훅 + recall 훅 + capture mutation
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { captureText, captureVoice, memoryKeys, recall } from "./api";

const MAX_RECORD_MS = 5 * 60 * 1000;

export function useRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const chunks = useRef<Blob[]>([]);
  const recorder = useRef<MediaRecorder | null>(null);
  const stopTimer = useRef<number | null>(null);

  async function start(onStop: (blob: Blob) => void) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunks.current = [];
      mr.ondataavailable = (e) => chunks.current.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunks.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        onStop(blob);
      };
      mr.start();
      recorder.current = mr;
      setIsRecording(true);
      stopTimer.current = window.setTimeout(stop, MAX_RECORD_MS);
    } catch {
      setPermissionDenied(true);
    }
  }

  function stop() {
    if (recorder.current && recorder.current.state === "recording") {
      recorder.current.stop();
    }
    setIsRecording(false);
    if (stopTimer.current) window.clearTimeout(stopTimer.current);
  }

  useEffect(() => () => stop(), []);

  return { isRecording, permissionDenied, start, stop };
}

export function useCaptureText(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => captureText(workspaceId, text),
    onSuccess: () => qc.invalidateQueries({ queryKey: memoryKeys.all(workspaceId) }),
  });
}

export function useCaptureVoice(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (blob: Blob) => captureVoice(workspaceId, blob),
    onSuccess: () => qc.invalidateQueries({ queryKey: memoryKeys.all(workspaceId) }),
  });
}

export function useRecall(workspaceId: string, query: string) {
  return useQuery({
    queryKey: memoryKeys.recall(workspaceId, query),
    queryFn: () => recall(workspaceId, query),
    enabled: query.length >= 2,
    staleTime: 30_000,
  });
}
```

- [ ] **Step 4: Write `components/workspace-type-badge.tsx`**

```tsx
// frontend/src/features/memory/components/workspace-type-badge.tsx
// Workspace type 표시 배지 (DESIGN.md §Workspace Types)
import { Lock, Users } from "lucide-react";
import type { WorkspaceType } from "../types";

export function WorkspaceTypeBadge({ type }: { type: WorkspaceType }) {
  const isPersonal = type === "personal";
  const Icon = isPersonal ? Lock : Users;
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[11px] font-mono ${
        isPersonal ? "text-muted" : "text-accent bg-accent/10"
      }`}
    >
      <Icon className="w-3 h-3" />
      {isPersonal ? "Personal" : "Team"}
    </span>
  );
}
```

- [ ] **Step 5: Write `components/recall-result-card.tsx`**

```tsx
// frontend/src/features/memory/components/recall-result-card.tsx
// Recall 결과 카드 (DESIGN.md §Recall Result Card)
import { ArrowUpRight } from "lucide-react";
import type { MemoryRecallSource } from "../types";

export function RecallResultCard({
  source,
  onPromote,
}: {
  source: MemoryRecallSource;
  onPromote: (memoryId: string) => void;
}) {
  const timeAgo = new Date(source.created_at).toLocaleString();
  return (
    <article className="bg-surface border border-border-subtle rounded-md p-4 hover:bg-surface-hover transition-colors">
      <header className="flex items-start justify-between gap-2">
        <h3 className="font-display text-lg font-semibold text-primary">{source.title}</h3>
        <button
          onClick={() => onPromote(source.memory_id)}
          className="inline-flex items-center gap-1 text-xs font-medium text-secondary hover:text-accent hover:underline"
        >
          <ArrowUpRight className="w-3.5 h-3.5" />
          팀으로 올리기
        </button>
      </header>
      <p className="text-sm text-secondary mt-2 line-clamp-2">{source.atomic_notes_excerpt}</p>
      <footer className="mt-3 flex items-center gap-3 text-[11px] font-mono text-muted">
        <span>{timeAgo}</span>
        <span>·</span>
        <span>{source.match_type === "keyword" ? "⚡ keyword match" : `${source.score.toFixed(2)} score`}</span>
      </footer>
    </article>
  );
}
```

- [ ] **Step 6: Write `components/capture-sheet.tsx`**

```tsx
// frontend/src/features/memory/components/capture-sheet.tsx
// FAB 클릭 시 열리는 capture modal sheet — 녹음 + textarea
"use client";
import { Mic, Square, X } from "lucide-react";
import { useState } from "react";
import { useCaptureText, useCaptureVoice, useRecorder } from "../hooks";

export function CaptureSheet({
  workspaceId,
  onClose,
}: {
  workspaceId: string;
  onClose: () => void;
}) {
  const [text, setText] = useState("");
  const { isRecording, permissionDenied, start, stop } = useRecorder();
  const captureText = useCaptureText(workspaceId);
  const captureVoice = useCaptureVoice(workspaceId);

  function handleStart() {
    start((blob) => {
      captureVoice.mutate(blob, { onSuccess: onClose });
    });
  }

  function handleSave() {
    if (!text.trim()) return;
    captureText.mutate(text.trim(), { onSuccess: onClose });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-surface border border-border rounded-t-xl w-full max-w-lg p-6 space-y-4">
        <header className="flex items-center justify-between">
          <h2 className="text-xl font-display font-semibold">새 메모</h2>
          <button onClick={onClose} aria-label="Close"><X className="w-5 h-5" /></button>
        </header>
        {permissionDenied && (
          <p className="text-xs font-mono text-warning">마이크 권한 차단 — 텍스트만 가능</p>
        )}
        <button
          onClick={isRecording ? stop : handleStart}
          disabled={permissionDenied}
          className={`w-20 h-20 mx-auto rounded-full flex items-center justify-center transition ${
            isRecording ? "bg-error" : "bg-accent"
          } disabled:opacity-30`}
        >
          {isRecording ? <Square className="w-8 h-8 text-white" /> : <Mic className="w-8 h-8 text-white" />}
        </button>
        <p className="text-center text-xs font-mono text-muted">{isRecording ? "녹음 중 · max 5min" : "— or —"}</p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="type a thought..."
          rows={4}
          className="w-full bg-bg border border-border-subtle rounded-md p-3 text-sm resize-none"
        />
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={captureText.isPending || !text.trim()}
            className="px-4 py-2 bg-accent text-bg font-semibold rounded-md disabled:opacity-30"
          >
            {captureText.isPending ? "저장 중..." : "저장"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Write `/memory` page — B3 search-first FAB layout**

```tsx
// frontend/src/app/(app)/memory/page.tsx
// /memory route — B3 search-first FAB layout
"use client";
import { Mic, Search } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useRecall } from "@/features/memory/hooks";
import { CaptureSheet } from "@/features/memory/components/capture-sheet";
import { RecallResultCard } from "@/features/memory/components/recall-result-card";
import { useActiveWorkspace } from "@/features/workspaces/hooks"; // 기존 hook 가정

export default function MemoryPage() {
  const workspace = useActiveWorkspace();
  const params = useSearchParams();
  const [query, setQuery] = useState(params?.get("q") ?? "");
  const [showCapture, setShowCapture] = useState(false);
  const [tab, setTab] = useState<"personal" | "team">("personal");

  const recall = useRecall(workspace?.id ?? "", query);

  if (!workspace) return null;

  return (
    <main className="max-w-3xl mx-auto px-8 py-8 pb-32 relative min-h-screen">
      <header className="mb-6">
        <h1 className="text-4xl font-display font-bold">Memory</h1>
        <p className="text-xs font-mono text-muted mt-1">{new Date().toISOString().slice(0, 10)}</p>
      </header>

      <div className="relative mb-4">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search your memory..."
          className="w-full h-16 bg-surface border border-border-subtle rounded-lg pl-12 pr-20 text-base"
        />
        <kbd className="absolute right-4 top-1/2 -translate-y-1/2 text-[11px] font-mono text-muted bg-bg px-2 py-1 rounded">⌘K</kbd>
      </div>

      <nav className="flex gap-6 mb-6 text-sm font-medium">
        <button
          onClick={() => setTab("personal")}
          className={tab === "personal" ? "text-accent border-b-2 border-accent pb-2" : "text-secondary pb-2"}
        >
          🔒 Personal
        </button>
        <button
          onClick={() => setTab("team")}
          className={tab === "team" ? "text-accent border-b-2 border-accent pb-2" : "text-secondary pb-2"}
        >
          👥 Team
        </button>
      </nav>

      {query.length < 2 ? (
        <p className="text-center text-secondary py-12">
          🌱 첫 메모를 저장하세요. 우측 하단 🎙️ FAB을 눌러 시작.
        </p>
      ) : recall.isLoading ? (
        <p className="text-center text-muted py-12">검색 중...</p>
      ) : recall.data?.sources.length === 0 ? (
        <p className="text-center text-muted py-12">검색 결과 없음. 다른 단어로 다시.</p>
      ) : (
        <div className="space-y-4">
          {recall.data?.fallback_used && (
            <p className="text-xs font-mono text-warning">⚡ keyword fallback (vector 0건)</p>
          )}
          {recall.data?.sources.map((s) => (
            <RecallResultCard key={s.memory_id} source={s} onPromote={() => {}} />
          ))}
        </div>
      )}

      <button
        onClick={() => setShowCapture(true)}
        className="fixed bottom-8 right-8 w-14 h-14 rounded-full bg-accent text-bg flex items-center justify-center shadow-lg hover:scale-105 transition"
        aria-label="Capture new memory"
      >
        <Mic className="w-6 h-6" />
      </button>

      {showCapture && (
        <CaptureSheet workspaceId={workspace.id} onClose={() => setShowCapture(false)} />
      )}
    </main>
  );
}
```

- [ ] **Step 8: Write tests `frontend/src/features/memory/__tests__/memory-page.test.tsx`**

```tsx
// vitest + @testing-library/react
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MemoryPage from "@/app/(app)/memory/page";

vi.mock("@/features/workspaces/hooks", () => ({
  useActiveWorkspace: () => ({ id: "ws1", type: "personal" }),
}));
vi.mock("next/navigation", () => ({ useSearchParams: () => null }));

describe("/memory page", () => {
  it("renders search bar + FAB", () => {
    render(<MemoryPage />);
    expect(screen.getByPlaceholderText(/Search your memory/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Capture new memory/i)).toBeInTheDocument();
  });

  it("shows empty state when query <2 chars", () => {
    render(<MemoryPage />);
    expect(screen.getByText(/첫 메모를 저장하세요/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 9: Run frontend tests**

```bash
cd frontend && pnpm test src/features/memory
# Expected: PASS
```

- [ ] **Step 10: Manual dev server check**

```bash
cd frontend && NEXT_PUBLIC_RECALL_ENABLED=true pnpm dev
# 브라우저에서 http://localhost:3000/memory 확인 — search bar + FAB + empty state 표시
```

- [ ] **Step 11: Commit R4**

```bash
git add frontend/.env.example frontend/src/components/layout/sidebar.tsx frontend/src/features/memory/ frontend/src/app/\(app\)/memory/
git commit -m "feat(memory): R4 FE /memory page — B3 search-first FAB + capture sheet + recall result card"
```

---

### Task R6: Promote 1-button — BE promote endpoint + audit row + FE modal

**Files:**
- Modify: `backend/src/memory/router.py` (POST /promote)
- Modify: `backend/src/memory/service.py` (promote method)
- Create: `backend/tests/memory/test_promote.py`
- Create: `frontend/src/features/memory/components/promote-modal.tsx`
- Modify: `frontend/src/features/memory/components/recall-result-card.tsx` (onPromote 연결)
- Modify: `frontend/src/features/memory/api.ts` (promote API)

- [ ] **Step 1: Write failing test `backend/tests/memory/test_promote.py`**

```python
import uuid
import pytest

@pytest.mark.asyncio
async def test_promote_creates_duplicate_in_target_ws(memory_client, auth_user, personal_ws, team_ws, seed_memory):
    response = memory_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/memory/{seed_memory.id}/promote",
        json={"target_workspace_id": str(team_ws.id)},
        headers=auth_user.bearer_header,
    )
    assert response.status_code == 202
    body = response.json()
    assert body["new_memory_id"] is not None
    assert body["audit_id"] is not None


@pytest.mark.asyncio
async def test_promote_audit_row_inserted(integration_session, seed_memory, team_ws, auth_user):
    from src.memory.models import PromotionAudit
    from sqlmodel import select
    result = await integration_session.execute(
        select(PromotionAudit).where(PromotionAudit.target_workspace_id == team_ws.id)
    )
    assert result.scalar_one_or_none() is not None
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && pytest tests/memory/test_promote.py -v
```

- [ ] **Step 3: Add `promote` method to `MemoryService`**

```python
async def promote(
    self,
    *,
    memory_id: uuid.UUID,
    source_workspace_id: uuid.UUID,
    target_workspace_id: uuid.UUID,
    promoted_by_user_id: uuid.UUID,
) -> dict:
    # 1. 원본 fetch (workspace_id 필터 강제)
    source = await self.repo.get_by_id(memory_id, source_workspace_id)
    # 2. 복제본 신규 entity
    duplicate = MemoryItem(
        user_id=promoted_by_user_id,
        workspace_id=target_workspace_id,
        type=source.type,
        raw_content=source.raw_content,
        distilled_json=source.distilled_json,
        r2_audio_key=source.r2_audio_key,
        status="embedding_pending",
    )
    await self.repo.save(duplicate)
    # 3. promotion_audit row 신설
    from src.memory.models import PromotionAudit
    audit = PromotionAudit(
        source_memory_id=source.id,
        target_workspace_id=target_workspace_id,
        promoted_by_user_id=promoted_by_user_id,
        embedding_status="pending",
    )
    await self.repo.save_promotion_audit(audit)
    await self.repo.commit()
    return {"new_memory_id": str(duplicate.id), "audit_id": str(audit.id)}
```

- [ ] **Step 4: Add router endpoint**

`backend/src/memory/router.py`에:

```python
from pydantic import BaseModel

class PromoteIn(BaseModel):
    target_workspace_id: uuid.UUID


@router.post("/{memory_id}/promote", status_code=202)
async def promote_memory(
    workspace_id: uuid.UUID,
    memory_id: uuid.UUID,
    body: PromoteIn,
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> dict:
    return await service.promote(
        memory_id=memory_id,
        source_workspace_id=workspace_id,
        target_workspace_id=body.target_workspace_id,
        promoted_by_user_id=user.id,
    )
```

- [ ] **Step 5: Write `frontend/src/features/memory/components/promote-modal.tsx`**

```tsx
// Promote modal — C1 dropdown variant (DESIGN.md §Promote Modal)
"use client";
import { Users } from "lucide-react";
import { useState } from "react";
import { useUserWorkspaces } from "@/features/workspaces/hooks";
import { apiFetch } from "@/lib/api";

export function PromoteModal({
  memoryId,
  sourceWorkspaceId,
  onClose,
}: {
  memoryId: string;
  sourceWorkspaceId: string;
  onClose: () => void;
}) {
  const { data: workspaces } = useUserWorkspaces();
  const teamWs = (workspaces ?? []).filter((w) => w.type === "team");
  const [targetId, setTargetId] = useState(teamWs[0]?.id);
  const [submitting, setSubmitting] = useState(false);

  async function handleConfirm() {
    if (!targetId) return;
    setSubmitting(true);
    try {
      await apiFetch(`/api/v1/workspaces/${sourceWorkspaceId}/memory/${memoryId}/promote`, {
        method: "POST",
        body: JSON.stringify({ target_workspace_id: targetId }),
        headers: { "Content-Type": "application/json" },
      });
      onClose();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-surface border border-border rounded-xl p-6 w-full max-w-md">
        <h2 className="text-2xl font-display font-semibold mb-2">팀으로 올리기</h2>
        <p className="text-sm text-secondary mb-4">어느 팀 워크스페이스로 보낼까요?</p>
        <label className="block text-[11px] font-mono uppercase text-muted mb-2">TARGET WORKSPACE</label>
        <select
          value={targetId}
          onChange={(e) => setTargetId(e.target.value)}
          className="w-full h-14 bg-bg border border-border-subtle rounded-md px-3 mb-6"
        >
          {teamWs.map((w) => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-secondary">취소</button>
          <button
            onClick={handleConfirm}
            disabled={submitting || !targetId}
            className="px-4 py-2 bg-accent text-bg rounded-md disabled:opacity-30"
          >
            {submitting ? "복사 중..." : "팀으로 올리기"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Wire `RecallResultCard` onPromote + page state**

`page.tsx`에 PromoteModal state 추가:

```tsx
const [promoteId, setPromoteId] = useState<string | null>(null);
// ... result card에서
onPromote={(id) => setPromoteId(id)}
// ... 최하단에
{promoteId && workspace && (
  <PromoteModal memoryId={promoteId} sourceWorkspaceId={workspace.id} onClose={() => setPromoteId(null)} />
)}
```

- [ ] **Step 7: Run tests + manual e2e**

```bash
cd backend && pytest tests/memory/test_promote.py -v
cd frontend && pnpm test src/features/memory
```

- [ ] **Step 8: Commit R6**

```bash
git add backend/src/memory/router.py backend/src/memory/service.py backend/tests/memory/test_promote.py frontend/src/features/memory/components/promote-modal.tsx frontend/src/features/memory/api.ts frontend/src/app/\(app\)/memory/page.tsx frontend/src/features/memory/components/recall-result-card.tsx
git commit -m "feat(memory): R6 promote 1-button — BE endpoint + audit row + FE modal (C1 dropdown variant)"
```

---

### Task R7: Instrumentation — capture/recall/promote count + latency p50/p95 + /admin/recall-metrics

**Files:**
- Modify: `backend/src/memory/router.py` (GET /metrics)
- Modify: `backend/src/memory/service.py` (get_metrics + latency middleware)
- Modify: `backend/src/memory/repository.py` (count methods 이미 R1.3에 추가됨, 검증)
- Create: `frontend/src/app/(app)/admin/recall-metrics/page.tsx`
- Create: `backend/tests/memory/test_metrics.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/memory/test_metrics.py
import pytest

@pytest.mark.asyncio
async def test_metrics_returns_5_counts(memory_client, auth_user, test_workspace, seed_memories):
    response = memory_client.get(
        f"/api/v1/workspaces/{test_workspace.id}/memory/metrics",
        headers=auth_user.bearer_header,
    )
    assert response.status_code == 200
    body = response.json()
    assert "capture_count" in body
    assert "recall_count" in body
    assert "promote_count" in body
    assert "recall_p50_ms" in body
    assert "recall_p95_ms" in body
```

- [ ] **Step 2: 간단 in-memory latency tracker + service method**

`backend/src/memory/service.py`에 모듈-level latency buffer 추가:

```python
from collections import deque
import time

_RECALL_LATENCIES_MS: deque[float] = deque(maxlen=200)
_RECALL_COUNTER = 0


def _percentile(values: list[float], pct: float) -> int | None:
    if not values: return None
    sorted_v = sorted(values)
    idx = min(int(len(sorted_v) * pct), len(sorted_v) - 1)
    return int(sorted_v[idx])


class MemoryService:
    # ... existing
    async def recall(self, workspace_id, query, top_k=3):
        global _RECALL_COUNTER
        start = time.time()
        result = await self._recall_impl(workspace_id, query, top_k)  # rename existing logic
        elapsed_ms = (time.time() - start) * 1000
        _RECALL_LATENCIES_MS.append(elapsed_ms)
        _RECALL_COUNTER += 1
        return result

    async def get_metrics(self, workspace_id):
        from src.memory.schemas import MemoryMetricsOut
        capture_count = await self.repo.count_by_workspace(workspace_id)
        promote_count = await self.repo.count_promotions_by_workspace(workspace_id)
        latencies = list(_RECALL_LATENCIES_MS)
        return MemoryMetricsOut(
            capture_count=capture_count,
            recall_count=_RECALL_COUNTER,
            promote_count=promote_count,
            recall_p50_ms=_percentile(latencies, 0.5),
            recall_p95_ms=_percentile(latencies, 0.95),
        )
```

- [ ] **Step 3: Add `GET /metrics` route**

```python
@router.get("/metrics", response_model=MemoryMetricsOut)
async def get_metrics(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryMetricsOut:
    return await service.get_metrics(workspace_id)
```

- [ ] **Step 4: Write `frontend/src/app/(app)/admin/recall-metrics/page.tsx` (founder only)**

```tsx
// founder-only admin metrics view
"use client";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useActiveWorkspace } from "@/features/workspaces/hooks";
import { useUser } from "@clerk/nextjs";

const FOUNDER_CLERK_ID = process.env.NEXT_PUBLIC_FOUNDER_CLERK_ID;

export default function RecallMetricsPage() {
  const { user } = useUser();
  const workspace = useActiveWorkspace();
  const metrics = useQuery({
    queryKey: ["memory", "metrics", workspace?.id],
    queryFn: () => apiFetch(`/api/v1/workspaces/${workspace?.id}/memory/metrics`),
    enabled: !!workspace?.id && user?.id === FOUNDER_CLERK_ID,
  });

  if (user?.id !== FOUNDER_CLERK_ID) return <p className="p-8">접근 권한 없음.</p>;
  if (metrics.isLoading) return <p className="p-8">로딩 중...</p>;

  return (
    <main className="p-8 max-w-2xl">
      <h1 className="text-3xl font-display font-bold mb-6">Recall Metrics</h1>
      <dl className="grid grid-cols-2 gap-4 font-mono text-sm">
        <div><dt className="text-muted">Capture count</dt><dd className="text-2xl">{metrics.data?.capture_count ?? 0}</dd></div>
        <div><dt className="text-muted">Recall count</dt><dd className="text-2xl">{metrics.data?.recall_count ?? 0}</dd></div>
        <div><dt className="text-muted">Promote count</dt><dd className="text-2xl">{metrics.data?.promote_count ?? 0}</dd></div>
        <div><dt className="text-muted">Recall p50 / p95</dt><dd className="text-2xl">{metrics.data?.recall_p50_ms ?? "-"} / {metrics.data?.recall_p95_ms ?? "-"} ms</dd></div>
      </dl>
    </main>
  );
}
```

- [ ] **Step 5: Run tests + commit R7**

```bash
cd backend && pytest tests/memory/test_metrics.py -v
git add backend/src/memory/router.py backend/src/memory/service.py backend/tests/memory/test_metrics.py frontend/src/app/\(app\)/admin/recall-metrics/page.tsx
git commit -m "feat(memory): R7 instrumentation — metrics endpoint + founder admin page"
```

---

### Task R8: PERSONA outreach + 7일 testing + 인터뷰 (코드 없음, manual log)

**Files:**
- Create: `docs/dev-log/sprint-15-r8-outreach.md` (Day 0~14 log)

- [ ] **Step 1: Create outreach log skeleton**

`docs/dev-log/sprint-15-r8-outreach.md` 신규 — Day 0 outreach 채널/메시지/응답 추적:

```markdown
# Sprint 15 R8 — PERSONA Outreach + Testing Log

## Outreach Schedule (O-D lock-in: 인디해커즈 1st → X DM 2nd → HN-Show 3rd)

### Day 0 (TBD)

**Channel 1: 인디해커즈 Discord/Slack #show-and-tell**
- Post date:
- Subject: "AI memory layer 5분 인터뷰 + 1주 사용 testing 의향 있으신 분?"
- Link: (production URL)
- Responses (Day 0~3):

**Channel 2: X DM (Notion/Mem.ai 팔로워)**
- 10명 DM list:
- Subject: "30분 인터뷰 + 7일 testing"
- Responses:

**Channel 3: HN-Show 또는 IH-Show**
- Post date:
- Title:
- Responses:

### Day 3 SLA Gate

- 응답자 수: __/5
- 0/5 → cold expansion (LinkedIn / Reddit r/SaaS / 본인 X 친구 DM)
- 1+/5 → 1st interview 시작

### Day 7 SLA Gate

- 응답자 수: __/5
- ≤1 → Success criteria = Minimum (founder + 1) 자동 전환

## Interview Log (per PERSONA)

### PERSONA-001 (이름):
- 인터뷰 일시:
- 30분 demo 결과:
- 7일 사용 자료 동의: yes/no
- Slack/Discord 채널 invite:
- 7일 후 follow-up 일정:

(반복)

## Day 7 후 follow-up 인터뷰

각 PERSONA "would miss this?" unprompted 발언 캡처 (Codex evidence pattern):
- PERSONA-001: yes (unprompted) / no / nudged
- (반복)

## Final Result (Day 14)

- Best (3+ unprompted + 1+ paying): yes/no
- Medium (2+ unprompted): yes/no
- Minimum (founder + 1): yes/no
- Sprint 16 결정:
```

- [ ] **Step 2: Day 0 outreach send (founder manual ~1h)**

3 채널 동시 시작. founder가 직접 진행:
- 인디해커즈 Discord/Slack 게시
- X DM 10명
- HN-Show 또는 IH-Show 1건

- [ ] **Step 3: Commit R8 log**

```bash
git add docs/dev-log/sprint-15-r8-outreach.md
git commit -m "docs(r8): Sprint 15 PERSONA outreach + testing log skeleton (Day 0~14)"
```

---

## §3. Dependencies

| 항목 | 필요성 | 상태 / 처리 |
|------|--------|------------|
| Clerk Production key | R8 외부 5명 PERSONA testing 전 필수 | Sprint 14 carry-over — Day 0 외 founder가 발급 작업 진행 |
| Whisper API quota | voice ≥10/명 × 5명 = 50 calls | 무시 (~$0.06 × 5분 × 50 = $15) |
| Gemini distill quota | ≥30 × 5명 = 150 calls | 무시 |
| OpenAI embedding quota | ≥30 × 5명 = 150 embeds | 무시 |
| R2 storage cost | 75MB / 5명 / 30일 | 무시 (~$0.001/월) |
| ffmpeg (R1 webm → wav) | server-side audio normalize | Dockerfile에 `apt-get install ffmpeg` 추가 (Day 1 task) |

> **codex Q4 검증 대상**: Day 0 spike 10 sample call로 latency p95 ≤2s + cost estimate 실측. R1 acceptance gate.

---

## §4. Success Criteria (Stage 1 design doc 정합)

### Sprint 15 R1~R8 종료 (Day 14):

| 등급 | 조건 |
|------|------|
| **Best** | founder Day 6~12 capture ≥30회 + recall click-through ≥30% + PERSONA 5명 인터뷰 완료 + 3명+ "이거 없으면 불편" unprompted + 1명+ 월 $10~20 결제 의사 + Promote ≤30% of recall |
| **Medium** | founder 동일 + PERSONA 2명+ unprompted + 결제 signal 0~1명 |
| **Minimum (founder-only fallback)** | founder dogfooding capture ≥30회 + recall thumbs-up ≥3건 (R3 day-3 gate 통과) |

### Fail criteria (Pivot trigger):

- ❌ **R1~R3 Day 3 gate fail**: founder Day 1~3 capture ≤5회 또는 recall thumbs-up ≤2건 → R3 fix 우선, R6/R7 block.
- ❌ **R8 minimum fail**: founder Day 14 capture ≤10회 또는 recall thumbs-down ≥50% → Recall wedge 자체 reject. PRD v3.0 thesis pivot 재고.
- ❌ **PERSONA hard fail**: PERSONA 응답자 (≥1명) 100% "이거 왜 필요?" → thesis pivot 자체 reject. v2.x "팀의 세컨드 브레인" 회귀 검토.

---

## §5. Verification (Stage 4 진입 입력)

### 5.1 First failing test

```bash
cd backend && pytest tests/test_alembic_memory.py::test_memory_items_table_exists -v
# Expected: FAIL — memory_items table 미존재. R2 alembic migration이 첫 fix.
```

### 5.2 e2e capture → recall 검증

R1 + R3 완료 시점에:

```bash
# 1. BE 기동
cd backend && uvicorn src.main:app --reload

# 2. capture 1회 (text)
curl -X POST http://localhost:8000/api/v1/workspaces/<personal-ws-id>/memory \
  -H "Authorization: Bearer <clerk-jwt>" \
  -F "text=오늘 Sprint 15 wedge 결정 Recall-first"

# 3. recall
curl "http://localhost:8000/api/v1/workspaces/<personal-ws-id>/memory/recall?q=Sprint+wedge" \
  -H "Authorization: Bearer <clerk-jwt>"
# Expected: sources 1+ with title "오늘 Sprint 15 wedge 결정 Recall-first" or distilled title
```

### 5.3 Manual FE 검증

```bash
cd frontend && NEXT_PUBLIC_RECALL_ENABLED=true pnpm dev
# 1. /memory 페이지 진입 (sidebar Memory 항목 + NEW pill 노출 확인)
# 2. FAB 클릭 → CaptureSheet 열림
# 3. 텍스트 입력 + 저장 → 검색창에서 결과 노출
# 4. 결과 카드 [팀으로 올리기] 클릭 → PromoteModal → 확인 → 202
# 5. /admin/recall-metrics 진입 (founder Clerk ID로만) → 5 metric 노출
```

### 5.4 Stage 4 진입 + 단일 PR push

R1~R8 R8 outreach까지 commit 완료 시점:

```bash
git log sprint-15/personal-workspace --oneline | head -20
# pre-Stage 4: 5 commits (Stage 0+1+2 산출)
# post-Stage 4: + 10~15 commits (T0~R8)

# 사용자 승인 후만 push:
git push origin sprint-15/personal-workspace
gh pr create --title "Sprint 15: Recall-first prototype (R1~R8)" --base main
# PR description = 본 plan §0 Context + Success Criteria + R8 outreach 결과 link
```

---

## §6. Self-Review (writing-plans skill checklist)

### 6.1 Spec coverage check

| Spec 요구 | Task | 매핑 OK? |
|-----------|------|----------|
| Stage 1 R1 capture | R1.1~R1.4 | ✅ |
| Stage 1 R2 alembic | R2 | ✅ |
| Stage 1 R3 recall + I-9 patch atomic | R3 | ✅ |
| Stage 1 R4 FE memory page | R4 (B3 search-first FAB) | ✅ |
| Stage 1 R5 personal seed + I-19 코드 atomic | R5.1+R5.2 | ✅ |
| Stage 1 R6 promote 1-button | R6 (C1 dropdown variant) | ✅ |
| Stage 1 R7 instrumentation | R7 | ✅ |
| Stage 1 R8 PERSONA outreach | R8 | ✅ |
| ADR-016 AD-41 reframe | T0 | ✅ |
| 5 Open Q lock-in (Q2 brainstorm) | inline (O-A R3, O-B R3, O-C R8, O-D R8, O-E R1) | ✅ |
| atomic doc + 코드 강제 | R3 (I-9 + CONTEXT-MAP), R5 (I-19 코드만, CONTEXT-MAP defer) | ✅ |

### 6.2 Placeholder scan

- TBD / TODO / "implement later" / "Similar to Task N" — 없음.
- Day 0 outreach scheduling은 R8 manual task로 명시.
- ffmpeg apt-get은 R1 첫 Dockerfile patch task로 별도 — Day 1 build 진입 직전.

### 6.3 Type consistency

- `MemoryItem.distilled_json` JSONB / `DistilledJson` Pydantic schema 일관.
- `MemoryRecallSource.match_type` `"vector" | "keyword"` literal — service + schemas 일관.
- `Workspace.type` `"personal" | "team"` — alembic + invariant 코드 + FE type 일관.
- `PromotionAudit.embedding_status` `"pending" | "processing" | "completed" | "failed"` — schema 일관.

### 6.4 Ambiguity check

- ffmpeg server-side webm → wav 변환 위치: R1 service `_transcribe_with_whisper` 진입부에 추가 검토 — Whisper API가 webm 직접 받으므로 1차 시도는 webm raw. fail 시 ffmpeg fallback. Sprint 17+ 정식화.
- ProjectMember 변경 후 personal ws에 cross-ws ProjectMember가 자동 차단되는지? — R5 service `add_member` invariant code가 ws.type == 'personal' 시 차단하므로 ProjectMember도 service layer에서 동일 가드 필요. R5에서 함께 처리.

---

## §7. Execution Handoff

Plan complete + commit. 두 execution option:

1. **Subagent-Driven (recommended)** — fresh subagent per task + 양단 review + fast iteration. `superpowers:subagent-driven-development`
2. **Inline Execution** — 현 세션 안에서 batch task + checkpoint review. `superpowers:executing-plans`

> **사용자 정책 (handoff §7)**: 자동 commit OK, PR push만 사용자 승인. R1~R8 단일 PR로 main.

Stage 4 진입 시 어느 approach? — Q4 codex 적대적 검토 통과 후 결정.
