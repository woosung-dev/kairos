# Sprint 19 PR #1 handoff (2026-05-17, BUG-C01-EXT v3 골격 완료)

> 다음 세션 첫 read = 본 doc → `docs/dev-log/sprints/sprint-19-plan.md` §9 (v3 lock-in) → `backend/tests/integration/test_workspace_idor_matrix.py` (failing 골격).

---

## 1. 현재 상태 (2026-05-17 본 세션 종료 시점)

### 완료
- ✅ Sprint 19 v3 lock-in: 2차 codex review (VERDICT: BLOCK) 후 사용자 결정 4건 — scope = tenant/auth boundary, 새 P0 4건 모두 in, BUG-C01-EXT 범위 = 45 endpoint, 기간 2주 유지
- ✅ plan v3 최종화: `~/.claude/plans/read-docs-dev-log-sprint-19-plan-md-hazy-catmull.md` + 원본 `docs/dev-log/sprints/sprint-19-plan.md` §9 patch
- ✅ 워크트리 + 브랜치: `../kairos-sprint-19/` + `sprint-19/tenant-boundary-hardening` (main 기준)
- ✅ endpoint matrix lock-in: ripgrep으로 **45 endpoint** 확정 (메모리 5 + rag 1 발견, plan v3에서 누락)
- ✅ 회귀 테스트 골격: `backend/tests/integration/test_workspace_idor_matrix.py`
  - meetings 도메인 첫 failing test (`test_get_meeting_detail_passes_workspace_id_to_service`) PASS as failing
  - 도메인별 placeholder + TODO 마커
- ✅ docs/TODO.md Sprint 19 v3 진입 마크

### 미수행 (다음 세션)
- ⬜ PR #1 도메인별 fix commit 분할 진행 (10 commit, 42-60h)
- ⬜ PR #2~#9 stack 진행

---

## 2. 다음 세션 첫 행동 (PR #1 meetings 도메인 commit)

### Step 1: workspace ready 확인
```bash
cd /Users/woosung/project/agy-project/kairos-sprint-19
git status                          # On branch sprint-19/tenant-boundary-hardening
git log --oneline | head -5         # 본 세션 commit 1건만 (handoff + 골격)
```

### Step 2: failing TDD 한 번 더 확인
```bash
cd backend
uv run pytest tests/integration/test_workspace_idor_matrix.py::TestMeetingsIDORMatrix::test_get_meeting_detail_passes_workspace_id_to_service -x -v
# → FAILED: service.get_meeting_detail 호출 시 workspace_id 미전달 (예상)
```

### Step 3: meetings 도메인 fix (commit #1)
파일: `backend/src/meetings/router.py:82,93,109` + `backend/src/meetings/service.py:130,136,142`

변경 패턴:
1. `service.py` get_meeting_detail / export_meeting / get_meeting_status 시그니처에 `workspace_id: uuid.UUID` 필수 인자 추가
2. `repository.py` find_by_id / get_segments / get_summary 호출 시 `workspace_id` 전달
3. `router.py` 각 endpoint에서 path `workspace_id` 전달 (`service.method(meeting_id, workspace_id)`)
4. `meetings/pipeline_service.py` `export_meeting` 하위 호출 4건 (Codex H1) 동일 패턴
5. Atomic Update: `backend/src/meetings/CONTEXT.md` §엔드포인트 갱신 + `docs/api/endpoints.md` patch

기존 회귀 (현재 PASS인 meetings 테스트들)이 깨지지 않는지 확인:
```bash
uv run pytest tests/meetings/ -x
```

### Step 4: 나머지 endpoint test 활성화 (commit #1 또는 별도)
test 파일에서 `@pytest.mark.skip` 제거 + 본문 채움 (meetings 2/3 endpoint).

### Step 5: 도메인별 진행 순서
1. **meetings** (6 endpoint) — service.py:130,136,142 + pipeline_service.py
2. **notes** (6 endpoint) — service.py + pipeline_service.py:51,53 `delete_note_with_cleanup` (Codex H2)
3. **inbox** (3 endpoint)
4. **actions** (3 endpoint)
5. **projects** (11 endpoint, 가장 큰 분산) — service.py:172,202,210,111,162,214,231
6. **memory** (5 endpoint) — matrix lock-in 추가 발견
7. **rag** (1 endpoint, ask) — matrix lock-in 추가
8. **workspaces** (member 3 + invite 3 + main 2 = 8) — `find_member_by_id(member_id, workspace_id)` / `find_invite_by_id`
9. **upload** (2 endpoint) — file_key path 패턴은 PR #4 (BUG-UPL-OWN)에서 별도
10. **closeout**: `CONTEXT-MAP.md` §6 I-9 불변식 해소 commit + `test_workspace_idor_matrix.py` 45 전수 PASS 확인

각 도메인 commit마다:
- pytest 해당 도메인 + matrix 통합 PASS 확인
- Atomic Update: `backend/src/<domain>/CONTEXT.md` (존재 시) + `docs/api/endpoints.md`
- 사용자 commit 승인 받음 (CLAUDE.md Git Safety Protocol)

---

## 3. 환경 설정 메모

- 워크트리 .env: 메인 워크트리 `backend/.env` 카피 (본 세션에서 처리). 사용자 dev 키 그대로
- TestContainers PostgreSQL: 기존 conftest.py fixture (`integration_session`, `postgres_container`) 재사용
- 본 matrix test는 TestContainers 미사용 (dependency_overrides + AsyncMock 패턴)
- uv 환경: `uv run pytest` 표준

---

## 4. PR #1 진입 직전 [확인 필요] (사용자 결정)

PR #1 자체는 endpoint matrix lock-in 완료 (45개). 다음 PR 진입 시 [확인 필요]:
- PR #4 (BUG-UPL-OWN): 기존 R2 객체 backfill 정책
- PR #5 (BUG-PROJ-DEL): cascade vs archive only — 권장 archive
- PR #7 (BUG-P1-05): CSP report endpoint (BE vs Sentry)
- PR #8 (BUG-C03): Casual 페르소나 실제 진입점 재확인

---

## 5. 위험 + 완화 메모

- Sprint 19 총계 ~92-132h vs working hours ~80h. Day 10 진행률 측정 후 P1 (BUG-P1-06)을 Sprint 20로 이동 결정
- 메인 워크트리 main과 conflict 가능성: Sprint 19 머지 사이클 중 main에 hotfix 들어오면 rebase 필요. 메인 워크트리는 만지지 말 것
- alembic migration 2건 (PR #4 UPL-OWN + PR #5 PROJ-DEL): staging upgrade head 검증 + 양방향 (upgrade/downgrade) SQL 확인 필수
