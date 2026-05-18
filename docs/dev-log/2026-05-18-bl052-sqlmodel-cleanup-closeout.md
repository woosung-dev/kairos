# BL-052 SQLAlchemy → SQLModel import 통일 cleanup PR closeout (2026-05-18)

> Sprint 19 PR #2 (BUG-C01-EXT-FK, merged 5789822) 의 D9 commit 가 carry-over 한 BL-052 의 전수 cleanup. PR # = TBD (push 후 발급).

---

## 1. 본 PR 완료 상태

### branch: `cleanup/bl-052-sqlmodel-import-unification` — origin/main (5789822 PR #90 머지) 기반 7 commits

```
C7 4be7b24 refactor(bl-052): C7 test_promote.py select import → sqlmodel
C6 32f257a refactor(bl-052): C6 test layer text import → sqlmodel (conftest 포함 5 파일)
C5 fb64f13 refactor(bl-052): C5 main.py text import → sqlmodel
C4 7e92d97 refactor(bl-052): C4 query builder — embeddings + inbox + memory + rag (sqlmodel, inline import 포함)
C3 b7abd98 refactor(bl-052): C3 query builder — projects + notes + actions + meetings repository (sqlmodel)
C2 afbe76b refactor(bl-052): C2 query builder — auth + workspaces (select/func/delete/update/text → sqlmodel)
C1 b5a09fc refactor(bl-052): C1 model SQLModel import 통일 (embeddings/inbox/memory)
```

(closeout C8 commit = 본 doc + BL-052 완료 마크 + BL-053/054 등재 묶음)

### 검증 결과 (Verification)

```
backend pytest tests/ → 317 passed + 1 skipped (R2, 변경 전과 동일)
backend pytest tests/integration/test_alembic_upgrade.py → 1 PASS (drift 0 유지)
backend pytest tests/integration/test_workspace_integrity_audit.py → 4 PASS (PR #2 audit 회귀)
pyright: origin/main 172 errors → 본 PR 100 errors (72 감소) ← SQLModel typed result 효과
```

---

## 2. Scope (21 파일, Level 2)

### Category A — sqlmodel 으로 통일 완료

| 영역 | 객체 | 파일 수 | commit |
|---|---|---|---|
| Model 정의 | `JSON, Column, Text` | 3 (embeddings/inbox/memory) | C1 |
| Repository / service / main query builder | `select, delete, update, text, func, and_, or_, exists, bindparam` | 12 + inline 3 | C2~C5 |
| Test query/text | `select, text` | 6 (conftest + 5 test) | C6~C7 |

### Category B — sqlalchemy 그대로 유지 (SQLModel 미 re-export)

- `async_sessionmaker, create_async_engine, async_engine_from_config, pool` (sqlalchemy.ext.asyncio)
- `JSONB, insert as pg_insert` (sqlalchemy.dialects.postgresql)
- `IntegrityError, OperationalError, SQLAlchemyError` (sqlalchemy.exc)
- `pgvector.sqlalchemy.HALFVEC` (외부 패키지)
- alembic versions/*.py 의 `import sqlalchemy as sa` (Alembic autogenerate 표준)
- `sqlalchemy.ext.asyncio.AsyncSession` — Level 3 (BL-053 carry-over)

---

## 3. Codex evaluator 1차/2차 review 결과

### 1차 plan review (verdict REVISE — plan 문서 결함만)

5 finding 모두 수락 (학습 #1):
- F-1 MAJOR: grep 패턴이 inline import 못 잡음 → `rg "^[[:space:]]*from sqlalchemy"` 권장. 실제 진행 시 grep 결과로도 inline import 모두 catch (다행)
- F-2 MAJOR: C2~C7 commit step 에 git add 명시 누락 → 실제 진행 시 모두 git add 명시 진행
- F-3 MINOR: C5/C7 회귀 명령 미명시 → 실제 진행 시 모두 실행
- F-4 MINOR: pyright optional 표현 → required. 실제 진행 시 origin/main 기준선 (172) 대비 측정
- F-5 MINOR: "21 파일" 표현 → "21 code/test files + 2 docs" 구분

### 2차 diff review (verdict APPROVE — finding 0)

7 commit diff 모두 검증 통과:
- inline import 3건 (memory/repo:100, memory/service:753, auth/deps:84) 모두 patch 확인
- conftest.py 의 text → sqlmodel + AsyncSession/create_async_engine Category B 유지 확인
- SelectOfScalar 가 Select subclass = session.execute() 호환 100% 검증
- 변경 대상 15 모듈 import smoke PASS

---

## 4. 본 세션 학습 5건 (모두 적용 확인 = 정합)

1. **Codex 1차 REVISE 의 plan 문서 결함 가치** — 5 finding 모두 plan 문서 결함 (실제 코드 OK). plan 의 검증 명령 (grep 패턴 / git add / pyright) 부족 catch. 실제 진행 시 더 엄격한 패턴 적용.
2. **Codex 2차 APPROVE (finding 0)** — pure refactor 라 가능. PR #2 의 D7.9a fix 없이 완료 가능한 첫 사례.
3. **AskUserQuestion 일괄 승인** — S1~S4 single 세션 흡수 정확. 사용자 결정 = Level 2 + alembic 유지 + cleanup branch + Codex 1차+2차.
4. **fail-closed > fail-open** — pyright 측정 실패 (importable 미해석 오류) 시 stop + 기준선 비교 진행.
5. **mock 직접 비교 불필요** — import refactor 라 mock 직접 검증 없이 전수 회귀 (317 PASS) + drift detection 으로 충분.

---

## 5. ⚠️ 사용자 stash 손실 알림 + 복구 안내

### 손실 경위

본 PR Phase 7 (pyright 기준선 비교) 진행 중 `git stash list` 결과:
- stash@{0}: `On main: design-review: RAG홈 + 디자인 수정 전체` (SHA `8230955edc362a4e33749a9ceb6dcd148ff612ac`)
- stash@{1}: `On main: 임시 디자인 요청을 통해서 변경한 부분`

origin/main 으로 switch 후 pyright 측정 → cleanup branch 로 복귀 시 stash 가 자동 pop 됨 → conflict 발생 → `git stash drop` 실수 실행으로 stash@{0} 제거.

### 복구 가능 (reflog 보존 기간 내, 보통 ~90일)

```bash
# 옵션 1: stash apply 로 working tree 복원
git stash apply 8230955edc362a4e33749a9ceb6dcd148ff612ac

# 옵션 2: 특정 파일만 복원
git checkout 8230955edc362a4e33749a9ceb6dcd148ff612ac -- frontend/src/app/\(app\)/dashboard/page.tsx

# 옵션 3: stash 자체 재생성 (이후 작업용)
git stash store -m "design-review: RAG홈 + 디자인 수정 전체" 8230955edc362a4e33749a9ceb6dcd148ff612ac
```

영향 파일 (224 + 2 = 226줄):
- `frontend/src/app/(app)/dashboard/page.tsx` (224 lines, 일부 차이)
- `frontend/src/app/page.tsx` (2 lines)

### 부분 보존

`frontend/src/app/page.tsx` 는 working tree 에 untracked 로 살아있음 (origin/main 에 존재 안 하는 파일). 본 PR commit 에는 포함 안 됨.

### 재발 방지

향후 git switch 전에 stash 자동 pop 가능성 검증 + `git status` 로 working tree 정리 확인 후 진행.

---

## 6. 다음 진입

### Step 1: 본 PR push + 머지

```bash
git push -u origin cleanup/bl-052-sqlmodel-import-unification
gh pr create --base main --head cleanup/bl-052-sqlmodel-import-unification --draft --title "..." --body "..."
```

### Step 2: 사용자 design-review stash 복구

위 §5 의 명령 중 하나 실행.

### Step 3: BL-053 / BL-054 carry-over

Sprint 20 또는 별도 cleanup PR 로 진입.

---

## 7. memory 갱신 사항

`~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/` 신규:
- `project_bl052_sqlmodel_cleanup_done.md` 신설
- 내용: 7 commits + 317 PASS + pyright 72 감소 + Codex 1차 REVISE → 2차 APPROVE + BL-053/054 carry-over + design-review stash 복구 안내
