# Sprint 27c — P0 fix (외부 5명 dogfooding 진입 prerequisite)

> Sprint 27c audit (`git history`) 산출 P0 3건 fix. **외부 5명 진입 직전 코드 PR 1건 + API key 재발급 + 이미지 fix**. 예상 ~1-2h.

## 진입 조건

- Sprint 27c audit (2026-05-23) 산출 P0 3건 확정:
  - **P0-1**: `get_current_user` lazy seed race condition (verified)
  - **P0-2**: `GEMINI_API_KEY` invalid (verified)
  - **P0-3**: landing screenshot 3건 400 (verified, source code bug)
- audit verdict: 🔴 NOT-READY — P0 fix 후 외부 5명 진입 unlocking

## Wave 1 — lazy seed race condition fix (P0-1, BL-S27c-1)

**위치**: `backend/src/auth/dependencies.py:158-221` `get_current_user`

**현 상태** (race-unsafe, line 160-169):
```python
repo = UserRepository(session)
user = await repo.find_by_clerk_id(claims["sub"])
is_new_user = user is None
if user is None:
    user = User(
        clerk_id=claims["sub"],
        display_name=claims.get("name", "사용자"),
        email=claims.get("email", ""),
    )
    user = await repo.save(user)         # ← race window
    await repo.commit()
```

**Fix 옵션 A (권장)** — `ON CONFLICT (clerk_id) DO NOTHING` + re-fetch (workspace INSERT 패턴 정합, 같은 file line 175-184):

```python
from sqlmodel import text as _text

repo = UserRepository(session)
user = await repo.find_by_clerk_id(claims["sub"])
is_new_user = user is None
if user is None:
    # Race-safe INSERT — workspace INSERT 패턴 정합 (line 175-184)
    await session.execute(
        _text(
            """
            INSERT INTO users (id, clerk_id, display_name, email, created_at, updated_at, onboarding_step)
            VALUES (gen_random_uuid(), :clerk_id, :name, :email, now(), now(), 0)
            ON CONFLICT (clerk_id) DO NOTHING
            """
        ),
        {
            "clerk_id": claims["sub"],
            "name": claims.get("name", "사용자"),
            "email": claims.get("email", ""),
        },
    )
    # Re-fetch after race-safe INSERT (one row guaranteed)
    user = await repo.find_by_clerk_id(claims["sub"])
```

**Fix 옵션 B** — try/except IntegrityError fallback:

```python
from sqlalchemy.exc import IntegrityError

repo = UserRepository(session)
user = await repo.find_by_clerk_id(claims["sub"])
is_new_user = user is None
if user is None:
    user = User(clerk_id=claims["sub"], display_name=..., email=...)
    try:
        user = await repo.save(user)
        await repo.commit()
    except IntegrityError:
        await session.rollback()
        user = await repo.find_by_clerk_id(claims["sub"])
        is_new_user = False  # race lose 측은 created 처리 skip
```

**선택**: 옵션 A. 이유:
- 같은 file 의 workspace INSERT (line 175-184) + workspace_members INSERT (line 186-200) 와 동일 패턴 → 일관성
- IntegrityError 처리는 SQLAlchemy session state 복잡 (rollback 후 후속 commit 영향) 회피
- `ON CONFLICT DO NOTHING` 는 PostgreSQL 한정 (Kairos = Neon Postgres = OK)

**회귀 가드 신규 추가**: `backend/tests/auth/test_get_current_user_race.py`
- 5 concurrent `asyncio.gather` 로 동일 clerk_id 의 lazy seed 시도 → 모두 user row 동일하게 return (no IntegrityError raise)

## Wave 2 — GEMINI_API_KEY 재발급 (P0-2, BL-S27c-2)

**사용자 액션** (코드 변경 0):

1. Google AI Studio (`https://aistudio.google.com`) login
2. 기존 key invalidate 후 새 key 발급 (gemini-3.1-flash-lite access 권한 verify)
3. `backend/.env` 갱신: `GEMINI_API_KEY=<new>`
4. Cloud Run secret manager 동기화 (jetaime-dev → kairos-api → Variables & Secrets → GEMINI_API_KEY)
5. Cloud Run revision 재배포 (secret 변경 후 자동 또는 manual)

**verify**: 회의 1건 업로드 → status="완료" 도달 + meeting detail 의 요약/액션 표시.

## Wave 3 — landing screenshot 3건 fix (P0-3, BL-S27c-3)

**위치**: `frontend/public/landing/screenshots/`

**현 상태**:
- 파일 존재 (disk verify): `screenshot-dashboard.png`, `screenshot-meeting-summary.png`, `screenshot-rag-answer.png`
- Next.js Image optimizer → `_next/image?url=/landing/screenshots/...` → **400 Bad Request**
- localhost + production 동일 → source/file 자체 issue (deploy 와 무관)

**진단 절차**:
1. 파일 dimension + format 검사: `file /Users/woosung/project/agy-project/kairos/frontend/public/landing/screenshots/*.png`
2. 파일 크기 0 byte 또는 corrupt verify
3. Next.js `next.config.mjs` 의 `images.formats` / `images.remotePatterns` 검사
4. Direct fetch (Image optimizer 우회): `curl http://localhost:3000/landing/screenshots/screenshot-dashboard.png` → 200 OK 인지

**Fix 후보**:
- 파일 corrupt 시 → 새 screenshot 재생성 (사용자 의 production 캡쳐)
- Next.js config 시 → `formats: ['image/webp']` 또는 `unoptimized` 옵션 검토
- dimension issue 시 → `<Image width={...} height={...} />` prop 정렬

## Wave 4 — 재진입 audit (~15분)

P0-1 PR 머지 + P0-2 key 갱신 + P0-3 screenshot fix 후:

1. localhost + production 환경에서 Account #3 (c@e.com) login → dashboard 500 → **200 OK** verify
2. 회의 1건 업로드 → status="완료" + 요약 표시 verify
3. landing 5초 진입 → screenshot 3건 정상 표시 verify
4. console.error 0건 confirm (PopoverTrigger 경고는 P1 별도)

P0 0건 confirm 후 외부 5명 모집 시작 (Sprint 27c audit plan §6 hard cap = 1주).

## 검증 증거 표준 (`.ai/templates/workflow.md` §3)

- **BE**: `pytest backend/tests/auth/test_get_current_user_race.py -v` 결과 + `alembic` 변경 0 (지정)
- **FE**: localhost 의 dashboard 첫 진입 console.error 0건 + screenshot 3건 정상 표시 evidence
- **API contract**: race condition fix 가 endpoint signature 변경 X → schemathesis skip

## Risk + Mitigation

| Risk | Mitigation |
|---|---|
| 옵션 A 의 SQL INSERT 가 User model 의 추가 컬럼 누락 시 DB-level default 처리 | model.py 의 `Field(default=...)` 모든 컬럼 verify. `created_at/updated_at` 은 `now()` 명시. `onboarding_step` 은 0 default. `email/avatar_url` 은 nullable=True 또는 NOT NULL with default 검토 |
| 옵션 A 의 `ON CONFLICT (clerk_id)` 가 partial index 가 아닌 `ix_users_clerk_id` 단순 UNIQUE 인덱스 사용 — model.py 의 `clerk_id: str = Field(unique=True, index=True)` 정합 | model + INSERT 패턴 일치 verify |
| GEMINI_API_KEY 갱신 시 Cloud Run revision 재배포 누락 | secret 변경 후 `gcloud run services describe` 로 active revision 의 env 검증 |
| landing screenshot 재생성 시 production 캡쳐 미수행 | placeholder image 또는 skeleton SVG fallback 임시 적용 |

## 후속 (P0 fix 후)

- Sprint 27c audit re-run 짧게 (~10분, 시나리오 #1~#4)
- BL-S27c-4~11 (P1/P2 9건) 는 Sprint 28+ 또는 외부 5명 dogfooding 중 발견된 신규 finding 과 합쳐서 별도 sprint
- memory `project_sprint27c_audit_done` archeology lock-in

## 종료 기준

- BL-S27c-1 PR merge + main HEAD 에 race-safe fix
- BL-S27c-2 사용자 API key 갱신 + Cloud Run secret 동기화
- BL-S27c-3 screenshot 3건 정상 표시
- 재진입 audit verdict 🟢 READY confirm

이 plan 종료 후 → 외부 5명 모집 1주 hard cap 진입 (audit plan §6).
