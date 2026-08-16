<!-- workspaces 도메인 — 멀티테넌시 격리 단위 (personal/team) + Member RBAC + Invite (2026-07-01 arch-verification 신설) -->

# workspaces CONTEXT

> 상위: `/apps/api/CONTEXT.md` → `/CONTEXT-MAP.md`. 별칭 금지: Workspace ≠ Team / Tenant / Org / Organization (헌법 §2.1).

---

## 1. 책임

- Workspace CRUD (`personal` / `team` 두 종류, Sprint 15)
- **WorkspaceMember** 소유 — RBAC 역할 (`owner` / `admin` / `member` / `viewer`, ADR-025)
- **WorkspaceInvite** 소유 — 초대 링크 발급 / 검증 / 가입 (`default_project_visibility` 시드, Sprint 6 L-8)
- 워크스페이스별 설정 (`inbox_threshold`, I-10)
- 멀티테넌시 격리의 최상위 경계 — 모든 콘텐츠 도메인의 `workspace_id` 부모

## 2. 비책임

- 인증 발급 + User row 매핑 (`auth` 도메인 / Better Auth)
- Project 멤버십 / visibility (`projects` — ProjectMember 는 별도)
- 콘텐츠 자체 (회의/노트/액션/메모리 각 도메인)

---

## 3. 엔티티 (소유)

- **Workspace** (`workspaces`)
  - `type`: `personal` / `team` (default `team` — 기존 row 호환, Sprint 15)
  - `owner_id` → `users.id`
  - `inbox_threshold`: float (default 0.9, PATCH 가능, I-10)
- **WorkspaceMember** (`workspace_members`)
  - `role`: `owner` / `admin` / `member` / `viewer`
  - `default_project_visibility`: `str | None` — 초대 수락 시 invite 에서 복사 (W-5). null = 워크스페이스 기본 `public`
  - **DB UNIQUE `(workspace_id, user_id)` = `uq_workspace_member`** (BUG-WS-MEMBER-UNIQUE, S28b) — lazy-seed/invite-accept 의 app-level `NOT EXISTS` 가드는 멀티워커(Cloud Run >1 인스턴스) interleave 에 backstop 없음 → DB 제약으로 중복 멤버십 차단
- **WorkspaceInvite** (`workspace_invites`)
  - `code`: nanoid 12자리 (`unique`, indexed)
  - `role`: 가입 시 부여할 역할
  - `default_project_visibility`: `public` / `draft` / `private` (Sprint 6 L-8)
  - `max_uses`: `int | None` (null = 무제한), `use_count`, `expires_at: datetime | None` (null = 만료 없음), `is_active`

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 |
|---|---|---|
| in | `projects/service.add_member` | Repository — `find_member` 로 cross-workspace ProjectMember 차단 검증 (I-17) |
| in | 모든 콘텐츠 도메인 | `workspace_id` FK 부모 (멀티테넌시, I-9) |
| out | `onboarding` | hook — 워크스페이스 생성 시 onboarding_step 전이 (Sprint 22 OBN-02) |
| out | `auth` | User row + `require_*` 역할 dependency |

---

## 5. 핵심 불변식

| # | 불변식 |
|---|---|
| W-1 | **모든 Member / Invite 조회·변이는 `workspace_id` 필터 강제** (헌법 I-9 멀티테넌시) |
| W-2 | **I-19 personal workspace = 1인 격리**: `type=='personal'` → owner 1명, `WorkspaceInvite` 발급 금지 + 멤버 추가 금지 (`invite_service.py` create/accept 에서 차단 — invite 가 유일한 멤버 추가 경로). ProjectMember 도 1명 (R5) |
| W-3 | **역할 RBAC 4-cell** (`owner` / `admin` / `member` / `viewer`, ADR-025). admin 이상 = 멤버 초대/제거. **역할 변경은 owner 전용** (`member_router.py` `require_owner`). owner 는 강등/제거 불가 대상 |
| W-4 | **I-10 inbox_threshold 워크스페이스별** (default 0.9, `PATCH /{workspace_id}/settings`). Inbox 자동 분류 confidence 임계값 |
| W-5 | **초대 가입 시 `default_project_visibility` 시드** — accept 시 invite 값을 `WorkspaceMember.default_project_visibility` 로 복사, 프로젝트 생성 시 visibility 미지정이면 이 시드 적용 (`projects/router.py` 폴백 체인 `data.visibility → member 시드 → public`). private 생성 시 creator 는 ProjectMember 로 자동 추가 (락아웃 방지). FE 생성 다이얼로그(`create-project-dialog.tsx`)의 기본 옵션 "워크스페이스 기본값" = visibility 미전송 → 이 폴백 체인 유지, 명시 선택 시만 전송 (2026-07-05 Stage 2 #4, e2e T20). (헌법 §5) |
| W-6 | **I-13 prefix 예외**: `workspaces` 루트는 `/api/v1/workspaces` (워크스페이스 자체 CRUD). 하위 리소스(members/invites)는 `/api/v1/workspaces/{workspace_id}/...` 표준 |

---

## 6. 엔드포인트

```
# /api/v1/workspaces (루트 — I-13 예외)
POST   /                                   생성 (201, personal/team)
GET    /                                   내 워크스페이스 목록
GET    /{workspace_id}                     디테일
PATCH  /{workspace_id}/settings            설정 변경 (inbox_threshold 등)
DELETE /{workspace_id}                     영구 삭제 (204, owner 전용) — personal 차단 (W-2),
                                           산하 데이터 앱 레벨 cascade (단일 트랜잭션),
                                           R2 객체는 r2-cleanup cron 위임

# /api/v1/workspaces/{workspace_id}/members
GET    /                                   멤버 목록
PATCH  /{member_id}                        역할 변경 (owner 전용)
DELETE /{member_id}                        멤버 제거 (204, admin+)

# /api/v1/workspaces/{workspace_id}/invites
POST   /                                   초대 링크 생성 (201, admin+) — personal 차단 (W-2)
GET    /                                   초대 목록 (admin+)
DELETE /{invite_id}                        초대 비활성화 (204, admin+)

# /api/v1/invites (public_router — 가입 진입)
       초대 코드 검증 + 가입 (멤버십 생성)
```

---

## 7. 엣지 케이스

- personal → team 승격: 현재 미지원 (`type` 변경 경로 없음, Sprint 15 lock-in)
- 만료/비활성 초대 코드 가입 시도 → 거부 (`invite_service.py:299` `is_active` + `expires_at` 검증)
- 멀티워커 동시 invite-accept → DB `uq_workspace_member` 가 중복 멤버십 backstop (W-1)
- owner 제거/강등 시도 → 거부 (W-3)
- cross-workspace 멤버 추가 시도 → `projects` 도메인이 `find_member` None → `CrossWorkspaceMemberError(403)` (I-17)
