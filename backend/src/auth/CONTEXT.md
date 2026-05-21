<!-- auth 도메인 — Clerk JWT 검증 + User 매핑 + 서버 측 onboarding tracker -->

# auth CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- Clerk JWT 검증 (`get_current_user`)
- Clerk 외부 ID → 내부 User row 매핑 + lazy seed (Sprint 15)
- Personal Workspace + WorkspaceMember lazy seed (`uq_workspaces_owner_personal` partial unique index race-safe)
- RBAC 분기 (`rbac.py`)
- 서버 측 영속 onboarding step 보유 (User 컬럼, Sprint 22 OBN-02)

## 2. 비책임

- 도메인 권한 정책 자체 (각 도메인 router/service)
- 워크스페이스 invitation / role 관리 (`workspaces`)
- 클라이언트 sync hook (`frontend/src/features/auth`)

---

## 3. 엔티티 (소유)

- **User**
  - `id: UUID` (PK)
  - `clerk_id: str` (unique, indexed) — Clerk 외부 ID
  - `display_name: str`
  - `email: str`
  - `avatar_url: str | None`
  - `created_at / updated_at: datetime`
  - **`onboarding_step: int = 0`** — 0=NOT_STARTED, 1=WORKSPACE_CREATED, 2=FIRST_PROJECT, 3=FIRST_MEETING (distillation 완료), 4=FIRST_RAG. Sprint 22 OBN-02 (alembic `d8623df0adab`). 기존 row 는 backfill step=4.
  - **`onboarded_at: datetime | None`** — step=4 도달 시 set (idempotent, backfill 시 `created_at` 동기).

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 |
|---|---|---|
| in  | 모든 BE 도메인 router (`require_user` Depends) | L1 |
| out | `workspaces.repository` (lazy seed) | L1 |
| out | Clerk SDK (JWT 검증) | L0 (외부) |

---

## 5. 핵심 불변식

- Clerk JWT 부재 / 만료 → 401 (router level)
- User 부재 시 `get_current_user` 가 lazy seed 1회 (Sprint 15)
- Personal Workspace 부재 시 lazy seed 1회 (race-safe: `uq_workspaces_owner_personal` partial unique index)
- `onboarding_step` 은 단조 증가 (downgrade 없음) — Sprint 22 OBN-02
- **Clerk webhook endpoint 부재** (Sprint 25 T-SEC-1 / BUG-SENTINEL-005, ADR-022 lock-in) — `POST /api/v1/users/sync` 핸들러 + `AuthService.sync_user` 메서드 제거됨. 2026-05-21 사용자 결정: Clerk Production 인스턴스 미발급 + Clerk webhook SKIP (memory `project_gcp_migration_jetaime_dev_done.md` lock-in, ADR-022 archeology). GA launch 시 Svix 검증 추가 + 재도입 별도 sprint.

---

## 6. 노출 엔드포인트 (prefix `/api/v1/users`)

- `GET /me` — 인증된 사용자 정보 (`get_current_user` lazy seed 포함)
- ~~`POST /sync`~~ — Sprint 25 T-SEC-1로 제거 (BUG-SENTINEL-005). 위 §5 불변식 참조.
