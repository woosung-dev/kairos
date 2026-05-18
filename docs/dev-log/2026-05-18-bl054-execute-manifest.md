# BL-054 session.execute() Allowlist Manifest (2026-05-18)

> Codex 1차 plan review MAJOR-2 finding 수락 — BL-054 진입 전 모든 `session.execute()` 호출을 5 카테고리로 분류한 manifest. F5 gate 의 기준 (manifest 외 잔존 시 fail).
>
> baseline (origin/main@195b8e3 + BL-053 PR #92 적용 후):
> - `rg "\.execute\(" src/ -n` → **76 호출** (src/)
> - `rg "\.execute\(" tests/ -n` → **34 호출** (tests/, G5)

---

## 분류 기준

| G | 처리 | 정의 | sqlmodel 의 동작 |
|---|---|---|---|
| **G1** | exec 변환 | typed scalar select (.scalars() chain) | SM exec(select) → ScalarResult, `.all()` / `.first()` / `.one_or_none()` / `.one()` |
| **G2** | execute 유지 | tuple/raw select (`.all()` 직접, group by, count) | SM exec 도 가능하지만 tuple unpacking 패턴은 execute 가 명확 |
| **G3-convert** | exec 변환 | DML (update / delete / insert) w/o rowcount/inserted_primary_key | SM exec(update/delete) OK |
| **G3-keep** | execute 유지 | DML w/ `.rowcount` 또는 `.inserted_primary_key` | SM exec 의 결과 ScalarResult 에 rowcount 없음 |
| **G4** | execute 유지 | raw text (SET LOCAL / healthcheck / raw UPDATE) | SM exec 가 `text()` 받지 못함 (UpdateBase 만) |
| **G5** | F4 commit | tests/ 의 모든 `.execute()` | 변환 가능하지만 tests 별도 batch |

---

## G3-convert 분포 (DML 변환 가능, 17 호출)

| 파일 | line | DML | commit |
|---|---|---|---|
| src/projects/repository.py | 172, 226 | delete(ProjectMember) / delete(MeetingProjectLink) | F1 |
| src/workspaces/repository.py | 52, 103, 116, 166, 179 | update Workspace/WorkspaceMember/WorkspaceMember delete/update WorkspaceInvite ×2 | F1 |
| src/memory/repository.py | 62, 74, 83, 92, 143 | update MemoryItem ×5 | F1 |
| src/embeddings/repository.py | 91, 98 | delete EmbeddingChunk ×2 | F2 |
| src/memory/service.py | 761, 770, 793 | update PromotionAudit ×3 (bg task) | F1 (memory 포함) |

---

## G3-keep 분포 (DML execute 유지, 1 호출)

| 파일 | line | DML | 사유 |
|---|---|---|---|
| src/actions/repository.py | 75-84 | update(ActionItem) + `result.rowcount` 반환 | rowcount 사용 — SM exec ScalarResult 에 미존재 |

---

## G4 분포 (raw text execute 유지, 8 호출)

| 파일 | line | 호출 | 사유 |
|---|---|---|---|
| src/main.py | 135 | `session.execute(text("SELECT 1"))` | healthcheck — SM exec 가 text 못 받음 |
| src/embeddings/repository.py | 19-21 | `session.execute(text("SET LOCAL hnsw...."))` ×3 | HNSW tuning (Sprint 16 ADR-020) |
| src/embeddings/repository.py | 110 | `session.execute(text("""..."""))` | raw multiline query |
| src/embeddings/repository.py | 321 | `session.execute(text("UPDATE semantic_caches..."))` | raw UPDATE — text DML |
| src/auth/dependencies.py | 103, 114 | `session.execute(_text("INSERT INTO..."))` ×2 | personal_ws + WorkspaceMember(owner) seed (ON CONFLICT) |

---

## G2 분포 (tuple result.all 유지, 3 호출)

| 파일 | line | 패턴 |
|---|---|---|
| src/memory/repository.py | ~247 | `items_result = await self.session.execute(items_q); items_result.all()` (tuple result, exec 가능하지만 tuple unpack 명확성) |
| src/memory/repository.py | ~196 | 유사 |
| src/memory/repository.py | ~268 | 유사 |

(주: G2 도 SM exec 변환 가능. 단 tuple 패턴은 execute 의 의도가 명확 → 본 PR 에서는 유지 후속 검토.)

---

## G1 분포 (typed scalar select 변환 가능, ~50 호출)

(F1~F3 commit 에서 진행. multi-line `result = await session.execute(stmt); rows = result.scalars().all()` 패턴 단일줄 `rows = (await session.exec(stmt)).all()` 으로.)

도메인별 분포:
- F1 workspaces (~9) + memory (~6) + projects (~5)
- F2 embeddings (~3) + meetings (~5) + actions (~4)
- F3 auth (~3) + inbox (~2) + notes (~3) + rag (~?)

---

## F5 gate (BL-054 manifest 정합 검증)

본 PR 의 모든 F-commit 후 다음 grep 으로 잔존 검증:

```bash
# 변환 대상 (G1 + G3-convert) 잔존 = 0 이어야 함
rg "await self\.session\.execute\(\s*select\(" src/ -n | wc -l  # expected 0
rg "await self\.session\.execute\(\s*(update|delete)\(" src/ -n | wc -l  # expected 1 (G3-keep)

# 유지 대상 (G2 + G3-keep + G4) 잔존 검증
rg "\.execute\(" src/ -n | wc -l  # expected ~12 (3 G2 + 1 G3-keep + 8 G4)
```

F5 실패 = 변환 누락 또는 keep 대상 변환. 즉시 stop + root-cause.

---

## 헌법 patch (Codex 1차 MAJOR-1 수락, F6 closeout 동시 commit)

본 PR closeout (F6) 에 `CONTEXT-MAP.md` I-14 + `backend/CONTEXT.md` B-10 + `.ai/rules/backend.md` 의 `session.exec() 금지` 규칙을 본 manifest 의 allowlist 로 정정:

```
[before] B-10 100% async: session.exec() 금지, await session.execute(select(...)) + .scalars().all() 패턴

[after]  B-10 100% async + SQLModel typed query:
         - SQLModel typed select: session.exec() (.all() / .first() / .one_or_none() / .one())
         - raw text() + DML w/ .rowcount + tuple result: session.execute() (manifest G2/G3-keep/G4)
         - manifest: docs/dev-log/2026-05-18-bl054-execute-manifest.md
```

---

## 근거

- ~/.claude/plans/sprint-20-pure-wozniak.md "BL-054 execute Manifest" 섹션
- Codex 1차 plan review (verdict REVISE) MAJOR-1 + MAJOR-2 finding 수락
- Sprint 19 PR #2 D9 + BL-052 PR #91 Plan agent verdict
