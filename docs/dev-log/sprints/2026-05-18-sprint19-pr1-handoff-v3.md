# Sprint 19 PR #1 handoff v3 (2026-05-18, BUG-C01-EXT v3 종결 45/45 = 100%)

> 본 doc 은 PR #88 (4 도메인) 머지 후 잔여 27 endpoint + closeout 을 단일 세션에서 완료한 최종 handoff.
> 다음 진입 = PR #2 (BUG-C01-EXT-FK composite FK + alembic migration).

---

## 1. 본 세션 (2026-05-18) 완료 상태

### branch: `sprint-19/tenant-boundary-hardening-pt2` — 5 commits ahead `origin/main`

```
e18a81e fix(sprint-19): BUG-C01-EXT v3 C13a — Codex 2차 review F-1 inbox.classify source_id meeting workspace 검증
88f42fd fix(sprint-19): BUG-C01-EXT v3 C12 workspaces 8 endpoint + F-5 mutation WHERE (main 2 + member 3 + invite 3)
75180a2 fix(sprint-19): BUG-C01-EXT v3 C11 rag 1 + upload 2 endpoint (Codex F-2/F-6/F-7)
7c48ae4 fix(sprint-19): BUG-C01-EXT v3 C10 memory 5 endpoint + promote target_workspace_id (Codex F-4)
6f646e7 fix(sprint-19): BUG-C01-EXT v3 C9 projects 11 endpoint + cross-domain cascade (Codex 1차 F-1 BLOCK/F-3/F-4/F-6)
```

(closeout C13 commit 은 본 doc + CONTEXT-MAP + BL 등재 묶음, 본 commit 후 push)

### 검증 결과 (Verification)

```
backend pytest tests/ → 309 passed + 1 skipped (외부 R2 의존)
backend pytest tests/integration/ → 모든 도메인 matrix anchor + real DB + audit PASS (5 도메인 placeholder 0)
```

상세:
- meetings 12 + notes 8 + inbox 15 + actions 18 + projects 96 + memory 27 + rag 38 + workspaces 60+ 등
- matrix anchor 5 도메인 활성화: TestProjectsIDORMatrix 10 + TestMemoryIDORMatrix 4 + TestRagIDORMatrix 2 + TestWorkspacesIDORMatrix 8 + TestUploadIDORMatrix 3
- real DB: 7 (기존 4 + projects 3) + 신규 TestInboxClassifySourceMeetingRealDB 2
- audit: 4 (기존 3 + project_members 1)

---

## 2. PR #1 총 진행률 = 45/45 endpoint = 100%

| 도메인 | endpoint | 시점 | 회귀 |
|---|---|---|---|
| meetings | 6 | C1 (PR #88) | 12 PASS |
| notes | 6 | C2 (PR #88) | 8 PASS |
| inbox | 3 | C3 (PR #88) + C13a (source_id 검증) | 15 PASS |
| actions | 3 | C4 (PR #88) | 18 PASS |
| real DB integration | 4 | C5 (PR #88) | + projects 3 + inbox 2 = 9 |
| integrity audit | 3 | C6 (PR #88) | + project_members 1 = 4 |
| **projects** | **11** | **C9 (본 PR)** | 96 PASS |
| **memory** | **5** | **C10 (본 PR)** | 27 PASS |
| **rag** | **1** | **C11 (본 PR)** | 38 PASS |
| **upload** | **2** | **C11 (본 PR)** | matrix anchor only |
| **workspaces** | **8** (main 2 + member 3 + invite 3) | **C12 (본 PR)** | 60+ PASS |
| closeout | — | C13 (본 commit) | CONTEXT-MAP §6 I-9 정밀화 + BL-047/048 |

---

## 3. Codex evaluator 1차/2차 review 결과

### 1차 plan review (verdict BLOCK)
- 9 finding (F-1 BLOCK + F-2~F-6 MAJOR 5 + F-7~F-9 MINOR 3) 모두 수락
- 핵심 F-1: ProjectRepository 시그니처 변경 cascade — actions/inbox/notes/rag 호출자 전수 patch 강제
- plan v2 patch 후 ExitPlanMode

### 2차 diff review (verdict REVISE → C13a fix 후 PASS)
- F-1 MAJOR: inbox.classify 의 source_id (meeting_id) cross-tenant 검증 누락 — **C13a 에서 fix** (InboxService meeting_repo 동반 주입 + fail-closed)
- F-2 MAJOR: matrix endpoint forward test coverage 일부 → **BL-048 등재** (본 PR scope 외)

### 본 세션 학습 5건 (모두 적용 확인)
1. Codex 1차 BLOCK 의 plan v2 가치 — 9 finding 모두 수락 → BLOCK 해소 + scope 확장 ✓
2. Codex 2차 REVISE → fix 패턴 — silent return (inbox source_id) 자동 catch ✓
3. AskUserQuestion 일괄 승인 — C9~C13a 5 commits 단일 세션 ~6-9h ✓
4. fail-closed > fail-open — RuntimeError 차단 (memory/inbox/projects/actions/notes) ✓
5. mock + call_args.kwargs == value 정확 비교 — matrix anchor + endpoint forward ✓

---

## 4. 다음 세션 진입 (PR #1 머지 후 → PR #2)

### Step 1: 본 PR push + 머지

```bash
git -C /Users/woosung/project/agy-project/kairos-sprint-19 push -u origin sprint-19/tenant-boundary-hardening-pt2
gh pr create --base main --head sprint-19/tenant-boundary-hardening-pt2 --title "..."
```

### Step 2: PR #2 진입 (BUG-C01-EXT-FK composite FK + alembic)

- composite FK 추가 (`action_items` + `notes` + `meeting_project_links` + `project_members`)
- alembic migration 신설
- 기존 mismatch row backfill (audit SQL 결과 토대로, 본 PR audit 4 케이스 0 row PASS 이므로 backfill 0 예상)

### Step 3: Sprint 19 잔여 PR

- PR #3-#9: AUTH-WH / UPL-OWN / PROJ-DEL / PIPE-LLM / P1-05+P1-06 / C02+C03 / closeout

---

## 5. 잔여 BL (closeout C13 에 등재)

- **BL-047**: projects.repository find_projects_by_meeting / add_meeting_link cross-domain cascade 모니터링 (handoff v2 Codex 2차 Minor 3 후속)
- **BL-048**: Sprint 19 PR #1 matrix endpoint 전수 forward coverage 강화 (Codex 2차 F-2 finding)

(BL-046 = inbox.classify source_id 검증 finding 은 본 C13a 에서 fix — 등재 X, doc 기록만)

---

## 6. 위험 + 완화

- **branch 전략**: PR #88 merge commit 으로 인해 기존 branch rebase 시 conflict → 새 branch `sprint-19/tenant-boundary-hardening-pt2` 생성 (origin/main 기반) 선택 ✓ 사용자 결정 (b)
- **시그니처 cascade**: ProjectRepository / MemoryRepository / WorkspaceRepository 시그니처 변경의 호출자 grep + 전수 patch 완료 — pyright/pytest 모두 GREEN
- **dependencies.py 동반 주입**: projects (meeting_repo) + memory (workspace_repo) + inbox (meeting_repo) 모두 동일 session 으로 주입 — production fail-closed RuntimeError 없음 (DI 검증 완료)
- **MeetingProjectLink workspace 컬럼**: PR #2 명시 분리 (composite FK 별도)
- **새 PR 머지 시점**: 사용자 결정 (본 PR 별도 단계 승인 gate)

---

## 7. memory 갱신 사항

`~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint19_pr1_kickoff.md` 또는 신규 `project_sprint19_pr1_closeout.md`:
- 상태 = "본 PR (#?) push pending. BUG-C01-EXT v3 종결 45/45 = 100% (PR #88 18 + 본 PR 27 = 45)"
- 다음 = PR #2 (BUG-C01-EXT-FK composite FK + alembic)

---

## 8. 본 세션 (Phase 1~6) 학습 (다음 세션 전달)

1. **Codex 1차 plan review 가 BLOCK 출 가능성 매우 높음** — 모든 finding 수락 가치. F-1 (ProjectRepository cascade) 1건만으로도 본 patch scope ~3h → ~7h 로 확장. 단 안전성 압도적.
2. **Codex 2차 review 가 silent return / fail-open / forwarding 누락 자동 catch** — C13a inbox source_id 가 정확 예시. handoff v2 의 Minor 2 가 본 review 에서 MAJOR 로 승격 (정합).
3. **단일 세션 일괄 승인 + 5 commit 분할** — handoff v2 §8.3 패턴 그대로. ~7-9h 한 번에 흡수, retrospect 가능.
4. **fail-closed RuntimeError 패턴이 plan v2 patch 의 핵심 학습** — silent skip 가 generator 의 가장 큰 risk. 모든 repo None 시 RuntimeError 차단 + 단위 테스트.
5. **branch 전략 미리 결정** — PR merge 패턴 확인 (squash vs merge commit) 후 rebase 가능 여부 결정. squash 면 그대로 reset, merge 면 새 branch.

---

## 9. closeout commit (C13 = 본 commit)

본 doc + `CONTEXT-MAP.md` §6 I-9 정밀화 + `REFACTORING-BACKLOG.md` BL-047/048 등재 = 단일 commit.
