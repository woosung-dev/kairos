# Sprint 19 PR #1 handoff v2 (2026-05-18, C1~C7 + Codex 2차 PASS)

> 다음 다음 세션 첫 read = 본 doc → `docs/dev-log/sprint-19-plan.md` §9 (v3 lock-in) → `backend/tests/integration/test_workspace_idor_matrix.py` (잔여 5 도메인 placeholder skip).

---

## 1. 본 세션 (2026-05-18) 완료 상태

### branch: `sprint-19/tenant-boundary-hardening` — 9 commits ahead `origin/main`, push 안 함

```
f6a0b96 fix(sprint-19): BUG-C01-EXT v3 C7 — Codex 2차 review Major 1 + Major 2 + Minor 1 (REVISE → PASS)
3556445 test(sprint-19): BUG-C01-EXT v3 workspace integrity audit 3 케이스 (Codex F-5)
1fe1db6 test(sprint-19): BUG-C01-EXT v3 real DB cross-tenant integration 4 도메인 (Codex F-3)
9296816 fix(sprint-19): BUG-C01-EXT v3 actions 3 endpoint + 3 secondary FK 검증 (Codex F-1/F-2/F-6)
221cb6f fix(sprint-19): BUG-C01-EXT v3 inbox 3 endpoint + classify project_ids secondary FK (Codex F-1/F-2/F-6)
fe3c53f fix(sprint-19): BUG-C01-EXT v3 notes 6 endpoint + delete pipeline 옵션 A + project_id secondary FK (Codex F-1/F-2/F-6)
8021f4f fix(sprint-19): BUG-C01-EXT v3 meetings 6 endpoint + pipeline 진입점 workspace_id 강제 (Codex F-1)
cc11b7a test(sprint-19): BUG-C01-EXT v3 IDOR matrix 골격 (failing TDD, 45 endpoint) — 직전 세션
834738c docs(sprint-19): v3 plan lock-in — tenant/auth boundary scope, P0 9건, matrix 45 endpoint — 직전 세션
```

### 검증 결과 (Verification)

```
backend pytest tests/meetings tests/notes tests/inbox tests/actions tests/integration/
→ 76 passed + 5 skipped (잔여 도메인 placeholder)
  - meetings 12 + notes 8 + inbox 13 + actions 18 + matrix 19 + real DB 4 + audit 3 = 77

placeholder 5 = projects / memory / rag / workspaces / upload (다음 다음 세션 진입)
```

### Codex evaluator 1차/2차 review 결과

- **1차 (BLOCK)** — F-1 (meetings pipeline 진입점) / F-2 (4 secondary FK) / F-3 (mock + real DB) / F-4 (404 lock-in) / F-5 (integrity audit) / F-6 (Tenant boundary 형식) 모두 사용자 결정 **수락**
- **2차 (REVISE → PASS)** — Major 1 (notes DELETE 204→404) / Major 2 (actions meeting_id forwarding) / Minor 1 (fail-closed repo None) 모두 C7 반영

### Codex 2차 잔존 Minor

- **Minor 2**: inbox.classify 가 source_type=="meeting" 일 때 item.source_id meeting workspace 직접 검증 안 함. 현재 pipeline 생성 경로상 같은 workspace 보장 (by construction) 이지만 malformed row 시 mismatch 가능. **PR #2 composite FK 또는 BL 등재** 처리.
- **Minor 3**: `meetings/service.py:106` `find_projects_by_meeting(meeting_id)` 와 `meetings/pipeline_service.py:119` `add_meeting_link(meeting.id, project_id)` 는 projects 도메인 repository 변경 사항이라 **projects 도메인 commit (잔여 27 endpoint 안)** 에서 처리.

---

## 2. PR #1 진행률 = 18/45 endpoint = 40% + 추가 보안 가드 +5

| 도메인 | endpoint | 상태 | 회귀 |
|---|---|---|---|
| meetings | 6 | ✅ C1 + F-1 pipeline 진입점 + 8 mutation 시그니처 + matrix 6 | meetings 12 PASS |
| notes | 6 | ✅ C2 + F-2 project_id + 옵션 A + matrix 7 | notes 8 PASS |
| inbox | 3 | ✅ C3 + F-2 project_ids 전수 검증 + matrix 4 | inbox 13 PASS |
| actions | 3 | ✅ C4 + F-2 3 secondary FK + matrix 5 + C7 meeting_id forwarding | actions 18 PASS |
| **소계** | **18** | **C1~C4 완료** | |
| real DB integration | 4 | ✅ C5 (TestContainers cross-tenant) | 4 PASS |
| integrity audit | 3 | ✅ C6 (action_items/notes/meeting_project_links) | 3 PASS |
| projects | 11 | ⬜ 잔여 (다음 다음 세션) | placeholder skip |
| memory | 5 | ⬜ 잔여 | placeholder skip |
| rag | 1 | ⬜ 잔여 | placeholder skip |
| workspaces | 8 | ⬜ 잔여 (member 3 + invite 3 + main 2) | placeholder skip |
| upload | 2 | ⬜ 잔여 | placeholder skip |
| closeout | — | ⬜ `CONTEXT-MAP.md` §6 I-9 불변식 + matrix 45 전수 PASS commit | |

---

## 3. 다음 다음 세션 첫 행동 (PR #1 잔여 27 endpoint)

### Step 1: workspace 동기화

```bash
git -C /Users/woosung/project/agy-project/kairos-sprint-19 status     # clean, 9 commits ahead
git -C /Users/woosung/project/agy-project/kairos-sprint-19 log --oneline -10
```

### Step 2: matrix placeholder 5 도메인 확인

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-19/backend
uv run pytest tests/integration/test_workspace_idor_matrix.py -v 2>&1 | tail -10
# → 19 passed + 5 skipped (placeholders)
```

### Step 3: 잔여 도메인 진입 순서 — projects (11) 부터

1. **projects (11 endpoint)** — `backend/src/projects/{router,service,repository}.py`. service 호출 8건 (`grep -n find_by_id backend/src/projects/service.py`), add_meeting_link / find_projects_by_meeting workspace_id 강제 + meetings/service.py:106 + meetings/pipeline_service.py:119 호출자 동시 patch. ~3h. commit C8.
2. **memory (5 endpoint)** — `backend/src/memory/{router,service,repository}.py`. ~1.5h. commit C9.
3. **rag (1 endpoint)** — `backend/src/rag/router.py:24` (ask). ~30min. commit C10.
4. **workspaces (8 endpoint)** — main 2 + member 3 + invite 3. `find_member_by_id` / `find_invite_by_id` 시그니처 변경. ~2.5h. commit C11.
5. **upload (2 endpoint)** — `backend/src/upload/router.py:31,46`. file_key path 패턴 (BUG-UPL-OWN) 은 별도 PR #4. ~1h. commit C12.
6. **closeout C13**: `CONTEXT-MAP.md` §6 I-9 불변식 텍스트 patch + 매트릭스 45 전수 PASS 확인 + `docs/REFACTORING-BACKLOG.md` BL 등재 (Codex 2차 Minor 2 inbox source_id meeting workspace 검증 + Minor 3 projects find_projects_by_meeting).

### 잠재 3차 Codex review

C8~C12 완료 후 잔여 27 endpoint도 1차/2차 패턴 동일. PR #1 closeout 직전 codex review 1회 권장.

---

## 4. PR #1 진입 직전 [확인 필요] (다음 다음 세션 결정 사항)

- **MeetingProjectLink workspace 컬럼** — Sprint 19 PR #2 (BUG-C01-EXT-FK + alembic) 명시 분리. 별도 PR.
- **inbox.classify source_id meeting workspace 검증** (Codex 2차 Minor 2) — PR #1 잔여 또는 PR #2 composite FK 결정.
- **projects 도메인 visibility 권한 검증** (private project 검증) — 본 PR scope 외, 별도 BL.

---

## 5. Sprint 19 다음 PR 진입 (PR #1 머지 후)

PR #1 closeout commit C13 머지 → PR #2 (BUG-C01-EXT-FK composite FK + alembic 업그레이드) 진입.

- PR #2: composite FK 추가 (`action_items` + `notes` + `meeting_project_links`) + alembic migration + 기존 mismatch row backfill (`audit` SQL 결과 토대로)
- PR #3-#9: AUTH-WH / UPL-OWN / PROJ-DEL / PIPE-LLM / P1-05+P1-06 / C02+C03 / closeout

---

## 6. 위험 + 완화

- **메인 워크트리 main rebase 위험**: main에 hotfix 들어오면 `../kairos-sprint-19` 워크트리 rebase 필요. 본 세션 9 commits 무손실 보존 위해 다음 다음 세션 진입 직전 `git fetch origin main && git rebase origin/main` 권장.
- **잔여 27 endpoint 시간 예산**: 다음 다음 세션 ~7-9h 추정 (projects 가장 큼). 본 세션 ~10h 와 비슷.
- **fail-closed RuntimeError 운영 노출**: 새로 추가된 `RuntimeError("project_repo 필수")` 가 production 에서 발생하면 dependency provider 누락. Phase 6 dependencies.py 모두 fail-closed 통과 확인됨 — production 영향 0.
- **Codex 2차 verdict REVISE → C7 PASS**: 본 commit f6a0b96 으로 해소. 3차 review (다음 다음 세션) 에서 잔여 5 도메인 검증.

---

## 7. memory 갱신 사항

`~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint19_pr1_kickoff.md` 를 본 세션 완료 후 patch:
- 상태 = "9 commits ahead, push pending. PR #1 18/45 = 40% + 추가 보안 가드 5 (F-1~F-6 + 2차 Major/Minor)"
- 다음 다음 세션 진입 = projects 도메인 (11 endpoint) 부터

---

## 8. 본 세션 학습 (메인 세션 → 다음 다음 세션 전달)

1. **Codex 1차 BLOCK 가 plan v2 만들기에 가장 큰 가치** — 6 finding 모두 수락하니 PR scope 가 ~7-8h → ~13-17h 로 확장됐지만 보안 완성도가 압도적. 잔여 27 endpoint 도 동일 패턴 적용 권장.
2. **Codex 2차 REVISE → C7 PASS** — 메인 세션이 놓친 silent return / forwarding 누락 / fail-open 3건을 잡음. 잔여 도메인 진입 직전에도 동일 2차 review 권장.
3. **Generator-Evaluator + AskUserQuestion 일괄 승인 패턴** — 단일 세션 강행 ~13-17h 안에서 도메인별 commit ×8 회 stop 부담을 일괄 승인으로 흡수. 매번 stop 의도가 없으면 사용자 명시 받고 흐름 유지.
4. **fail-closed > fail-open** — F-2 secondary FK 검증에서 repo None silent skip 은 tenant hardening 코드로 약함. RuntimeError 차단이 옳음 (Codex 2차 Minor 1).
5. **mock + call_args.kwargs == value 값 동치** — `"workspace_id" in kwargs` 만으로는 false positive (값 틀려도 통과). 정확 비교가 옳음 (Codex F-3).
