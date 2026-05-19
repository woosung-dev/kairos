# Sprint 23 — cozy-crystal Design Spec

> codename: **cozy-crystal**
> 작성: 2026-05-19
> baseline: main HEAD `22da49b` (Sprint 22 expressive-squirrel PR #97 squash merge)
> branch: `sprint-23/cozy-crystal`
> worktree: `~/project/agy-project/kairos-sprint-23`
> plan doc (Stage 2): `docs/superpowers/plans/2026-05-19-sprint23-cozy-crystal-tasks.md`

---

## 1. Context — 왜 진행하는가

Sprint 22 (expressive-squirrel, 2026-05-19 PR #97 squash merge `22da49b`) closeout 직후 dogfooding 진행 중 발견한 dogfood issue 4건 (D1~D4) + Sprint 22 미완료 sync 항목 4건 (F1~F4) 통합 fix sprint.

**기조**:
- dogfood fix 우선 (feature 추가 X)
- ADR-019 Phase B (Gemini 3.1-flash-lite 코드 swap, 2026-05-28 EOL) 는 Sprint 24 로 defer
- 단일 PR 통합 (`feedback_single_session_closure` 패턴)

**진입 결정 (사용자 lock-in)**:
1. **D4 풀 generic 화** — BE 4 도메인 promote endpoint 신설 + FE shared component 추출 + 4 entry point mount
2. **D2 design-shotgun 신규 실행** — Settings 시안 doc 부재 확정 (`~/.gstack` + project root + `docs/` 전수 탐색)
3. **codename cozy-crystal lock-in**

---

## 2. Scope — 8건 (~22-30h)

### 🔴 P0 — dogfood high (3건)
- **D1**: 워크스페이스 스위처 클릭 시 컨텍스트 전환 동작 안 됨 (2-4h)
- **D3**: Inbox 무시/확정 처리 persist 안 됨 (3-5h)
- **D4**: 워크스페이스 이동 UI 가 memory 검색 결과에서만 노출 (12-15h, scope 확대)

### 🟡 P1 — Sprint 23 권장 포함 (5건)
- **D2**: Settings 페이지 design-shotgun 신규 실행 + 구현 (3-4h)
- **F1**: `docs/TODO.md` + `docs/REFACTORING-BACKLOG.md` sync (30min-1h)
- **F2**: memory `project_sprint22_done.md` final 갱신 (15min)
- **F3**: HTML 결과 보고서 final 갱신 (30min)
- **F4**: G7 spec storageState key fix (30min)

---

## 3. Section: Architecture

작업 분기 3축:

1. **D1/D3 = 진단 first → fix 패턴** — 사용자 보고와 코드 거동에 mismatch 존재. 추측 기반 surface-level fix 금지. Playwright reproduce → DevTools/log fact-check → minimal fix.

2. **D4 = BE/FE 풀 generic 화** — `Promotable` BE 추상화 + 4 endpoint 신설 (meetings/notes/inbox/actions) + FE `ItemPromoteModal` shared component 추출 + 5 entry point mount (기존 memory 포함). 헌법 I-18 (Promotion 정책: 복제 + tombstone, 이동 금지) 변경 없이 적용 도메인만 확장.

3. **D2 = design-shotgun 게이트** — variant 4-6 생성 → 사용자 1 안 선택 → 구현. variant 선택 결정 전 코드 변경 0.

**의존성**:
- D2 design-shotgun 결과 대기 = blocker (3-4h gap)
- gap 동안 D4 BE 작업 병렬 진행 가능
- F1~F4 는 Sprint 진입 직후 / closeout 직전 일괄 처리

---

## 4. Section: Components / 변경 영역

### D1 — WorkspaceSwitcher 진단 + minimal fix

**현 코드**:
- `frontend/src/features/workspaces/components/WorkspaceSwitcher.tsx:43-48` `handleSwitch`:
  ```typescript
  const handleSwitch = (wid: string) => {
    if (wid === activeWid) return;
    setActiveWorkspaceId(wid);     // Zustand store
    queryClient.clear();             // ⚠️ 모든 캐시 초기화
    router.refresh();                // Next.js 리렌더링
  };
  ```
- `frontend/src/features/workspaces/store.ts:25-49` Zustand persist key = `kairos-workspace`
- `frontend/src/app/(app)/dashboard/page.tsx:124-126` **render-time setState** (race condition 후보)

**root cause 가설**:
- (1) `queryClient.clear()` + Zustand persist sync 실패
- (2) dashboard render-time setState 가 state thrash 유발
- (3) `router.refresh()` 가 useQuery 와 독립 → stale

**Fix 방향**:
1. Stage 4 진입 직후 Playwright reproduce + console/DevTools fact-check (1h)
2. 진단 결과 기반 minimal fix:
   - dashboard render-time setState → `useEffect(() => { ... }, [currentWid])` 로 이동
   - `queryClient.clear()` → `queryClient.invalidateQueries({ predicate: q => q.queryKey[1] === wid })` (workspace-scoped 만)
   - `router.refresh()` 제거 검토 (invalidate 만으로 충분한지)
3. 회귀 spec `frontend/e2e/tests/workspace-switch.spec.ts` 1개 신규

### D3 — Inbox persist 진단 + FE explicit params

**현 코드**:
- BE persist **정상 확인**:
  - `backend/src/inbox/service.py:82-128` dismiss/classify 모두 `item.is_processed=True` + `repo.commit()`
  - `backend/src/inbox/repository.py:26-38` list 조회에 `is_processed: bool | None` 필터 지원
- FE 문제:
  - `frontend/src/features/inbox/hooks.ts:21-52` `useInbox(wid)` 가 params 없이 fetch
  - `frontend/src/features/inbox/components/smart-inbox.tsx:44-95` 가 client-side `!isProcessed` filter
- 사용자 보고와 코드 거동 mismatch → 진단 first

**root cause 가설**:
- (1) BE response 의 field name mismatch (`is_processed` snake_case vs FE Zod `isProcessed` camelCase) → Zod fail silently → 모든 item 이 isProcessed=false 로 표시 (가장 강한 후보)
- (2) FE `onSuccess` invalidate 의 queryKey mismatch
- (3) Sprint 19 BUG-C01-EXT v3 의 endpoint 45 matrix 점검 시 response shape 변경 가능성

**Fix 방향**:
1. BE response 직접 확인 (curl 또는 Playwright Network tab) → field name + invalidate 동작 verify
2. 가설 (1) 확정 시: FE Zod schema 의 `is_processed` snake_case 추가 또는 BE response transformer 통일
3. 가설 (2) 확정 시: invalidate queryKey 정합 fix
4. **FE 개선 (가설과 무관 권장)**: `useInbox(wid, { is_processed: false })` 명시적 params → BE filter 위임 + client filter 단순화
5. 회귀 pytest `test_inbox_dismiss_then_list_excludes.py` 신규 1개

### D4 — Promotable 추상화 + ItemPromoteModal

**현 코드**:
- FE: `frontend/src/features/memory/components/PromoteModal.tsx` — memory-specific (`memoryId` prop)
- BE: `POST /api/v1/workspaces/{wid}/memory/{memory_id}/promote` (memory only, 202 Accepted)
- 다른 4 도메인 promote endpoint 부재

**BE 구조 (4 endpoint 신설)**:
```
POST /api/v1/workspaces/{wid}/meetings/{meeting_id}/promote
POST /api/v1/workspaces/{wid}/notes/{note_id}/promote
POST /api/v1/workspaces/{wid}/inbox/{inbox_id}/promote
POST /api/v1/workspaces/{wid}/actions/{action_id}/promote
```

각 endpoint body schema (통일):
```python
class PromoteIn(BaseModel):
    target_workspace_id: uuid.UUID
```

각 도메인 service 의 `promote(item, target_wid)`:
- 메타데이터 복제 (deep copy + new UUID + target_workspace_id)
- 임베딩 복제 (각 도메인 별 ledger 구조 — Stage 2 verify)
- tombstone 마킹 (`promoted_to_workspace_id` 또는 등가)
- audit log 등재 (memory 패턴 재사용)

**FE shared component**:
- `frontend/src/features/memory/components/PromoteModal.tsx` → `frontend/src/components/shared/ItemPromoteModal.tsx`
- prop:
  ```typescript
  interface ItemPromoteModalProps {
    itemType: 'memory' | 'meeting' | 'note' | 'inbox' | 'action';
    itemId: string;
    sourceWorkspaceId: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
  }
  ```
- itemType 기반 endpoint dispatch (5 URL pattern)

**4 entry point mount**:
- `frontend/src/app/(app)/meetings/[id]/page.tsx` — detail dropdown 메뉴
- `frontend/src/app/(app)/notes/page.tsx` — note 카드 액션
- `frontend/src/app/(app)/inbox/page.tsx` — inbox 항목 액션
- `frontend/src/app/(app)/actions/page.tsx` — action 카드 액션 (detail 부재 시 list 에서 직접)

### D2 — Settings re-design

**현 상태**:
- `frontend/src/app/(app)/settings/page.tsx` + `features/members/components/{member-list, invite-manager}.tsx`
- shadcn Tabs 3 tab: 멤버 / 초대 / 일반

**Fix 방향**:
1. Stage 3 Task 1 에서 `/design-shotgun` 실행 — 현재 코드 + dogfood 불만 입력 → 4-6 variant
2. 사용자 1 안 선택
3. visual-only 구현 (RBAC/mutation 로직 손대지 않음)
4. 산출물 doc 경로 (예상): `~/.gstack/projects/woosung-dev-kairos/designs/sprint-23-settings-20260519/`

### F1~F4 — 문서 patch

| ID | 대상 | 변경 |
|---|---|---|
| F1 | `docs/TODO.md` + `docs/REFACTORING-BACKLOG.md` | Sprint 19/20/21/22 closeout + CO-1~14 등재 + Next Actions Sprint 23 갱신 |
| F2 | `~/.claude/projects/.../memory/project_sprint22_done.md` | merge SHA `22da49b` 반영 + 6 follow-up commit 등재 |
| F3 | `docs/dev-log/2026-05-19-sprint22-result-report.html` | Codex 2차 APPROVE 반영 + CI final result |
| F4 | `frontend/e2e/tests/auth-relogin.spec.ts` | storageState key 정정 + skip 가드 제거 |

---

## 5. Section: Data Flow

### D3 Invalidation Flow (lock-in)

```
[User] dismiss click
  → useDismissInbox.mutate
  → POST /workspaces/{wid}/inbox/{id}/dismiss
  → BE: item.is_processed=True + commit (검증됨)
  → onSuccess: queryClient.invalidateQueries({ queryKey: inboxKeys.list(wid) })
  → useInbox(wid, { is_processed: false }) 재조회
  → BE: SELECT WHERE workspace_id=wid AND is_processed=false (pending 만)
  → FE: list 에서 dismissed 항목 부재 ✓
```

### D4 Promote Flow (도메인 무관 통일)

```
[User] ItemPromoteModal open (itemType, itemId)
  → POST /workspaces/{src_wid}/{itemType}/{itemId}/promote
       body: { target_workspace_id }
  → BE: source service.promote(item, target_wid)
       - 메타데이터 복제 (deep copy + new UUID)
       - 임베딩 복제 (도메인별 ledger)
       - tombstone 마킹
       - audit log 등재
  → 202 Accepted (BackgroundTask 패턴)
  → FE: invalidate { itemType }Keys.all + tombstone UI 표시
```

### D1 Workspace Switch Flow (post-fix 목표)

```
[User] click workspace option
  → handleSwitch(wid)
  → setActiveWorkspaceId(wid)  // Zustand persist
  → queryClient.invalidateQueries({
      predicate: q => q.queryKey[1] === oldWid  // workspace-scoped 만
    })
  → 자동 refetch (사이드바 / Today / Inbox / Projects / Actions)
  → dashboard useEffect 가 [currentWid] dep 으로 sync (render-time setState X)
```

---

## 6. Section: Error Handling

| 영역 | 처리 |
|---|---|
| **D1** | 진단 단계 console.error 로 fail point 잡음. fix 후 `router.refresh()` 실패 fallback (page reload prompt). race condition → useEffect dependency 명시. |
| **D3** | BE commit 실패 → 기존 try/except 유지. FE invalidate 실패 → toast + retry. Zod schema strict validate (Sprint 22 datetime 사례 재발 방지). |
| **D4** | `target_workspace_id == src_wid` → 400. target workspace 비 member → 403. 임베딩 복제 실패 → source rollback (BackgroundTask 패턴). 이미 promote 된 item 재promote → idempotent (audit log 추가). |
| **D2** | visual-only 변경 우선. RBAC / mutation 로직 손대지 않음. |
| **F1~F4** | 텍스트 patch — 에러 영역 없음. |

---

## 7. Section: Testing

| 축 | 검증 |
|---|---|
| **D1** | Playwright spec 1 추가 — `workspace-switch.spec.ts`: 2 workspace → 스위처 클릭 → URL/sidebar/today-feed 새 workspace data 표시. CI e2e PASS. |
| **D3** | BE pytest 1 추가 — `test_inbox_dismiss_then_list_excludes.py`: dismiss → list `is_processed=false` 호출 → 해당 item 부재 verify. |
| **D4 BE** | 각 도메인 service.promote 단위 test 4 도메인 × 4 case = 16 (메타데이터 + 임베딩 + tombstone + 보안). |
| **D4 FE** | Vitest — `ItemPromoteModal` 5 itemType 모두 정확한 endpoint dispatch verify (msw mock). |
| **D2** | 구현 후 design-shotgun 시안 캡처 vs 실 화면 80%+ 일치 (사용자 manual verify). |
| **F4** | G7 spec runtime — Playwright reporter 에서 G7 PASS verify. |
| **회귀** | pytest 352+ → 369+ (D3 +1, D4 BE +16). pyright 신규 코드 0. FE typecheck/lint 0. Codex 1차/2차 APPROVE. |

---

## 8. Success Criteria (PR 머지 가능 기준)

### 자동 회귀
- ✅ pytest 369+ PASS / 0 fail / baseline 회귀 0
- ✅ pyright 본 sprint 신규 코드 0 errors
- ✅ FE typecheck 0 / lint 0 / build 12/12 OK
- ✅ Playwright 17+ passed + 6 skipped (G7 활성화)
- ✅ alembic drift gate PASS

### 사용자 수동
- ✅ D1: 워크스페이스 스위처 클릭 → 새 workspace 컨텍스트 모든 영역 새 데이터
- ✅ D2: Settings 시안 vs 실 구현 80%+ 일치
- ✅ D3: Inbox dismiss/classify → 재진입 → 처리 항목 부재
- ✅ D4: 5 entry point 모두에서 워크스페이스 이동 가능
- ✅ F2/F3: memory + HTML 보고서 fact-check (squash SHA 일치)
- ✅ F4: G7 spec CI PASS

### Codex 게이트
- ✅ 1차 plan review APPROVE 또는 REVISE 100% 수락
- ✅ 2차 diff review APPROVE

### PR 게이트
- ✅ `gh pr view <N> --json baseRefName` → "main" 확인 (`feedback_stack_pr_base_check`)
- ✅ CI 5/5 PASS

---

## 9. 사용자 결정 사항 (Stage 진행 중 필요)

| 결정 | 시점 |
|---|---|
| Stage 3 Task 1: design-shotgun 4-6 variant 중 1 안 선택 | Task 1 진입 시 |
| (필요 시) D1 진단 결과가 코드 외부 원인일 때 carry-over 결정 | Stage 4 진단 후 |
| (필요 시) scope overrun (35h+ 진행) 시 D2 또는 D4 일부 carry-over | Stage 3 진행 중 |

---

## 10. References

- handoff: `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint23_kickoff_handoff.md`
- 직전 sprint: `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint22_done.md`
- workflow: `.ai/templates/workflow.md` Stage 0~6
- atomic update: `.ai/common/global.md` §2 (feedback `atomic_doc_update`)
- 헌법: `CONTEXT-MAP.md` §6 불변식 I-18 (Promotion 정책)
- domain CONTEXT: `backend/src/{inbox,meetings,notes,actions,memory}/CONTEXT.md`
- 기존 memory promote: `backend/src/memory/router.py:125-143` + `backend/src/memory/service.py` `promote` 메서드
- 기존 PromoteModal: `frontend/src/features/memory/components/PromoteModal.tsx`
