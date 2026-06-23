<!-- actions 도메인 — 액션 아이템 추출/추적 (nullable 부모) -->

# actions CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- ActionItem CRUD (생성/조회/수정)
- 회의에서 자동 추출된 액션 저장 (meetings 파이프라인이 호출, `project_id` 미설정 가능)
- 사용자 수동 액션 생성 + 상태 변경
- 담당자 / 마감일 / 우선순위 관리

## 2. 비책임

- 액션 추출 알고리즘 (`services/ai_processing` — meetings 파이프라인이 사용)
- 알림 발송 (Phase B / 추후)

---

## 3. 엔티티 (소유)

- **ActionItem**
  - `workspace_id` (required — 멀티테넌시)
  - `meeting_id`: **nullable** (수동 생성 시 null)
  - `project_id`: **nullable** (orphan 허용, 후속 분류 대상 — §7 D-10)
  - `assignee_id`: **nullable** (미할당 액션 가능)
  - `due_date`: `date | None` — **timezone 없음** (`datetime.date` 타입). FE에서 사용자 로컬 해석
  - `title`, `description`
  - `priority`: `high` / `medium` / `low` (기본 `medium`)
  - `status`: `todo` / `in_progress` / `done` / `cancelled` (기본 `todo`)

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 |
|---|---|---|
| in | `meetings/pipeline` | Repository — 추출된 액션 저장 |
| out | `projects/repository` | Repository (read-only) — 부모 프로젝트 검증 (project_id 있을 때만) |
| out | `workspaces/repository` | Repository (read-only) — 담당자(WorkspaceMember) 검증 + promote target 검증 (I-18) |
| out | `common/promote_helpers` | utility — validate_promote_target + build_item_promotion_audit (Sprint 23 D4) |
| out | `common/promote_models` | Model — ItemPromotionAudit row 저장 (item_type='action') |

---

## 5. 핵심 불변식

| # | 불변식 |
|---|---|
| A-1 | **`workspace_id` 필수**, 그 외 부모 FK는 모두 nullable. `project_id=null` orphan은 허용 (사용자 분류 대상 — D-10) |
| A-2 | **status 전이는 자유** (todo ↔ in_progress ↔ done ↔ cancelled) |
| A-3 | **assignee는 워크스페이스 멤버만** (외부 사용자 할당 금지). null 허용 |
| A-4 | **AI 추출 액션도 사용자 수정 가능** — 출처(`meeting_id`)는 보존 |
| A-5 | **`due_date`는 `date` 타입 (timezone 없음)**. FE에서 사용자 로컬로 해석 — 시각 표시 시 timezone 추론 금지 |
| A-6 | **헌법 I-9 (Sprint 19 PR #1, Codex F-1)** — service / repository 모든 메서드 workspace_id 필수. find_by_id(action_id, workspace_id), update_action_item(action_id, workspace_id, ...) 시그니처 |
| A-7 | **Codex F-2 Critical 3 secondary FK** — create / update 시 project_id / meeting_id / assignee_id 모두 같은 workspace 검증. project = ProjectRepository.find_by_id + project.workspace_id, meeting = MeetingRepository.find_by_id(meeting_id, workspace_id), assignee = WorkspaceRepository.find_member(workspace_id, assignee_id). 거부 시 모두 404 |
| A-8 | **owning project visibility 게이트 (F1/F2, 2026-06-23 fullsweep; notes CAND-A 정합)** — `list_action_items`(repo `_action_visibility_filter`) + `update_action_item`(`_verify_action_visibility`) 이 requester_user_id/requester_role 로 게이트. private = ProjectMember 만, draft = project.created_by_id 만, admin/owner 우회, project_id=None/public 통과. requester_role=None(내부/파이프라인) = skip. 비-멤버 list 제외 / update 404 |

---

## 6. 엔드포인트

> `/api/v1/workspaces/{workspace_id}/action-items` prefix (리소스 이름은 케밥 케이스).

```
GET    /                목록 (필터: project / assignee / status)
POST   /                생성 (201)
PATCH  /{id}            수정 (status / assignee / due_date / project_id 등)
POST   /{id}/promote    cross-workspace 복제 (I-18, Sprint 23 D4, 202)
```

### Promote 정책 (Sprint 23 D4, I-18 강제)

- `POST /api/v1/workspaces/{wid}/action-items/{id}/promote` — body `{ "targetWorkspaceId": uuid }`
- 검증: source != target / target.type='team' / promoter 가 target ws 멤버
- 복제 정책:
  - `meeting_id` / `project_id`: **None reset** (composite FK `fk_action_items_meeting_workspace` / `fk_action_items_project_workspace` 강제 — target ws 와 무관)
  - `assignee_id`: **None reset** (단순화 — 헌법 A-3: assignee 는 워크스페이스 멤버만 + cross-workspace 사용자 책임 모호. 사용자가 target ws 에서 재할당)
  - `title` / `description` / `priority` / `status` / `due_date`: 보존 (history 의미)
- 임베딩 ledger 부재 → BG embedding 복제 없음. `ItemPromotionAudit.embedding_status='n/a'` + 응답 `status='completed'` (inbox 와 동일, notes/meetings 의 'embedding_pending' 과 차이)
- 에러: 400 (same_workspace / target_personal), 403 (target_invalid / not_member), 404 (source action_id)
- 회귀 가드: `backend/tests/actions/test_action_promote.py` 4 케이스

### Tenant boundary (Sprint 19 PR #1, Codex F-1/F-2/F-4/F-6 반영)

- 인증/인가: `require_member` (POST/PATCH) / `require_viewer` (GET) 통과
- service / repository: 모든 호출에 path `workspace_id` 필수 (헌법 I-9, A-6)
  - `service.update_action_item(action_id, workspace_id, ...)`
  - `repository.find_by_id(action_id, workspace_id)`
- secondary FK 검증 (Codex F-2 Critical, A-7) — `_verify_secondary_fks` helper:
  - `project_id` → `ProjectRepository.find_by_id` + `project.workspace_id == workspace_id` → `ProjectNotFoundError` (404)
  - `meeting_id` → `MeetingRepository.find_by_id(meeting_id, workspace_id)` (이미 시그니처 강제) → `MeetingNotFoundError` (404)
  - `assignee_id` → `WorkspaceRepository.find_member(workspace_id, assignee_id)` → `NotFoundError("워크스페이스 멤버")` (404)
  - create + update 양쪽 동일 검증
- cross-tenant 응답: 모두 404
- dependencies: `get_action_service` 가 `ProjectRepository` / `MeetingRepository` / `WorkspaceRepository` 동반 주입 (동일 session 공유)
- 회귀 가드: `backend/tests/integration/test_workspace_idor_matrix.py::TestActionsIDORMatrix` 5 케이스 + `tests/actions/test_actions_service.py` 18 케이스

---

## 7. 엣지 케이스

- 회의 삭제 → 자동 추출된 액션의 `meeting_id` null 처리 (액션 자체는 보존)
- 프로젝트 삭제 → 자동 archive 또는 cascade (Phase B 결정). 액션은 `project_id=null` orphan 처리 (§7 D-10)
- 마감 지난 액션 → 자동 알림 (Phase B / 추후)
- 같은 회의에서 중복 추출 → 텍스트 유사도 dedupe 부재 (CONTEXT-MAP §7 D-7)
