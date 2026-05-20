# Sprint 24 — diligent-beaver Design Spec

> **codename**: `diligent-beaver`
> **branch**: `sprint-24/diligent-beaver` (worktree `../kairos-sprint-24`)
> **baseline**: main HEAD `d659c03` (Sprint 23 cozy-crystal squash, 2026-05-19) / pytest **379 passed + 1 skipped** / alembic head `9dd1a3b80431`
> **추정**: ~20-30h (Codex iterative cycle 포함, Sprint 23 동급 예산)
> **단일 PR 통합**: BL-066 dogfood verify + BL-063 ActionItem 자동 복제 + BL-064 Note BG schedule

---

## Context — 왜 이 Sprint인가

### 1. ADR-019 Phase B 는 이미 main 적용 완료 (사실 verify 결과)

User prompt 와 memory `project_sprint15_adr019_phase_a_done.md` (5일 전 시점) 가 stale. git blame 결과:

| commit | 일시 | 내용 |
|---|---|---|
| `003908a` | 2026-05-15 17:20 | `feat(ai): Gemini 2.5-flash → 3.1-flash-lite migration (ADR-019 Phase B)` |
| `f482865` | 2026-05-15 | PR #32 머지 (`sprint-17/adr-019-phase-b-gemini-swap`) |
| `5912f84` | 2026-05-15 | `docs(adr-019): Phase B Accepted + Atomic Update 매트릭스 docs sync` |

git-tracked 6 spots 모두 `gemini-3.1-flash-lite` 적용 완료. `.ai/common/global.md:151` stale 주석은 `.gitignore:59` 의 `.ai/` 정책으로 **drop** (의도적 제외).

### 2. Sprint 23 carry-over 마무리 = 본 sprint 실 scope

Sprint 23 D4 promote sprint (`d659c03`) 가 4 도메인 (meetings/notes/inbox/actions) 자동 promote 를 도입했으나 3 가지 carry-over 발생. 본 sprint = **promote 정합성 보강 sprint**.

| BL | 작업 | 추정 |
|---|---|---|
| **BL-066** (P2) | Sprint 23 D1 (WorkspaceSwitcher) + D3 (Inbox dismiss) fix 실 효과 dev server / Playwright reproduce | 2-4h |
| **BL-063** (P3→P1) | Meeting promote 시 source ActionItem rows **자동 복제** (Codex 3차 P3 fix 보강) | 4-6h |
| **BL-064** (P3→P1) | Note promote chunk 0 case → `embed_note_async` **BG schedule + UX 진행 표시** | 5-8h |
| Codex iterative + closeout | ~10 cycle 예산 | 8-12h |

### 3. 사용자 결정 사항 (5 게이트, 모두 추천 옵션 채택)

| # | 결정 | 채택 |
|---|---|---|
| 1 | ADR-019 mismatch 처리 | Plan 언급 + polish drop (gitignored 정책 존중) |
| 2 | BL-063 ActionItem 복제 방향 | 자동 복제 default |
| 3 | BL-064 Note 임베딩 재계산 UX | 자동 BG schedule + `embedding_status` 진행 표시 |
| 4 | Codex iterative cycle 예산 | Sprint 23 동급 (~10 cycle) |
| 5 | BL-063 assignee_id remap | target ws member 면 유지 / 아니면 None reset (cross-ws 누출 차단) |

---

## 1. Architecture

### BL-063 — Meeting promote 시 ActionItem 자동 복제

```
[Meeting promote endpoint]
  POST /workspaces/{wid}/meetings/{id}/promote
       ↓
  MeetingService.promote(...)  # Codex 1차 P2-1: 실 메서드명 promote() (snake_case 헌법 정합)
       ↓ (parent SAVEPOINT)
   ├─ source meeting → target ws 복제 (Sprint 23 dc20757 패턴)
   ├─ promote_helpers.clone_action_items_for_promote(    ← NEW
   │       source_meeting_id, target_meeting_id,
   │       target_workspace_id, target_project_id, session
   │   )
   │       ↓ ActionItemRepository.bulk_save_promoted_action_items(items)
   │       ↓ assignee_id 분기 (target ws WorkspaceMember verify → 부재 시 None)
   │       ↓ composite FK remap (workspace_id + project_id + meeting_id)
   └─ ItemPromotionAudit row 저장
         (action_item_count = 실 복제 row count, Sprint 23 의 0 reset 제거)
```

### BL-064 — Note promote chunk 0 case → BG schedule + UX

```
[Note promote endpoint]
  POST /workspaces/{wid}/notes/{id}/promote
       ↓
  NoteService.promote_note(...)
       ↓
   ├─ source.plain_text 부재 + chunk 0  → 400 NotePromoteNotEmbeddedError (회귀 유지)
   ├─ source.plain_text 존재 + chunk N>0 → promote OK + embedding_status="ready"
   └─ source.plain_text 존재 + chunk 0   → promote OK
          ↓ target note 생성 (chunk 미복제, source EmbeddingChunk 복제 분기 skip)
          ↓ ItemPromotionAudit row 저장 (기존 `embedding_status` column, 초기값 "pending")
          ↓ BackgroundTasks.add_task(self._regenerate_embed_with_audit_async,
                                     audit.id, target_note_id, target_ws_id, pipeline)
                                     ← Codex 2차 P1 fix: wrapper BG task (audit_id 받음).
                                       기존 pipeline.embed_note_async 만 호출 시 audit
                                       lifecycle 갱신 안 됨 — wrapper 가 책임.
          ↓ wrapper 내부 lifecycle: "pending" → "processing" → "completed" / "failed"
          ↓ response.embedding_status = audit raw value 그대로 (초기 "pending", snake_case 보존)

[FE ItemPromoteModal success callback]
       ↓ response.embeddingStatus 분기 (camelCase, BE alias 정합)
   ├─ "completed" → toast "Promote 완료"
   ├─ "n/a"       → toast "Promote 완료" (임베딩 ledger 부재 도메인, 본 sprint scope 외)
   └─ "pending" | "processing" → toast "Promote 완료 (임베딩 재생성 중)"
                       + setInterval(5000ms) × 3회
                            ↓ GET /workspaces/{wid}/notes/{tid}/embedding-status
                            ↓ status === "completed" → clearInterval + toast 갱신
                            ↓ status === "failed" → clearInterval + toast "재생성 실패"
                            ↓ 3회 후에도 pending/processing → toast "잠시 후 확인"
```

### BL-066 — Sprint 23 D1/D3 dogfood verify

```
[dev server reproduce]
  cd backend && uv run uvicorn src.main:app --reload --port 8000
  cd frontend && pnpm dev (port 3000)
       ↓
  Playwright MCP browser_navigate(http://localhost:3000)
       ↓
   ├─ D1: WorkspaceSwitcher 클릭 → 다른 ws 전환 → dashboard data 정확히 갱신?
   │       검증: queryClient.clear() + invalidateQueries(predicate) 효과
   │              router.refresh() 의존 제거 verify
   └─ D3: Inbox 항목 dismiss → list 즉시 사라짐 + reload 후 미보임
           검증: useInbox({ isProcessed: false }) queryKey 격리
                  autoProcessed 그룹 제거 + camelCase param BE 정합
       ↓
  진단 doc 작성 → 효과 충분 → BL-066 ✅ closed
                 효과 부족 → carry-over BL 등재 + root cause 분석
```

---

## 2. Components

### BL-063

| 파일 | 역할 | 변경 |
|---|---|---|
| `backend/src/common/promote_helpers.py` | `clone_action_items_for_promote(...)` helper 추가 | NEW function |
| `backend/src/common/promote_models.py` | `ItemPromotionAudit` 기존 컬럼 (변경 없음) | — |
| `backend/src/meetings/service.py` | `promote` 의 `action_item_count=0` reset 제거 + helper 호출 (실 메서드명, Codex 1차 P2-1 정정) | MOD |
| `backend/src/actions/repository.py` | `bulk_save_promoted_action_items(items: list[ActionItem]) -> int` | NEW method |
| `backend/src/actions/models.py` | 변경 없음 (composite FK 이미 Sprint 21 적용) | — |
| `backend/tests/meetings/test_meeting_promote.py` | 4 → 7 case (3 신규: rows 3건 / rows 0건 / assignee None reset) | EXT |
| `backend/src/meetings/CONTEXT.md` | §의존에 actions repo 추가 + §엔드포인트 응답 변경 | MOD |
| `backend/src/common/CONTEXT.md` | §helper 에 clone_action_items_for_promote 등재 | MOD |
| `docs/api/endpoints.md` | `/meetings/{id}/promote` 응답 변경 (`actionItemCount` 실제) | MOD |

### BL-064

> **알람**: spec 작성 시 가정 오류 발견 (R1 fact-check) → `ItemPromotionAudit.embedding_status` column 이 이미 존재 (default "pending", enum: pending/processing/completed/failed/n/a). 신규 column / alembic / drift gate 변경 **불필요**. 기존 lifecycle 활용. spec 정정 commit 으로 반영.

| 파일 | 역할 | 변경 |
|---|---|---|
| `backend/src/notes/service.py` | `NoteService.promote()` (snake_case, NOT promote_note — Codex 2차 P2-2 정정) 의 chunk 0 + plain_text 분기 → `_regenerate_embed_with_audit_async` wrapper BG task schedule (audit lifecycle 책임). + signature 에 `pipeline: NotePipelineService` DI 추가. | MOD |
| `backend/src/notes/service.py` | `_regenerate_embed_with_audit_async(audit_id, note_id, workspace_id, pipeline)` wrapper BG task 신설 — Sprint 23 D4 `_replicate_chunks_async` 패턴 정합. audit `pending → processing → completed/failed` lifecycle (Codex 2차 P1 fix). | NEW method |
| `backend/src/notes/router.py` | `GET /workspaces/{wid}/notes/{id}/embedding-status` (`require_viewer`) | NEW endpoint |
| `backend/src/notes/schemas.py` | `PromoteNoteOut.embedding_status: Literal["pending","processing","completed","failed","n/a"]` (snake_case 보존, alias 없음 — Codex 2차 P2-3: 기존 ItemPromoteModal 의 NEW_ID_KEY snake_case read 호환성) + `EmbeddingStatusOut` (NEW endpoint, chunkCount camelCase OK) | MOD |
| `backend/src/common/promote_models.py` | 변경 없음 (기존 `embedding_status` column 활용) | — |
| alembic | 변경 없음 (head `9dd1a3b80431` 유지) | — |
| `backend/tests/notes/test_note_promote.py` | 4 → 7 case (3 신규: chunk 0+plain_text → embed_note_async schedule + audit pending / chunk N → 기존 흐름 정합 / plain_text 부재 → 400 회귀) | EXT |
| `backend/tests/notes/test_embedding_regenerate.py` | embed_note_async idempotency + polling endpoint RBAC | NEW |
| `frontend/src/features/notes/api.ts` | `getEmbeddingStatus(token, workspaceId, noteId)` client — 기존 `apiClient<T>(path, {token})` 패턴 정합 (Codex 2차 P2-4 정정, Clerk token Authorization) | NEW function |
| `frontend/src/components/shared/ItemPromoteModal.tsx` | embeddingStatus pending/processing 분기 + polling (Codex 1차 P2-4 정정) | MOD |
| `frontend/src/components/shared/__tests__/ItemPromoteModal.test.tsx` | pending → polling → completed transition (기존 file 에 신규 case 추가) | MOD |
| `backend/src/notes/CONTEXT.md` | §엔드포인트 patch (chunk 0 + plain_text 분기 추가 명시) | MOD |
| `backend/src/common/CONTEXT.md` | 변경 없음 (column 추가 X) | — |
| `docs/api/endpoints.md` | `/notes/{id}/promote` 응답 enum 명시 + `/notes/{id}/embedding-status` 신설 | MOD |
| `docs/architecture/cross-domain-pipeline.md` | notes promote chunk 0 case BG schedule 흐름 추가 | MOD |
| `CONTEXT-MAP.md` | 변경 없음 (column 추가 X) | — |

### BL-066

| 파일 | 역할 | 변경 |
|---|---|---|
| `docs/dev-log/2026-05-19-sprint24-bl-066-verify.md` | dogfood 진단 결과 보고서 (D1 + D3 screenshot + 검증 포인트) | NEW |
| `frontend/tests/e2e/specs/workspace-switch.spec.ts` | skip 가드 제거 + dashboard data assertion (효과 충분 시) | MOD |
| `frontend/tests/e2e/specs/inbox-dismiss.spec.ts` | dismiss → list disappear → reload 후 보존 | NEW (선택) |

---

## 3. Data Flow

### BL-063 transactional 보장

Sprint 23 `dc20757` Meeting promote 의 parent SAVEPOINT 안에서 ActionItem 복제도 atomic. 부분 실패 시 entire promote rollback. audit row 저장도 SAVEPOINT 안 (실패 시 audit 미생성).

### BL-063 assignee remap 정책 (사용자 게이트 #5)

```python
async def clone_action_items_for_promote(
    source_meeting_id: UUID,
    target_meeting_id: UUID,
    target_workspace_id: UUID,
    target_project_id: UUID | None,
    session: AsyncSession,
) -> int:
    source_items = await actions_repo.list_by_meeting(source_meeting_id, session)
    target_member_user_ids = await workspaces_repo.list_member_user_ids(target_workspace_id, session)
    cloned: list[ActionItem] = []
    for item in source_items:
        assignee_id = item.assignee_id if item.assignee_id in target_member_user_ids else None
        cloned.append(ActionItem(
            workspace_id=target_workspace_id,
            project_id=target_project_id,
            meeting_id=target_meeting_id,
            assignee_id=assignee_id,
            title=item.title,
            description=item.description,
            status=item.status,
            due_date=item.due_date,
            # ... 기타 필드 그대로 복제
        ))
    return await actions_repo.bulk_save_promoted_action_items(cloned)
```

### BL-064 BG schedule idempotency

`embed_note_async` 진입 시점 race-safe 보장:

```python
async def embed_note_async(note_id: UUID, workspace_id: UUID):
    chunk_count = await embeddings_repo.count_chunks(note_id)
    if chunk_count > 0:
        logger.info(f"embed_note_async skipped (already embedded): {note_id}")
        return
    # ... 기존 임베딩 로직
```

다중 schedule 발생 (예: promote 후 사용자가 manual retry button 또 클릭) 해도 결과 멱등.

### BL-064 embedding_status enum (기존 audit raw values 그대로 노출)

```python
EmbeddingStatus = Literal["pending", "processing", "completed", "failed", "n/a"]

# response.embedding_status (audit raw value 그대로):
#   "pending"     — promote 직후 초기값, BG task 진입 대기
#   "processing"  — BG task 진행 중 (chunk insert)
#   "completed"   — BG task 성공 (target chunk count > 0)
#   "failed"      — BG task 영구 실패
#   "n/a"         — 임베딩 ledger 부재 도메인 (inbox/actions, notes 에는 발생 안 함)
```

기존 `notes/service.py` 의 BG task lifecycle (`pending → processing → completed/failed`) 그대로 활용. chunk 0 + plain_text 분기는 신규 `embed_note_async` schedule 만 추가 (audit row 의 lifecycle 동일).

### BL-066 진단 first 강제 (R3 mitigation)

Playwright MCP browser_navigate/click/snapshot 결과로 D1/D3 실 효과 확인. 효과 부족 시 root cause grep + carry-over BL 등재. **코드 변경 금지** (Task 1 만으로는 spec 만 추가).

---

## 4. Error Handling

| Case | Status | 동작 |
|---|---|---|
| **BL-063: ActionItem 복제 일부 row 실패** | 500 | parent SAVEPOINT rollback → entire Meeting promote 500 + audit 미생성 |
| **BL-063: assignee target ws 부재** | — | `assignee_id = None` reset, 로그만 (silent), promote OK |
| **BL-063: source ActionItem 0건** | 200 | promote OK + `action_item_count = 0` |
| **BL-063: composite FK remap 실패** | 500 | rollback (alembic preflight 가 미리 검증) |
| **BL-064: plain_text 부재 + chunk 0** | 400 | `NotePromoteNotEmbeddedError` (Sprint 23 6차 P2 동작 유지) |
| **BL-064: plain_text 존재 + chunk 0** | 200 | promote OK + audit `embedding_status="pending"` + `embed_note_async` BG schedule |
| **BL-064: BG embed 진행 중 polling** | 200 | `status="pending"` 또는 `"processing"` + `chunkCount=0` |
| **BL-064: BG embed 완료 후 polling** | 200 | `status="completed"` + `chunkCount=N>0` |
| **BL-064: target note 부재 polling** | 404 | (정상 RBAC 후 발생 가능 — note 삭제됨) |
| **BL-064: BG embed 영구 실패** | 200 polling | audit `embedding_status="failed"` → FE toast "재생성 실패" |
| **BL-064: polling endpoint RBAC** | 403 | non-member 호출 → require_viewer dependency 차단 |
| **BL-066: dev server 기동 실패** | — | 환경 의존 issue → carry-over BL 등재, 본 sprint scope 외로 처리 |

---

## 5. Testing

### BL-063 pytest 3 신규 case (`backend/tests/meetings/test_meeting_promote.py`)

| Case | Setup | 검증 |
|---|---|---|
| `test_promote_meeting_with_3_action_items` | source meeting + 3 ActionItem (status 다양: todo/done/in_progress) | target meeting 의 action 탭 = 3 rows + 같은 status, audit.action_item_count == 3 |
| `test_promote_meeting_with_zero_action_items` | source meeting, ActionItem 0건 | promote OK + audit.action_item_count == 0 + target action 탭 빈 |
| `test_promote_meeting_assignee_non_member_resets_to_none` | source ActionItem assignee = user X (source ws member, target ws 비member) | target ActionItem.assignee_id IS NULL |

### BL-064 pytest 3 신규 case (`backend/tests/notes/test_note_promote.py`) + 2 신규 (`test_embedding_regenerate.py`)

| Case | Setup | 검증 |
|---|---|---|
| `test_promote_note_chunk_zero_plain_text_schedules_embed` | source note: plain_text="..." + chunk 0 | response.embedding_status == "pending" + audit row "pending" + embed_note_async scheduled (mock verify) |
| `test_promote_note_chunk_n_completed_lifecycle` | source note: plain_text + chunk count N>0 (기존 흐름) | response.embedding_status == "pending" (BG schedule 직후) + EmbeddingChunk 복제 BG task scheduled |
| `test_promote_note_no_plain_text_no_chunk_rejected` | source note: plain_text="" + chunk 0 | 400 NotePromoteNotEmbeddedError (Sprint 23 6차 회귀 가드) |
| `test_embed_note_async_idempotent` | target note 이미 chunk count > 0 일 때 embed_note_async 재호출 | skip (early return 멱등 verify) |
| `test_embedding_status_endpoint_rbac_viewer` | non-member 가 GET /notes/{id}/embedding-status | 403 + viewer/member/admin/owner = 200 |

### BL-064 vitest 1 신규 case (`frontend/src/components/shared/__tests__/ItemPromoteModal.test.tsx` 기존 file 에 case 추가, Codex 1차 P2-4 정정)

| Case | 검증 |
|---|---|
| `pending status triggers toast and polling` | response.embeddingStatus="pending" → toast 노출 + 5s 후 polling endpoint 호출 verify (mock) + "completed" 응답 시 clearInterval |

### BL-066 Playwright spec 보강

- `workspace-switch.spec.ts` — skip 가드 제거 + dashboard data assertion (효과 충분 시)
- `inbox-dismiss.spec.ts` 신설 (선택) — dismiss → list disappear → reload 후 보존

### 회귀 baseline

- BE pytest: **379 → 385** expected (BL-063 3 신규 + BL-064 3 신규 + embedding_regenerate 2 신규 - 1 회귀 갱신)
  - 정확히는: meeting_promote 4→7 (+3), note_promote 4→7 (+3), test_embedding_regenerate.py NEW 2, alembic 변경 없음
- FE vitest: 49 → 50 expected
- alembic upgrade head: 변경 없음 (head `9dd1a3b80431` 유지)
- drift gate: 변경 없음 (allowlist 변경 X)
- E2E Playwright: 신규 spec PASS (선택)

### Codex iterative

본 PR diff 에 대해 `codex review --base origin/main` cycle 10회 예산. APPROVE 까지 finding 100% 수락 (P1/P2/P3 정책).

---

## Success Criteria

| ID | 검증 |
|---|---|
| **BL-063 success** | target meeting 의 action 탭에 source row 복제 (assignee remap 정합) 노출, `action_item_count` = 실 row count, transactional 일관성 (부분 실패 = entire rollback) |
| **BL-064 success** | source chunk 0 + plain_text note 의 promote = 400 대신 OK + audit `embedding_status` "pending" 시작 + 5-15s 내 `embed_note_async` 완료 → audit "completed" + target chunk count > 0, `GET embedding-status` polling endpoint 동작 + RBAC viewer. **alembic / column 변경 0** (기존 `embedding_status` column 활용) |
| **BL-066 success** | D1/D3 fix 실 효과 dev server / Playwright reproduce 로 확인, 효과 부족 시 carry-over BL 등재 |
| **Codex iterative** | APPROVE (Sprint 23 동급 ~10 cycle 예산) |
| **회귀 가드** | pytest **385** + 1 skipped / vitest 50 / FE typecheck 0 / build 12/12 / E2E Playwright 신규 PASS / alembic head 변경 X (`9dd1a3b80431` 유지) / drift gate 변경 X |
| **Atomic Update §4** | docs sync 매트릭스 (CONTEXT-MAP / CONTEXT.md / endpoints.md / cross-domain-pipeline.md) 동일 PR 내 동시 갱신 |

---

## Out of Scope (carry-over)

- **BL-065** Member.last_active_at 필드 (Sprint 23 D2 carry CO-17, P3 → Sprint 26+)
- **BL-067** pyright `_update(...).where(...)` false-positive (Sprint 23 CO-19, P4 → Sprint 27+)
- **BL-024** pg_prewarm Cloud Run cold start
- **BL-026** dev DB export + ground truth (production scale recall)
- BL-064 audit `embedding_status="failed"` 상태의 사용자 명시 retry button — 후속 sprint
- BL-064 의 inbox/actions 도메인 (audit `embedding_status="n/a"`) polling 확장 — 본 sprint 는 notes 만 적용
- ActionItem 명시 trigger UI (별도 endpoint 활용) — BL-063 자동 복제 default 채택으로 불필요
- Clerk Production key / Sentry DSN 발급 — founder 작업, founder 외부 환경 의존
- 외부 user 1명 실제 dogfooding (Sprint 22 spec 12분 walkthrough) — founder 작업

---

## R1~R8 Risk Mitigation (Sprint 22/23 학습)

| Risk | Mitigation |
|---|---|
| **R1. Codex fact-mismatch** | Stage 4 진입 직전 ActionItem repo 메서드명 / NotePromoteResponse schema / promote_helpers signature grep verify. 10 cycle 까지 정상 |
| **R2. Sub-agent stall** | BL-063 + BL-064 BE 만 sub-agent dispatch. FE 는 controller 직접. ~1.5h 한도 |
| **R3. 코드 외부 원인** | BL-066 = 진단 first. Playwright reproduce 결과 부족 시 carry-over BL |
| **R4. BE/FE shape mismatch** | NotePromoteResponse 의 `embedding_status` snake/camel alias 명시 (헌법 I-16). Sprint 23 D3 inbox camelCase 학습 |
| **R5. alembic migration scope** | spec 초안 의 alembic / column 추가 = R1 fact-check 로 불필요 확인 (기존 `embedding_status` column 활용). alembic head `9dd1a3b80431` 유지, drift gate 변경 0 |
| **R6. scope overrun** | 30h 초과 시 BL-064 만 carry-over (BL-063 + BL-066 우선 완료) |
| **R7. stack PR base** | `gh pr view <N> --json baseRefName` = "main" verify (PR #93 사고 학습) |
| **R8. stash@{0} 보존** | 어떤 worktree 에서도 pop 금지. Sprint 22 design-review 잔재 보존 |

---

## References

### 내부
- plan: `~/.claude/plans/sprint-24-adr-019-distributed-dolphin.md` (codename diligent-beaver로 결정됨)
- Sprint 23 closeout memory: `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint23_cozy_crystal_done.md`
- ADR-019 Phase B 결과: `docs/dev-log/019-gemini-eol-migration.md` §Implementation Phase B (DONE 2026-05-15)
- 이전 sprint spec/plan 패턴: `docs/superpowers/specs/2026-05-19-sprint23-cozy-crystal-design.md` + `docs/superpowers/plans/2026-05-19-sprint23-cozy-crystal-tasks.md`

### 코드 참조 (Sprint 23 학습)
- `backend/src/memory/router.py:125-143` — promote endpoint 원형 패턴
- `backend/src/meetings/service.py` (Sprint 23 `dc20757`) — Meeting promote 현 구현
- `backend/src/notes/service.py` (Sprint 23 `7c54438` + `1141c37`) — Note promote + chunk 0 거부
- `backend/src/inbox/service.py` (Sprint 23 `2f724f0`) — camelCase param 학습
- `backend/src/actions/service.py:261` + `router.py:82-88` — ActionItem promote endpoint 원형
- `backend/src/common/promote_helpers.py` (Sprint 23 `6b1dce1`) — validate_promote_target / build_item_promotion_audit
- `backend/src/actions/models.py:32-37` — ActionItem composite FK (Sprint 21 BL-050 Simple 4 적용 완료)

### 헌법 / 표준
- `CONTEXT-MAP.md` I-12 (AI 모델 고정) / I-16 (DB snake ↔ API camel) / I-18 (cross-workspace promote)
- `.ai/common/global.md` §2 Atomic Update 매트릭스 (gitignored, project hub)
- `.ai/templates/workflow.md` Stage 0~6
