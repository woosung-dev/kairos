# Sprint 23 — cozy-crystal Task Plan

> spec doc: [`2026-05-19-sprint23-cozy-crystal-design.md`](../specs/2026-05-19-sprint23-cozy-crystal-design.md)
> branch: `sprint-23/cozy-crystal`
> baseline: main HEAD `22da49b`
> 추정: ~22-30h
> 단일 PR 통합 (dogfood D1~D4 + sync F1~F4)

---

## 0. Task 의존성 + 진행 순서

```
Task 0 (F1 docs sync) ─┐
                        │
                        ├─→ Task 2 (D4 BE)   ──┐
Task 1 (D2 shotgun) ────┤     │                │
       ↓ (사용자 결정)   │     │                │
Task 3 (D2 구현) ───────┘     │                │
                              │                │
                              └─→ Task 4 (D4 FE) ──┐
                                                    │
Task 5 (D1 진단/fix) ──────────────────────────────┤
                                                    │
Task 6 (D3 진단/fix) ──────────────────────────────┤
                                                    │
                                                    └─→ Task 7 (F2/F3/F4 closeout)
                                                          ↓
                                                       Stage 4 Codex 2차
                                                          ↓
                                                       Stage 5 PR push
                                                          ↓
                                                       Stage 6 closeout
```

**병렬 가능**:
- Task 0 + Task 1 (D2 shotgun 시작) 동시
- Task 2 (D4 BE) 진행 동안 Task 1 사용자 결정 대기
- Task 5 / Task 6 sub-agent 직렬 (worktree 1개)

---

## Task 0. F1 docs sync (30min-1h, controller 직접)

### 산출물
- `docs/TODO.md` 갱신 — Sprint 19/20/21/22 Recently Completed 등재 + CO-1~14 carry-over + Next Actions Sprint 23
- `docs/REFACTORING-BACKLOG.md` 갱신 — BL-017 ✅ verify + CO-1~14 carry-over BL 등재

### Step
1. 현재 `docs/TODO.md` 의 "Next Actions (Sprint 19 v3)" 섹션 → "Next Actions (Sprint 23 cozy-crystal)" 로 교체
2. "Recently Completed" 섹션 상단에 Sprint 19/20/21/22 closeout 4 entry 추가
3. CO-1~14 carry-over 항목 → `docs/REFACTORING-BACKLOG.md` 의 적절한 BL 등재 (이미 BL-* 으로 등재된 항목과 cross-link)
4. BL-017 (Mobile FAB collision) 가 Sprint 22 OBN-04 에서 해소됐는지 git log 로 verify → ✅ mark
5. Blocked 섹션 = Clerk Production / Sentry DSN / 외부 user dogfooding 유지
6. commit: `docs: Sprint 23 cozy-crystal kickoff — TODO + BACKLOG sync (Sprint 19-22 closeout 등재)`

### 검증
- TODO.md 의 "Next Actions" 가 D1~D4 + F1~F4 8건 모두 명시
- BACKLOG.md 의 CO-1~14 BL 등재 또는 기존 BL 와 cross-link

---

## Task 1. D2 design-shotgun 실행 → 사용자 결정 (3-4h, gap 동안 Task 2 병렬)

### 산출물
- `~/.gstack/projects/woosung-dev-kairos/designs/sprint-23-settings-20260519/` (4-6 variant PNG + design-board.html + approved.json)
- 사용자 1 안 선택 결과

### Step
1. `/design-shotgun` 실행 — 현재 Settings 페이지 코드 + 사용자 dogfood 불만 (시안 불일치 보고) 입력
2. 4-6 variant 생성 대기
3. 사용자에게 design-board.html link 제시 + 1 안 선택 요청 (AskUserQuestion)
4. 선택 결과 → approved.json 기록 → Task 3 진입 게이트 해제

### 검증
- design-board.html 열람 OK
- 사용자 선택 1 안 lock-in

### Failure criteria
- 사용자가 4-6 variant 모두 reject → carry-over Sprint 24 + 본 sprint 에서 D2 제외

---

## Task 2. D4 BE — Promotable 추상화 + 4 도메인 endpoint (6-8h, sub-agent 분할 권장)

### 산출물
- `backend/src/{meetings,notes,inbox,actions}/router.py` — promote endpoint 4개 신설
- `backend/src/{meetings,notes,inbox,actions}/service.py` — promote 메서드 4개 신설
- (필요 시) `backend/src/common/promote_base.py` — Promotable 추상화 클래스
- 도메인별 임베딩 복제 ledger 코드 (각 도메인 패턴)
- 회귀 test: `backend/tests/{meetings,notes,inbox,actions}/test_*_promote.py` 4 파일 + ~16 cases

### Step (각 도메인 sub-agent 직렬, Sprint 22 학습 = 큰 task 4 sub-task 로 분할)

#### Step 2.1 — 기존 memory promote 구조 분석
- `backend/src/memory/router.py:125-143` + service.promote + 임베딩 복제 로직 + tombstone 컬럼 verify
- 다른 도메인 모델에 tombstone 컬럼 (`promoted_to_workspace_id` 또는 등가) 부재 시 alembic migration 필요한지 결정

#### Step 2.2 — meetings promote (가장 복잡, transcript 임베딩 복제)
- Sub-agent dispatch:
  - `POST /workspaces/{wid}/meetings/{meeting_id}/promote` router endpoint
  - `MeetingService.promote(meeting_id, target_wid)` — 메타데이터 복제 + transcript segments 복제 + embedding chunks 복제 + tombstone
  - audit log: `meeting_promotion_audit` 등재 (memory 패턴)
  - pytest 4 cases: 성공 / target 비 member 403 / 동일 workspace 400 / 이미 promote 재promote idempotent
- Atomic Update: `backend/src/meetings/CONTEXT.md` §엔드포인트 + §의존 + `docs/api/endpoints.md`

#### Step 2.3 — notes promote
- Sub-agent dispatch:
  - notes router + service.promote + note_chunks 복제
  - pytest 4 cases (동일 패턴)
- Atomic Update: `backend/src/notes/CONTEXT.md` + `docs/api/endpoints.md`

#### Step 2.4 — inbox promote
- Sub-agent dispatch:
  - inbox router + service.promote — inbox item 은 임베딩 없을 가능성 (Stage 1 spec verify) → 메타데이터만 복제
  - pytest 4 cases
- Atomic Update: `backend/src/inbox/CONTEXT.md` + `docs/api/endpoints.md`

#### Step 2.5 — actions promote
- Sub-agent dispatch:
  - actions router + service.promote — action 은 임베딩 없음 → 메타데이터 + meeting reference 복제
  - pytest 4 cases
- Atomic Update: `backend/src/actions/CONTEXT.md` + `docs/api/endpoints.md`

#### Step 2.6 — (선택) Promotable abstract base 추출
- 4 도메인 service.promote 의 공통 로직 (메타데이터 복제 + tombstone + audit) 을 `backend/src/common/promote_base.py` 의 추상 클래스로 추출
- 도메인별 임베딩 복제만 override
- 헌법 I-18 변경 없음, 적용 도메인 확장 명시 (`CONTEXT-MAP.md` §6)
- Atomic Update: `CONTEXT-MAP.md` §6 (I-18 적용 도메인 확장 명시) + `backend/CONTEXT.md` §4

### 검증
- pytest 16 cases PASS (도메인 4 × case 4)
- alembic drift gate PASS (모델 변경 시 migration 반영)
- pyright 신규 코드 0 errors
- 기존 memory promote 회귀 0 (~5 test PASS)

---

## Task 3. D2 시안 구현 (2-3h, Task 1 결정 후)

### 산출물
- `frontend/src/app/(app)/settings/page.tsx` 갱신 + (필요 시) sub-routes 추가
- `frontend/src/features/members/components/*` 의 layout/style 조정

### Step
1. Task 1 의 사용자 선택 시안 캡처 (`~/.gstack/.../sprint-23-settings-20260519/variant-X.png`) 기반 layout/spacing/typography 적용
2. Tabs 구조 유지 (멤버 / 초대 / 일반) — 시안에서 구조 변경 명시되지 않으면
3. visual-only — RBAC / mutation hook 손대지 않음
4. 시안 vs 실 화면 80%+ 일치 manual verify
5. commit: `feat(settings): design-shotgun 시안 X 적용 (D2 dogfood fix)`
6. Atomic Update: design-shotgun 시안 doc cross-link을 commit 메시지 또는 PR 본문에 포함

### 검증
- 사용자 manual verify 시안 80%+ 일치
- 기존 settings 동작 회귀 0 (멤버 추가 / 초대 발급 / 임계값 변경 모두 동작)
- FE typecheck/lint 0

---

## Task 4. D4 FE — ItemPromoteModal 추출 + 4 entry point mount (5-7h, sub-agent 분할)

### 산출물
- `frontend/src/components/shared/ItemPromoteModal.tsx` — 추출된 generic component
- `frontend/src/features/memory/components/PromoteModal.tsx` — deprecated 또는 wrapper 로 유지
- `frontend/src/app/(app)/{meetings/[id],notes,inbox,actions}/*` — 4 entry point mount
- Vitest: `ItemPromoteModal` 5 itemType endpoint dispatch verify

### Step

#### Step 4.1 — ItemPromoteModal 추출
- Sub-agent dispatch:
  - `frontend/src/features/memory/components/PromoteModal.tsx` 의 로직을 `frontend/src/components/shared/ItemPromoteModal.tsx` 로 이전
  - prop signature 변경: `{ memoryId }` → `{ itemType, itemId, sourceWorkspaceId, open, onOpenChange }`
  - itemType 기반 endpoint dispatch (5 URL pattern: memory/meeting/note/inbox/action)
  - 기존 memory 사용처 (`RecallResultCard` 등) 의 호출을 `<ItemPromoteModal itemType="memory" itemId={memoryId} ... />` 로 갱신
  - Vitest 신규 spec: 5 itemType 모두 정확한 endpoint dispatch verify (msw mock)
- Atomic Update: `docs/architecture/directory-map.md` frontend tree 갱신

#### Step 4.2 — meetings detail mount
- `frontend/src/app/(app)/meetings/[id]/page.tsx` 에 "워크스페이스 이동" dropdown 메뉴 추가 (DropdownMenuItem)
- 클릭 시 `<ItemPromoteModal itemType="meeting" itemId={meetingId} sourceWorkspaceId={activeWid} ... />` 열림
- Atomic Update: (FE 라우트 만 — frontend 도메인 CONTEXT.md 없으면 skip)

#### Step 4.3 — notes mount
- `frontend/src/app/(app)/notes/page.tsx` 의 note 카드에 "워크스페이스 이동" 액션 추가
- 카드 ContextMenu 또는 dropdown 패턴

#### Step 4.4 — inbox mount
- `frontend/src/app/(app)/inbox/page.tsx` 의 SmartInbox 카드에 "워크스페이스 이동" 액션 추가
- dismiss/classify 와 함께 위치

#### Step 4.5 — actions mount
- `frontend/src/app/(app)/actions/page.tsx` 의 action 카드에 "워크스페이스 이동" 액션 추가
- detail 라우트 부재 시 list 에서 직접

### 검증
- 5 entry point 모두에서 promote 가능 (manual)
- Vitest 5 cases PASS
- FE typecheck/lint 0
- memory promote 기존 동작 회귀 0

---

## Task 5. D1 진단 + minimal fix (2-4h, controller 직접 권장)

### 산출물
- WorkspaceSwitcher / store / dashboard fix
- 회귀 spec: `frontend/e2e/tests/workspace-switch.spec.ts` 신규 1개

### Step

#### Step 5.1 — Playwright reproduce
1. 로컬 dev 기동 (`pnpm dev` + `uvicorn`)
2. Playwright codegen 또는 manual click — 워크스페이스 스위처 옵션 클릭
3. 관찰:
   - Network tab: 새 workspace 의 API 호출 발생?
   - Application tab → localStorage.kairos-workspace: activeWorkspaceId 변경?
   - Console: error log?
   - React DevTools: dashboard component re-render?

#### Step 5.2 — 진단 결과 기반 minimal fix
- 가설 (1) 확정: `queryClient.clear()` → `invalidateQueries({ predicate })` 로 변경
- 가설 (2) 확정: `dashboard/page.tsx:124-126` 의 render-time setState → useEffect 로 이동
- 가설 (3) 확정: `router.refresh()` 제거 (invalidate 로 충분)
- 가설 둘 이상 또는 코드 외부 원인: 진단 결과 정리 후 사용자 보고 → 결정

#### Step 5.3 — 회귀 spec 작성
- `workspace-switch.spec.ts`: 2 workspace 시드 → 스위처 클릭 → URL/sidebar/today/inbox 모두 새 workspace data 표시
- skip 가드 없이 활성

#### Step 5.4 — Atomic Update
- `frontend/src/features/workspaces/components/WorkspaceSwitcher.tsx` / `store.ts` / `app/(app)/dashboard/page.tsx` 변경
- FE CONTEXT.md 없으면 skip

### 검증
- Playwright workspace-switch.spec.ts PASS
- 5 area (사이드바 / Today / Inbox / Projects / Actions) 모두 새 workspace data 표시 manual
- FE typecheck/lint 0

---

## Task 6. D3 진단 + FE explicit params (3-5h, controller 직접 권장)

### 산출물
- FE `useInbox` 의 explicit params 갱신 또는 Zod schema fix
- 회귀 pytest: `backend/tests/inbox/test_dismiss_then_list_excludes.py` 신규 1개

### Step

#### Step 6.1 — BE response verify
1. 로컬 BE 기동
2. curl 또는 Playwright Network tab — dismiss → list 호출:
   ```bash
   curl -X POST $BE/api/v1/workspaces/$WID/inbox/$ID/dismiss -H "Authorization: Bearer $TOKEN"
   curl $BE/api/v1/workspaces/$WID/inbox -H "Authorization: Bearer $TOKEN" | jq '.[] | {id, is_processed}'
   ```
3. response 의 필드명 (`is_processed` snake_case vs `isProcessed` camelCase) verify

#### Step 6.2 — 진단 결과 기반 fix
- 가설 (1) (가장 강함, field name mismatch):
  - FE Zod schema 의 `InboxItem` 에 `is_processed` field 추가 또는 `.transform(camelCase)` 적용
  - BE response transformer 가 camelCase 변환 안 한다면 BE 가 truth
- 가설 (2) (invalidate queryKey mismatch):
  - `useDismissInbox().onSuccess` 의 queryKey 가 `inboxKeys.list(wid)` 와 동일한지 verify
  - `useInbox` 의 queryKey 와 일치 강제
- 가설 (3) (Sprint 19 response shape 변경):
  - PR #88-91 diff 의 inbox endpoint 부분 확인 + 회귀 차단

#### Step 6.3 — FE explicit params (가설과 무관, 권장)
- `frontend/src/features/inbox/hooks.ts:21-52` `useInbox(wid, params?)` → `useInbox(wid, params = { is_processed: false })` 기본값 설정
- `smart-inbox.tsx:44` 호출은 그대로 (params 생략 시 pending 만 반환)
- `smart-inbox.tsx:94-95` client filter 단순화 또는 제거

#### Step 6.4 — 회귀 pytest 작성
- `test_dismiss_then_list_excludes.py`:
  ```python
  async def test_dismiss_then_list_excludes(client, inbox_factory, user_token):
      item = await inbox_factory(workspace_id=WID, is_processed=False)
      await client.post(f"/workspaces/{WID}/inbox/{item.id}/dismiss", headers=auth)
      resp = await client.get(f"/workspaces/{WID}/inbox?is_processed=false", headers=auth)
      assert all(i["is_processed"] is False for i in resp.json())
      assert item.id not in [i["id"] for i in resp.json()]
  ```

#### Step 6.5 — Atomic Update
- `frontend/src/features/inbox/hooks.ts` 변경 → FE CONTEXT 없으면 skip
- `backend/src/inbox/CONTEXT.md` 변경 없음 (BE 는 정상 verify)

### 검증
- pytest dismiss_then_list_excludes PASS
- manual: Inbox dismiss → 다른 page → Inbox 재진입 → 처리 항목 부재
- FE typecheck/lint 0

---

## Task 7. F2 / F3 / F4 closeout 일괄 patch (1.5h, controller 직접)

### F2 — memory `project_sprint22_done.md` final 갱신 (15min)

#### Step
1. 실 git log 로 PR #97 squash SHA verify (`22da49b`)
2. 6 follow-up commit (e0cd4e4 / 79a7118 / 2d7d1f3 / f49e006 / 69a6db8 / 7d97d5f) git log 로 verify
3. memory file 의 "merge SHA: pending" → "merge SHA: `22da49b`"
4. commits 표에 6 follow-up 추가

### F3 — HTML 결과 보고서 final 갱신 (30min)

#### Step
1. `docs/dev-log/sprints/2026-05-19-sprint22-result-report.html` 의 "Codex 2차 진행 중" → "**APPROVE** (3 P2 finding 100% 수락)" 갱신
2. e2e baseline fix 4 commit timeline 추가 (`2d7d1f3` ~ `7d97d5f`)
3. CI final result 추가 (5/5 PASS, run 26068170657)

### F4 — G7 spec storageState key fix (30min)

#### Step
1. `frontend/e2e/tests/auth-relogin.spec.ts` 의 `localStorage.getItem("activeWorkspaceId")` 호출 찾음
2. `JSON.parse(localStorage.getItem("kairos-workspace") ?? "{}").state?.activeWorkspaceId` 로 정정
3. skip 가드 제거 → 실 검증 활성화
4. (옵션) local 에서 Playwright G7 spec PASS verify

### 통합 commit
- `chore: Sprint 22 closeout sync (F2 memory + F3 HTML 보고서 + F4 G7 spec storageState)`

---

## Atomic Update §4 매트릭스 (강제, PR 본문에 첨부)

| 코드 변경 | 동시 갱신 docs |
|---|---|
| `backend/src/inbox/router.py` (D3 + D4 promote) | `backend/src/inbox/CONTEXT.md` §엔드포인트 + `docs/api/endpoints.md` |
| `backend/src/inbox/service.py` (D3 + D4 promote) | `backend/src/inbox/CONTEXT.md` §의존 |
| `backend/src/{meetings,notes,actions}/router.py` (D4) | 각 도메인 `CONTEXT.md` §엔드포인트 + `docs/api/endpoints.md` |
| `backend/src/{meetings,notes,actions}/service.py` (D4 promote) | 각 도메인 `CONTEXT.md` §의존 |
| Promotable 추상화 신설 (D4 Step 2.6, 선택) | `CONTEXT-MAP.md` §6 (I-18 적용 도메인 확장 명시) + `backend/CONTEXT.md` §4 |
| `frontend/src/features/memory/components/PromoteModal.tsx` → `frontend/src/components/shared/ItemPromoteModal.tsx` (D4) | `docs/architecture/directory-map.md` frontend tree |
| `frontend/src/app/(app)/settings/*` (D2) | design-shotgun 시안 doc cross-link in PR 본문 |
| `docs/TODO.md` + `docs/REFACTORING-BACKLOG.md` (F1) | 본 file 자체 |

**PR 본문 "Docs sync" 별도 섹션 필수** — `git diff --stat docs/ backend/**/CONTEXT.md CONTEXT-MAP.md` 결과 첨부.

---

## Stage 4 — Codex 2차 diff review

### 진행
```bash
cd /Users/woosung/project/agy-project/kairos-sprint-23
codex review --base origin/main   # PROMPT 없이, --base 만
```

### Verdict 분기
- **APPROVE** → Stage 5 진입
- **REVISE** → finding 분석 + 100% 수락 또는 reject 사유 명시 → polish commit → 재실행

---

## Stage 5 — PR push + create

### 진행
```bash
cd /Users/woosung/project/agy-project/kairos-sprint-23
git push -u origin sprint-23/cozy-crystal

gh pr create --draft \
  --base main \
  --head sprint-23/cozy-crystal \
  --title "Sprint 23 cozy-crystal: dogfood fix (D1~D4) + Sprint 22 sync (F1~F4)" \
  --body-file /tmp/sprint-23-pr-body.md

# 머지 직전 base 확인 (필수)
gh pr view <N> --json baseRefName,headRefName,state
# baseRefName = "main" 확인
```

### PR 본문 필수 섹션
1. ## Summary — 8건 (D1~D4 + F1~F4) 1줄 요약
2. ## Code changes — backend / frontend 영역별
3. ## Docs sync — Atomic Update 매트릭스 적용 결과 (git diff --stat)
4. ## Test plan — pytest + pyright + FE typecheck + Playwright + manual verify checklist
5. ## Codex review — 1차/2차 verdict + finding 수락 표
6. ## R5/R11 — scope overrun 또는 carry-over 결정 사항

---

## Stage 6 — closeout

### Step
1. 머지 후 main HEAD verify (`git fetch && git log origin/main --oneline -3` → squash SHA 확인)
2. worktree 정리:
   ```bash
   cd /Users/woosung/project/agy-project/kairos
   git worktree remove ../kairos-sprint-23
   git branch -D sprint-23/cozy-crystal
   ```
3. memory `~/.claude/projects/.../memory/project_sprint23_cozy_crystal_done.md` 신설
4. `MEMORY.md` 인덱스 1줄 추가
5. (선택) HTML 결과 보고서 작성 `docs/dev-log/sprints/2026-05-19-sprint23-result-report.html` (Sprint 22 패턴 재현)
6. BACKLOG/TODO final sync — Sprint 23 completed mark + Sprint 24 진입 준비
7. 사용자 보고 — Sprint 24 (ADR-019 Phase B) 진입 준비 완료

---

## 진행 시 사용자 게이트 (사용자 결정 필요 시점)

| 시점 | 결정 |
|---|---|
| Task 1 design-shotgun 결과 후 | 4-6 variant 중 1 안 선택 |
| Task 5 D1 진단 결과 후 (코드 외부 원인 시) | carry-over Sprint 24 또는 추가 진단 |
| Task 6 D3 진단 결과 후 (가설 모두 reject 시) | 추가 진단 또는 carry-over |
| Stage 4 진행 중 scope overrun (35h+) | D2 또는 D4 일부 carry-over |
| Stage 5 PR 머지 직전 | base = main 확인 (`feedback_stack_pr_base_check`) |
