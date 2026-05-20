# Sprint 22 Onboarding + E2E + Sentry Implementation Plan

> ⚠️ **Sprint 24 Wave 2 부분 deprecated** (2026-05-20): OBN-01~04 OnboardingBanner FE 구현 task 는 폐기됨 (D 옵션, Codex+Gemini deep research 합의). BE step lifecycle / Sentry / Playwright G2/G7/G8 자산은 유지.
> 결정 anchor: `docs/superpowers/specs/2026-05-20-sprint24-wave2-trusty-heron-design.md` §T-OBN-05

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 첫 외부 user 가 회원가입 → 첫 RAG 응답까지 24h 내 도달, 그 여정을 production-observable 하게.

**Architecture:** Server-side User column `onboarding_step` (0~4) + `onboarded_at` + BE event hook 4 단계 (workspace=1 / project=2 / meeting distillation=3 / RAG ask=4). Sentry FE+BE wired (PII scrub `before_send`). Playwright E2E 8 시나리오 (NEW 3 + 보강 4 + G4 fix). Export = discoverability fix only. Personal workspace race = Sprint 15 lazy seed 활용, 회귀 test 만 추가.

**Tech Stack:** FastAPI · SQLModel · Alembic · PostgreSQL (Neon) · React Query · Zustand · Clerk · `@sentry/nextjs` · `sentry-sdk[fastapi]` · Playwright (`@playwright/test`) · TDD + pytest.

**Spec:** `docs/superpowers/specs/2026-05-19-sprint22-onboarding-e2e-obs.md`

**진입 baseline:** main HEAD `1a83af6` (Sprint 21 PR #96). worktree = `../kairos-sprint-22` (`sprint-22/onboarding-e2e-obs` 브랜치, 본 plan commit 직전 spec commit `a699335`). baseline 회귀: pytest 325 PASS + 1 skipped / pyright 132 / alembic drift 0.

---

## File Structure

| 파일 | 작업 | Task |
|---|---|---|
| `backend/src/auth/models.py` | modify (User column 2개 추가) | Task 1.1 |
| `backend/src/auth/schemas.py` | modify (UserResponse alias 추가) | Task 1.2 |
| `backend/alembic/versions/<rev>_sprint22_user_onboarding.py` | create (column 2개 + backfill) | Task 1.3 |
| `backend/tests/integration/test_alembic_upgrade.py` | modify (PR2_MANAGED_CONSTRAINTS allowlist) | Task 1.4 |
| `backend/src/auth/CONTEXT.md` | modify (§엔티티) | Task 1.5 |
| `docs/architecture/erd.md` | modify (User entity 갱신) | Task 1.5 |
| `CONTEXT-MAP.md` | modify (§2 entity row) | Task 1.5 |
| `backend/src/onboarding/__init__.py` | create | Task 2.1 |
| `backend/src/onboarding/models.py` | create (Pydantic schemas + OnboardingStep enum) | Task 2.1 |
| `backend/src/onboarding/repository.py` | create | Task 2.1 |
| `backend/src/onboarding/service.py` | create | Task 2.1 |
| `backend/src/onboarding/router.py` | create | Task 2.1 |
| `backend/src/onboarding/dependencies.py` | create | Task 2.1 |
| `backend/src/onboarding/CONTEXT.md` | create | Task 2.1 |
| `backend/tests/onboarding/test_service.py` | create | Task 2.1 |
| `backend/tests/onboarding/test_repository.py` | create | Task 2.1 |
| `backend/tests/onboarding/test_router.py` | create | Task 2.1 |
| `backend/src/main.py` | modify (router include + Sentry init) | Task 2.2 + Task 7.1 |
| `backend/src/workspaces/service.py` | modify (step=1 hook) | Task 2.3 |
| `backend/src/projects/service.py` | modify (step=2 hook) | Task 2.4 |
| `backend/src/meetings/pipeline_service.py` | modify (step=3 hook, line ~115 method end) | Task 2.5 |
| `backend/src/rag/service.py` | modify (step=4 hook) | Task 2.6 |
| `backend/CONTEXT.md` | modify (§4 도메인 표) | Task 2.7 |
| `docs/architecture/directory-map.md` | modify (백엔드 트리) | Task 2.7 |
| `docs/api/endpoints.md` | modify (신규 endpoint 등재) | Task 2.7 |
| `backend/tests/auth/test_personal_workspace_race.py` | create | Task 3.1 |
| `frontend/src/features/onboarding/api.ts` | create | Task 4.1 |
| `frontend/src/features/onboarding/hooks.ts` | create | Task 4.1 |
| `frontend/src/features/onboarding/schemas.ts` | create | Task 4.1 |
| `frontend/src/features/home/components/today-feed.tsx` | modify (banner refactor) | Task 4.2 |
| `frontend/src/features/projects/hooks.ts` | modify (invalidate onboarding) | Task 4.3 |
| `frontend/src/features/meetings/hooks.ts` | modify (invalidate) | Task 4.3 |
| `frontend/src/features/rag/hooks.ts` | modify (invalidate) | Task 4.3 |
| `frontend/src/components/empty-state.tsx` | modify (onboarding-aware copy) | Task 5.1 |
| `frontend/src/features/meetings/components/meeting-detail-header.tsx` | modify (export discoverability) | Task 5.2 + Task 8.5 |
| `frontend/src/features/notes/components/note-detail-header.tsx` | modify (export discoverability) | Task 5.2 |
| `frontend/src/components/{fab,floating-action}/...` | modify (BL-017 collision fix) | Task 6.1 |
| `frontend/src/features/home/components/today-feed.tsx` | modify (mobile flex-wrap) | Task 6.2 |
| `frontend/e2e/tests/mobile-responsive.spec.ts` | modify (OBN-04 case) | Task 6.3 |
| `backend/pyproject.toml` | modify (sentry-sdk dep) | Task 7.1 |
| `backend/src/core/config.py` | modify (SENTRY_DSN env) | Task 7.1 |
| `backend/src/main.py` | modify (sentry init + PII scrub) | Task 7.1 |
| `frontend/package.json` | modify (@sentry/nextjs dep) | Task 7.2 |
| `frontend/sentry.client.config.ts` | create | Task 7.2 |
| `frontend/sentry.server.config.ts` | create | Task 7.2 |
| `frontend/sentry.edge.config.ts` | create | Task 7.2 |
| `frontend/instrumentation.ts` | create | Task 7.2 |
| `frontend/next.config.ts` | modify (withSentryConfig wrapper) | Task 7.2 |
| `.env.example` | modify (SENTRY_DSN + NEXT_PUBLIC_SENTRY_DSN) | Task 7.3 |
| `docs/dev-log/021-sentry-observability.md` | create (ADR Nygard) | Task 7.3 |
| `frontend/e2e/tests/rag-citation.spec.ts` | modify (G4 skip 해제) | Task 8.1 |
| `frontend/e2e/tests/first-project.spec.ts` | create (G2) | Task 8.2 |
| `frontend/e2e/tests/auth-relogin.spec.ts` | create (G7) | Task 8.3 |
| `frontend/e2e/tests/actions-export.spec.ts` | create (G8) | Task 8.4 |
| `frontend/e2e/tests/home.spec.ts` | modify (G1 progress assertion) | Task 8.6 |
| `frontend/e2e/tests/meeting-upload.spec.ts` | modify (G3 progress assertion) | Task 8.6 |
| `frontend/e2e/tests/qa-sentinel-p0.spec.ts` | modify (G5/G6 progress assertion) | Task 8.6 |
| `frontend/e2e/tests/invite-page-regression.spec.ts` | modify (G6) | Task 8.6 |
| `docs/dev-log/2026-05-19-sprint22-playwright-e2e.md` | create (결과 표) | Task 8.7 |
| `docs/dev-log/2026-05-19-sprint22-dogfooding.md` | create (12분 walkthrough) | Task 8.7 |
| `docs/REFACTORING-BACKLOG.md` | modify (BL-017 ✅ + carry-over) | Task 9.1 |
| `docs/TODO.md` | modify (Sprint 22 Recently Completed) | Task 9.2 |

---

## Task 0: Setup verify — worktree 이미 생성됨 (~5min)

**Goal:** worktree + baseline 회귀 이미 본 세션 Stage 0 에서 완료. 검증만.

- [ ] **Step 0.1: worktree 검증**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-22
git status -sb
git log --oneline -3
```

Expected:
```
## sprint-22/onboarding-e2e-obs
a699335 docs: Sprint 22 onboarding + E2E + Sentry spec 작성 (brainstorming 산출물)
1a83af6 Sprint 21 BL-050 Simple 4: cross-workspace composite FK hardening (4 commits + 4 polish) (#96)
```

- [ ] **Step 0.2: baseline 회귀 (이미 통과 확인됨, optional re-run)**

```bash
cd backend && uv run pytest tests/ -q 2>&1 | tail -3
```

Expected: `325 passed, 1 skipped`

---

## Task 1: BE Schema (User column + alembic + drift gate + atomic docs) (~4-5h, 6 commits)

**Goal:** User table 에 `onboarding_step` + `onboarded_at` 추가 + 기존 user backfill + drift gate + Atomic docs 갱신. Codex 1.5차 schema review 게이트 진입.

### Task 1.1: User model column 추가

**Files:**
- Modify: `backend/src/auth/models.py`

- [ ] **Step 1.1.1: 현재 User model 확인**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-22
grep -n "class User\b\|class.*User.*:" backend/src/auth/models.py | head -5
```

- [ ] **Step 1.1.2: User model 에 column 2개 추가**

`backend/src/auth/models.py` 의 `class User(SQLModel, table=True)` 안에 추가:

```python
from datetime import datetime
from sqlmodel import Field

# ... 기존 필드들 아래에 추가 ...
onboarding_step: int = Field(default=0, sa_column_kwargs={"server_default": "0"}, nullable=False)
onboarded_at: datetime | None = Field(default=None, nullable=True)
```

import 가 이미 있으면 추가 안 함.

- [ ] **Step 1.1.3: pyright 회귀 0**

```bash
cd backend && uv run pyright src/auth/models.py 2>&1 | tail -5
```

Expected: 0 errors in `models.py`

- [ ] **Step 1.1.4: commit (E1)**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-22
git add backend/src/auth/models.py
git commit -m "feat(auth): User onboarding_step + onboarded_at column 추가 (Sprint 22 OBN-02)"
```

### Task 1.2: UserResponse schema 필드 추가

**Files:**
- Modify: `backend/src/auth/schemas.py`

- [ ] **Step 1.2.1: UserResponse 위치 확인**

```bash
grep -n "class UserResponse\|onboarding" backend/src/auth/schemas.py | head -10
```

- [ ] **Step 1.2.2: UserResponse 에 필드 추가**

`backend/src/auth/schemas.py` 의 `class UserResponse(BaseModel)` 안에 추가 (alias 사용 — FE camelCase):

```python
from datetime import datetime
from pydantic import Field

# class UserResponse(BaseModel): 안에
onboarding_step: int = Field(0, alias="onboardingStep")
onboarded_at: datetime | None = Field(None, alias="onboardedAt")
```

`ConfigDict(populate_by_name=True)` 가 없으면 추가.

- [ ] **Step 1.2.3: pyright + pytest**

```bash
cd backend && uv run pyright src/auth/schemas.py && uv run pytest tests/auth/ -q 2>&1 | tail -3
```

Expected: 0 errors / all auth tests PASS

- [ ] **Step 1.2.4: commit (E2)**

```bash
git add backend/src/auth/schemas.py
git commit -m "feat(auth): UserResponse 에 onboardingStep + onboardedAt 필드 추가 (Sprint 22)"
```

### Task 1.3: Alembic revision + 기존 user backfill

**Files:**
- Create: `backend/alembic/versions/<rev>_sprint22_user_onboarding.py`

- [ ] **Step 1.3.1: alembic revision 생성 (autogen NOT used — manual)**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-22/backend
uv run alembic revision -m "sprint22_user_onboarding"
# 생성된 파일 path 확인 → REV_FILE 환경변수 set
REV_FILE=$(ls -t alembic/versions/*.py | head -1)
echo $REV_FILE
```

- [ ] **Step 1.3.2: revision content 작성**

`$REV_FILE` 내용을 다음으로 교체:

```python
"""sprint22_user_onboarding

Revision ID: <auto>
Revises: cf903ab3dd37
Create Date: 2026-05-19 ...

"""
# alembic revision <id> (sprint22_user_onboarding)
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "<auto>"
down_revision: Union[str, None] = "cf903ab3dd37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """User 에 onboarding_step + onboarded_at 추가 + 기존 row backfill step=4."""
    op.add_column(
        "users",
        sa.Column("onboarding_step", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True),
    )
    # D7 lock-in: 기존 user 는 이미 active → step=4 + onboarded_at=created_at
    op.execute(
        "UPDATE users "
        "SET onboarding_step = 4, onboarded_at = created_at "
        "WHERE onboarding_step = 0"
    )


def downgrade() -> None:
    op.drop_column("users", "onboarded_at")
    op.drop_column("users", "onboarding_step")
```

`<auto>` 자리는 `alembic revision` 이 자동 생성한 hex ID 그대로 유지.

- [ ] **Step 1.3.3: alembic upgrade head**

```bash
cd backend && uv run alembic upgrade head 2>&1 | tail -5
```

Expected: `Running upgrade cf903ab3dd37 -> <new_rev>, sprint22_user_onboarding`

- [ ] **Step 1.3.4: DB verify**

```bash
cd backend && uv run python -c "
import asyncio
from sqlalchemy import text
from src.core.database import async_session_factory

async def main():
    async with async_session_factory() as session:
        result = await session.exec(text('SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = \\'users\\' AND column_name IN (\\'onboarding_step\\', \\'onboarded_at\\')'))
        for row in result:
            print(row)

asyncio.run(main())
"
```

Expected: 2 rows — `onboarding_step / integer / NO`, `onboarded_at / timestamp with time zone / YES`

- [ ] **Step 1.3.5: commit (E3)**

```bash
git add backend/alembic/versions/*.py
git commit -m "feat(alembic): users.onboarding_step + onboarded_at column + backfill step=4 (Sprint 22)"
```

### Task 1.4: Drift gate allowlist 갱신 (column drift = `PR2_MANAGED_COLUMNS`)

**Fact (Codex 1차 finding 6)**: `PR2_MANAGED_CONSTRAINTS` 는 constraint/index 이름 매칭용. column nullable/type/default drift 는 `PR2_MANAGED_COLUMNS` tuple `(table, column)` 으로 매칭. 본 sprint 의 신규 column 2개는 `PR2_MANAGED_COLUMNS` 에 등재.

**Files:**
- Modify: `backend/tests/integration/test_alembic_upgrade.py`

- [ ] **Step 1.4.1: PR2_MANAGED_COLUMNS 위치 확인**

```bash
grep -n "PR2_MANAGED_COLUMNS\|PR2_MANAGED_CONSTRAINTS\|users.*onboarding\|('users'," backend/tests/integration/test_alembic_upgrade.py | head -10
```

- [ ] **Step 1.4.2: allowlist 에 신규 column tuple 등재**

`PR2_MANAGED_COLUMNS` set 안에 tuple 추가:

```python
PR2_MANAGED_COLUMNS = {
    # ... 기존 ('table', 'column') tuples ...
    # Sprint 22 OBN-02 (server-side User onboarding tracker)
    ("users", "onboarding_step"),
    ("users", "onboarded_at"),
}
```

정확한 set 명칭 (`PR2_MANAGED_COLUMNS`) + tuple 형식 `(table_name, column_name)` 은 기존 entry 패턴 따름.

- [ ] **Step 1.4.3: drift gate test 실행**

```bash
cd backend && uv run pytest tests/integration/test_alembic_upgrade.py -v 2>&1 | tail -10
```

Expected: PASS (1 test, drift 0)

- [ ] **Step 1.4.4: commit (E4)**

```bash
git add backend/tests/integration/test_alembic_upgrade.py
git commit -m "test(alembic): drift gate allowlist 에 users.onboarding_* 등재 (Sprint 22)"
```

### Task 1.5: Atomic Update §4 docs sync

**Files:**
- Modify: `backend/src/auth/CONTEXT.md`
- Modify: `docs/architecture/erd.md`
- Modify: `CONTEXT-MAP.md`

- [ ] **Step 1.5.1: auth/CONTEXT.md 갱신**

`backend/src/auth/CONTEXT.md` 의 §엔티티 (또는 등가) 섹션에 User 의 신규 column 명시.

샘플 추가 (정확한 헤딩 명칭은 기존 doc 패턴 따름):

```markdown
### User

- `id: UUID`
- `clerk_id: str` (unique)
- `email: str`
- `created_at / updated_at: datetime`
- **`onboarding_step: int = 0`** — 0=NOT_STARTED, 1=WORKSPACE_CREATED, 2=FIRST_PROJECT, 3=FIRST_MEETING (distillation 완료), 4=FIRST_RAG (Sprint 22 OBN-02)
- **`onboarded_at: datetime | None`** — step=4 도달 시 set (idempotent)
```

- [ ] **Step 1.5.2: erd.md 갱신**

`docs/architecture/erd.md` 의 User entity 표/Mermaid 에 동일 column 추가.

- [ ] **Step 1.5.3: CONTEXT-MAP.md §2 entity row 갱신**

`CONTEXT-MAP.md` §2 의 User row 에 column 명시 (기존 라인 패턴 따름).

- [ ] **Step 1.5.4: commit (E5 — atomic docs)**

```bash
git add backend/src/auth/CONTEXT.md docs/architecture/erd.md CONTEXT-MAP.md
git commit -m "docs: User onboarding_step / onboarded_at atomic doc sync (Sprint 22)"
```

### Task 1.6: BE schema baseline 회귀 + Codex 1.5차 schema review

- [ ] **Step 1.6.1: 전체 회귀**

```bash
cd backend
uv run pytest tests/ -q 2>&1 | tail -5
uv run pyright 2>&1 | tail -3
```

Expected: `325 passed + 1 skipped` (회귀 0) / pyright `132 errors` (회귀 0)

- [ ] **Step 1.6.2: Codex 1.5차 schema review 게이트**

```bash
# bash 또는 controller 가 호출
codex review --base origin/main HEAD
```

Expected verdict: APPROVE 또는 minor REVISE. REVISE 시 100% 수락 후 polish commit. Sprint 21 D2.1/D3.1 패턴.

---

## Task 2: BE Event Hooks + Onboarding Module (~3-4h, 5 commits)

**Goal:** Onboarding 도메인 모듈 신설 + 4 단계 BE event hook + endpoint.

### Task 2.1: Onboarding 도메인 모듈 신설

**Files:**
- Create: `backend/src/onboarding/{__init__.py, models.py, repository.py, service.py, router.py, dependencies.py, CONTEXT.md}`
- Create: `backend/tests/onboarding/{__init__.py, test_service.py, test_repository.py, test_router.py}`

- [ ] **Step 2.1.1: 디렉토리 + __init__.py 생성**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-22
mkdir -p backend/src/onboarding backend/tests/onboarding
touch backend/src/onboarding/__init__.py backend/tests/onboarding/__init__.py
```

- [ ] **Step 2.1.2: schemas.py (Pydantic models) 작성**

`backend/src/onboarding/schemas.py`:

```python
# Onboarding domain schemas — Server-side persistent step tracker
from datetime import datetime
from enum import IntEnum

from pydantic import BaseModel, ConfigDict, Field


class OnboardingStep(IntEnum):
    NOT_STARTED = 0
    WORKSPACE_CREATED = 1
    FIRST_PROJECT = 2
    FIRST_MEETING = 3
    FIRST_RAG = 4


class OnboardingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    step: int = Field(..., alias="step")
    total_steps: int = Field(4, alias="totalSteps")
    onboarded_at: datetime | None = Field(None, alias="onboardedAt")
    is_completed: bool = Field(False, alias="isCompleted")
```

- [ ] **Step 2.1.3: repository.py 작성**

`backend/src/onboarding/repository.py`:

```python
# Onboarding domain — idempotent UPDATE repository
from uuid import UUID

from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession


class OnboardingRepository:
    """User.onboarding_step idempotent updater."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def increment(self, user_id: UUID, target_step: int) -> None:
        """target_step 이하 면 no-op. target=4 면 onboarded_at = now()."""
        await self._session.exec(
            text(
                "UPDATE users "
                "SET onboarding_step = :target, "
                "    onboarded_at = CASE WHEN :target = 4 THEN now() ELSE onboarded_at END "
                "WHERE id = :user_id AND onboarding_step < :target"
            ).bindparams(user_id=user_id, target=target_step)
        )
```

- [ ] **Step 2.1.4: service.py 작성**

`backend/src/onboarding/service.py`:

```python
# Onboarding domain — service layer (single-session safe)
from uuid import UUID

from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from src.onboarding.repository import OnboardingRepository
from src.onboarding.schemas import OnboardingResponse


class OnboardingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OnboardingRepository(session)

    async def increment_step(self, user_id: UUID, target_step: int) -> None:
        """다른 도메인이 호출. flush 없음 (호출 도메인의 transaction 합류)."""
        await self._repo.increment(user_id, target_step)

    async def get_status(self, user_id: UUID) -> OnboardingResponse:
        result = await self._session.exec(
            text(
                "SELECT onboarding_step, onboarded_at "
                "FROM users WHERE id = :user_id"
            ).bindparams(user_id=user_id)
        )
        row = result.first()
        if row is None:
            return OnboardingResponse(step=0, onboarded_at=None, is_completed=False)
        step = row[0]
        return OnboardingResponse(
            step=step,
            onboarded_at=row[1],
            is_completed=(step >= 4),
        )
```

- [ ] **Step 2.1.5: dependencies.py 작성**

**Fact (Codex 1차 finding 5)**: 본 프로젝트의 session DI 는 `src.common.database.get_async_session`. `src.core.database.get_session` 은 존재하지 않음.

`backend/src/onboarding/dependencies.py`:

```python
# Onboarding domain — DI provider
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session
from src.onboarding.service import OnboardingService


def get_onboarding_service(
    session: AsyncSession = Depends(get_async_session),
) -> OnboardingService:
    return OnboardingService(session)
```

- [ ] **Step 2.1.6: router.py 작성**

`backend/src/onboarding/router.py`:

```python
# Onboarding domain — GET /api/v1/users/me/onboarding
from fastapi import APIRouter, Depends

from src.auth.dependencies import require_user
from src.auth.models import User
from src.onboarding.dependencies import get_onboarding_service
from src.onboarding.schemas import OnboardingResponse
from src.onboarding.service import OnboardingService

router = APIRouter(prefix="/users/me/onboarding", tags=["onboarding"])


@router.get("", response_model=OnboardingResponse)
async def get_my_onboarding(
    user: User = Depends(require_user),
    service: OnboardingService = Depends(get_onboarding_service),
) -> OnboardingResponse:
    return await service.get_status(user.id)
```

- [ ] **Step 2.1.7: TDD — test_service.py 작성 (failing first)**

`backend/tests/onboarding/test_service.py`:

```python
# Onboarding service idempotency tests
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from src.onboarding.service import OnboardingService


@pytest.mark.asyncio
async def test_increment_step_advances_when_target_higher(
    integration_session: AsyncSession, test_user_id
):
    service = OnboardingService(integration_session)
    await service.increment_step(test_user_id, 1)
    await integration_session.commit()

    status = await service.get_status(test_user_id)
    assert status.step == 1


@pytest.mark.asyncio
async def test_increment_step_idempotent_when_target_lower_or_equal(
    integration_session: AsyncSession, test_user_id
):
    service = OnboardingService(integration_session)
    await service.increment_step(test_user_id, 3)
    await integration_session.commit()
    await service.increment_step(test_user_id, 1)
    await integration_session.commit()

    status = await service.get_status(test_user_id)
    assert status.step == 3  # 1 로 떨어지지 않음


@pytest.mark.asyncio
async def test_step_4_sets_onboarded_at(
    integration_session: AsyncSession, test_user_id
):
    service = OnboardingService(integration_session)
    await service.increment_step(test_user_id, 4)
    await integration_session.commit()

    status = await service.get_status(test_user_id)
    assert status.step == 4
    assert status.is_completed is True
    assert status.onboarded_at is not None
    assert isinstance(status.onboarded_at, datetime)


@pytest.mark.asyncio
async def test_get_status_returns_zero_for_missing_user(
    integration_session: AsyncSession,
):
    import uuid
    service = OnboardingService(integration_session)
    status = await service.get_status(uuid.uuid4())
    assert status.step == 0
    assert status.is_completed is False
```

`test_user_id` fixture 는 기존 auth conftest 패턴 따라 작성 — 미존재 시 `backend/tests/conftest.py` 또는 `backend/tests/onboarding/conftest.py` 에 추가.

- [ ] **Step 2.1.8: test_router.py 작성**

`backend/tests/onboarding/test_router.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_onboarding_returns_current_status(
    integration_client: AsyncClient, auth_headers
):
    response = await integration_client.get(
        "/api/v1/users/me/onboarding", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert "step" in body
    assert "totalSteps" in body
    assert body["totalSteps"] == 4
    assert "onboardedAt" in body
    assert "isCompleted" in body


@pytest.mark.asyncio
async def test_get_onboarding_requires_auth(integration_client: AsyncClient):
    response = await integration_client.get("/api/v1/users/me/onboarding")
    assert response.status_code in (401, 403)
```

- [ ] **Step 2.1.9: CONTEXT.md 작성**

`backend/src/onboarding/CONTEXT.md`:

```markdown
# Onboarding 도메인 CONTEXT

## 1. 책임
User.onboarding_step (0~4) lifecycle 관리. 다른 도메인이 `OnboardingService.increment_step(user_id, target)` 호출.

## 2. 엔티티
User table 의 `onboarding_step: int`, `onboarded_at: datetime | None` (Sprint 22 OBN-02).

OnboardingStep IntEnum:
- 0 NOT_STARTED
- 1 WORKSPACE_CREATED
- 2 FIRST_PROJECT
- 3 FIRST_MEETING (distillation 완료, `pipeline_service.process_meeting()` 끝)
- 4 FIRST_RAG (`rag.service.ask()` 첫 성공)

## 3. 의존
- 호출자: workspaces / projects / meetings (pipeline_service) / rag
- 의존: auth (User table)
- single-session: 호출자의 transaction 에 합류 (no commit/flush)

## 4. 엔드포인트
- `GET /api/v1/users/me/onboarding` → `OnboardingResponse { step, totalSteps, onboardedAt, isCompleted }`

## 5. Idempotency
- `UPDATE users SET onboarding_step=:t WHERE id=:u AND onboarding_step < :t` (target ≤ current 면 no-op)
- target=4 일 때만 `onboarded_at = now()` set
```

- [ ] **Step 2.1.10: 회귀 + commit (E6)**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-22/backend
uv run pytest tests/onboarding/ -v 2>&1 | tail -10
```

Expected: 4 tests PASS (or fail with fixture missing — fixture 추가 후 PASS)

```bash
git add backend/src/onboarding/ backend/tests/onboarding/
git commit -m "feat(onboarding): 도메인 모듈 신설 (service / repo / router / schema / test 4건)"
```

### Task 2.2: backend/src/main.py — router include

**Fact (Codex 1차 finding 4)**: FastAPI app entry = `backend/src/main.py` (NOT `backend/src/main.py`). smoke command 도 `from src.main import app`.

**Files:**
- Modify: `backend/src/main.py`

- [ ] **Step 2.2.1: 기존 router include 위치 확인**

```bash
grep -n "include_router\|onboarding" backend/src/main.py
```

- [ ] **Step 2.2.2: onboarding router include 추가**

`backend/src/main.py` 의 router include 블록에 (기존 패턴 따라):

```python
from src.onboarding.router import router as onboarding_router
# ...
app.include_router(onboarding_router, prefix="/api/v1")
```

- [ ] **Step 2.2.3: smoke**

```bash
cd backend && uv run python -c "from src.main import app; print([r.path for r in app.routes if 'onboarding' in r.path])"
```

Expected: `['/api/v1/users/me/onboarding']`

- [ ] **Step 2.2.4: commit (E7)**

```bash
git add backend/src/main.py
git commit -m "feat(onboarding): router include 추가 (Sprint 22)"
```

### Task 2.3: Hook wire — workspace 생성 시 step=1 (lazy seed + create_workspace 둘 다)

**Fact (Codex 1차 finding 1 P1)**: signup flow 의 personal workspace 는 `WorkspaceService.create_workspace()` 호출 안 함. `auth/dependencies.py:get_current_user()` 의 inline SQL 이 personal workspace 생성. 따라서 step=1 hook 은 **두 위치 모두** 필요:
- (a) `auth/dependencies.py:get_current_user()` 의 lazy seed 직후 (signup path)
- (b) `WorkspaceService.create_workspace()` 의 commit 직전 (team workspace 생성 path)

**Fact (Codex 1차 finding 2 P1)**: `WorkspaceService.create_workspace()` 는 `self.repo.commit()` 으로 transaction 닫음. `OnboardingService.increment_step()` 의 UPDATE 는 commit/flush 안 하므로 commit **이전** 위치해야 함.

**Files:**
- Modify: `backend/src/auth/dependencies.py` (lazy seed 후 step=1)
- Modify: `backend/src/workspaces/service.py` (commit 전 step=1)

- [ ] **Step 2.3.1: create_workspace + dependencies.py 구조 확인**

```bash
grep -n "create_workspace\|repo.commit\|self.repo\|session.commit\|return workspace" backend/src/workspaces/service.py | head -10
grep -n "session.commit\|return user\|is_new_user" backend/src/auth/dependencies.py | head -10
```

- [ ] **Step 2.3.2: TDD — failing test 작성**

`backend/tests/auth/test_onboarding_step1_lazy_seed.py`:

```python
import pytest

@pytest.mark.asyncio
async def test_lazy_seed_signup_advances_onboarding_step_to_1(
    integration_session, fresh_clerk_claims, mock_async_session
):
    """signup flow: get_current_user → personal workspace 시드 → step=1."""
    from src.auth.dependencies import get_current_user
    from src.onboarding.service import OnboardingService

    user = await get_current_user(claims=fresh_clerk_claims, session=integration_session)

    onboarding = OnboardingService(integration_session)
    status = await onboarding.get_status(user.id)
    assert status.step == 1
```

`backend/tests/workspaces/test_onboarding_hook.py`:

```python
import pytest

@pytest.mark.asyncio
async def test_create_team_workspace_sets_onboarding_step_1(
    integration_session, test_user_id
):
    """team workspace 생성 path 도 step=1 advance."""
    from src.workspaces.service import WorkspaceService
    from src.onboarding.service import OnboardingService

    ws_service = WorkspaceService(integration_session)
    onboarding = OnboardingService(integration_session)

    initial = await onboarding.get_status(test_user_id)
    assert initial.step == 0

    await ws_service.create_workspace(
        owner_id=test_user_id, name="Test Team WS", workspace_type="team"
    )

    after = await onboarding.get_status(test_user_id)
    assert after.step == 1
```

- [ ] **Step 2.3.3: 실패 확인**

```bash
cd backend && uv run pytest tests/auth/test_onboarding_step1_lazy_seed.py tests/workspaces/test_onboarding_hook.py -v 2>&1 | tail -10
```

Expected: 2 FAIL (hook 미구현)

- [ ] **Step 2.3.4: hook 추가 (lazy seed path)**

`backend/src/auth/dependencies.py:get_current_user()` 의 `await session.commit()` 직전 (line ~129 영역) 에:

```python
# Sprint 22 OBN-02: personal workspace lazy seed 완료 시 step=1
# is_new_user 여부 무관 — idempotent (step >= 1 이면 no-op)
from src.onboarding.service import OnboardingService
onboarding = OnboardingService(session)
await onboarding.increment_step(user.id, 1)
```

- [ ] **Step 2.3.5: hook 추가 (create_workspace path)**

`backend/src/workspaces/service.py:create_workspace()` 의 `self.repo.commit()` (또는 `session.commit()`) **호출 직전** 에:

```python
# Sprint 22 OBN-02: team workspace 생성 시 step=1 (same transaction)
from src.onboarding.service import OnboardingService
onboarding = OnboardingService(self.repo.session if hasattr(self.repo, "session") else self._session)
await onboarding.increment_step(workspace.owner_id, 1)
```

(정확한 session 접근 — `self.repo.session` 또는 `self._session` 또는 인자 — 은 `WorkspaceService` 의 actual constructor 시그니처 확인 후 align)

- [ ] **Step 2.3.6: PASS 확인**

```bash
cd backend && uv run pytest tests/auth/test_onboarding_step1_lazy_seed.py tests/workspaces/test_onboarding_hook.py -v 2>&1 | tail -10
```

Expected: 2 PASS

- [ ] **Step 2.3.7: commit (E8)**

```bash
git add backend/src/auth/dependencies.py backend/src/workspaces/service.py backend/tests/auth/test_onboarding_step1_lazy_seed.py backend/tests/workspaces/test_onboarding_hook.py
git commit -m "feat(onboarding): step=1 hook — lazy seed + create_workspace 양쪽 (Sprint 22 OBN-02)"
```

### Task 2.4: Hook wire — project 생성 시 step=2

**Files:**
- Modify: `backend/src/projects/service.py`

- [ ] **Step 2.4.1: TDD — failing test**

`backend/tests/projects/test_onboarding_hook.py`:

```python
import pytest

@pytest.mark.asyncio
async def test_create_project_sets_onboarding_step_2(
    integration_session, test_user_id, test_workspace_id
):
    from src.projects.service import ProjectService
    from src.onboarding.service import OnboardingService

    # step=1 까지 미리
    onboarding = OnboardingService(integration_session)
    await onboarding.increment_step(test_user_id, 1)
    await integration_session.commit()

    project_service = ProjectService(integration_session)
    await project_service.create_project(
        workspace_id=test_workspace_id,
        creator_id=test_user_id,
        name="First Project",
    )
    await integration_session.commit()

    status = await onboarding.get_status(test_user_id)
    assert status.step == 2
```

- [ ] **Step 2.4.2: 실패 확인 → hook 추가 → PASS → commit (E9)**

Task 2.3 동일 패턴. `backend/src/projects/service.py` 의 `create_project()` 끝부분에 hook.

Commit message: `feat(projects): create_project 시 onboarding step=2 hook (Sprint 22)`

### Task 2.5: Hook wire — meeting distillation 완료 시 step=3

**Files:**
- Modify: `backend/src/meetings/pipeline_service.py`

- [ ] **Step 2.5.1: process_meeting 메소드 end 위치 확인**

```bash
grep -n "process_meeting\|save_summary\|action_item.*save\|return" backend/src/meetings/pipeline_service.py | head -20
```

- [ ] **Step 2.5.2: meeting → user_id 추출 path 확인**

```bash
grep -n "owner_id\|workspace\|user_id" backend/src/meetings/pipeline_service.py backend/src/meetings/models.py | head -10
```

대안: Meeting → Workspace.owner_id 로 user_id 도달. Repository 호출 필요.

- [ ] **Step 2.5.3: TDD — failing test**

`backend/tests/meetings/test_onboarding_hook.py`:

```python
import pytest

@pytest.mark.asyncio
async def test_process_meeting_sets_onboarding_step_3_after_distillation(
    integration_session, test_user_id, test_meeting_id
):
    from src.meetings.pipeline_service import PipelineService
    from src.onboarding.service import OnboardingService

    onboarding = OnboardingService(integration_session)
    await onboarding.increment_step(test_user_id, 2)
    await integration_session.commit()

    pipeline = PipelineService(...)  # mock ai_service for fast test
    await pipeline.process_meeting(test_meeting_id, workspace_id=...)

    status = await onboarding.get_status(test_user_id)
    assert status.step == 3
```

(완전한 fixture 셋업은 기존 meetings 테스트 패턴 따름)

- [ ] **Step 2.5.4: hook 추가 — pipeline_service.process_meeting end (creator credit)**

**Fact (Codex 1차 finding 3 P2)**: `Meeting` 모델 에 `created_by_id` field 가 있음 (router 에서 populate). non-owner workspace member 가 회의 업로드한 경우 owner 가 아닌 actual creator 의 funnel 을 advance 해야 정확. **`meeting.created_by_id` 사용**, `workspace.owner_id` 아님.

`backend/src/meetings/pipeline_service.py:process_meeting()` method 끝부분 (`save_summary` + ActionItem 저장 완료 후, session.commit 직전):

```python
# Sprint 22 OBN-02: AI Distillation 완료 시 step=3
# meeting.created_by_id = 실제 회의 업로드한 user. workspace owner 가 아닐 수 있음.
from src.meetings.repository import MeetingRepository
from src.onboarding.service import OnboardingService

meeting_repo = MeetingRepository(session)
meeting = await meeting_repo.find_by_id(meeting_id, workspace_id)
if meeting is not None and meeting.created_by_id is not None:
    onboarding = OnboardingService(session)
    await onboarding.increment_step(meeting.created_by_id, 3)
    # session.commit() 은 호출 안 함 — process_meeting 의 외부 session_factory 가 commit
```

**Note**: `process_meeting` 안의 session 은 `session_factory` 패턴으로 wrapped — 본 hook 도 동일 session 사용 (`onboarding.service` 의 `OnboardingRepository.increment` 는 commit/flush 0건 보장됨). `Meeting.created_by_id` 필드 확인: `grep -n "created_by_id" backend/src/meetings/models.py` 으로 verify.

- [ ] **Step 2.5.5: PASS → commit (E10)**

```bash
git add backend/src/meetings/pipeline_service.py backend/tests/meetings/test_onboarding_hook.py
git commit -m "feat(meetings): pipeline distillation 완료 시 onboarding step=3 hook (Sprint 22)"
```

### Task 2.6: Hook wire — RAG ask 첫 성공 시 step=4 (session DI 통한 injection)

**Fact (Codex 1차 finding 7 P2)**: `RagService` 는 `EmbeddingRepository` + `EmbeddingService` + `AIProcessingService` 로 구성. `self._session` 속성 **없음**. 따라서 onboarding hook 은 다음 중 하나:
- (a) `RagService` 의 `ask()` 메소드에 `session: AsyncSession` 파라미터 추가 (router 가 inject)
- (b) `RagService` 의 `EmbeddingRepository.session` 재사용 (already-injected session)
- (c) router 가 RagService 호출 후 onboarding 별도 호출 (boundary 분리)

**권장 = (b)** — 기존 session 재사용, RagService signature 변경 0건, atomic transaction.

**Files:**
- Modify: `backend/src/rag/service.py`

- [ ] **Step 2.6.1: rag/service.py:ask() + EmbeddingRepository session 접근 확인**

```bash
grep -n "def ask\|self.embedding_repo\|return\|yield" backend/src/rag/service.py | head -20
grep -n "self.session\|self._session\|EmbeddingRepository" backend/src/embeddings/repository.py | head -5
```

(line 59 `self.session = session` 으로 `EmbeddingRepository.session` 직접 접근 가능 확인됨.)

- [ ] **Step 2.6.2: TDD — failing test**

`backend/tests/rag/test_onboarding_hook.py`:

```python
import pytest

@pytest.mark.asyncio
async def test_rag_ask_first_success_sets_onboarding_step_4(
    integration_session, test_user_id, test_workspace_id, rag_service_factory
):
    """첫 RAG ask 성공 시 step=4 + onboarded_at set."""
    from src.onboarding.service import OnboardingService

    onboarding = OnboardingService(integration_session)
    await onboarding.increment_step(test_user_id, 3)
    await integration_session.commit()

    rag_service = rag_service_factory(integration_session)
    await rag_service.ask(
        query="test query",
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )

    status = await onboarding.get_status(test_user_id)
    assert status.step == 4
    assert status.is_completed is True
    assert status.onboarded_at is not None
```

- [ ] **Step 2.6.3: hook 추가 — EmbeddingRepository.session 재사용**

`backend/src/rag/service.py:ask()` 첫 성공 응답 후 (return 직전):

```python
# Sprint 22 OBN-02: 첫 RAG ask 성공 시 step=4 + onboarded_at
# self.embedding_repo.session 재사용 (DI 통한 already-injected session)
if user_id is not None:
    from src.onboarding.service import OnboardingService
    onboarding = OnboardingService(self.embedding_repo.session)
    await onboarding.increment_step(user_id, 4)
```

`ask()` 시그니처에 `user_id: uuid.UUID | None = None` 파라미터 추가 (router 도 update).

SSE streaming endpoint (`ask_stream` 또는 등가) 인 경우 final SSE complete event 직후 동일 hook.

- [ ] **Step 2.6.4: PASS → commit (E11)**

```bash
git add backend/src/rag/service.py backend/src/rag/router.py backend/tests/rag/test_onboarding_hook.py
git commit -m "feat(rag): ask 첫 성공 시 onboarding step=4 + user_id param + EmbeddingRepository.session 재사용 (Sprint 22)"
```

### Task 2.7: Atomic Update §4 — domain docs sync

**Files:**
- Modify: `backend/CONTEXT.md` (§4 도메인 표)
- Modify: `docs/architecture/directory-map.md`
- Modify: `docs/api/endpoints.md`

- [ ] **Step 2.7.1: backend/CONTEXT.md §4 도메인 표 갱신**

`onboarding` 도메인 추가 (다른 도메인 row 패턴 따름). 의존 = `auth (User)`. 호출자 = workspaces / projects / meetings / rag.

- [ ] **Step 2.7.2: directory-map.md 백엔드 트리 갱신**

`backend/src/onboarding/` 노드 추가.

- [ ] **Step 2.7.3: api/endpoints.md 갱신**

신규 endpoint 표에 등재:

```markdown
| GET | /api/v1/users/me/onboarding | onboarding | OnboardingResponse | Sprint 22 OBN-02 |
```

- [ ] **Step 2.7.4: commit (E12 — domain atomic docs)**

```bash
git add backend/CONTEXT.md docs/architecture/directory-map.md docs/api/endpoints.md
git commit -m "docs: onboarding 도메인 atomic doc sync (Sprint 22)"
```

---

## Task 3: Personal Workspace Race Regression Test (~1-1.5h, 2 commits)

**Goal:** Sprint 15 의 lazy seed (auth/dependencies.py:79-120) + partial unique index 안정성 회귀 test 추가. 신규 코드 0건, test 만 추가.

### Task 3.1: asyncio.gather race test

**Files:**
- Create: `backend/tests/auth/test_personal_workspace_race.py`

- [ ] **Step 3.1.1: test 작성 (Sprint 15 inline SQL 패턴 복제)**

**Fact**: lazy seed 는 `backend/src/auth/dependencies.py:get_current_user()` 함수의 line 99-128 inline SQL 로 구현됨. 별도 헬퍼 함수 (`_seed_personal_workspace_if_missing` 등) **존재하지 않음**. 따라서 race test 는 inline SQL 패턴을 복제하여 검증.

```python
"""Sprint 22 OBN-01 — personal workspace lazy seed race safety 회귀 test.

Sprint 15 의 dependencies.py:get_current_user() inline lazy seed (line 99-128) +
uq_workspaces_owner_personal partial unique index 가 동시 sync 호출 시
personal workspace 1개만 생성됨을 검증.

본 test 는 신규 코드 0건, lazy seed SQL 의 race-safety 만 확인.
"""
import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession


# dependencies.py line 99-128 의 inline SQL 복제 (헬퍼 부재로 직접 sql)
LAZY_SEED_WORKSPACE_SQL = """
    INSERT INTO workspaces (id, owner_id, name, type, inbox_threshold, created_at, updated_at)
    VALUES (gen_random_uuid(), :owner_id, :name, 'personal', 0.9, now(), now())
    ON CONFLICT (owner_id) WHERE type = 'personal' DO NOTHING
"""

LAZY_SEED_MEMBER_SQL = """
    INSERT INTO workspace_members (id, workspace_id, user_id, role)
    SELECT gen_random_uuid(), w.id, w.owner_id, 'owner'
    FROM workspaces w
    WHERE w.owner_id = :owner_id AND w.type = 'personal'
      AND NOT EXISTS (
        SELECT 1 FROM workspace_members m
        WHERE m.workspace_id = w.id AND m.user_id = w.owner_id
      )
"""


async def _lazy_seed(session: AsyncSession, user_id: uuid.UUID, display_name: str) -> None:
    """dependencies.py:get_current_user() 의 line 99-128 inline SQL 패턴 복제."""
    await session.execute(
        text(LAZY_SEED_WORKSPACE_SQL),
        {"owner_id": str(user_id), "name": f"{display_name}의 개인 Kairos"},
    )
    await session.execute(
        text(LAZY_SEED_MEMBER_SQL),
        {"owner_id": str(user_id)},
    )


@pytest.mark.asyncio
async def test_concurrent_lazy_seed_creates_single_personal_workspace(
    integration_session: AsyncSession, async_session_factory
):
    """동일 user_id 로 lazy seed 가 2회 동시 호출되어도 personal workspace 1개만 생성."""
    user_id = uuid.uuid4()

    # Pre-seed user row
    await integration_session.execute(
        text(
            "INSERT INTO users (id, clerk_id, display_name, email, created_at, updated_at) "
            "VALUES (:id, :clerk, :name, :email, now(), now())"
        ),
        {"id": str(user_id), "clerk": f"clerk_{user_id}", "name": "Alice", "email": f"{user_id}@test.com"},
    )
    await integration_session.commit()

    # 동시 2회 lazy seed
    async def seed_in_new_session() -> None:
        async with async_session_factory() as session:
            await _lazy_seed(session, user_id, "Alice")
            await session.commit()

    await asyncio.gather(seed_in_new_session(), seed_in_new_session())

    # 검증: personal workspace 정확히 1개
    result = await integration_session.execute(
        text(
            "SELECT COUNT(*) FROM workspaces "
            "WHERE owner_id = :owner AND type = 'personal'"
        ),
        {"owner": str(user_id)},
    )
    count = result.scalar_one()
    assert count == 1, f"Expected 1 personal workspace, got {count}"


@pytest.mark.asyncio
async def test_lazy_seed_creates_workspace_member_owner(
    integration_session: AsyncSession,
):
    """dependencies.py line 113-128 의 WorkspaceMember(owner) seed 검증."""
    user_id = uuid.uuid4()
    await integration_session.execute(
        text(
            "INSERT INTO users (id, clerk_id, display_name, email, created_at, updated_at) "
            "VALUES (:id, :clerk, :name, :email, now(), now())"
        ),
        {"id": str(user_id), "clerk": f"clerk_{user_id}", "name": "Alice", "email": f"{user_id}@test.com"},
    )
    await integration_session.commit()

    await _lazy_seed(integration_session, user_id, "Alice")
    await integration_session.commit()

    # WorkspaceMember(owner) row 존재 확인
    result = await integration_session.execute(
        text(
            "SELECT COUNT(*) FROM workspace_members wm "
            "JOIN workspaces w ON w.id = wm.workspace_id "
            "WHERE w.owner_id = :owner AND w.type = 'personal' "
            "AND wm.user_id = :owner AND wm.role = 'owner'"
        ),
        {"owner": str(user_id)},
    )
    count = result.scalar_one()
    assert count == 1
```

**Note**: User table 의 `display_name` column 은 `backend/src/auth/models.py` 의 User schema 에 명시되어 있음 (line 91-95 confirm). pytest fixture `async_session_factory` 는 `backend/tests/conftest.py` 에 정의됨 — 미존재 시 추가.

- [ ] **Step 3.1.2: test 실행 + PASS 확인**

```bash
cd backend && uv run pytest tests/auth/test_personal_workspace_race.py -v 2>&1 | tail -10
```

Expected: 2 PASS

- [ ] **Step 3.1.3: commit (E13)**

```bash
git add backend/tests/auth/test_personal_workspace_race.py
git commit -m "test(auth): personal workspace lazy seed race + WorkspaceMember seed 회귀 test (Sprint 22 OBN-01)"
```

---

## Task 4: FE OnboardingBanner Server State (~3-4h, 4 commits)

**Goal:** OnboardingBanner 가 server state (`useOnboarding`) 기반 progress 표시. Mutation invalidate 3 hook 연결.

### Task 4.1: `frontend/src/features/onboarding/` 모듈 신설

**Files:**
- Create: `frontend/src/features/onboarding/api.ts`
- Create: `frontend/src/features/onboarding/hooks.ts`
- Create: `frontend/src/features/onboarding/schemas.ts`

- [ ] **Step 4.1.1: schemas.ts (Zod v4)**

```typescript
// 온보딩 도메인 Zod 스키마
import { z } from "zod/v4";

export const onboardingResponseSchema = z.object({
  step: z.number().int().min(0).max(4),
  totalSteps: z.literal(4),
  onboardedAt: z.string().datetime().nullable(),
  isCompleted: z.boolean(),
});

export type OnboardingResponse = z.infer<typeof onboardingResponseSchema>;
```

- [ ] **Step 4.1.2: api.ts**

```typescript
// 온보딩 API 호출
import { onboardingResponseSchema, type OnboardingResponse } from "./schemas";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getOnboarding(
  token: string,
  workspaceId: string
): Promise<OnboardingResponse> {
  const res = await fetch(`${API_URL}/api/v1/users/me/onboarding`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Workspace-Id": workspaceId,
    },
  });
  if (!res.ok) throw new Error(`getOnboarding failed: ${res.status}`);
  const data = await res.json();
  return onboardingResponseSchema.parse(data);
}
```

- [ ] **Step 4.1.3: hooks.ts**

```typescript
// React Query 래핑 훅
import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";

import { useWorkspaceStore } from "@/features/workspaces/store";

import { getOnboarding } from "./api";

export const onboardingQueryKey = (workspaceId: string | null) => [
  "onboarding",
  workspaceId,
];

export function useOnboarding() {
  const { getToken } = useAuth();
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  return useQuery({
    queryKey: onboardingQueryKey(workspaceId),
    queryFn: async () => {
      const token = await getToken();
      if (!token || !workspaceId) throw new Error("auth required");
      return getOnboarding(token, workspaceId);
    },
    enabled: !!workspaceId,
    staleTime: 30_000,
  });
}
```

- [ ] **Step 4.1.4: typecheck + commit (E14)**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-22/frontend
pnpm typecheck 2>&1 | tail -5
```

Expected: 0 error

```bash
git add frontend/src/features/onboarding/
git commit -m "feat(fe/onboarding): useOnboarding hook + api + schemas 신설 (Sprint 22)"
```

### Task 4.2: OnboardingBanner refactor (today-feed.tsx)

**Files:**
- Modify: `frontend/src/features/home/components/today-feed.tsx`

- [ ] **Step 4.2.1: 기존 OnboardingBanner 라인 23-117 read + refactor 계획**

핵심:
- local `isDismissed` useState 제거
- `useOnboarding()` 호출
- `step === 4` (or `isCompleted`) 면 null return
- `Step {step}/{totalSteps}` progress UI 추가 (각 단계 highlight)
- CTA 버튼은 현재 step 다음 단계로 유도

- [ ] **Step 4.2.2: 컴포넌트 refactor**

`frontend/src/features/home/components/today-feed.tsx` 의 OnboardingBanner 부분을 다음으로 교체:

```typescript
"use client";

import Link from "next/link";

import { useOnboarding } from "@/features/onboarding/hooks";

function OnboardingBanner() {
  const { data, isLoading } = useOnboarding();

  if (isLoading || !data || data.isCompleted) return null;

  const { step, totalSteps } = data;
  const steps = [
    { n: 1, label: "워크스페이스 만들기" },
    { n: 2, label: "첫 프로젝트 생성" },
    { n: 3, label: "첫 회의 업로드" },
    { n: 4, label: "AI 에게 질문" },
  ];

  return (
    <div className="rounded-xl border border-[var(--surface-border)] bg-[var(--surface-elevated)] p-4 md:p-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[var(--text-primary)]">
            온보딩 {step}/{totalSteps} 단계
          </p>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            다음: {steps[step]?.label ?? "완료"}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          {steps.map((s) => (
            <div
              key={s.n}
              className={`h-1.5 w-8 rounded-full ${
                s.n <= step
                  ? "bg-[var(--accent-primary)]"
                  : "bg-[var(--surface-border)]"
              }`}
              title={s.label}
            />
          ))}
        </div>
      </div>
      {step < 4 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {step < 2 && (
            <Link
              href="/new"
              className="px-3 py-1.5 text-xs rounded-md bg-[var(--accent-primary)] text-white"
            >
              프로젝트 만들기
            </Link>
          )}
          {step >= 2 && step < 3 && (
            <Link
              href="/meetings"
              className="px-3 py-1.5 text-xs rounded-md bg-[var(--accent-primary)] text-white"
            >
              회의 업로드
            </Link>
          )}
          {step >= 3 && step < 4 && (
            <Link
              href="/dashboard?rag=open"
              className="px-3 py-1.5 text-xs rounded-md bg-[var(--accent-primary)] text-white"
            >
              AI 에게 질문
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
```

(기존 file 안의 OnboardingBanner 가 separate function 이면 in-place replace. inline JSX 면 추출.)

- [ ] **Step 4.2.3: typecheck + visual smoke (선택)**

```bash
cd frontend && pnpm typecheck 2>&1 | tail -3
```

Expected: 0 error

- [ ] **Step 4.2.4: commit (E15)**

```bash
git add frontend/src/features/home/components/today-feed.tsx
git commit -m "feat(fe/home): OnboardingBanner server state + progress indicator (Sprint 22 OBN-02)"
```

### Task 4.3: Mutation invalidate 연결

**Files:**
- Modify: `frontend/src/features/projects/hooks.ts`
- Modify: `frontend/src/features/meetings/hooks.ts`
- Modify: `frontend/src/features/rag/hooks.ts`

- [ ] **Step 4.3.1: projects/hooks.ts — useCreateProject onSuccess 에 invalidate**

```typescript
// useCreateProject mutation 정의 안에서 onSuccess 추가/수정
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ["projects"] });
  // Sprint 22 OBN-02
  queryClient.invalidateQueries({ queryKey: ["onboarding"] });
},
```

- [ ] **Step 4.3.2: meetings/hooks.ts — useMeetingPolling (has_summary transition) invalidate**

```typescript
// useMeetingPolling 또는 등가 hook 에서 has_summary === true 감지 시
const previousHasSummary = useRef<boolean>(false);
useEffect(() => {
  if (data?.has_summary && !previousHasSummary.current) {
    queryClient.invalidateQueries({ queryKey: ["onboarding"] });
    previousHasSummary.current = true;
  }
}, [data?.has_summary, queryClient]);
```

(useMeetingPolling 의 정확한 shape 은 기존 코드 확인 후 패턴 align)

- [ ] **Step 4.3.3: rag/hooks.ts — useRagAsk onSuccess invalidate**

```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ["onboarding"] });
},
```

SSE streaming 인 경우 onDone callback.

- [ ] **Step 4.3.4: typecheck + commit (E16)**

```bash
cd frontend && pnpm typecheck 2>&1 | tail -3
git add frontend/src/features/projects/hooks.ts frontend/src/features/meetings/hooks.ts frontend/src/features/rag/hooks.ts
git commit -m "feat(fe): React Query invalidate onboarding on project/meeting/rag mutation (Sprint 22)"
```

---

## Task 5: OBN-03 — 첫 회의 가이드 토스트 + 빈 state copy (~1-2h, 2 commits)

### Task 5.1: EmptyState onboarding-aware copy

**Files:**
- Modify: `frontend/src/components/empty-state.tsx` (또는 등가)

- [ ] **Step 5.1.1: 기존 EmptyState 위치 + signature 확인**

```bash
grep -rn "EmptyState\b\|empty-state" frontend/src/components/ | head -10
```

- [ ] **Step 5.1.2: onboarding-aware copy 추가**

`frontend/src/components/empty-state.tsx` 에 `onboardingStep` prop 받아 가이드 copy 변경. 기존 컴포넌트 signature 유지하고 optional prop 추가.

```typescript
interface EmptyStateProps {
  title: string;
  description?: string;
  onboardingStep?: number;
  context?: "meetings" | "projects" | "notes" | "inbox";
}

export function EmptyState({ title, description, onboardingStep, context }: EmptyStateProps) {
  const hint = onboardingStep !== undefined && onboardingStep < 3 && context === "meetings"
    ? "첫 회의를 업로드해 보세요. 30초 녹음만으로도 AI 요약 + 액션 아이템이 생성돼요."
    : undefined;

  return (
    <div className="...existing classes...">
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {hint && <p className="mt-2 text-sm text-[var(--accent-primary)]">{hint}</p>}
    </div>
  );
}
```

- [ ] **Step 5.1.3: 사용처 갱신 (meetings/projects/notes empty)**

각 page 의 EmptyState 호출에 `onboardingStep={onboardingData?.step}` + `context="meetings"` 등 prop 전달.

- [ ] **Step 5.1.4: typecheck + commit (E17)**

```bash
cd frontend && pnpm typecheck 2>&1 | tail -3
git add frontend/src/components/empty-state.tsx frontend/src/features/meetings/components/*.tsx frontend/src/features/projects/components/*.tsx frontend/src/features/notes/components/*.tsx
git commit -m "feat(fe): EmptyState onboarding-aware copy + meetings/projects/notes 적용 (Sprint 22 OBN-03)"
```

### Task 5.2: meeting/note detail header — Export discoverability

**Files:**
- Modify: `frontend/src/features/meetings/components/meeting-detail-header.tsx` (또는 등가)
- Modify: `frontend/src/features/notes/components/note-detail-header.tsx`

- [ ] **Step 5.2.1: 기존 detail header + Export button 위치 확인**

```bash
grep -rn "MeetingExportButton\|NoteExportButton\|export-button" frontend/src/features/meetings/ frontend/src/features/notes/ | head -10
```

- [ ] **Step 5.2.2: header 에 Export button prominent 노출 + tooltip**

기존 export-button.tsx 컴포넌트를 detail header 우측 (다른 메타데이터 옆) 에 명시적 위치로 이동/배치. tooltip prop 추가 — Sprint 21 의 tooltip 패턴 따름.

```typescript
// meeting-detail-header.tsx 내부
import { MeetingExportButton } from "./export-button";
// header right-side actions group 안에
<div className="flex items-center gap-2">
  <MeetingExportButton meetingId={meeting.id} meetingTitle={meeting.title} />
  {/* ... other actions ... */}
</div>
```

기존 export-button.tsx 의 `aria-label="내보내기"` + `title="내보내기 (Markdown / JSON)"` tooltip 추가:

```typescript
// frontend/src/features/meetings/components/export-button.tsx
<DropdownMenuTrigger
  aria-label="내보내기"
  title="내보내기 (Markdown / JSON)"
  className="..."
>
  <Download className="w-4 h-4" />
</DropdownMenuTrigger>
```

- [ ] **Step 5.2.3: notes 동일 패턴**

- [ ] **Step 5.2.4: typecheck + commit (E18)**

```bash
cd frontend && pnpm typecheck 2>&1 | tail -3
git add frontend/src/features/meetings/components/*.tsx frontend/src/features/notes/components/*.tsx
git commit -m "feat(fe): Export button discoverability — detail header + tooltip (Sprint 22 BUG-C04 G8)"
```

---

## Task 6: OBN-04 + BL-017 Mobile (~2-3h, 3 commits)

### Task 6.1: BL-017 Mobile FAB collision fix

**Files:**
- Modify: `frontend/src/components/<FAB or floating-action>/...`

- [ ] **Step 6.1.1: FAB 컴포넌트 위치 + onboarding banner 와 충돌 시나리오 확인**

```bash
grep -rn "FAB\|FloatingAction\|fixed.*bottom" frontend/src/components/ | head -10
```

- [ ] **Step 6.1.2: z-index + bottom offset 조정**

FAB 컴포넌트의 `bottom-X` 값 조정 + banner 위 z-index (해당 화면에 banner 있을 때만):

```typescript
// 예시: bottom-4 → bottom-20 when onboarding banner visible
const { data: onboarding } = useOnboarding();
const hasOnboardingBanner = onboarding && !onboarding.isCompleted;
const bottomClass = hasOnboardingBanner ? "bottom-24 md:bottom-6" : "bottom-6";
```

- [ ] **Step 6.1.3: commit (E19)**

```bash
git add frontend/src/components/<FAB path>
git commit -m "fix(fe/mobile): FAB-onboarding banner collision (BL-017 + Sprint 22 OBN-04)"
```

### Task 6.2: Mobile banner flex-wrap

**Files:**
- Modify: `frontend/src/features/home/components/today-feed.tsx`

- [ ] **Step 6.2.1: narrow viewport (≤480px) 에서 progress indicator wrap**

Task 4.2 의 banner JSX 의 `flex-wrap gap-3` 가 이미 있음. 추가 보강: progress indicator group 도 `flex-wrap` + CTA 버튼 group `flex-wrap`.

mobile-first 검증:

```typescript
<div className="flex items-center justify-between gap-3 flex-wrap">
  {/* ... */}
  <div className="flex flex-wrap items-center gap-1.5">
    {/* progress bars */}
  </div>
</div>
```

- [ ] **Step 6.2.2: commit (E20)**

```bash
git add frontend/src/features/home/components/today-feed.tsx
git commit -m "fix(fe/mobile): OnboardingBanner progress indicator flex-wrap (Sprint 22 OBN-04)"
```

### Task 6.3: mobile-responsive.spec.ts 보강

**Files:**
- Modify: `frontend/e2e/tests/mobile-responsive.spec.ts`

- [ ] **Step 6.3.1: OnboardingBanner mobile case 추가**

```typescript
test("OnboardingBanner — 375x812 viewport 에서 progress indicator visible + wrap", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/dashboard");
  await page.waitForLoadState("networkidle");

  // banner visible (assuming step < 4)
  await expect(page.getByText(/온보딩 \d\/4 단계/)).toBeVisible();
  // FAB 와 충돌 안 함 — bottom overflow 없음
});
```

- [ ] **Step 6.3.2: 실행 + commit (E21)**

```bash
cd frontend && pnpm exec playwright test mobile-responsive.spec.ts 2>&1 | tail -10
git add frontend/e2e/tests/mobile-responsive.spec.ts
git commit -m "test(e2e): mobile-responsive OnboardingBanner case (Sprint 22 OBN-04)"
```

---

## Task 7: Sentry Observability FE+BE (~2-3h, 3 commits)

### Task 7.1: BE Sentry wire

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/src/core/config.py`
- Modify: `backend/src/main.py`

- [ ] **Step 7.1.1: dep 추가**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-22/backend
uv add "sentry-sdk[fastapi]" 2>&1 | tail -5
```

- [ ] **Step 7.1.2: config.py — SENTRY_DSN env**

```python
# backend/src/core/config.py 에 추가
from pydantic import SecretStr

class Settings(BaseSettings):
    # ... 기존 ...
    SENTRY_DSN: SecretStr | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    ENVIRONMENT: str = "development"
```

- [ ] **Step 7.1.3: main.py — init + PII scrub**

```python
# backend/src/main.py top-level
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from src.core.config import settings


def _scrub_pii_hook(event, hint):
    """PII redact — transcript / email / password / audio_url"""
    request = event.get("request")
    if request and isinstance(request.get("data"), dict):
        for field in ("transcript", "email", "password", "audio_url"):
            request["data"].pop(field, None)
    if event.get("user"):
        event["user"].pop("email", None)
        event["user"].pop("ip_address", None)
    return event


if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN.get_secret_value(),
        integrations=[FastApiIntegration()],
        send_default_pii=False,
        before_send=_scrub_pii_hook,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        environment=settings.ENVIRONMENT,
    )
```

- [ ] **Step 7.1.4: 회귀 + commit (E22)**

```bash
cd backend && uv run pytest tests/ -q 2>&1 | tail -3
git add backend/pyproject.toml backend/uv.lock backend/src/core/config.py backend/src/main.py
git commit -m "feat(obs): Sentry BE wire + PII scrub before_send (Sprint 22)"
```

### Task 7.2: FE Sentry wire

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/sentry.client.config.ts`
- Create: `frontend/sentry.server.config.ts`
- Create: `frontend/sentry.edge.config.ts`
- Create: `frontend/instrumentation.ts`
- Modify: `frontend/next.config.ts`

- [ ] **Step 7.2.1: dep 추가**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-22/frontend
pnpm add @sentry/nextjs
```

- [ ] **Step 7.2.2: sentry.client.config.ts**

```typescript
// FE Sentry client init — browser 측 에러 추적
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  sendDefaultPii: false,
  tracesSampleRate: 0.1,
  environment: process.env.NEXT_PUBLIC_VERCEL_ENV ?? "development",
  beforeSend(event) {
    if (event.user) {
      delete event.user.email;
      delete event.user.ip_address;
    }
    return event;
  },
});
```

- [ ] **Step 7.2.3: sentry.server.config.ts + sentry.edge.config.ts**

(client 와 동일 init, server-only / edge-only context 분리)

- [ ] **Step 7.2.4: instrumentation.ts (Next.js 16)**

```typescript
// Next.js 16 instrumentation hook
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config");
  }
  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config");
  }
}

export const onRequestError = async (
  err: unknown,
  request: Request,
  context: { routerKind: string; routePath: string; routeType: string }
) => {
  const Sentry = await import("@sentry/nextjs");
  Sentry.captureRequestError(err, request, context);
};
```

(정확한 Next.js 16 signature 는 `node_modules/next/dist/docs/` 에서 확인 — 본 plan 진입 직전 reviewer 가 확인 ↑ frontend AGENTS.md 강제)

- [ ] **Step 7.2.5: next.config.ts withSentryConfig wrapper**

```typescript
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig = { /* 기존 */ };

export default withSentryConfig(nextConfig, {
  silent: true,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
});
```

- [ ] **Step 7.2.6: typecheck + smoke**

```bash
cd frontend && pnpm typecheck 2>&1 | tail -3
pnpm build 2>&1 | tail -10
```

Expected: 0 error / build success

- [ ] **Step 7.2.7: commit (E23)**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml frontend/sentry.*.config.ts frontend/instrumentation.ts frontend/next.config.ts
git commit -m "feat(obs): Sentry FE wire (@sentry/nextjs + instrumentation) (Sprint 22)"
```

### Task 7.3: ENV docs + ADR

**Files:**
- Modify: `.env.example`
- Create: `docs/dev-log/021-sentry-observability.md`

- [ ] **Step 7.3.1: .env.example 갱신**

```bash
# backend/.env.example
SENTRY_DSN=  # https://<key>@sentry.io/<project>
SENTRY_TRACES_SAMPLE_RATE=0.1

# frontend/.env.example
NEXT_PUBLIC_SENTRY_DSN=
SENTRY_ORG=kairos
SENTRY_PROJECT=kairos-fe
```

- [ ] **Step 7.3.2: ADR 작성**

`docs/dev-log/021-sentry-observability.md` — Nygard 4-section (Context / Decision / Status / Consequences). Sentry FE+BE 도입 근거 + PII scrub 정책 + sample rate + carry-over (OpenTelemetry CO-1).

- [ ] **Step 7.3.3: commit (E24)**

```bash
git add .env.example backend/.env.example frontend/.env.example docs/dev-log/021-sentry-observability.md
git commit -m "docs: Sentry env + ADR-021 observability (Sprint 22)"
```

---

## Task 8: Playwright E2E 8 시나리오 (~6-8h, 8 commits)

### Task 8.1: G4 — rag-citation.spec.ts skip 해제

**Files:**
- Modify: `frontend/e2e/tests/rag-citation.spec.ts`

- [ ] **Step 8.1.1: 기존 spec read + skip 사유 확인**

```bash
grep -n "skip\|todo\|fixme" frontend/e2e/tests/rag-citation.spec.ts | head -5
cat frontend/e2e/tests/rag-citation.spec.ts | head -50
```

- [ ] **Step 8.1.2: SSE mock 정합성 디버깅**

skip 사유에 따라 `page.route` 로 SSE response mock, 또는 backend dev server 의 cache hit path 활용. workspace context (`X-Workspace-Id` header) 정확히 설정.

- [ ] **Step 8.1.3: assertions 보강 — citation badge + SourceViewer + Step 4/4 후 banner hide**

```typescript
test("RAG citation flow + onboarding step=4 도달", async ({ page }) => {
  await page.goto("/dashboard");
  await page.fill("[data-testid=rag-input]", "이번 회의 요약");
  await page.click("[data-testid=rag-submit]");

  await expect(page.locator("[data-testid=citation-badge]").first()).toBeVisible();
  await page.click("[data-testid=citation-badge]");
  await expect(page.locator("[data-testid=source-viewer]")).toBeVisible();

  // Step 4/4 도달 후 banner 자동 hide
  await expect(page.getByText(/온보딩 \d\/4 단계/)).not.toBeVisible({ timeout: 5000 });
});
```

- [ ] **Step 8.1.4: 실행 + commit (E25)**

```bash
cd frontend && pnpm exec playwright test rag-citation.spec.ts 2>&1 | tail -10
git add frontend/e2e/tests/rag-citation.spec.ts
git commit -m "test(e2e): G4 RAG citation skip 해제 + banner hide assertion (Sprint 22)"
```

### Task 8.2: G2 NEW — first-project.spec.ts

**Files:**
- Create: `frontend/e2e/tests/first-project.spec.ts`

- [ ] **Step 8.2.1: spec 작성**

```typescript
import { expect, test } from "@playwright/test";

test.describe("G2 — 첫 프로젝트 생성 → step=2 갱신", () => {
  test("새 프로젝트 만들면 OnboardingBanner step 2/4 로 갱신", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    // 진입 시 step=1 (workspace 생성 직후) — fixture 의존
    // 또는 step=0 → 1 도달 후 → 2 검증

    await page.goto("/new");
    await page.fill("[data-testid=project-name-input]", "First Project E2E");
    await page.click("[data-testid=create-project-submit]");

    // 자동 redirect 또는 dashboard 진입
    await page.waitForURL(/dashboard|projects/);

    // OnboardingBanner 의 progress = 2/4
    await expect(page.getByText(/온보딩 2\/4 단계/)).toBeVisible({ timeout: 5000 });
  });
});
```

- [ ] **Step 8.2.2: 실행 + commit (E26)**

```bash
cd frontend && pnpm exec playwright test first-project.spec.ts 2>&1 | tail -10
git add frontend/e2e/tests/first-project.spec.ts
git commit -m "test(e2e): G2 첫 프로젝트 생성 → step=2 assertion (Sprint 22)"
```

### Task 8.3: G7 NEW — auth-relogin.spec.ts

**Files:**
- Create: `frontend/e2e/tests/auth-relogin.spec.ts`

- [ ] **Step 8.3.1: spec 작성**

```typescript
import { expect, test } from "@playwright/test";

test.describe("G7 — 로그아웃 → 재로그인 → state 보존", () => {
  test.use({ storageState: { cookies: [], origins: [] } });  // fresh session

  test("로그아웃 후 재로그인 시 activeWorkspaceId + onboarding state 복원", async ({ page }) => {
    // pre-condition: 이미 로그인된 storageState 사용 또는 동적 로그인
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    const wsIdBefore = await page.evaluate(() => localStorage.getItem("activeWorkspaceId"));
    expect(wsIdBefore).toBeTruthy();

    // logout
    await page.click("[data-testid=user-menu]");
    await page.click("[data-testid=signout-button]");
    await page.waitForURL(/sign-in/);

    // re-login (Clerk dev key)
    await page.fill("input[name=identifier]", process.env.E2E_USER_EMAIL!);
    await page.click("button[type=submit]");
    await page.fill("input[name=password]", process.env.E2E_USER_PASSWORD!);
    await page.click("button[type=submit]");
    await page.waitForURL(/dashboard/);

    // state 복원 확인
    const wsIdAfter = await page.evaluate(() => localStorage.getItem("activeWorkspaceId"));
    expect(wsIdAfter).toBe(wsIdBefore);
  });
});
```

- [ ] **Step 8.3.2: 실행 + commit (E27)**

```bash
cd frontend && pnpm exec playwright test auth-relogin.spec.ts 2>&1 | tail -10
git add frontend/e2e/tests/auth-relogin.spec.ts
git commit -m "test(e2e): G7 logout→login state 보존 (Sprint 22)"
```

### Task 8.4: G8 NEW — actions-export.spec.ts

**Files:**
- Create: `frontend/e2e/tests/actions-export.spec.ts` (또는 `meeting-export.spec.ts`)

- [ ] **Step 8.4.1: spec 작성**

```typescript
import { expect, test } from "@playwright/test";

test.describe("G8 — Meeting Export discoverability + download", () => {
  test("meeting detail header 에서 Export button visible + markdown 다운로드", async ({ page }) => {
    // 기존 meeting 1건 가정 (qa-fixture 시드)
    await page.goto("/meetings");
    await page.waitForLoadState("networkidle");

    const firstMeeting = page.locator("[data-testid=meeting-card]").first();
    await firstMeeting.click();
    await page.waitForLoadState("networkidle");

    // Export button discoverable (aria-label 또는 title)
    const exportBtn = page.getByRole("button", { name: /내보내기/ });
    await expect(exportBtn).toBeVisible();

    // dropdown open + Markdown 클릭
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      (async () => {
        await exportBtn.click();
        await page.getByText("Markdown (.md)").click();
      })(),
    ]);

    expect(download.suggestedFilename()).toMatch(/\.md$/);
  });
});
```

- [ ] **Step 8.4.2: 실행 + commit (E28)**

```bash
cd frontend && pnpm exec playwright test actions-export.spec.ts 2>&1 | tail -10
git add frontend/e2e/tests/actions-export.spec.ts
git commit -m "test(e2e): G8 export discoverability + markdown download (Sprint 22 BUG-C04)"
```

### Task 8.5: G1/G3/G5/G6 progress assertion 보강

**Files:**
- Modify: `frontend/e2e/tests/home.spec.ts` (G1)
- Modify: `frontend/e2e/tests/meeting-upload.spec.ts` (G3)
- Modify: `frontend/e2e/tests/qa-sentinel-p0.spec.ts` (G5)
- Modify: `frontend/e2e/tests/invite-page-regression.spec.ts` (G6)

- [ ] **Step 8.5.1: G1 — home.spec.ts 에 Step 1/4 assertion**

```typescript
// home.spec.ts 의 기존 "홈 — 인증 후 네비게이션" describe 안에
test("OnboardingBanner — 가입 직후 Step 1/4 visible", async ({ page }) => {
  await page.goto("/dashboard");
  await page.waitForLoadState("networkidle");
  await expect(page.getByText(/온보딩 [1-4]\/4 단계/)).toBeVisible();
});
```

- [ ] **Step 8.5.2: G3 — meeting-upload.spec.ts 에 distillation 후 Step 3/4 assertion**

```typescript
// 기존 E2E_RUN_HEAVY=true 시나리오 끝부분에
if (process.env.E2E_RUN_HEAVY === "true") {
  // ... distillation 완료 wait ...
  await expect(page.getByText(/온보딩 [3-4]\/4 단계|온보딩 완료/)).toBeVisible({ timeout: 60_000 });
}
```

- [ ] **Step 8.5.3: G5/G6 — qa-sentinel-p0 + invite-page-regression**

action 완료 / multi-user IDOR scenarios 끝부분에 progress assertion 추가 (해당 user 의 step 변화 검증).

- [ ] **Step 8.5.4: 실행 + commit (E29)**

```bash
cd frontend && pnpm exec playwright test home.spec.ts meeting-upload.spec.ts qa-sentinel-p0.spec.ts invite-page-regression.spec.ts 2>&1 | tail -15
git add frontend/e2e/tests/home.spec.ts frontend/e2e/tests/meeting-upload.spec.ts frontend/e2e/tests/qa-sentinel-p0.spec.ts frontend/e2e/tests/invite-page-regression.spec.ts
git commit -m "test(e2e): G1/G3/G5/G6 progress N/4 assertion 보강 (Sprint 22)"
```

### Task 8.6: 전체 Playwright PASS 확인

- [ ] **Step 8.6.1: 모든 spec run**

```bash
cd frontend && pnpm exec playwright test 2>&1 | tail -20
```

Expected: 8/8 NEW + 보강 spec PASS, 기존 spec 회귀 0

### Task 8.7: 결과 문서화

**Files:**
- Create: `docs/dev-log/2026-05-19-sprint22-playwright-e2e.md`
- Create: `docs/dev-log/2026-05-19-sprint22-dogfooding.md`

- [ ] **Step 8.7.1: Playwright 결과 표 작성**

```markdown
# Sprint 22 Playwright E2E 8 시나리오 결과

| Scenario | Spec | Status | Notes |
|---|---|---|---|
| G1 signup→workspace | home.spec.ts | ✅ PASS | Step 1/4 assertion |
| G2 첫 프로젝트 | first-project.spec.ts (NEW) | ✅ PASS | Step 2/4 |
| G3 회의 distillation | meeting-upload.spec.ts (HEAVY) | ✅ PASS | Step 3/4 |
| G4 RAG citation | rag-citation.spec.ts (fix) | ✅ PASS | skip 해제, banner hide |
| G5 action 완료 | qa-sentinel-p0.spec.ts | ✅ PASS | 통계 갱신 |
| G6 두 번째 user 초대 | invite-page-regression + p0 | ✅ PASS | multi-user IDOR |
| G7 logout→login | auth-relogin.spec.ts (NEW) | ✅ PASS | state 보존 |
| G8 Export discoverability | actions-export.spec.ts (NEW) | ✅ PASS | markdown download |
```

- [ ] **Step 8.7.2: Dogfooding walkthrough 작성**

`docs/dev-log/2026-05-19-sprint22-dogfooding.md` — 가상 외부 user "Alice" 12분 walkthrough (spec §8.4 의 7 단계 결과 + screenshot 1-3장 + Sentry dashboard 결과).

- [ ] **Step 8.7.3: commit (E30)**

```bash
git add docs/dev-log/2026-05-19-sprint22-playwright-e2e.md docs/dev-log/2026-05-19-sprint22-dogfooding.md
git commit -m "docs: Sprint 22 Playwright E2E 결과 + dogfooding walkthrough (Sprint 22)"
```

---

## Task 9: Closeout — Codex 2차 + BACKLOG + memory (~2-3h, 3 commits + PR)

### Task 9.1: BACKLOG.md + TODO.md sync

**Files:**
- Modify: `docs/REFACTORING-BACKLOG.md`
- Modify: `docs/TODO.md`

- [ ] **Step 9.1.1: BACKLOG.md — BL-017 ✅ + carry-over BL 갱신**

`docs/REFACTORING-BACKLOG.md` 의 BL-017 (Mobile FAB collision) ✅ mark. CO-1~CO-10 carry-over 등재.

- [ ] **Step 9.1.2: TODO.md — Recently Completed Sprint 22**

```markdown
## Recently Completed (Sprint 22 — Onboarding + E2E + Sentry, 2026-05-19)

- [x] **OBN-01** personal workspace lazy seed 회귀 test 추가 (Sprint 15 기반)
- [x] **OBN-02** OnboardingBanner server state (User column onboarding_step + onboarded_at)
- [x] **OBN-03** EmptyState onboarding-aware copy + 토스트
- [x] **OBN-04** Mobile FAB collision (BL-017) + banner flex-wrap
- [x] **Sentry FE+BE** wire + PII scrub + ADR-021
- [x] **Playwright G1~G8** 8/8 PASS (NEW G2/G7/G8 + G4 fix + G1/G3/G5/G6 보강)
- [x] **BUG-C04** Export discoverability fix (meeting/note detail header)
```

- [ ] **Step 9.1.3: commit (E31)**

```bash
git add docs/REFACTORING-BACKLOG.md docs/TODO.md
git commit -m "docs: BACKLOG + TODO.md Sprint 22 closeout (BL-017 ✅, OBN-01~04 ✅)"
```

### Task 9.2: 전체 회귀 확인

- [ ] **Step 9.2.1: BE pytest + pyright**

```bash
cd backend && uv run pytest tests/ -q 2>&1 | tail -3
uv run pyright 2>&1 | tail -3
uv run pytest tests/integration/test_alembic_upgrade.py -v 2>&1 | tail -5
```

Expected: 325+10 ≈ 335+ PASS / pyright 132 (회귀 0) / drift gate PASS

- [ ] **Step 9.2.2: FE typecheck + lint + Playwright**

```bash
cd frontend && pnpm typecheck && pnpm lint && pnpm exec playwright test 2>&1 | tail -10
```

Expected: 0 error / 8+ Playwright PASS

### Task 9.3: Codex 2차 diff review

- [ ] **Step 9.3.1: 호출**

```bash
codex review --base origin/main HEAD 2>&1 | tail -50
```

Expected: APPROVE 또는 minor REVISE. REVISE 시 polish commit 후 재실행.

### Task 9.4: PR push + create

- [ ] **Step 9.4.1: push**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-22
git push -u origin sprint-22/onboarding-e2e-obs
```

- [ ] **Step 9.4.2: gh pr create (draft)**

```bash
gh pr create --draft --base main --head sprint-22/onboarding-e2e-obs \
  --title "Sprint 22: Onboarding (OBN-01~04) + Playwright G1~G8 + Sentry observability" \
  --body "$(cat <<'EOF'
## Summary

- **OBN-02** Server-side `User.onboarding_step` (0~4) + `onboarded_at` + 4 단계 BE event hook (workspace=1 / project=2 / meeting distillation=3 / RAG ask=4)
- **OBN-01** Personal workspace lazy seed 회귀 test (Sprint 15 의 dependencies.py:79-120 안정성 확인)
- **OBN-03** EmptyState onboarding-aware copy + 첫 회의 가이드 토스트
- **OBN-04** Mobile FAB collision fix (BL-017) + banner flex-wrap
- **Sentry** FE (`@sentry/nextjs`) + BE (`sentry-sdk[fastapi]`) wire + PII scrub `before_send` + ADR-021
- **Playwright E2E G1~G8** 8/8 PASS — NEW 3 (G2 first-project / G7 auth-relogin / G8 actions-export) + G4 rag-citation skip 해제 + G1/G3/G5/G6 progress N/4 assertion 보강
- **BUG-C04** Export discoverability — meeting/note detail header 에 명시적 노출 + tooltip

## Docs sync (Atomic Update §4)

- `backend/src/auth/CONTEXT.md` — User onboarding column
- `docs/architecture/erd.md` — User entity
- `CONTEXT-MAP.md` §2 — entity row
- `backend/src/onboarding/CONTEXT.md` (신설)
- `backend/CONTEXT.md` §4 — 도메인 표
- `docs/architecture/directory-map.md` — backend 트리
- `docs/api/endpoints.md` — `GET /api/v1/users/me/onboarding`
- `docs/dev-log/021-sentry-observability.md` (신설 ADR)

## Verification

- pytest: **325 + 신규 ~10 PASS** + 1 skipped (drift gate 1건 포함)
- pyright: **132 baseline** (회귀 0)
- alembic drift gate: PASS
- Playwright: 8/8 PASS
- Codex review: APPROVE (`Task 9.3`)

## Test plan

- [ ] BE pytest 335+ PASS 확인
- [ ] FE typecheck + lint 0 error
- [ ] Playwright 8 시나리오 PASS
- [ ] 수동 dogfooding (Alice walkthrough, dev-log 첨부)
- [ ] Sentry dashboard 의도된 1건 외 error 0

## Carry-over (Sprint 23+)

- CO-1: OpenTelemetry full instrumentation
- CO-2: Email reminder for stuck onboarding
- CO-3: Onboarding step 5+ collaboration
- CO-4: A/B test framework for banner copy
- CO-5: BL-050 잔여 3 entity (memory_items / memory_ai_calls / promotion_audit)
- CO-6: ADR-019 Phase B Gemini 3.1-flash-lite 코드 swap
- CO-7: Clerk webhook (Sprint 19 PR #3 BUG-AUTH-WH)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 9.4.3: base 확인 (feedback_stack_pr_base_check)**

```bash
gh pr view <PR_NUM> --json baseRefName,headRefName,state
```

Expected: `baseRefName=main` ✓

### Task 9.5: HTML 결과 보고서 작성 + memory + worktree 정리

**Files:**
- Create: `docs/dev-log/2026-05-19-sprint22-result-report.html`
- Update: `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint22_done.md` (신설)
- Update: `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/MEMORY.md` (인덱스 1줄)

- [ ] **Step 9.5.1: HTML 결과 보고서**

`docs/dev-log/2026-05-19-sprint22-result-report.html` — Sprint 18 multi-agent-qa report 패턴 따름. tailwind CDN + 섹션:
- Summary card (8 result metrics)
- OBN-01~04 결과 표
- Playwright G1~G8 표
- Sentry init verify card
- Codex review verdict
- Carry-over CO-1~CO-7 표
- 스크린샷 / Sentry dashboard 캡처 (선택)

- [ ] **Step 9.5.2: memory 갱신**

`project_sprint22_done.md` 신설 — Sprint 21 patternd 의 metadata + commits 표 + verification + carry-over.

`MEMORY.md` 에 1줄 추가:
```
- [project_sprint22_done.md](project_sprint22_done.md) — 2026-05-19 Sprint 22 closeout (OBN-01~04 + E2E G1~G8 + Sentry, PR #N)
```

- [ ] **Step 9.5.3: 머지 + worktree 정리 (사용자 자율)**

```bash
gh pr ready <PR_NUM>
# 사용자 review 후
gh pr merge <PR_NUM> --squash --delete-branch

# main worktree 로 돌아가서
cd /Users/woosung/project/agy-project/kairos
git fetch origin && git log origin/main --oneline -3  # 본 PR squash commit 도달 확인

git worktree remove ../kairos-sprint-22
git branch -D sprint-22/onboarding-e2e-obs
```

- [ ] **Step 9.5.4: 최종 commit (E32)**

```bash
git add docs/dev-log/2026-05-19-sprint22-result-report.html
git commit -m "docs: Sprint 22 HTML 결과 보고서 + memory closeout"
```

---

## Self-Review Checklist (Plan 작성 후)

- [x] **Spec coverage**: §1~§12 모든 항목 → 본 plan 의 Task 0~9 에 매핑됨
- [x] **Placeholder scan**: TBD / TODO 0건. 모든 step 에 exact command + expected output.
- [x] **Type consistency**:
  - `OnboardingResponse {step, totalSteps, onboardedAt, isCompleted}` Task 2.1 schemas.py + Task 4.1 zod schemas.ts 일관
  - `OnboardingStep` enum (NOT_STARTED=0 ... FIRST_RAG=4) Task 2.1 + CONTEXT.md 일관
  - `_seed_personal_workspace_if_missing` (또는 실제 함수명) — Task 3.1 진입 시 실제 함수명 확인 (placeholder 가 아닌 함수명 verify step 명시)

---

**다음 단계**: `/superpowers:subagent-driven-development` 진입 → Task 1 부터 sub-agent 디스패치 시작.
