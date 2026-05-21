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
| **G2** | execute 유지 | tuple/raw select (`.all()` 직접, raw SQL tuple result) | raw text 또는 multi-column tuple result. SM exec 가 받지 못함 (UpdateBase 만). |
| **G3-convert** | exec 변환 | DML (update / delete) w/o rowcount/inserted_primary_key | SM exec(update/delete) OK |
| **G3-keep** | execute 유지 | DML w/ `.rowcount` 또는 `.inserted_primary_key` | rowcount contract preservation (SQLModel 0.0.37 시점 dialect/version 에 따라 DML exec return type 모호). |
| **G3-keep-dialect** | execute 유지 | PostgreSQL dialect insert + ON CONFLICT | `from sqlalchemy.dialects.postgresql import insert as pg_insert` 는 SM 미 re-export + SM exec() type narrow 가 dialect insert 받지 못함. |
| **G4** | execute 유지 | raw text (SET LOCAL / healthcheck / raw UPDATE / raw SELECT) | SM exec 가 `text()` 받지 못함 (UpdateBase 만) |
| **G5** | F4 commit (본 PR 제외) | tests/ 의 모든 `.execute()` | 대부분 G4 raw text (information_schema). 변환 가치 낮음. 본 PR scope 외. |

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

## G4 분포 (raw text execute 유지, src/ 17 호출 — Codex 2차 review F1 수락 후 정확화)

| 파일 | line | 호출 | 사유 |
|---|---|---|---|
| src/main.py | 135 | `session.execute(text("SELECT 1"))` | healthcheck — SM exec 가 text 못 받음 |
| src/auth/dependencies.py | 103, 114 | `session.execute(_text("INSERT INTO..."))` ×2 | personal_ws + WorkspaceMember(owner) seed (ON CONFLICT) |
| src/embeddings/repository.py | 19-21 | `session.execute(text("SET LOCAL hnsw...."))` ×3 | HNSW tuning (Sprint 16 ADR-020) |
| src/embeddings/repository.py | 110 | `session.execute(text("""UPDATE embedding_chunks SET project_id..."""))` | raw multiline UPDATE |
| src/embeddings/repository.py | 198 | `session.execute(query, params)` — vector_search raw text + halfvec CAST | typed bindparam halfvec query |
| src/embeddings/repository.py | 242 | `session.execute(query, params)` — text_search raw trigram | pg_trgm similarity query |
| src/embeddings/repository.py | 302 | `session.execute(query, params)` — find_similar_cache raw text + halfvec | semantic cache lookup |
| src/embeddings/repository.py | 322 | `session.execute(text("UPDATE semantic_caches SET hit_count..."))` | raw cache hit increment |
| src/embeddings/repository.py | 350 | `session.execute(query, params)` — compute_max_visibility raw text | visibility MAX query |
| src/embeddings/repository.py | 397 | `session.execute(query, params)` — _all_chunks_visible raw anti-join | BL-041/042 visibility check |
| src/memory/repository.py | 105 | `session.execute(stmt)` — get_metrics_counts: tuple result.all() (multi-column event_type/count) | tuple 행이라 SM exec().all() 도 가능하지만 명확성 위해 keep |
| src/memory/repository.py | 123 | `session.execute(stmt, {"wid": ...})` — get_recall_latency_percentiles raw text percentile_cont | raw text + named params |
| src/memory/repository.py | 194 | `session.execute(sql, {"qvec":..., "wid":..., "limit":...})` — vector_search raw + halfvec bindparam | pgvector cosine query |
| src/memory/repository.py | 239 | `session.execute(sql, params)` — search_keyword raw token overlap | raw multi-column query |

---

## G2 분포 (raw SQL tuple result 유지)

본 PR F1 에서 검증 결과 G2 정확한 분포 = 0건. handoff 초안의 memory/repository.py 의
`items_result` (~247) 는 G1 typed select 였고 F1 에서 exec 로 변환됨. G2 는 raw text +
tuple 형태로 별도 카테고리 (G4 와 함께 raw_text 유지) 로 통합 — Codex 2차 review F1 수락.

## G3-keep-dialect 분포 (PostgreSQL dialect insert ON CONFLICT 유지, 1 호출)

| 파일 | line | 사유 |
|---|---|---|
| src/memory/repository.py | 304 | `pg_insert(MemoryQueryEmbeddingCache.__table__).on_conflict_do_nothing()` — SA dialect Insert, SQLModel 미 re-export, SM exec() type narrow 미수용 |

---

## G1 분포 (typed scalar select 변환 가능, ~50 호출)

(F1~F3 commit 에서 진행. multi-line `result = await session.execute(stmt); rows = result.scalars().all()` 패턴 단일줄 `rows = (await session.exec(stmt)).all()` 으로.)

도메인별 분포:
- F1 workspaces (~9) + memory (~6) + projects (~5)
- F2 embeddings (~3) + meetings (~5) + actions (~4)
- F3 auth (~3) + inbox (~2) + notes (~3) + rag (~?)

---

## F5 gate (BL-054 manifest 정합 검증, Codex 2차 review F1 수락 후 정확화)

본 PR 의 모든 F-commit 후 다음 grep 으로 잔존 검증:

```bash
# 변환 대상 (G1 + G3-convert) 잔존 = 0 이어야 함
rg "await self\.session\.execute\(\s*select\(" src/ -n | wc -l  # expected 0
rg "await self\.session\.execute\(\s*\n*\s*(update|delete)\(" src/ -n -U --multiline | wc -l  # expected 1 (G3-keep)

# 유지 대상 (G3-keep + G3-keep-dialect + G4) 잔존 검증
rg "\.execute\(" src/ -n | wc -l  # expected 19 (1 G3-keep actions + 1 G3-keep-dialect memory:304 + 17 G4) + ~1 comment match
```

본 PR 실측 결과 (F3 commit 후):
- 변환 누락 = 0
- 잔존 .execute() = 20 (19 실 호출 + 1 actions/repository.py:72 docstring 줄)
- 잔존 분포: G3-keep 1 + G3-keep-dialect 1 + G4 17 = manifest 100% 정합

F5 실패 = 변환 누락 또는 keep 대상 변환. 즉시 stop + root-cause.

---

## 헌법 patch (Codex 1차 MAJOR-1 수락, F6 closeout 동시 commit)

본 PR closeout (F6) 에 `CONTEXT-MAP.md` I-14 + `backend/CONTEXT.md` B-10 + `.ai/rules/backend.md` 의 `session.exec() 금지` 규칙을 본 manifest 의 allowlist 로 정정:

```
[before] B-10 100% async: session.exec() 금지, await session.execute(select(...)) + .scalars().all() 패턴

[after]  B-10 100% async + SQLModel typed query:
         - SQLModel typed select: session.exec() (.all() / .first() / .one_or_none() / .one())
         - raw text() + DML w/ .rowcount + tuple result: session.execute() (manifest G2/G3-keep/G4)
         - manifest: docs/dev-log/notes/2026-05-18-bl054-execute-manifest.md
```

---

## 근거

- ~/.claude/plans/sprint-20-pure-wozniak.md "BL-054 execute Manifest" 섹션
- Codex 1차 plan review (verdict REVISE) MAJOR-1 + MAJOR-2 finding 수락
- Sprint 19 PR #2 D9 + BL-052 PR #91 Plan agent verdict
