# Sprint 19 PR #2 closeout — BUG-C01-EXT-FK composite FK + alembic (handoff v4)

> 본 doc 은 PR #88 (PR #1 도메인 18 endpoint) + PR #89 (PR #1 잔여 27 endpoint + closeout) + PR #90 (본 PR, BUG-C01-EXT-FK) 의 최종 handoff.
> 다음 진입 = PR #3 (AUTH-WH) 또는 사용자 결정.

---

## 1. 본 PR (#90) 완료 상태

### branch: `sprint-19/bug-c01-ext-fk` — origin/main (3f3679d, PR #89 머지 후) 기반

11 commits:

```
D1   3f2ed28 test(sprint-19): D1 BUG-C01-EXT-FK failing test (TDD failing first, Codex v2 F-1/F-5)
D2   6c43d14 feat(sprint-19): D2 BUG-C01-EXT-FK alembic 단일 revision — 4 entity composite FK + mpl.workspace_id
D3a  a1d99a0 feat(sprint-19): D3a BUG-C01-EXT-FK Project UQ(id, workspace_id) model sync (Codex v2 F-2 BLOCK fix)
D3   f808351 feat(sprint-19): D3 BUG-C01-EXT-FK meetings UNIQUE(id, workspace_id) — composite FK target
D4   94a0af0 feat(sprint-19): D4 BUG-C01-EXT-FK action_items composite FK + D1 cross-tenant test 통과
D5   045a930 feat(sprint-19): D5 BUG-C01-EXT-FK notes composite FK (nullable MATCH SIMPLE) + D1 2 test 통과
D6   d0b52fd feat(sprint-19): D6 BUG-C01-EXT-FK mpl workspace_id + 2 composite FK + repo 3 함수 patch (Codex v2 F-7)
D7   1a6ba7f feat(sprint-19): D7 BUG-C01-EXT-FK project_members model sync (schema drift 방지)
D7.5a 3954f34 feat(sprint-19): D7.5a alembic env.py — 외부 sqlalchemy.url 우선 (테스트 주입 지원, Codex v2 F-3)
D7.5b 508f9b0 test+fix(sprint-19): D7.5b BUG-C01-EXT-FK drift detection (compare_metadata) + D7 FK 컬럼 순서 fix
D7.9a 7dcd1d2 fix(sprint-19): D7.9a BUG-C01-EXT-FK Codex 2차 review 3 finding fix (REVISE → PASS)
```

(closeout D8 commit = 본 doc + CONTEXT-MAP §6 I-9 (9)(10)(11) 신설 + projects/CONTEXT.md P-10 + BL-049/050/051 등재 묶음. 본 commit 후 push)

### 검증 결과 (Verification)

```
backend pytest tests/ → 317 passed + 1 skipped (R2)
  - 기존 309 + D1 7 (cross-tenant 4 + nullable 2 + mpl valid 1) + D7.5b 1 (drift) = 317
backend pytest tests/integration/test_workspace_integrity_audit.py → 4 PASS (PR #1 audit 회귀)
backend pytest tests/integration/test_workspace_fk_cross_tenant_block.py → 7 PASS (D1)
backend pytest tests/integration/test_alembic_upgrade.py → 1 PASS (D7.5b compare_metadata)
```

---

## 2. PR #2 산출물 = 4 entity DB-level composite FK hardening + drift detection 신설

### scope (4 entity composite FK + 1 model sync)

| Entity | 변경 | commit |
|---|---|---|
| `projects` | model `__table_args__` UQ(id, workspace_id) 동기화 (alembic 7ebd009f89a4 의 DB UQ 와 sync) | D3a |
| `meetings` | UQ(id, workspace_id) 신설 (composite FK target) | D2 + D3 |
| `action_items` | composite FK (workspace_id, project_id) → projects(workspace_id, id) | D2 + D4 |
| `notes` | composite FK 동일 패턴 (nullable, MATCH SIMPLE 면제) | D2 + D5 |
| `meeting_project_links` | workspace_id 컬럼 신설 + backfill + NOT NULL + 단순 FK + 2 composite FK + repo 3 함수 patch | D2 + D6 |
| `project_members` | model `__table_args__` FK 명시 (DB constraint 이미 존재, alembic 변경 X) | D7 |

### 신설 산출물

- `backend/alembic/versions/e5f6g7h8i9ja_sprint19_pr2_composite_fk.py` — 단일 revision (down_revision = `d4e5f6a7b8c9`) + preflight `DO $$ RAISE EXCEPTION` 4 entity mismatch 검사 + backfill 후 NULL 검사 (Codex v2 F-2 fix)
- `backend/tests/integration/test_workspace_fk_cross_tenant_block.py` — 7 case (action/notes/mpl cross-tenant 4 + nullable 면제 2 + mpl valid 1)
- `backend/tests/integration/test_alembic_upgrade.py` — `alembic.compare_metadata` + PR #2 managed constraint allowlist + pgvector image
- `backend/alembic/env.py` — 외부 `sqlalchemy.url` 우선 (테스트 주입 지원, Codex v2 F-3 fix)
- `CONTEXT-MAP.md` §6 I-9 — (9)(10)(11) 항 신설
- `backend/src/projects/CONTEXT.md` — P-10 신설 (composite FK + repo 3 함수)
- `docs/REFACTORING-BACKLOG.md` — BL-049/050/051 등재

---

## 3. Codex evaluator 1차/2차 review 결과

### 1차 plan review (verdict BLOCK)
- 8 finding (F-1~F-3 BLOCK + F-4~F-7 MAJOR + F-8 MINOR) 모두 수락 → plan v2 patch:
  - F-1 BLOCK: D1 raw SQL `users.name` 컬럼 오류 → ORM SQLModel 사용 (display_name 정확)
  - F-2 BLOCK: Project `__table_args__` UQ(id, workspace_id) 누락 → D3a 신설
  - F-3 BLOCK: env.py 외부 URL 무시 + Config 경로 + pgvector image → D7.5a + D7.5b
  - F-4 MAJOR: drift test 가 single name 비교 → `compare_metadata` 사용
  - F-5 MAJOR: MPL test 단일 case → 3 case 분리 (project / meeting / valid)
  - F-6 MAJOR: staging audit hard gate 부재 → Phase 5.0 manual gate + alembic preflight
  - F-7 MAJOR: mpl `remove_meeting_link` / `find_projects_by_meeting` workspace_id WHERE/JOIN 누락 → D6
  - F-8 MINOR: scope clarify → CONTEXT-MAP I-9 (11) 신설 + BL-050

### 2차 diff review (verdict REVISE → PASS)
- F-1 MAJOR: drift filter 가 너무 broad (notes/projects 테이블 전체 제외) → constraint name allowlist (`PR2_MANAGED_CONSTRAINTS`)
- F-2 MINOR: alembic preflight 부재 → 4 entity mismatch + NULL 검사 RAISE EXCEPTION
- F-3 MINOR: action_items nullable 면제 test 부재 → `test_action_items_nullable_project_id_allowed` 신설
- 모두 D7.9a (1 commit) 으로 fix

### 본 세션 학습 5건 (모두 적용 확인 = 정합)
1. **Codex 1차 BLOCK 의 plan v2 가치** — 8 finding 모두 수락 + plan v2 patch 후 ExitPlanMode → 본 PR scope ~3h → ~9h 로 확장 (정확한 cost). 단 안전성 압도적 (F-1 ORM 전환만으로도 raw SQL 4 test 깨짐 회피).
2. **Codex 2차 REVISE → fix 패턴** — drift filter 의 false-negative (F-1) 가 자동 catch. 본 review 가 없었으면 PR #2 의 핵심 constraint drift 가 silent pass 가능했음.
3. **AskUserQuestion 일괄 승인** — S1~S6 (branch / commit / alembic / NOT VALID / scope / Codex BLOCK 대응) 단일 세션 ~9h 흡수 정확. PR #89 의 5 commit 패턴 그대로.
4. **fail-closed > fail-open** — alembic preflight RAISE EXCEPTION (D7.9a) + drift test scope filter 의 보수적 catch (PR2_MANAGED_*). production 안전.
5. **mock + call_args 정확 비교** — 본 PR 은 repo 3 함수 patch 라 mock 직접 검증보다 ORM commit + IntegrityError 검증으로 대체 (D1 7 case). 정합.

---

## 4. 다음 세션 진입 (PR #2 머지 후 → PR #3)

### Step 1: 본 PR push + 머지

```bash
git -C /Users/woosung/project/agy-project/kairos-sprint-19 push -u origin sprint-19/bug-c01-ext-fk
gh pr create --base main --head sprint-19/bug-c01-ext-fk --draft --title "..." --body "..."
```

### Step 2: Staging audit hard gate (사용자 manual, 머지 전 필수)

PR 본문에 명시된 4 audit SQL 을 staging DB 에서 직접 실행. mismatch 0 + NULL 0 확인 후 머지:

```sql
-- 1. action_items mismatch (반드시 0)
SELECT COUNT(*) FROM action_items a JOIN projects p ON p.id = a.project_id WHERE a.workspace_id != p.workspace_id;

-- 2. notes mismatch (반드시 0)
SELECT COUNT(*) FROM notes n JOIN projects p ON p.id = n.project_id
  WHERE n.project_id IS NOT NULL AND n.workspace_id != p.workspace_id;

-- 3. meeting_project_links mismatch (반드시 0)
SELECT COUNT(*) FROM meeting_project_links mpl
  JOIN meetings m ON m.id = mpl.meeting_id
  JOIN projects p ON p.id = mpl.project_id
  WHERE m.workspace_id != p.workspace_id;

-- 4. (alembic upgrade head 후) backfill 후 NULL 검사
SELECT COUNT(*) FROM meeting_project_links WHERE workspace_id IS NULL;
```

만약 1 row 라도 발견 시: 본 PR alembic 의 preflight `DO $$ RAISE EXCEPTION` 가 자동 fail-fast. 사용자가 fix script 작성 → 재실행 → 0 확인.

### Step 3: Sprint 19 잔여 PR

PR #3-#9: AUTH-WH / UPL-OWN / PROJ-DEL / PIPE-LLM / P1-05+P1-06 / C02+C03 / closeout. sprint-19-plan.md 의 P0 4건 + P1 7건 참조.

### Step 4: Sprint 20 carry-over (BL-049/050/051)

- BL-049: production-scale alembic guard (첫 외부 user 온보딩 직전 audit)
- BL-050: 잔여 7+ entity cross-workspace single-FK audit (action_items.meeting_id 등)
- BL-051: Sprint 15/16 기존 schema drift 정리 (TIMESTAMP↔DateTime, HNSW 인덱스 명시, server_default 등)

---

## 5. 위험 + 완화

- **alembic preflight 의 RAISE EXCEPTION**: dogfooding 단계에서 mismatch 0 확신이지만 staging audit 가 첫 안전망. PR 머지 전 사용자 manual gate 필수. preflight 이 fail 하면 alembic upgrade 중단 + Cloud Run 컨테이너 startup 실패 → traffic 받기 전 자연 차단.
- **drift detection 의 false-negative**: D7.9a 의 `PR2_MANAGED_CONSTRAINTS` allowlist 가 PR #2 관련 constraint name 8개 + column 1개 catch. 향후 추가 composite FK 등재 시 본 allowlist 도 갱신 필수 (BL-050 진행 시 등재).
- **MeetingProjectLink workspace_id 신설 시 기존 row backfill**: PR #1 audit `test_meeting_project_links_workspace_match` 0 row 통과 = m.workspace_id == p.workspace_id 보장. backfill SQL = `UPDATE mpl SET workspace_id = m.workspace_id`. orphan meeting (meeting 삭제 후 mpl row 잔여) 의 경우 backfill 후 NULL → preflight fail-fast.
- **PR #1 service-level 가드 영구 유지**: 헌법 I-9 (9) 에 명시 — "DB constraint violation 은 500 = 정보 누설". service-level 404 가드 제거 금지.
- **production DB lock 시간**: dogfooding scale = ms 단위. BL-049 등재로 1만 row 임계값 이후 NOT VALID + VALIDATE 2단계 패턴 적용 권장.

---

## 6. memory 갱신 사항

`~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/` 에 신규 또는 갱신:
- 기존 `project_sprint19_pr1_closeout.md` → `project_sprint19_pr2_closeout.md` 신설
- 내용: PR #2 11 commits + 317 PASS + Codex 1차 BLOCK→PASS + 2차 REVISE→PASS + 학습 5건 + BL-049/050/051 + 다음 = PR #3 (AUTH-WH)

다음 다음 세션 첫 read = `[[project_sprint19_pr2_closeout]]` → 본 doc → PR #90 머지 후 PR #3 진입.

---

## 7. 본 세션 학습 5건 (다음 세션 전달)

1. **plan agent 의 APPROVE 조건부 8 권장사항이 Codex 1차 BLOCK 8 finding 의 부분집합과 일치** — plan agent + Codex 1차 = 이중 검증 패턴. Plan agent 가 빠뜨린 finding (F-3 env.py 경로) 도 Codex 가 catch.

2. **TDD failing-first 가 ORM 으로 작성 시 schema 변경에 자동 대응** — raw SQL 의 컬럼명 오류 (F-1) 회피. 본 PR 같은 schema 변경 PR 에서 특히 중요.

3. **compare_metadata + constraint name allowlist 가 BL 분리 핵심** — table 단위 exclude 는 false-negative 위험. 본 PR 의 `PR2_MANAGED_CONSTRAINTS` 패턴이 향후 schema-change PR 의 표준 template.

4. **alembic preflight `DO $$ RAISE EXCEPTION` 의 명확한 에러 메시지** — `op.create_foreign_key` 실패 시 모호한 `FOREIGN KEY constraint violation` 대신 `PR #2 preflight: action_items mismatch=N` 같은 actionable message. 운영 효율 ↑.

5. **alembic env.py 의 외부 URL 우선 patch (D7.5a)** — 테스트 fixture 가 alembic 을 호출할 수 있게 하는 작은 patch (4줄). schema drift detection 의 enabler. 운영 영향 0.

---

## 8. closeout commit (D8 = 본 commit)

본 doc + `CONTEXT-MAP.md` §6 I-9 (9)(10)(11) 신설 + `backend/src/projects/CONTEXT.md` P-10 신설 + `docs/REFACTORING-BACKLOG.md` BL-049/050/051 등재 = 단일 commit.
