<!-- projects 도메인 — 작업 단위 (PARA Replace) + MeetingProjectLink + 인사이트 + 멤버십 (Sprint 6) -->

# projects CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- Project CRUD (생성/조회/수정/삭제/아카이브)
- **MeetingProjectLink** N:M 관계 소유 (Project ↔ Meeting)
- 태그 (AI 자동 + 사용자 수정)
- 인사이트 L1~L4 (현재 L1/L2 활용, L3 부분, L4 Phase 4)
- 멤버십 + visibility (Sprint 6 예정 — 현재 미구현, §7 D-1)

## 2. 비책임

- 회의/노트/액션 콘텐츠 자체 (각 도메인)
- 임베딩/RAG (각 도메인)
- 워크스페이스 멤버 관리 (`workspaces`)

---

## 3. 엔티티 (소유)

- **Project**
  - `status`: `active` / `completed` / `archived`
  - `tags`: JSONB (AI 자동 + 사용자)
  - `sort_order`
  - `visibility`: `public` / `draft` / `private` — **Sprint 6 추가 예정** (현재 미구현, CONTEXT-MAP §7 D-1)
- **MeetingProjectLink** — N:M (`(meeting_id, project_id)` 유일). meetings 도메인이 아닌 **projects 도메인 소유**.

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
| P-5 | **visibility 미구현** — 현재 모든 Project는 워크스페이스 멤버 모두 접근 가능 (Sprint 6 격리 도입) |
| P-6 | **삭제는 hard delete + cascade 또는 soft (status=archived)** — UI는 archive 우선 노출 |
| P-7 | **권한**: `archive` / `delete` / `update settings`는 `admin` 이상. 일반 멤버는 read + N:M 링크만 |

---

## 6. 엔드포인트

> `/api/v1/workspaces/{workspace_id}/projects` prefix.

```
GET    /                                                    목록 (워크스페이스 범위)
GET    /{id}                                                디테일
POST   /                                                    생성 (201)
PATCH  /{id}                                                수정
DELETE /{id}                                                삭제 (204, admin+)
POST   /{id}/archive                                        archive 전환 (admin+)
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

## 8. Sprint 6 작업 영역 (예정)

- `visibility` 칼럼 추가 + 마이그레이션 (Alembic)
- ProjectMember 엔티티 (또는 visibility=private 시 추가 ACL)
- 권한 체크 로직 — Repository 레벨에서 강제 (멀티테넌시 패턴 준용)
- FE: 가시성 토글 UI + 멤버 초대 다이얼로그
