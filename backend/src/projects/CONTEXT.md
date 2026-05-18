<!-- projects 도메인 — 작업 단위 (PARA Replace) + MeetingProjectLink + 인사이트 + 멤버십 + visibility (Sprint 6 완료) -->

# projects CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- Project CRUD (생성/조회/수정/삭제/아카이브)
- **MeetingProjectLink** N:M 관계 소유 (Project ↔ Meeting)
- **ProjectMember** N:M 관계 소유 (Project ↔ User, Sprint 6 L-6)
- 태그 (AI 자동 + 사용자 수정)
- 인사이트 L1~L4 (현재 L1/L2 활용, L3 부분, L4 Phase 4)
- visibility 기반 권한 분기 (public/draft/private, Sprint 6 BE-T1~T8 + T15)

## 2. 비책임

- 회의/노트/액션 콘텐츠 자체 (각 도메인)
- 임베딩/RAG (각 도메인)
- 워크스페이스 멤버 관리 (`workspaces`)

---

## 3. 엔티티 (소유)

- **Project**
  - `status`: `active` / `completed` / `archived`
  - `visibility`: `public` / `draft` / `private` (default `public`, indexed) — Sprint 6 BE-T1 (마이그레이션 `c4c5709a4ab4`)
  - `tags`: JSONB (AI 자동 + 사용자)
  - `sort_order`
- **MeetingProjectLink** — N:M (`(meeting_id, project_id)` 유일). meetings 도메인이 아닌 **projects 도메인 소유**.
- **ProjectMember** — N:M (`(project_id, user_id)` 유일). visibility=Private 시 명시적 멤버 매핑 (Sprint 6 BE-T5, 마이그레이션 `754f571d5544`). `role` 컬럼은 향후 sprint 7+ 확장 여지로 두되 1차는 `"member"` 단일 (AD-27).

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 |
|---|---|---|
| in | `inbox/service` | Repository (read) — 후보 프로젝트 조회 |
| in | `meetings/pipeline` | Repository — 자동 연결 + MeetingProjectLink 생성 |
| in | `notes/service` | Repository — 노트 부모 검증 |
| in | `actions/service` | Repository — 액션 부모 검증 (nullable) |
| in | `rag/service` | Repository — 범위 검색 권한 검증 |

> **Project는 다수 도메인의 부모.** 다른 도메인이 Project Repository를 read-only로 의존하는 것은 허용 (CONTEXT-MAP §4.2 #1).

---

## 5. 핵심 불변식

| # | 불변식 |
|---|---|
| P-1 | **Project는 항상 `workspace_id` 소속** — 워크스페이스 간 이동 금지 |
| P-2 | **status 전이**: `active` ↔ `completed` ↔ `archived` (순환 가능) |
| P-3 | **archived → 자동 인사이트 추출 트리거** (Phase B 또는 Sprint 6 결정) |
| P-4 | **태그는 정규화 (소문자, 한글 OK)** — 검색 일관성 |
| P-5 | **visibility 권한 분기** (Sprint 6 BE-T8, repository.py `_apply_visibility_filter`): `public` = 워크스페이스 멤버 모두 / `draft` = creator + admin/owner / `private` = ProjectMember + admin/owner. admin/owner는 모든 visibility 우회 |
| P-6 | **삭제는 hard delete + cascade 또는 soft (status=archived)** — UI는 archive 우선 노출 |
| P-7 | **권한**: `archive` / `delete`는 `admin` 이상. **`visibility` 변경은 `admin` 이상 (Sprint 6 BE-T15)**. 일반 update(title/description/status/tags)는 require_member 유지 (AD-32). ProjectMember 추가/제거는 `admin` 이상 (BE-T7) |
| P-8 | **ProjectMember 추가 cross-workspace 차단** (Sprint 7 — AD-33): `add_member`는 `workspace_id`를 필수 인자로 받아 cross-workspace 검증 수행. 검증 순서: project 존재(404) → workspace mismatch(404) → ws_member 존재(403) → 중복(DB UniqueConstraint). is_active 검증 없음 (WorkspaceMember.is_active 컬럼 미존재). |
| **P-9** | **모든 Repository / Service find / mutation 시그니처에 `workspace_id` 강제** (Sprint 19 PR #1 C9, 헌법 I-9, Codex F-1/F-3): `find_by_id(project_id, workspace_id)` / `find_members(project_id, workspace_id)` / `is_member(project_id, user_id, workspace_id)` / `remove_member(project_id, user_id, workspace_id)` / `add_meeting_link(meeting_id, project_id, workspace_id)` / `remove_meeting_link(meeting_id, project_id, workspace_id)` / `find_projects_by_meeting(meeting_id, workspace_id)` 전부 WHERE workspace_id 절 적용. cross-tenant resource 는 `ProjectNotFoundError(404)` 로 정보 누설 방지 (F-4 lock-in). secondary FK (`meeting_id`) 입력 시 `_verify_secondary_fks` fail-closed (repo None → `RuntimeError`). cross-domain 호출자 (meetings/inbox/actions/notes/rag) 모두 동시 cascade patch. |

---

## 6. 엔드포인트

> `/api/v1/workspaces/{workspace_id}/projects` prefix. Sprint 19 PR #1 C9: 11 endpoint 전수 `workspace_id` 시그니처 강제 + cross-tenant → 404 lock-in.

```
GET    /                                                    목록 (visibility 필터 적용)
GET    /{id}                                                디테일 (visibility 검증, find_by_id workspace_id)
POST   /                                                    생성 (201, visibility 지정 가능)
PATCH  /{id}                                                수정 (visibility 변경은 admin+, F-1)
DELETE /{id}                                                삭제 (204, admin+, F-1)
POST   /{id}/archive                                        archive 전환 (admin+, F-1)
GET    /{id}/members                                        프로젝트 멤버 목록 (Sprint 6 BE-T7, viewer+, F-1)
POST   /{id}/members                                        멤버 추가 (Sprint 6, admin+)
DELETE /{id}/members/{user_id}                              멤버 제거 (Sprint 6, admin+, F-1)
```

> 추가 prefix `/api/v1/workspaces/{workspace_id}/meetings/{meeting_id}/projects`:

```
POST   /{project_id}                                        Meeting-Project 링크 생성
DELETE /{project_id}                                        Meeting-Project 링크 해제
```

---

## 7. 엣지 케이스

- archived 프로젝트의 콘텐츠 → RAG 검색 대상 유지 (조직 지식 베이스)
- 멤버 0인 private 프로젝트 (Sprint 6) → owner만 접근
- 태그 수동 수정 후 AI 재추천 → 사용자 태그 우선 (덮어쓰기 금지)
- 프로젝트 삭제 → 관련 ActionItem은 `project_id=null` 처리 (orphan, §7 D-10)

---

## 8. Sprint 6 [완료]

- ✅ `visibility` 컬럼 추가 + 마이그레이션 `c4c5709a4ab4` (BE-T1, commit e779541)
- ✅ ProjectMember 엔티티 + 마이그레이션 `754f571d5544` (BE-T5, commit cecc888)
- ✅ Repository visibility 필터 — `_apply_visibility_filter` (BE-T8, public/draft creator/private member 분기)
- ✅ ProjectMember CRUD endpoint (BE-T7, GET viewer+ / POST·DELETE admin+)
- ✅ visibility 변경 admin 강제 (BE-T15)
- ✅ FE 시안 1A+1C/2A/3A 구현 (T-DESIGN-2 + 575c613/9a975e7)

**Sprint 7+ 잔여 (AD-32~33)**:
- BE-T16: Project update 권한 강화 (creator-only 또는 admin) — 보류 (member 협업 마찰 우려)
- ✅ ProjectMember 추가 cross-workspace 차단 — Sprint 7 BE-T1~T3 완료 (AD-33)

## 멤버 추가 정책 (Sprint 7 — AD-33)

`add_member` 호출 시 workspace_id를 필수 인자로 받아 cross-workspace 검증 수행.
검증 순서: project 존재(404) → workspace mismatch(404) → ws_member 존재(403) → 중복(DB UniqueConstraint).
is_active 검증 없음 (WorkspaceMember.is_active 컬럼 미존재).
