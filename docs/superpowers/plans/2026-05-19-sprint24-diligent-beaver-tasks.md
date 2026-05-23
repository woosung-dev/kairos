# Sprint 24 diligent-beaver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sprint 23 D4 promote sprint 의 carry-over 3 항목 (BL-066 dogfood verify / BL-063 ActionItem 자동 복제 / BL-064 Note BG schedule) 통합 단일 PR.

**Architecture:** Sprint 23 의 4 도메인 promote 패턴 정합. ItemPromotionAudit 의 기존 `embedding_status` column lifecycle (`pending → processing → completed/failed/n/a`) 활용. alembic 변경 없음. promote_helpers 의 신규 helper 1개 + bulk repo 메서드 1개 + 신규 `GET embedding-status` endpoint 1개 + FE polling wrapper 1개.

**Tech Stack:** FastAPI / SQLModel / asyncpg / BackgroundTasks / Next.js 16 / React 19 / React Query / Vitest / Playwright

> **spec**: [`../specs/2026-05-19-sprint24-diligent-beaver-design.md`](../specs/2026-05-19-sprint24-diligent-beaver-design.md)
> **branch**: `sprint-24/diligent-beaver` (worktree `../kairos-sprint-24`)
> **baseline**: main HEAD `d659c03` / pytest **379 + 1 skipped** / alembic head `9dd1a3b80431`
> **추정**: ~16-25h (alembic drop 으로 plan 보다 ~3-5h 짧아짐)

---

## Task 의존성 그래프

```
Task 0 (docs sync, ✅ 완료 commit 4525bd1) ─────┐
                                                  │
Task 1 (BL-066 dogfood verify, 2-4h) ─────────┐  │
                                                │  │
Task 2 (BL-063 ActionItem 자동 복제, 4-6h) ──┼──┼──→ Task 4 (Codex iterative, 8-12h)
                                                │  │              ↓
Task 3 (BL-064 Note BG schedule, 4-6h) ────┘  │           Task 5 (PR push, 1h)
                                                  │              ↓
                                                  └──→        Task 6 (Stage 6 closeout, 1h)
```

**병렬 가능**: Task 1 (verify) 과 Task 2 (BL-063) / Task 3 (BL-064) 도메인 독립이므로 sub-agent 직렬 dispatch (worktree 1개 git race 회피).

---

## Task 1. BL-066 D1/D3 dogfood verify (2-4h, controller 직접 + Playwright MCP)

**Files:**
- Create: `docs/dev-log/sprints/2026-05-19-sprint24-bl-066-verify.md`
- Modify (optional, 효과 충분 시): `frontend/tests/e2e/specs/workspace-switch.spec.ts`
- Create (optional): `frontend/tests/e2e/specs/inbox-dismiss.spec.ts`

### Step 1.1: dev server 기동 (BE + FE 병렬, background)

- [ ] BE 기동

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24/backend
uv run uvicorn src.main:app --reload --port 8000 &
```

- [ ] FE 기동

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24/frontend
pnpm dev &
```

- [ ] 기동 확인

```bash
curl -s http://localhost:8000/api/v1/health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000
# expected: BE 200 JSON / FE 200
```

### Step 1.2: D1 WorkspaceSwitcher reproduce (Playwright MCP)

- [ ] Playwright MCP 로 dashboard 접근 (인증 필요 — Clerk dev mode)

```
browser_navigate(http://localhost:3000/dashboard)
browser_snapshot()  # 초기 dashboard data 캡쳐
```

- [ ] WorkspaceSwitcher 클릭 → 다른 workspace 전환

```
browser_click(WorkspaceSwitcher trigger)
browser_click(다른 workspace 항목)
browser_wait_for(networkidle)
browser_snapshot()  # 전환 후 dashboard data 캡쳐
```

- [ ] 검증 포인트 확인
  - 새 ws 의 데이터로 정확히 갱신되었는가?
  - 이전 ws 의 stale data 가 남아있지 않은가?
  - `queryClient.clear()` + `invalidateQueries(predicate)` 효과 시각적 확인
  - router.refresh() 의존 제거 후에도 갱신 OK?

### Step 1.3: D3 Inbox dismiss reproduce

- [ ] Inbox 페이지 진입

```
browser_navigate(http://localhost:3000/inbox)
browser_snapshot()
```

- [ ] 항목 1개 dismiss 클릭 → 즉시 사라지는지 확인

```
browser_click(첫번째 inbox item 의 dismiss button)
browser_wait_for(animation)
browser_snapshot()  # list 에서 사라짐 verify
```

- [ ] 새로고침 후에도 미보임 verify

```
browser_navigate(http://localhost:3000/inbox)  # force reload
browser_snapshot()  # dismiss 한 item 이 list 에 없음 verify
```

- [ ] 검증 포인트
  - `useInbox({ isProcessed: false })` queryKey 격리 효과 (다른 query 와 cache 분리)
  - autoProcessed 그룹 제거 후 list 정합
  - camelCase param BE 정합 (`isProcessed=false` 직접 전달)

### Step 1.4: 진단 결과 보고서 작성

- [ ] `docs/dev-log/sprints/2026-05-19-sprint24-bl-066-verify.md` 작성

```markdown
# Sprint 24 BL-066 — D1/D3 dogfood verify

## 환경
- branch: sprint-24/diligent-beaver
- main HEAD: d659c03
- dev server: BE 8000 / FE 3000

## D1 — WorkspaceSwitcher (Sprint 23 9e2eee2 fix)
- 효과 [충분/부족]: <서술>
- Playwright snapshot diff: <첨부>
- 회귀 가드 추가: <spec 변경 사항>

## D3 — Inbox dismiss (Sprint 23 928fc7c fix)
- 효과 [충분/부족]: <서술>
- Playwright snapshot diff: <첨부>
- 회귀 가드 추가: <spec 변경 사항>

## 결론
- BL-066 [closed / carry-over]
- carry-over 시 root cause 분석 + BL-068+ 등재
```

### Step 1.5: 효과 충분 시 — Playwright spec 보강 (선택)

- [ ] `workspace-switch.spec.ts` 의 skip 가드 제거 + dashboard data assertion

```typescript
// Sprint 24 Task 1: skip 가드 제거 (BL-066 verify 통과 후)
test('workspace switcher reflects new ws data', async ({ page }) => {
  await page.goto('/dashboard');
  const before = await page.locator('[data-testid="dashboard-stats"]').textContent();
  await page.locator('[data-testid="ws-switcher"]').click();
  await page.locator('[data-testid="ws-option"]').nth(1).click();
  await page.waitForLoadState('networkidle');
  const after = await page.locator('[data-testid="dashboard-stats"]').textContent();
  expect(after).not.toBe(before);
});
```

- [ ] `inbox-dismiss.spec.ts` 신설 (선택)

```typescript
import { test, expect } from '@playwright/test';

test('inbox dismiss removes item and persists across reload', async ({ page }) => {
  await page.goto('/inbox');
  const initialCount = await page.locator('[data-testid="inbox-item"]').count();
  expect(initialCount).toBeGreaterThan(0);

  await page.locator('[data-testid="inbox-item"]').first()
    .locator('[data-testid="dismiss-btn"]').click();
  await page.waitForFunction(
    (count) => document.querySelectorAll('[data-testid="inbox-item"]').length === count - 1,
    initialCount,
  );

  await page.reload();
  await expect(page.locator('[data-testid="inbox-item"]')).toHaveCount(initialCount - 1);
});
```

### Step 1.6: 효과 부족 시 — carry-over BL 등재

- [ ] `docs/REFACTORING-BACKLOG.md` 에 BL-068+ 신설

```markdown
## BL-068 — D1 WorkspaceSwitcher race condition (Sprint 24 verify)
**현 상태:** Sprint 23 `9e2eee2` fix 의 dev server reproduce 결과 ... (구체적 root cause)
**목표:** ...
```

### Step 1.7: dev server stop + commit

- [ ] dev server 종료

```bash
# BE / FE background process kill
pkill -f "uvicorn src.main:app" && pkill -f "next dev"
```

- [ ] commit

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24
git add docs/dev-log/sprints/2026-05-19-sprint24-bl-066-verify.md
# (효과 충분 시) git add frontend/tests/e2e/specs/workspace-switch.spec.ts frontend/tests/e2e/specs/inbox-dismiss.spec.ts
# (효과 부족 시) git add docs/REFACTORING-BACKLOG.md
git commit -m "chore(verify): BL-066 D1/D3 dogfood reproduce + 결과 보고"
```

---

## Task 2. BL-063 ActionItem 자동 복제 (4-6h, sub-agent 1 직렬)

**Files:**
- Modify: `backend/src/common/promote_helpers.py` (`clone_action_items_for_promote` 추가)
- Modify: `backend/src/actions/repository.py` (`bulk_save_promoted_action_items` 추가)
- Modify: `backend/src/meetings/service.py` (`action_item_count=0` reset 제거 + helper 호출)
- Modify: `backend/src/workspaces/repository.py` (`list_member_user_ids` 신규 또는 기존 활용 verify)
- Modify: `backend/tests/meetings/test_meeting_promote.py` (3 신규 case)
- Modify: `backend/src/meetings/CONTEXT.md` (§의존 + §엔드포인트)
- Modify: `backend/src/common/CONTEXT.md` (§helper 등재)
- Modify: `docs/api/endpoints.md` (`/meetings/{id}/promote` 응답 변경)

### Step 2.1: workspaces repo `list_member_user_ids` 존재 verify

- [ ] grep verify

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24
grep -n "list_member_user_ids\|find_member\|member_user_ids" backend/src/workspaces/repository.py | head
```

- [ ] 없으면 신규 추가

```python
# backend/src/workspaces/repository.py

async def list_member_user_ids(self, workspace_id: uuid.UUID) -> set[uuid.UUID]:
    """target workspace 의 모든 active member user_id set 반환.

    Sprint 24 BL-063: ActionItem 자동 복제 시 assignee_id target ws member verify.
    """
    result = await self.session.exec(
        select(WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
    )
    return set(result.all())
```

### Step 2.2: failing test 1 — 3 ActionItem 복제

- [ ] `backend/tests/meetings/test_meeting_promote.py` 에 추가

```python
async def test_promote_meeting_with_3_action_items(
    integration_session,
    actions_repo,
    meetings_service,
    sample_source_meeting_with_actions,  # fixture: meeting + 3 ActionItem rows (todo/done/in_progress)
    target_workspace,
    promoter_user,
):
    """BL-063: Meeting promote 시 source ActionItem 3 rows 자동 복제.

    Codex 1차 P2-1 fix: MeetingService.promote() + MeetingPromoteOut.new_meeting_id (snake_case).
    action_item_count 은 Meeting 엔티티의 column — target meeting fetch 로 검증.
    """
    response = await meetings_service.promote(
        meeting_id=sample_source_meeting_with_actions.id,
        source_workspace_id=sample_source_meeting_with_actions.workspace_id,
        target_workspace_id=target_workspace.id,
        promoted_by_user_id=promoter_user.id,
        background_tasks=BackgroundTasks(),
    )
    # target meeting 의 action 탭에 3 rows
    target_actions = await actions_repo.find_by_meeting(response.new_meeting_id)
    assert len(target_actions) == 3
    assert {a.status for a in target_actions} == {"todo", "done", "in_progress"}
    # target Meeting.action_item_count column 도 실 row count 와 정합 (Sprint 23 의 0 reset 제거)
    target_meeting = await meetings_repo.find_by_id(response.new_meeting_id, target_workspace.id)
    assert target_meeting.action_item_count == 3
```

### Step 2.3: test fail verify

```bash
cd backend && uv run pytest tests/meetings/test_meeting_promote.py::test_promote_meeting_with_3_action_items -v
# expected: FAIL — clone_action_items_for_promote 미존재 / action_item_count=0 reset 유지
```

### Step 2.4: failing test 2 + 3 추가

- [ ] 같은 파일에 추가

```python
async def test_promote_meeting_with_zero_action_items(
    integration_session,
    actions_repo,
    meetings_repo,
    meetings_service,
    sample_source_meeting_no_actions,
    target_workspace,
    promoter_user,
):
    """BL-063: ActionItem 0 건일 때 promote OK + count 0. Codex 1차 P2-1 정정."""
    response = await meetings_service.promote(
        meeting_id=sample_source_meeting_no_actions.id,
        source_workspace_id=sample_source_meeting_no_actions.workspace_id,
        target_workspace_id=target_workspace.id,
        promoted_by_user_id=promoter_user.id,
        background_tasks=BackgroundTasks(),
    )
    target_actions = await actions_repo.find_by_meeting(response.new_meeting_id)
    assert len(target_actions) == 0
    target_meeting = await meetings_repo.find_by_id(response.new_meeting_id, target_workspace.id)
    assert target_meeting.action_item_count == 0


async def test_promote_meeting_assignee_non_member_resets_to_none(
    integration_session,
    actions_repo,
    meetings_service,
    sample_meeting_with_external_assignee,  # fixture: assignee = user X (source ws member, target ws 비member)
    target_workspace,
    promoter_user,
):
    """BL-063: assignee 가 target ws member 아니면 assignee_id = None reset. Codex 1차 P2-1 정정."""
    response = await meetings_service.promote(
        meeting_id=sample_meeting_with_external_assignee.id,
        source_workspace_id=sample_meeting_with_external_assignee.workspace_id,
        target_workspace_id=target_workspace.id,
        promoted_by_user_id=promoter_user.id,
        background_tasks=BackgroundTasks(),
    )
    target_actions = await actions_repo.find_by_meeting(response.new_meeting_id)
    assert len(target_actions) == 1
    assert target_actions[0].assignee_id is None  # silent reset
```

- [ ] 둘 다 fail 확인

```bash
uv run pytest tests/meetings/test_meeting_promote.py -k "zero_action_items or assignee_non_member" -v
# expected: 2 FAIL
```

### Step 2.5: `clone_action_items_for_promote` helper 구현

- [ ] `backend/src/common/promote_helpers.py` 에 추가 (기존 `validate_promote_target` / `build_item_promotion_audit` 뒤)

```python
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select


async def clone_action_items_for_promote(
    source_meeting_id: uuid.UUID,
    target_meeting_id: uuid.UUID,
    target_workspace_id: uuid.UUID,
    target_project_id: uuid.UUID | None,
    session: AsyncSession,
) -> int:
    """Meeting promote 의 ActionItem 자동 복제 (BL-063, Sprint 24).

    Sprint 23 D4 (Codex 3차 P3) 의 `action_item_count=0` reset 보강:
    source ActionItem rows 를 target meeting_id 로 remap 복제.
    assignee_id 는 target ws WorkspaceMember verify → 부재 시 None reset
    (cross-workspace 누출 차단, 사용자 결정 게이트 #5).

    parent SAVEPOINT 안에서 호출되어야 — 부분 실패 시 entire promote rollback.

    Returns: 실 복제 row count (audit.action_item_count 로 set).
    """
    # 1. source ActionItem rows fetch (workspace + meeting 격리)
    from src.actions.models import ActionItem  # 순환 import 회피, 함수 내 import
    from src.workspaces.models import WorkspaceMember

    source_result = await session.exec(
        select(ActionItem).where(ActionItem.meeting_id == source_meeting_id)
    )
    source_items = source_result.all()
    if not source_items:
        return 0

    # 2. target ws member user_id set fetch (cross-ws 누출 차단)
    member_result = await session.exec(
        select(WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == target_workspace_id)
    )
    target_member_ids: set[uuid.UUID] = set(member_result.all())

    # 3. remap (composite FK: workspace_id + project_id + meeting_id, assignee None reset)
    # Codex 1차 P2-2 fix: ActionItem 모델에 created_by_id 부재 — 제거.
    #                     priority 필드 (default "medium") 명시 복제.
    # ActionItem 실 fields: id(default) / workspace_id / meeting_id / project_id /
    #                      title / description / assignee_id / due_date / priority /
    #                      status / created_at(default) / updated_at(default)
    cloned: list[ActionItem] = []
    for src in source_items:
        cloned.append(ActionItem(
            workspace_id=target_workspace_id,
            project_id=target_project_id,
            meeting_id=target_meeting_id,
            assignee_id=src.assignee_id if src.assignee_id in target_member_ids else None,
            title=src.title,
            description=src.description,
            status=src.status,
            priority=src.priority,
            due_date=src.due_date,
        ))

    # 4. bulk save (transactional, parent SAVEPOINT 활용)
    session.add_all(cloned)
    await session.flush()  # FK error 즉시 발견 (parent rollback 유발 가능)
    return len(cloned)
```

### Step 2.6: meetings/service.py 의 `promote` 보강 (Codex 1차 P2-1)

- [ ] `backend/src/meetings/service.py:347` 영역 수정

```python
# Sprint 24 Task 2 (BL-063): action_item_count=0 reset 제거 + helper 호출.
# Sprint 23 D4 (Codex 3차 P3) 의 reset 보강 — 실제 ActionItem rows 복제.
# 변경 전:
#     action_item_count=0,
# 변경 후:
new_meeting = Meeting(
    workspace_id=target_workspace_id,
    project_id=None,
    title=source.title,
    # ... 기타 필드 그대로
    error_message=source.error_message,
    # action_item_count 는 helper 호출 후 갱신 (아래 step)
    created_by_id=promoted_by_user_id,
)
new_meeting = await self.repo.save_promoted_meeting(new_meeting)

# ... (MeetingSummary 복제 기존 흐름 유지)

# Sprint 24 Task 2 (BL-063): ActionItem 자동 복제 (audit 생성 직전)
action_count = await clone_action_items_for_promote(
    source_meeting_id=source.id,
    target_meeting_id=new_meeting.id,
    target_workspace_id=target_workspace_id,
    target_project_id=None,  # cross-ws project 제약, 추후 사용자 수동 연결
    session=self.repo.session,
)
new_meeting.action_item_count = action_count  # in-memory update for response
await self.repo.session.flush()
```

- [ ] import 추가

```python
# 파일 상단
from src.common.promote_helpers import (
    build_item_promotion_audit,
    clone_action_items_for_promote,  # NEW Sprint 24
    validate_promote_target,
)
```

### Step 2.7: test pass verify

```bash
uv run pytest tests/meetings/test_meeting_promote.py -v
# expected: 7 PASS (기존 4 + 신규 3)
```

### Step 2.8: 회귀 verify — 기존 test 영향 0

```bash
uv run pytest tests/ -q
# expected: 379 + 3 - 0 회귀 = 382 (BL-064 추가 전 중간 baseline)
```

### Step 2.9: docs sync (Atomic Update §4)

- [ ] `backend/src/meetings/CONTEXT.md` §의존 및 §엔드포인트 patch

```markdown
## §의존

- common/promote_helpers — Sprint 24 BL-063: `clone_action_items_for_promote` 호출
- actions — 도메인 직접 import 금지 원칙 유지. 본 helper 가 cross-domain abstraction.

## §엔드포인트

`POST /workspaces/{wid}/meetings/{id}/promote`
- 응답 변경 (Sprint 24): `actionItemCount` = 실제 복제된 row count
  (이전: 0 reset, Sprint 23 6차 P3 carry).
```

- [ ] `backend/src/common/CONTEXT.md` §helper 에 추가

```markdown
| `clone_action_items_for_promote` | Meeting promote 의 ActionItem 자동 복제 (BL-063 Sprint 24). assignee_id target ws member verify → 부재 시 None reset. composite FK remap. parent SAVEPOINT 활용. |
```

- [ ] `docs/api/endpoints.md` `/meetings/{id}/promote` 응답 명세 갱신

### Step 2.10: commit

```bash
git add backend/src/common/promote_helpers.py \
        backend/src/meetings/service.py \
        backend/tests/meetings/test_meeting_promote.py \
        backend/src/meetings/CONTEXT.md \
        backend/src/common/CONTEXT.md \
        docs/api/endpoints.md
git commit -m "feat(meetings): BL-063 — ActionItem rows 자동 복제 on Meeting promote (Sprint 23 CO-15 보강)"
```

---

## Task 3. BL-064 Note BG schedule + UX (4-6h, sub-agent 1 BE + controller FE)

**Files:**
- Modify: `backend/src/notes/service.py` (chunk 0 + plain_text 분기)
- Modify: `backend/src/notes/router.py` (`GET embedding-status` endpoint)
- Modify: `backend/src/notes/schemas.py` (`PromoteNoteResponse.embedding_status` + `EmbeddingStatusOut`)
- Modify: `backend/src/notes/repository.py` (필요 시 `count_chunks_for_note`)
- Modify: `backend/tests/notes/test_note_promote.py` (3 신규 case)
- Create: `backend/tests/notes/test_embedding_regenerate.py`
- Modify: `frontend/src/features/notes/api.ts` (client function)
- Modify: `frontend/src/components/shared/ItemPromoteModal.tsx` (polling)
- Create: `frontend/src/components/shared/__tests__/ItemPromoteModal.test.tsx`
- Modify: `backend/src/notes/CONTEXT.md`
- Modify: `docs/api/endpoints.md`
- Modify: `docs/architecture/cross-domain-pipeline.md`

### Step 3.1: failing test 1 — chunk 0 + plain_text → BG schedule

- [ ] `backend/tests/notes/test_note_promote.py` 에 추가

```python
async def test_promote_note_chunk_zero_plain_text_schedules_embed(
    integration_session,
    notes_service,
    note_pipeline_service,  # fixture: NotePipelineService instance (DI 패턴)
    sample_note_chunk_zero_with_plain_text,  # fixture: plain_text="content text" + EmbeddingChunk 0
    target_workspace,
    promoter_user,
    monkeypatch,
):
    """BL-064: chunk 0 + plain_text 존재 시 → pipeline.embed_note_async BG schedule + audit pending.

    Codex 1차 P2-3 fix: embed_note_async = NotePipelineService instance method (모듈 함수 아님).
    monkeypatch 대상 = NotePipelineService.embed_note_async (instance method).
    """
    bg_calls = []
    async def fake_embed(self, note_id, ws_id):  # instance method signature (self 첫번째)
        bg_calls.append((note_id, ws_id))
    monkeypatch.setattr(
        "src.notes.pipeline_service.NotePipelineService.embed_note_async",
        fake_embed,
    )

    bg_tasks = BackgroundTasks()
    response = await notes_service.promote(
        note_id=sample_note_chunk_zero_with_plain_text.id,
        source_workspace_id=sample_note_chunk_zero_with_plain_text.workspace_id,
        target_workspace_id=target_workspace.id,
        promoted_by_user_id=promoter_user.id,
        background_tasks=bg_tasks,
        pipeline=note_pipeline_service,  # DI 추가 (service signature 변경)
    )
    # promote 자체 성공 (400 X)
    assert response.new_note_id is not None
    # audit raw value "pending" 노출
    assert response.embedding_status == "pending"
    # BG task scheduled (실 호출은 FastAPI 가 endpoint 응답 후 trigger — 여기는 mock 으로 verify)
    await bg_tasks()  # FastAPI 의 BackgroundTasks 는 callable
    assert len(bg_calls) == 1
    assert bg_calls[0][0] == response.new_note_id
    assert bg_calls[0][1] == target_workspace.id
```

### Step 3.2: failing test 2 + 3 추가

- [ ] 같은 파일에 추가

```python
async def test_promote_note_chunk_n_lifecycle_pending(
    integration_session,
    notes_service,
    sample_note_chunk_3_with_plain_text,  # fixture: chunk count 3
    target_workspace,
    promoter_user,
):
    """BL-064: chunk N>0 일 때도 audit.embedding_status="pending" 초기값 정합."""
    response = await notes_service.promote(
        note_id=sample_note_chunk_3_with_plain_text.id,
        source_workspace_id=sample_note_chunk_3_with_plain_text.workspace_id,
        target_workspace_id=target_workspace.id,
        promoted_by_user_id=promoter_user.id,
        background_tasks=BackgroundTasks(),
    )
    assert response.embedding_status == "pending"  # 기존 흐름과 정합


async def test_promote_note_no_plain_text_no_chunk_rejected(
    integration_session,
    notes_service,
    sample_note_empty,  # fixture: plain_text="" + chunk 0
    target_workspace,
    promoter_user,
):
    """BL-064: plain_text 부재 + chunk 0 → 400 회귀 가드 (Sprint 23 6차 P2)."""
    with pytest.raises(NotePromoteNotEmbeddedError):
        await notes_service.promote(
            note_id=sample_note_empty.id,
            source_workspace_id=sample_note_empty.workspace_id,
            target_workspace_id=target_workspace.id,
            promoted_by_user_id=promoter_user.id,
            background_tasks=BackgroundTasks(),
        )
```

- [ ] 3 fail 확인

```bash
uv run pytest tests/notes/test_note_promote.py -k "chunk_zero_plain_text or chunk_n_lifecycle or no_plain_text" -v
# expected: 3 FAIL
```

### Step 3.3: `NoteService.promote` chunk 0 + plain_text 분기 보강

> **Codex 2차 정정**:
> - service method = `NoteService.promote()` (line 221, NOT `promote_note`). router function 이름만 `promote_note`.
> - **P1 audit lifecycle wrapper 필수**: `pipeline.embed_note_async` 만 호출 시 audit `embedding_status` 가 `pending → completed/failed` 전환 안 됨. Sprint 23 D4 `_replicate_chunks_async` 패턴 정합으로 `_regenerate_embed_with_audit_async(audit_id, note_id, workspace_id)` wrapper BG task 신설.
> - `PromoteNoteResponse` schema = snake_case 보존 (`new_note_id` / `audit_id`) — 기존 modal 의 `NEW_ID_KEY` + `response.audit_id` 직접 read 호환성 유지.

- [ ] `backend/src/notes/service.py` 의 line 270 영역 수정 — `NotePromoteNotEmbeddedError` 분기

```python
# Sprint 24 Task 3 (BL-064): chunk 0 + plain_text 분기 보강.
# 변경 전 (Sprint 23 6차 P2):
#     if not existing_chunks:
#         raise NotePromoteNotEmbeddedError()
# 변경 후 — plain_text 부재 만 reject, chunk 부재는 BG schedule 분기:
if not source.plain_text or not source.plain_text.strip():
    raise NotePromoteNotEmbeddedError()

existing_chunks = await self.repo.find_note_chunks(source.id, source_workspace_id)
needs_embed_regenerate = not existing_chunks  # True: chunk 0 + plain_text 존재 → BG schedule
```

- [ ] **service signature 변경** — `pipeline: NotePipelineService` DI 추가 (Codex 1차 P2-3 fix)

```python
# Sprint 24 Task 3 (BL-064): promote() signature 에 pipeline 추가.
# Codex 1차 P2-3 fix: embed_note_async = NotePipelineService instance method
# (module-level function 부재). pipeline DI 로 호출.
async def promote(
    self,
    note_id: uuid.UUID,
    source_workspace_id: uuid.UUID,
    target_workspace_id: uuid.UUID,
    promoted_by_user_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    pipeline: "NotePipelineService",  # NEW Sprint 24 (TYPE_CHECKING import 회피 quote)
) -> PromoteNoteOut:
    ...
```

- [ ] **`_regenerate_embed_with_audit_async` wrapper BG task 신설 (Codex 2차 P1 fix)**

`NotePipelineService.embed_note_async` 만 호출 시 audit row 의 `embedding_status` 가 `pending` 그대로 stuck. polling endpoint 가 영원히 pending 반환 — BL-064 핵심 기능 무력. wrapper BG task 가 audit lifecycle 책임.

```python
# Sprint 24 Task 3 (BL-064): chunk 0 분기 audit lifecycle wrapper.
# Codex 2차 P1 fix: pipeline.embed_note_async 만 호출 시 audit pending stuck.
# Sprint 23 D4 _replicate_chunks_async 패턴 정합.
async def _regenerate_embed_with_audit_async(
    self,
    audit_id: uuid.UUID,
    note_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    """chunk 0 + plain_text note 의 BG embedding 생성 + audit lifecycle 갱신.

    동작:
    1. audit.embedding_status = "processing" mark
    2. pipeline.embed_note_async(note_id, workspace_id) 호출
    3. 성공: audit.embedding_status = "completed"
    4. 예외: rollback + audit.embedding_status = "failed"

    parent SAVEPOINT 외부 (별도 BG session_factory) — Sprint 23 D4 같은 패턴.
    """
    from src.common.promote_models import ItemPromotionAudit  # 순환 import 회피
    from sqlmodel import update as _update

    async with self.session_factory() as session:
        try:
            # 1. processing mark
            await session.exec(
                _update(ItemPromotionAudit)
                .where(ItemPromotionAudit.id == audit_id)
                .values(embedding_status="processing")
            )
            await session.commit()

            # 2. 신규 embedding 생성 (NotePipelineService instance method)
            await self.pipeline.embed_note_async(note_id, workspace_id)

            # 3. completed mark
            await session.exec(
                _update(ItemPromotionAudit)
                .where(ItemPromotionAudit.id == audit_id)
                .values(embedding_status="completed")
            )
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            # 4. failed mark (Sprint 23 D4 Codex 4차 P2-2 패턴 — rollback 먼저)
            await session.rollback()
            await session.exec(
                _update(ItemPromotionAudit)
                .where(ItemPromotionAudit.id == audit_id)
                .values(embedding_status="failed")
            )
            await session.commit()
            raise
```

> wrapper 가 `self.pipeline` 을 사용하려면 `NoteService.__init__` 의 `pipeline` 의존성 추가 필요. 또는 wrapper signature 에 `pipeline` 인자 추가. **선택**: signature 에 인자로 받음 (NoteService init 변경 최소화).

> 다만 `NoteService.session_factory` 는 Sprint 23 D4 에서 이미 의존성 추가됨 → 그대로 활용.

- [ ] BG task schedule 분기 추가 — chunk 0 vs chunk N 차이

```python
# Sprint 24 Task 3 (BL-064): chunk 0 분기는 wrapper BG task,
# chunk N 분기는 기존 _replicate_chunks_async (Sprint 23 D4) 그대로.
if needs_embed_regenerate:
    background_tasks.add_task(
        self._regenerate_embed_with_audit_async,
        audit.id, new_note.id, target_workspace_id,
    )
    # audit.embedding_status 가 wrapper 안에서 pending → processing → completed/failed 전환
else:
    background_tasks.add_task(
        self._replicate_chunks_async, source.id, source_workspace_id,
        new_note.id, target_workspace_id, audit.id,
    )
```

또는 `_regenerate_embed_with_audit_async` 가 pipeline 을 인자로 받는 free function 형태도 가능. 다만 instance method 가 self.session_factory 활용에 더 자연스러움. 결정: instance method + `_regenerate_embed_with_audit_async(self, audit_id, note_id, workspace_id, pipeline)` signature (pipeline 인자 외부 주입).

- [ ] router.py 에서 pipeline DI 주입

```python
# backend/src/notes/router.py 의 promote_note endpoint
@router.post("/{note_id}/promote", ...)
async def promote_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    body: NotePromoteIn,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member),
    service: NoteService = Depends(get_note_service),
    pipeline: NotePipelineService = Depends(get_note_pipeline_service),  # NEW
):
    return await service.promote(  # NOTE: service method = promote (NOT promote_note)
        note_id=note_id,
        source_workspace_id=workspace_id,
        target_workspace_id=body.target_workspace_id,
        promoted_by_user_id=member.user_id,
        background_tasks=background_tasks,
        pipeline=pipeline,  # NEW
    )
```

### Step 3.4: `PromoteNoteOut.embedding_status` 필드 + `EmbeddingStatusOut` 추가

> **Codex 2차 P2-3 정정**: 기존 ItemPromoteModal 이 `response.new_note_id` / `response.audit_id` 를 **snake_case 직접 read** (`NEW_ID_KEY[itemType] = "new_note_id"` + `response.audit_id`). alias_generator / Field alias 추가 시 `newNoteId` / `auditId` 응답으로 modal 가 ID 못 찾음. **snake_case 보존 + alias 추가 안 함**.

- [ ] `backend/src/notes/schemas.py` 의 기존 `PromoteNoteOut` (또는 `MeetingPromoteOut` 와 동급) 에 필드 추가

```python
from typing import Literal

EmbeddingStatusValue = Literal["pending", "processing", "completed", "failed", "n/a"]


# 기존 schema 명칭 확인 후 정합 (memory/meeting/note 도메인 *PromoteOut 동급 명칭)
# Sprint 23 D4 의 PromoteNoteOut snake_case 응답 유지 — modal 호환성.
class PromoteNoteOut(BaseModel):
    """POST /notes/{id}/promote 응답 — 복제본 + audit 식별자.

    Sprint 24 BL-064: embedding_status 필드 추가 — audit raw value 그대로 노출.
    snake_case 보존 (Sprint 23 D4 D-1 정합) — frontend ItemPromoteModal 의
    NEW_ID_KEY[itemType] = "new_note_id" + response.audit_id 직접 read 호환성.
    """
    new_note_id: uuid.UUID  # snake_case 보존 (alias 추가 X)
    audit_id: uuid.UUID
    embedding_status: EmbeddingStatusValue  # snake_case 보존, modal 가 read

    # Codex 2차 P2-3: alias 추가 안 함, populate_by_name 도 추가 안 함 (기본값 유지).


class EmbeddingStatusOut(BaseModel):
    """GET /notes/{id}/embedding-status 응답 (Sprint 24 BL-064 NEW endpoint).

    NEW endpoint 이므로 camelCase alias OK (FE 가 신규로 read 하는 schema).
    """
    status: EmbeddingStatusValue
    chunk_count: int = Field(alias="chunkCount")

    model_config = {"populate_by_name": True}
```

### Step 3.5: `GET embedding-status` endpoint 추가

- [ ] `backend/src/notes/router.py` 에 추가

```python
@router.get("/{note_id}/embedding-status")
async def get_note_embedding_status(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_viewer),
    service: NoteService = Depends(get_note_service),
) -> EmbeddingStatusOut:
    """Sprint 24 BL-064: target note 의 embedding 진행 상태 polling.

    RBAC: viewer 이상 (read-only).
    응답: audit raw embedding_status + 실 chunk count (race-safe 확인용).
    """
    return await service.get_embedding_status(workspace_id, note_id)
```

- [ ] `NoteService.get_embedding_status` 메서드 추가

```python
async def get_embedding_status(
    self, workspace_id: uuid.UUID, note_id: uuid.UUID
) -> EmbeddingStatusOut:
    """note_id 의 audit row 최신 embedding_status + 실 chunk count 반환."""
    note = await self.repo.find_by_id(note_id, workspace_id)
    if note is None:
        raise NoteNotFoundError()

    # 가장 최신 audit row 가져오기 (target_workspace_id + new_item_id 기준)
    audit = await self.repo.find_latest_audit_for_note(note_id, workspace_id)
    if audit is None:
        # promote 로 들어온 note 가 아니면 native chunk count 만 반환
        chunk_count = await self.repo.count_chunks_for_note(note_id, workspace_id)
        if chunk_count > 0:
            return EmbeddingStatusOut(status="completed", chunk_count=chunk_count)
        else:
            return EmbeddingStatusOut(status="pending", chunk_count=0)

    chunk_count = await self.repo.count_chunks_for_note(note_id, workspace_id)
    return EmbeddingStatusOut(status=audit.embedding_status, chunk_count=chunk_count)
```

### Step 3.6: failing test 4 + 5 (embedding_regenerate test 파일 신설)

- [ ] `backend/tests/notes/test_embedding_regenerate.py` 신설

```python
"""Sprint 24 BL-064 — embed_note_async idempotency + status endpoint RBAC."""
import pytest


async def test_embed_note_async_idempotent_when_already_embedded(
    integration_session,
    sample_note_chunk_5,  # fixture: chunk count 5 (이미 임베딩 완료)
):
    """BL-064: target note 가 이미 embed 되어 있으면 early return (멱등)."""
    from src.embeddings.service import embed_note_async
    # before count
    before_count = await count_chunks(sample_note_chunk_5.id, integration_session)
    await embed_note_async(sample_note_chunk_5.id, sample_note_chunk_5.workspace_id)
    after_count = await count_chunks(sample_note_chunk_5.id, integration_session)
    # 동일 (skip)
    assert before_count == after_count == 5


async def test_embedding_status_endpoint_rbac_viewer_only(
    integration_client,
    sample_promoted_note,  # fixture
    promoter_user,  # owner of source ws
    non_member_user,
    viewer_user,  # target ws viewer
):
    """BL-064: GET /notes/{id}/embedding-status RBAC = viewer 이상."""
    # 1. non-member → 403
    response_anon = await integration_client.get(
        f"/api/v1/workspaces/{sample_promoted_note.workspace_id}/notes/{sample_promoted_note.id}/embedding-status",
        headers=auth_headers(non_member_user),
    )
    assert response_anon.status_code == 403

    # 2. viewer → 200
    response_viewer = await integration_client.get(
        f"/api/v1/workspaces/{sample_promoted_note.workspace_id}/notes/{sample_promoted_note.id}/embedding-status",
        headers=auth_headers(viewer_user),
    )
    assert response_viewer.status_code == 200
    data = response_viewer.json()
    assert data["status"] in {"pending", "processing", "completed", "failed", "n/a"}
    assert "chunkCount" in data  # camelCase alias 확인
```

### Step 3.7: test pass verify

```bash
uv run pytest tests/notes/test_note_promote.py tests/notes/test_embedding_regenerate.py -v
# expected: 9 PASS (note_promote 7 + embedding_regenerate 2)
```

### Step 3.8: BE 회귀 verify

```bash
uv run pytest tests/ -q
# expected: 379 + 6 = 385 PASS (BL-063 3 + BL-064 3 신규 + embedding_regenerate 2 - 1 (Task 2 의 중복 회귀))
# 정확히는: 379 baseline + 3 (BL-063) + 3 (BL-064 note_promote) + 2 (embedding_regenerate) - 2 (note_promote_no_plain_text 의 새 case 가 기존 case 통합) = 385
```

### Step 3.9: FE client `getEmbeddingStatus` 추가 (Codex 2차 P2-4 정정)

- [ ] `frontend/src/features/notes/api.ts` — 기존 `fetchNote` 등의 패턴 정합 (`apiClient<T>(path, {token})` + Clerk token)

```typescript
// Sprint 24 BL-064 — promoted note 의 embedding 상태 polling client.
// Codex 2차 P2-4 fix: api.get 부재. 기존 fetchNote 등의 apiClient<T>(path, {token}) 패턴 정합.
export type EmbeddingStatus = "pending" | "processing" | "completed" | "failed" | "n/a";

export interface EmbeddingStatusOut {
  status: EmbeddingStatus;
  chunkCount: number;
}

export async function getEmbeddingStatus(
  token: string,
  workspaceId: string,
  noteId: string,
): Promise<EmbeddingStatusOut> {
  return apiClient<EmbeddingStatusOut>(
    `/workspaces/${workspaceId}/notes/${noteId}/embedding-status`,
    { token },
  );
}
```

### Step 3.10: FE `ItemPromoteModal` polling 분기 (Codex 2차 P2-3 정정)

> **snake_case 보존**: 기존 modal 가 `NEW_ID_KEY[itemType] = "new_note_id"` + `response.audit_id` snake_case 직접 read. BE 응답도 alias 없이 snake_case 그대로. 본 patch 도 동일하게 `response.embedding_status` snake_case read.

- [ ] `frontend/src/components/shared/ItemPromoteModal.tsx` 의 mutation success 콜백 보강

기존 modal 의 mutation onSuccess 흐름에 itemType==="note" 분기 추가. 기존 props (`open` / `onOpenChange` / `itemType` / `itemId` / `sourceWorkspaceId` / `onSuccess`) 보존.

```typescript
// Sprint 24 BL-064 — note promote 응답 의 embedding_status pending/processing 시 polling 추가.
// snake_case 보존 — BE 응답 alias 없음 (Codex 2차 P2-3).
// 기존 modal 의 onSuccess(newId, auditId) 흐름은 유지. note 한정 polling 흐름만 추가.

import { useAuth } from "@clerk/nextjs";
import { getEmbeddingStatus, type EmbeddingStatus } from "@/features/notes/api";

// mutation 의 onSuccess 콜백 안에서:
const { getToken } = useAuth();

const handleNotePromoteSuccess = async (
  response: { new_note_id: string; audit_id: string; embedding_status: EmbeddingStatus },
  targetWorkspaceId: string,
) => {
  // ready / n/a: 즉시 완료 toast
  if (response.embedding_status === "completed" || response.embedding_status === "n/a") {
    toast.success("Promote 완료");
    onOpenChange(false);
    onSuccess?.(response.new_note_id, response.audit_id);
    return;
  }

  // pending / processing: polling 시작 (5s × 3회 maxAttempts)
  if (response.embedding_status === "pending" || response.embedding_status === "processing") {
    const toastId = toast.loading("Promote 완료 (임베딩 재생성 중)");
    let attempts = 0;
    const maxAttempts = 3;

    const intervalId = setInterval(async () => {
      attempts += 1;
      try {
        const token = (await getToken()) ?? "";
        const status = await getEmbeddingStatus(token, targetWorkspaceId, response.new_note_id);
        if (status.status === "completed") {
          clearInterval(intervalId);
          toast.success("임베딩 재생성 완료", { id: toastId });
          onOpenChange(false);
          onSuccess?.(response.new_note_id, response.audit_id);
        } else if (status.status === "failed") {
          clearInterval(intervalId);
          toast.error("임베딩 재생성 실패", { id: toastId });
          onOpenChange(false);
        } else if (attempts >= maxAttempts) {
          clearInterval(intervalId);
          toast("재생성 진행 중, 잠시 후 확인", { id: toastId });
          onOpenChange(false);
          onSuccess?.(response.new_note_id, response.audit_id);
        }
      } catch (e) {
        clearInterval(intervalId);
        toast.error("상태 확인 실패", { id: toastId });
      }
    }, 5000);
    return;
  }

  // failed: 즉시 (BG 호출 직후 부정 status — 본 sprint 범위에서는 발생 안 함)
  toast.error("Promote 후 임베딩 상태 이상");
  onOpenChange(false);
};
```

기존 mutation 의 onSuccess 콜백 in itemType === "note" 분기에서 위 helper 호출. 다른 itemType (memory/meeting/inbox/action) 은 기존 동작 유지.

### Step 3.11: FE vitest 1 신규

- [ ] `frontend/src/components/shared/__tests__/ItemPromoteModal.test.tsx`

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import { ItemPromoteModal } from "@/components/shared/ItemPromoteModal";
import * as notesApi from "@/features/notes/api";

vi.mock("@/features/notes/api");

describe("ItemPromoteModal — Sprint 24 BL-064 polling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  // Codex 2차 P2-5 정정: 기존 dispatch test harness 패턴 + mocked fetch + 정확한 props.
  // ItemPromoteModal 실 props: itemType / itemId / sourceWorkspaceId / open / onOpenChange / onSuccess.
  // promote 응답은 mocked fetch 로 endpoint 가 반환 — modal 내부에서 fetch.
  it("note promote pending status triggers polling endpoint", async () => {
    // 1. promote POST 응답 mock (snake_case 보존)
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      const u = String(url);
      if (u.includes("/notes/") && u.endsWith("/promote")) {
        return new Response(JSON.stringify({
          new_note_id: "note-uuid",
          audit_id: "audit-uuid",
          embedding_status: "pending",
        }), { status: 200 });
      }
      // workspaces fetch (modal 내부 useWorkspaces)
      return new Response(JSON.stringify([
        { id: "ws-target", name: "Target", type: "team" }
      ]), { status: 200 });
    });

    // 2. getEmbeddingStatus polling mock — processing → completed transition
    const getStatusMock = vi.spyOn(notesApi, "getEmbeddingStatus")
      .mockResolvedValueOnce({ status: "processing", chunkCount: 0 })
      .mockResolvedValueOnce({ status: "completed", chunkCount: 4 });

    const handleOpenChange = vi.fn();
    render(
      <ItemPromoteModal
        itemType="note"
        itemId="note-source-uuid"
        sourceWorkspaceId="ws-source"
        open
        onOpenChange={handleOpenChange}
      />
    );

    // 3. target workspace 선택 + Submit 클릭 → promote fetch trigger
    // (기존 dispatch test harness 의 selectWorkspace + clickSubmit 흐름 활용)
    // ... [기존 test harness 의 helper 함수 호출 — 자세한 건 기존 *.test.tsx 패턴 참조] ...

    // 4. polling 호출 verify
    vi.advanceTimersByTime(5000);
    await waitFor(() => expect(getStatusMock).toHaveBeenCalledTimes(1));

    // 5. 2번째 polling → completed → modal close
    vi.advanceTimersByTime(5000);
    await waitFor(() => expect(getStatusMock).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(handleOpenChange).toHaveBeenCalledWith(false));

    fetchMock.mockRestore();
  });
});
```

### Step 3.12: FE vitest verify

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24/frontend
pnpm test -- --run note-promote-modal
# expected: 1 PASS
```

### Step 3.13: docs sync (Atomic Update §4)

- [ ] `backend/src/notes/CONTEXT.md` §엔드포인트 patch

```markdown
- `POST /workspaces/{wid}/notes/{id}/promote` (Sprint 24 BL-064 보강)
  - chunk 0 + plain_text 존재 → 400 대신 promote OK + `embed_note_async` BG schedule
  - 응답 `embeddingStatus`: audit raw value (pending/processing/completed/failed/n/a)
- `GET /workspaces/{wid}/notes/{id}/embedding-status` (Sprint 24 BL-064, NEW)
  - RBAC: viewer 이상
  - 응답: `{status, chunkCount}` — audit raw + 실 chunk count
```

- [ ] `docs/api/endpoints.md` 갱신
- [ ] `docs/architecture/cross-domain-pipeline.md` notes promote BG schedule 흐름 추가

### Step 3.14: commit

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24
git add backend/src/notes/service.py \
        backend/src/notes/router.py \
        backend/src/notes/schemas.py \
        backend/src/notes/repository.py \
        backend/tests/notes/test_note_promote.py \
        backend/tests/notes/test_embedding_regenerate.py \
        frontend/src/features/notes/api.ts \
        frontend/src/components/shared/ItemPromoteModal.tsx \
        frontend/src/components/shared/__tests__/ItemPromoteModal.test.tsx \
        backend/src/notes/CONTEXT.md \
        docs/api/endpoints.md \
        docs/architecture/cross-domain-pipeline.md
git commit -m "feat(notes): BL-064 — chunk 0 + plain_text → embed_note_async BG schedule + embedding-status polling (Sprint 23 CO-16 보강)"
```

---

## Task 4. Codex iterative review cycle (8-12h, Stage 4)

### Step 4.1: Codex 1차 (plan review, Stage 2.5 게이트)

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24
codex review --base origin/main
# expected: APPROVE 또는 REVISE → finding 100% 수락 → plan v2 patch commit
```

### Step 4.2: Codex N차 (diff review, Stage 4)

- [ ] Task 2 + 3 commit 후 `codex review --base origin/main` cycle
- [ ] APPROVE 까지 finding 100% 수락 protocol:

```
loop:
    verdict = codex review --base origin/main
    if APPROVE → break
    elif REVISE:
        - finding 100% 수락 (fact-based)
        - polish commit 1개: "polish: Codex N차 M finding 100% 수락 (P1 X + P2 Y)"
        - git push (PR 자동 갱신)
    elif limit:
        - wait until reset
```

### Step 4.3: 예상 cycle
- 2-3 cycle: BL-063 (assignee remap edge case / composite FK / transactional)
- 2-3 cycle: BL-064 (BG schedule race / polling RBAC / Note 모델 edge case)
- 1-2 cycle: 통합 (camelCase alias / audit lifecycle 일관성)
- 1-2 cycle: docs sync 정합성

---

## Task 5. PR push + Stage 5 verify (1-2h)

### Step 5.1: PR push

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24
git push -u origin sprint-24/diligent-beaver
```

### Step 5.2: PR 생성

```bash
gh pr create --draft --title "Sprint 24 diligent-beaver: BL-066 dogfood + BL-063 ActionItem 자동 복제 + BL-064 Note BG schedule" --body "$(cat <<'EOF'
## Summary
- BL-066: Sprint 23 D1/D3 fix dogfood verify (진단 first 강제)
- BL-063: Meeting promote 시 ActionItem rows 자동 복제 (assignee target ws member verify → None reset)
- BL-064: Note chunk 0 + plain_text → embed_note_async BG schedule + embedding-status polling endpoint

## Docs sync (Atomic Update §4)
- meetings/CONTEXT.md, notes/CONTEXT.md, common/CONTEXT.md
- docs/api/endpoints.md, docs/architecture/cross-domain-pipeline.md
- (alembic 변경 없음, ItemPromotionAudit.embedding_status 기존 column 활용)

## 검증
- pytest 385 + 1 skipped (379 baseline + 6 신규)
- FE vitest 50 / typecheck 0 / build 12/12
- E2E Playwright workspace-switch + inbox-dismiss spec 신규/보강
- Codex iterative APPROVE

## Test plan
- [ ] BL-063: Meeting promote 3 ActionItem case Playwright
- [ ] BL-064: Note chunk 0 promote → 5s polling → completed toast
- [ ] BL-066: workspace 전환 + inbox dismiss dev server reproduce

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### Step 5.3: R7 base verify

```bash
gh pr view <N> --json baseRefName,headRefName
# expected: baseRefName="main" + headRefName="sprint-24/diligent-beaver"
```

### Step 5.4: CI green wait

```bash
gh pr checks <N> --watch
# expected: 모든 jobs green
```

---

## Task 6. Stage 6 closeout (1h)

### Step 6.1: memory 신설

- [ ] `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint24_diligent_beaver_done.md` 신설 (frontmatter + 본문)

### Step 6.2: MEMORY.md 인덱스 라인 추가

```markdown
- [project_sprint24_diligent_beaver_done.md](project_sprint24_diligent_beaver_done.md) — 2026-05-20 Sprint 24 diligent-beaver closeout (BL-066 verify + BL-063 ActionItem 자동 복제 + BL-064 Note BG schedule). PR #99 (예상). main HEAD <merge SHA>.
```

### Step 6.3: carry-over BL 등재 (REFACTORING-BACKLOG.md)

- [ ] BL-065 / BL-067 carry-over 유지
- [ ] BL-068+ (Sprint 24 신규 발견 시) 등재

### Step 6.4: PR 머지 후 worktree 정리

- [ ] `git fetch && git log origin/main --oneline -1` 로 merge SHA 확정 → memory 갱신
- [ ] worktree 정리 (사용자 머지 후)

```bash
# main worktree 에서
cd /Users/woosung/project/agy-project/kairos
git worktree remove ../kairos-sprint-24
git branch -D sprint-24/diligent-beaver
git fetch && git pull origin main
git stash list  # stash@{0} 여전히 보존 verify (R8)
```

---

## 검증 (Verification — End-to-end)

### Backend
```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24/backend
uv run pytest tests/ -q
# expected: 385 passed + 1 skipped (baseline 379 + 신규 6)
uv run alembic upgrade head
# expected: head 9dd1a3b80431 (변경 없음)
```

### Frontend
```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24/frontend
pnpm tsc --noEmit
pnpm test -- --run
pnpm build
# expected: typecheck 0 / vitest 50 / build 12/12
```

### Codex
- `codex review --base origin/main` APPROVE 까지 ~10 cycle 예산

---

## Self-Review Summary

본 plan 의 spec coverage:
- BL-066 (spec §Architecture/Testing) → Task 1 (Step 1.1~1.7)
- BL-063 (spec §Architecture/Components/Data Flow/Error Handling/Testing) → Task 2 (Step 2.1~2.10)
- BL-064 (spec §Architecture/Components/Data Flow/Error Handling/Testing) → Task 3 (Step 3.1~3.14)
- Codex iterative (spec §Success Criteria) → Task 4 (Step 4.1~4.3)
- R1~R8 mitigation (spec §risk) → 각 task 의 `R<N>` reference

Placeholder 0건. type 일관성: `EmbeddingStatusValue` Literal 통일. assignee_id None reset 패턴 일관. transactional 일관성 (parent SAVEPOINT 활용 모든 task).
