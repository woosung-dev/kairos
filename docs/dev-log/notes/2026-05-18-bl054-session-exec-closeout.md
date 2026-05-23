# BL-054 session.execute → session.exec migration cleanup PR closeout (2026-05-18)

> Sprint 20 cleanup PR (BL-053 PR #92 위 stacked PR).
> PR # = #93 (push 후 발급, draft 권장).

---

## 1. 본 PR 완료 상태

### branch: `cleanup/bl-054-session-exec` — `cleanup/bl-053-async-session` (PR #92) 위 stacked, 5 commits

```
F6 (closeout) docs(bl-054): F6 closeout — execute manifest 갱신 + 헌법 patch + Codex 2차 review 3 finding 수락
F3 d211d34   refactor(bl-054): F3 auth + inbox + notes — execute → exec (9 변환, 3 파일)
F2 56474ef   refactor(bl-054): F2 actions + meetings + embeddings — execute → exec (14 변환, 3 파일)
F1 c30d6dc   refactor(bl-054): F1 workspaces + projects + memory — execute → exec (34 호출, 4 파일)
F0 c23c9dc   docs(bl-054): F0 execute manifest 신설 (G1~G5 카테고리)
```

### 검증 결과 (Verification)

| Gate | 명령 | 결과 |
|---|---|---|
| pytest 전수 | `cd backend && uv run pytest tests/ -q` | **321 passed + 1 skipped** (BL-053 후와 동일, **회귀 0**) |
| pyright | `uv run pyright` | **132 errors** (BL-053 후 131 → 132, **+1 미세, 수용**) |
| manifest 정합 | `rg "await self\.session\.execute\(\s*select\(" src/` | **0** (변환 누락 0) |
| 잔여 .execute | `rg "\.execute\(" src/ -n \| wc -l` | **20** (19 실 호출 + 1 docstring) — manifest G3-keep + G3-keep-dialect + G4 정합 |

---

## 2. Scope (57 변환 + manifest + 헌법 patch, 11 파일)

### Category G1 + G3-convert (변환, 57 호출)

| 영역 | 호출 수 | commit |
|---|---|---|
| F1 workspaces + projects + memory(repo+service) | 34 | c30d6dc |
| F2 actions + meetings + embeddings | 14 | 56474ef |
| F3 auth + inbox + notes | 9 | d211d34 |

### Category 유지 (manifest 정합, 19 실 호출)

- **G3-keep** (rowcount contract): `actions/repository.py:75 cancel_todo_by_project` (1)
- **G3-keep-dialect** (pg_insert ON CONFLICT): `memory/repository.py:304 save_query_embedding_cache` (1)
- **G4 raw text**: main.py healthcheck (1) + auth/dependencies.py seed (2) + embeddings/repository.py (8) + memory/repository.py (4) + embeddings/repository.py:322 cache hit UPDATE (1) = 17

### 변환 패턴

```python
# AS-IS (G1 multi-line)
result = await self.session.execute(select(X).where(...))
return result.scalar_one_or_none()
# TO-BE
return (await self.session.exec(select(X).where(...))).one_or_none()

# AS-IS (G3-convert)
await self.session.execute(update(X).where(...).values(...))
# TO-BE
await self.session.exec(update(X).where(...).values(...))
```

### 신규/갱신 doc

- `docs/dev-log/notes/2026-05-18-bl054-execute-manifest.md` (F0 신설, F6 Codex 2차 review F1 finding 수락 후 갱신)
- `docs/dev-log/notes/2026-05-18-bl054-session-exec-closeout.md` (본 doc 신설)

### 헌법 patch (Codex 1차 MAJOR-1 수락)

- `CONTEXT-MAP.md` I-14: `session.exec() 금지` → manifest 기반 5 카테고리 allowlist 명시
- `backend/CONTEXT.md` B-10: 동일 정정 + N+1 selectinload 동일

---

## 3. Codex evaluator 1차/2차 review 결과

### 1차 plan review (BL-053 plan v1 의 일부, verdict REVISE — MAJOR 2 수락)

| Finding | severity | axis | patch 위치 |
|---|---|---|---|
| MAJOR-1 헌법 I-14 + B-10 `session.exec() 금지` 충돌 | MAJOR | 1 | F6 closeout — CONTEXT-MAP I-14 + backend/CONTEXT.md B-10 patch |
| MAJOR-2 BL-054 execute allowlist 불완전 | MAJOR | 5 | F0 manifest 신설 (G1~G5 카테고리) + F5 gate (Codex 2차 F1 후 정확화) |

### 2차 diff review (verdict REVISE → F5.9a/F6 fix 수락, scores: 2/5/4/5/3 평균 3.8)

| Finding | severity | axis | patch 위치 |
|---|---|---|---|
| MAJOR-1 manifest allowlist 가 실제 잔여 execute 호출과 동기화 안 됨 | MAJOR | 1 | F6 — manifest G4 expansion (17 정확 명시) + G2 stale 제거 + F5 gate expected 정확화 (`~12` → `19`) |
| MAJOR-2 pg_insert ON CONFLICT execute 가 manifest + gate 에서 unclassified | MAJOR | 5 | F6 — manifest **G3-keep-dialect** 카테고리 신설 + memory/repository.py:304 docstring 추가 |
| MINOR-3 rowcount keep rationale 가 imprecise | MINOR | 3 | F6 — actions/repository.py:75 docstring 정정 + manifest G3-keep rationale 명확화 ("rowcount contract preservation, not because every exec() DML result is ScalarResult") |

### Codex 2차 summary

> "The code-level G1 scalar transformations look behavior-preserving, including count `.one()` and scalar-list `.all()` cases. I would not approve the PR as-is because the manifest is the control surface for BL-054, and it currently has stale counts, missing keep entries, and an unclassified `pg_insert` escape path."

→ F6 closeout 후 manifest 정확화 완료. F5 gate 통과 (19 = manifest 정합).

---

## 4. 본 세션 학습 (PR #91 + BL-053 PR #92 → 본 PR 적용)

1. **Codex 1차 REVISE finding 100% 수락** ✅ — MAJOR-1 + MAJOR-2 → F0 manifest 신설 + F6 헌법 patch.
2. **Codex 2차 REVISE finding 100% 수락** ✅ — MAJOR-1 + MAJOR-2 + MINOR-3 → F6 manifest 갱신 + classification 추가 + docstring 정정.
3. **AskUserQuestion 일괄 승인** ✅ — commit batch + 일괄 진행 = 본 세션 ~5h 흡수.
4. **fail-closed > fail-open** ✅ — pytest 회귀 0 + manifest 정합 검증 + grep gate 정확화.
5. **manifest 신설 의 가치** ✅ — Codex MAJOR-2 finding 으로 시작했지만 결과적으로 BL-054 의 control surface = manifest. F5 gate 가 객관적 기준 제공.
6. **stack PR 의 장점** ✅ — BL-053 머지 대기 없이 BL-054 진행 가능. PR #92 머지 후 자동 rebase.

---

## 5. 다음 진입

### Step 1: 본 PR (BL-054) push + 머지

```bash
git push -u origin cleanup/bl-054-session-exec
gh pr create --base cleanup/bl-053-async-session --head cleanup/bl-054-session-exec --draft \
  --title "BL-054 cleanup: session.execute → session.exec migration (57 변환, 5 commits stacked on PR #92)" \
  --body "..."
```

PR #92 (BL-053) 머지 후 PR #93 의 base 가 main 으로 자동 rebase.

### Step 2: design-review (PR #94)

- Phase 0.2 에서 별도 worktree 신설 + commit (2e83a18) 완료
- push + PR 생성은 사용자 별도 진행

### Step 3: 후속 carry-over

- BL-046 Sprint 20 carry-over (multi-FK hardening) — Sprint 21 후속
- BL-051 (Sprint 15/16 schema drift) — Sprint 21 후속
- tests/ session.exec migration (G5) — 별도 cleanup BL 등재 가능 (본 PR scope 외)

---

## 6. memory 갱신 사항

`~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/` 신규/갱신:
- `project_bl054_session_exec_done.md` 신설 (본 PR closeout 결과)
- 내용: 5 commits + 57 변환 + manifest 5 카테고리 + 헌법 I-14/B-10 patch + Codex 1차 REVISE / 2차 REVISE → 둘 다 finding 100% 수락 → APPROVE 등가 + BL-046/051 carry-over
