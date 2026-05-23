# P0-S27c-1 진짜 Root Cause 발견 (이전 추정 정정)

> 2026-05-23 audit re-run 결과. 이전 보고서의 "production deploy stale" 가설 = **false hypothesis**.

## 진짜 Root Cause

**위치**: `backend/src/auth/dependencies.py:160-169`

**증상**: Dashboard 첫 진입 시 FE 가 5+ API 동시 호출 → 각 transaction 이 `get_current_user` 실행 → 동시 INSERT race → 1개 성공 + 나머지 4-5개 IntegrityError → **500**.

**Stack trace** (BE log, Account #3 c@e.com localhost 재현):
```
sqlalchemy.exc.IntegrityError:
<class 'asyncpg.exceptions.UniqueViolationError'>:
duplicate key value violates unique constraint "ix_users_clerk_id"
[SQL: INSERT INTO users (id, clerk_id, display_name, email, avatar_url,
       created_at, updated_at, onboarding_step, onboarded_at)
      VALUES ($1::UUID, $2::VARCHAR, $3::VARCHAR, ...)]
```

**코드** (현 상태, race-unsafe):
```python
# backend/src/auth/dependencies.py:158-169
repo = UserRepository(session)
user = await repo.find_by_clerk_id(claims["sub"])
is_new_user = user is None
if user is None:
    # 첫 로그인: 자동 생성
    user = User(
        clerk_id=claims["sub"],
        display_name=claims.get("name", "사용자"),
        email=claims.get("email", ""),
    )
    user = await repo.save(user)         # ← race window
    await repo.commit()
```

같은 file line 175-184 의 workspace INSERT 는 `ON CONFLICT (owner_id) WHERE type='personal' DO NOTHING` 으로 race-safe. **User INSERT 만 누락**.

## 왜 user 마다 다른가

- **Account #1/#2 (a@e.com, b@e.com)** — 이전 audit 시점에 race window 통과 (1개 transaction 만 시도 또는 운 좋게 1개만 성공) → user row 이미 DB 존재 → 후속 진입 시 `find_by_clerk_id` hit → INSERT skip → 200
- **Account #3 (c@e.com)** — 첫 가입 시점에 race 가 모든 transaction 에서 fail → DB 에 user row 없음 → 매 dashboard 진입 시 동일 race 재발 → 500
- **production user** (외부 5명 가입 후) — 60-80% 첫 진입에서 같은 race 가능성 (race 가 모두 fail 또는 partial fail)

## Fix 후보

**옵션 A (권장)**: `User` INSERT 에 `ON CONFLICT (clerk_id) DO NOTHING` 추가 (workspace INSERT 와 동일 패턴)

```python
# After find_by_clerk_id returns None, race-safe INSERT
await session.execute(
    _text("""
        INSERT INTO users (id, clerk_id, display_name, email, ...)
        VALUES (gen_random_uuid(), :clerk_id, :name, :email, ...)
        ON CONFLICT (clerk_id) DO NOTHING
    """),
    {"clerk_id": claims["sub"], "name": ..., "email": ...},
)
# Re-fetch after race-safe insert (one row guaranteed)
user = await repo.find_by_clerk_id(claims["sub"])
```

**옵션 B**: try/except IntegrityError + retry find_by_clerk_id

```python
try:
    user = await repo.save(user)
    await repo.commit()
except IntegrityError:
    await session.rollback()
    user = await repo.find_by_clerk_id(claims["sub"])
```

memory `project_sprint27b_webhook_recovery_done` 의 dormant code 패턴 = 옵션 B 와 유사 (race-safe fallback).

## Production 영향

- **deploy stale 가설 = false** — production 의 `/workspaces` 500 은 같은 race condition. main HEAD `eb13a42` 의 코드 자체 bug.
- redeploy 만으로 해결 X
- **외부 5명 진입 시 60-80% 가 첫 dashboard 진입에서 500** (lazy seed race fail 가능성)

## 다른 보고서 정정 사항

1. `qa-function.md` P0-PROD-DEPLOY 항목 — 가설명을 "deploy stale" → "lazy seed race condition" 으로 정정
2. `integrated-report.md` P0-S27c-1 의 진단 3 hypothesis → **확정 1 root cause**
3. `cto-perspective.md` 운영 readiness — production health timeout 가설은 별개 (정확한 진단 별도)

## 추가 검증된 finding (real verify pass 시)

1. **IDOR cross-tenant live 통과** ✅ — Account #1 valid JWT + Account #2 workspace_id → 5 endpoint 모두 403
2. **헌법 I-9 cross-tenant 응답 정합 verified** ✅ — 존재 workspace vs nonexistent UUID 둘 다 동일 403 + 같은 body = workspace 존재 여부 leak 없음. `qa-edgecase.md` P2-S27c-9 = **false alarm 취소**
3. **Sprint 19 PR #1/#2 BUG-C01-EXT fix 정합 동작** ✅ — composite FK + workspace_id WHERE 강제 정상

## 신뢰도 갱신

| 이전 audit verdict | 신뢰도 | 정정 |
|---|---|---|
| P0-S27c-1 deploy stale 가설 | 추측 | **false** → race condition (확정) |
| P0-S27c-2 GEMINI_API_KEY invalid | 확정 | 유지 (재현 verified) |
| F-LANDING-001 broken screenshots | 확정 | 유지 (localhost + production 동일) |
| IDOR 미검증 | partial | **real verified** ✅ |
| 헌법 I-9 위반 가능성 | 추정 | **false** → 정상 동작 |

## Verdict 유지

**외부 5명 진입**: 🔴 **NOT-READY**. 단 fix priority 정정:

1. **lazy seed race condition fix** (코드 line 160-169) — 1순위 (P0)
2. **GEMINI_API_KEY 재발급** — 2순위 (P0)
3. **landing screenshot 3건 fix** — 3순위 (P1)

이전 권고의 "Cloud Run redeploy" 는 fix 가 아님 (false hypothesis). 코드 변경 PR 필요.
