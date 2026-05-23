# Sprint 24 BL-066 — D1/D3 dogfood verify (정적 분석 진단)

> **일시**: 2026-05-20 (Sprint 24 diligent-beaver)
> **branch**: `sprint-24/diligent-beaver` (worktree `../kairos-sprint-24`)
> **baseline**: main HEAD `d659c03` (Sprint 23 squash)
> **접근**: 진단 first (R3 mitigation) — Playwright reproduce 는 Clerk 인증 + 실 user data 의존으로 사용자 manual carry-over

---

## 환경 진단

| 항목 | 상태 | 비고 |
|---|---|---|
| Backend dev server (port 8001) | ✓ 기동 OK, health 200 | sprint-24 worktree |
| Frontend `.env.local` | ✓ main worktree 에서 복사 완료 (Clerk dev key + API URL) | gitignored |
| Backend `.env` | ✓ DATABASE_URL Neon production | dev mode `APP_ENV=development` |
| alembic head | ✓ `9dd1a3b80431` (Sprint 24 변경 0) | Sprint 23 head |
| pytest baseline | ✓ **387 passed + 1 skipped** | BL-063 + BL-064 신규 8 case 포함 |
| FE typecheck | ✓ 0 errors | |
| FE vitest | ✓ **50 passed** | |

dev server 기동 자체는 가능. 단 D1/D3 시나리오 reproduce 는 다음 의존:
- **Clerk OAuth 인증** (Google) — Playwright MCP 자동화 한계 (사용자 manual 클릭 필요)
- **실 user data** — 여러 workspace 가 있는 user account + inbox 항목 다수 필요
- **본 sub-agent / Claude session 권한** — MCP browser_navigate 으로 Clerk OAuth 흐름 완주 어려움

→ **Playwright reproduce 는 사용자 manual carry-over**.

---

## D1 — WorkspaceSwitcher 정적 분석 (Sprint 23 commit `9e2eee2`)

### Sprint 23 fix 의도
1. `queryClient.clear()` → `queryClient.invalidateQueries({ predicate: ... })` (workspaces.list 보존 + workspace_id 의존 query 만 invalidate)
2. `router.refresh()` 호출 제거 (RSC 재페치 추가 트리거 → race condition 회피)
3. dashboard 의 render-time setState → useEffect 분리

### 현 코드 verify (`frontend/src/features/workspaces/components/WorkspaceSwitcher.tsx`)

```
line 41:  // Sprint 23 D1 fix: queryClient.clear() → predicate invalidate (ws list 보존)
line 45:  queryClient.invalidateQueries({ ...predicate... })  ✓
line 62:  // router.refresh() 제거: invalidateQueries 만으로 wid 의존 컴포넌트 모두 새 데이터.
line 63:  // Sprint 23 D1 진단 결과 — router.refresh() 가 RSC 재페치를 추가 트리거 → race.
```

→ **정적 분석 PASS**. 의도된 fix 가 정확히 코드에 반영. race condition 회피 + ws list 보존 패턴 lock-in.

### 사용자 manual 검증 시 확인 포인트
- WorkspaceSwitcher 트리거 클릭 → 다른 workspace 선택
- dashboard data 정확히 갱신 (이전 ws stale data 없음)
- ws list 자체는 잠깐도 사라지지 않음 (queryClient.clear() 폐기 효과)
- 새로고침 추가 trigger 없이 자연스러운 전환

---

## D3 — Inbox dismiss 정적 분석 (Sprint 23 commit `928fc7c`)

### Sprint 23 fix 의도
1. `useInbox(wid)` 와 `useInbox(wid, { isProcessed: false })` 가 같은 queryKey → 마지막 호출자의 params 가 실 fetch 결정 → 다른 callsite 의 의도 손상
2. queryKey 격리: `(wid, params)` 조합별 별도 cache entry
3. invalidate: `inboxKeys.byWorkspace(wid)` prefix 로 일괄 무효화
4. autoProcessed 그룹 (collapsed) 제거 — dismissed 항목 표시로 인한 사용자 혼란 차단
5. BE alias 정합: `isProcessed` camelCase param (Sprint 23 Codex 2.5차 P2)

### 현 코드 verify

`frontend/src/features/inbox/api.ts`:
```
line 8-9:  이전: useInbox(wid) 와 useInbox(wid, {isProcessed:false}) 가 같은 cache 사용 → 손상.
line 9:    이후: 각 (wid, params) 조합이 별도 cache entry. invalidate 시 inboxKeys.byWorkspace(wid) prefix 로 일괄.
line 31:   // Sprint 23 Codex 2.5차 P2 fix: BE router.py L22 가 alias="isProcessed" 강제 — snake_case 자동변환 X.
line 35:   searchParams.set("isProcessed", String(params.isProcessed));  ✓
```

`frontend/src/features/inbox/hooks.ts`:
```
line 22:  queryKey: inboxKeys.list(wid ?? "", params),  ✓ (params 포함)
line 54:  queryClient.invalidateQueries({ queryKey: inboxKeys.byWorkspace(wid) });  ✓ prefix
line 80:  queryClient.invalidateQueries({ queryKey: inboxKeys.byWorkspace(wid) });  ✓ prefix
```

`frontend/src/features/inbox/components/smart-inbox.tsx`:
```
line 4-5: 이전: useInbox(wid) 전체 → autoProcessed (collapsed) 그룹에 dismissed 항목 표시.
line 5:   이후: useInbox(wid, { isProcessed: false }) BE filter → 미처리만 list.
line 46:  useInbox(activeWorkspaceId ?? undefined, { isProcessed: false })  ✓
```

→ **정적 분석 PASS**. 의도된 fix 4가지 (queryKey 격리 / invalidate prefix / autoProcessed 그룹 제거 / camelCase param) 모두 코드에 정합.

### 사용자 manual 검증 시 확인 포인트
- Inbox 항목 dismiss 클릭 → 즉시 list 에서 사라짐
- 새로고침 후에도 dismiss 한 항목 미보임 (BE 의 `isProcessed=true` filter 정합)
- 다른 component (workspace switcher 등) 의 inbox count badge 도 즉시 갱신

---

## 결론

### BL-066 정적 분석 verdict: **PASS**

Sprint 23 D1 (`9e2eee2`) + D3 (`928fc7c`) commit 의 의도된 fix 가 현 코드 (main HEAD `d659c03`) 에 모두 정합 반영. 코드 차원의 회귀 위험 0.

### 잔여 작업 (사용자 manual carry-over → BL-068 등재)

| ID | 작업 | 추정 |
|---|---|---|
| BL-068 | D1 WorkspaceSwitcher Playwright/manual reproduce — Clerk 로그인 + 다중 ws account + dashboard data 갱신 verify | 30분 |
| BL-069 | D3 Inbox dismiss Playwright/manual reproduce — inbox 항목 다수 account + dismiss → list → reload 보존 verify | 30분 |

Playwright reproduce 시도 시 Clerk OAuth (Google) flow 자동화 한계 — 일반적으로:
- **방안 A**: Playwright `storageState` 캡쳐 (사용자 manual 1회 로그인 후 cookie state 저장) → spec 에서 재사용
- **방안 B**: Clerk dev mode 의 magic link/test user API 활용 (Sprint 22 OBN-01 의 test user 패턴)

이 두 방안 모두 사용자 또는 별도 sprint scope. **본 sprint BL-066 = 정적 분석 결과 closed, Playwright reproduce 는 carry-over**.

### Sprint 24 본 task closeout

- BL-066 = **closed (정적 분석)** — Sprint 23 fix 정합 확인
- BL-068 (NEW) + BL-069 (NEW) = carry-over (사용자 manual Playwright reproduce 또는 별도 sprint Clerk test user 인프라)

---

## 참조

- Sprint 23 commit `9e2eee2` — D1 WorkspaceSwitcher fix
- Sprint 23 commit `928fc7c` — D3 Inbox dismiss fix
- Sprint 23 Codex 2.5차 P2 — Inbox camelCase param alias fix (BE router.py L22 `alias="isProcessed"`)
- `docs/REFACTORING-BACKLOG.md` BL-066 entry (P2 — dogfood validation)
- 본 sprint plan v2.1 §Task 1 (BL-066 진단 first 강제 R3 mitigation)
