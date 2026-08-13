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

### 5.1 in-process 캐시 정책 (Sprint 28 BUG-S28-PERF-RT-1 + Stage 2 #6 하드닝 2026-07-05)

| 캐시 | 위치 | TTL | invalidation |
|---|---|---|---|
| JWT claims | `dependencies.py` `_JWT_CLAIMS_CACHE` | 60s | 자연 만료 |
| User (clerk_id→User) | `dependencies.py` `_USER_CACHE` | 60s | `invalidate_user_cache` |
| WorkspaceMember ((ws,user)→Member) | `rbac.py` `_MEMBER_CACHE` | **15s** | `invalidate_member_cache` — 호출 3곳: `workspaces/invite_service.py` (role 변경·remove) + `workspaces/service.py` (ws 삭제) |

- **admin/owner 게이트와 `require_member_fresh` 는 member 캐시 bypass** (`_CACHE_BYPASS_MIN_LEVEL` / 명시적 opt-in): `require_admin`/`require_owner` 는 항상, 그리고 **캐시된 role 을 admin 우회 판정에 소비하는 파괴적 member 라우트**(2026-08-02 기준 notes PATCH·DELETE·promote / meetings promote / actions PATCH / projects PATCH)는 `require_member_fresh` 로 DB fresh 조회 후 write-through. ⚠ **그 밖의 상태 변경 member 라우트(create·capture·classify·dismiss·upload 등)는 여전히 캐시 게이트** — 강등된 viewer 가 15s 창에서 member 급 쓰기를 통과할 수 있다 (BL-BE-RBAC-FRESH-REMAINING-1, 전면 적용은 성능 회귀라 별도 판단). 근거 — invalidation 은 in-process 전용이라 Cloud Run max-instances=3 에서 타 인스턴스 캐시에 전파되지 않음. bypass 로 강등된 role 의 파괴적 작업(멤버 관리·삭제·초대)은 cross-instance 에서도 즉시 차단. **알려진 잔여**: viewer/member 게이트를 지나는 읽기(RAG/visibility 판단의 requester_role 포함)는 cross-instance stale 상한 15s — 강등된 admin 이 타 인스턴스에서 최대 15s 간 private 읽기 가능. 완전 해소(Redis pub/sub 또는 DB version)는 GA 스케일업 재검토 (2026-07-05 비용 비교 후 의도적 수용).
- Redis pub/sub / DB version 칼럼 대안은 Stage 2 재평가(2026-07-05)에서 비용 대비 기각 — GA 스케일업 시 재검토.

---

## 6. 노출 엔드포인트 (prefix `/api/v1/users`)

- `GET /me` — 인증된 사용자 정보 (`get_current_user` lazy seed 포함)
- ~~`POST /sync`~~ — Sprint 25 T-SEC-1로 제거 (BUG-SENTINEL-005). 위 §5 불변식 참조.
