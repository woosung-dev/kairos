<!-- inbox 도메인 — 콘텐츠 1차 진입점 + AI 자동 분류 추천 + 사용자 조정 -->

# inbox CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- 모든 콘텐츠(회의/노트/자료)의 **1차 진입점** 적재
- AI가 추천한 프로젝트 연결 + 태그 저장 (`ai_suggested_*`)
- `workspaces.inbox_threshold` 기반 자동 확정 / 사용자 확인 분기
- 사용자의 분류(classify, N:M) 또는 무시(dismiss) 처리

## 2. 비책임

- 콘텐츠 원본 저장 (Meeting/Note/Source 도메인 별도)
- AI 추천 생성 (`services/ai_processing` — meetings 파이프라인이 호출)
- 임베딩

---

## 3. 엔티티 (소유)

- **InboxItem**
  - `title`, `summary` (UI 노출용 메타)
  - `source_type`: `meeting` / `note` / `attachment`
  - `source_id`: 원본 콘텐츠 ID
  - `ai_suggested_project_id` (단수), `ai_suggested_project_title`
  - `ai_suggested_tags` (JSONB)
  - `ai_confidence` (0.0~1.0)
  - `is_processed` (사용자 처리 완료 플래그)

> **비대칭 주의**: AI 추천은 **단수** (`ai_suggested_project_id`), 사용자 분류는 **N:M** (`classify` 엔드포인트의 `project_ids: list[UUID]`).

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 |
|---|---|---|
| out | `projects/repository` | Repository (read-only — 후보 프로젝트 조회) |
| out | `workspaces/repository` | Repository (read-only — `inbox_threshold` 조회, Sprint 23 D4 promote 시 target 검증) |
| out | `meetings/repository` | Repository (read-only — classify 의 source_id 검증) |
| out | `common/promote_helpers` | utility (Sprint 23 D4 — `validate_promote_target` + `build_item_promotion_audit`) |
| in | `meetings/pipeline_service` | service 위임 (적재 시) |
| in | `notes/service` | service 위임 (적재 시) |
| in | `upload/service` | service 위임 (적재 시) |

---

## 5. 핵심 흐름

### 5.1 적재 (다른 도메인 → Inbox)
```
콘텐츠 생성 (회의 처리 완료 / 노트 작성 / 파일 업로드)
  → InboxService.create_from_<source>()
  → AI 추천 (project_id + tags + confidence) 저장
  → confidence 분기 (워크스페이스의 `inbox_threshold` 사용):
     ├─ confidence ≥ threshold: is_processed=true 자동 확정 (사용자 수정/되돌리기 가능)
     └─ confidence <  threshold: is_processed=false (사용자 확인 대기)
```

### 5.2 사용자 처리
```
GET    /inbox                  → 미처리(is_processed=false) 우선 정렬
POST   /inbox/{id}/classify    → 사용자가 project_ids: list[UUID] + tags 확정 (N:M)
POST   /inbox/{id}/dismiss     → 사용자가 무시 (is_processed=true, projects 비움)
```

---

## 6. 핵심 불변식

| # | 불변식 |
|---|---|
| IB-1 | **자동 확정 시에도 `ai_suggested_*` 필드 보존** (사용자가 되돌릴 수 있음) |
| IB-2 | **confidence 임계값은 워크스페이스별 `workspaces.inbox_threshold`** (기본 0.9, PATCH 가능) — 헌법 I-10 |
| IB-3 | **dismiss는 삭제 아님** — 감사/되돌리기 위해 보존 |
| IB-4 | **source_type + source_id 유일성** — 같은 콘텐츠 중복 적재 금지 |
| IB-5 | **classify는 idempotent + N:M** — 같은 InboxItem을 여러 번 classify해도 마지막 입력의 project_ids/tags가 최종 |
| IB-6 | **헌법 I-9 (Sprint 19 PR #1, Codex F-1)** — service / repository 모든 메서드 workspace_id 필수. find_by_id(inbox_id, workspace_id), classify(inbox_id, workspace_id, project_ids), dismiss(inbox_id, workspace_id) 시그니처 |
| IB-7 | **Codex F-2 Critical secondary FK** — classify 의 project_ids 모두 같은 workspace 내인지 ProjectRepository.find_by_id + project.workspace_id 검증. cross-workspace 거부 → 404 (ProjectNotFoundError). add_meeting_link 시그니처 자체 변경은 후속 (PR #2 BUG-C01-EXT-FK alembic) |
| IB-8 | **헌법 I-18 promote = 복제 + tombstone (Sprint 23 D4)** — `POST /inbox/{id}/promote` 는 원본 InboxItem 보존 + target ws 복제본 신규 + `ItemPromotionAudit(item_type='inbox')` row. source != target / target.type='team' / promoter 가 target ws 멤버 검증. `ai_suggested_project_id`=None reset (composite FK fk_inbox_suggested_project_workspace 제약, target ws orphan). `is_processed`=False reset (복제본은 사용자 재분류 대기). `source_id`/`ai_suggested_project_title`/`ai_suggested_tags`/`ai_confidence` 는 메타로 보존. InboxItem 임베딩 ledger 부재 → audit.embedding_status='n/a' + status='completed' (notes/meetings 와 차이) |

---

## 7. 엔드포인트

> 모두 `/api/v1/workspaces/{workspace_id}/inbox` prefix.

```
GET    /                    목록 (미처리 우선)
POST   /{id}/classify       확정/수정 (project_ids: list, tags: list)
POST   /{id}/dismiss        무시
POST   /{id}/promote        Sprint 23 D4 — Inbox → team workspace 복제 (I-18, 202)
```

### Tenant boundary (Sprint 19 PR #1, Codex F-1/F-2/F-4/F-6 반영)

- 인증/인가: `require_member` (POST classify/dismiss) / `require_viewer` (GET list) 통과
- service / repository: 모든 호출에 path `workspace_id` 필수 전달 (헌법 I-9, IB-6)
  - `service.classify(inbox_id, workspace_id, project_ids)`
  - `service.dismiss(inbox_id, workspace_id)`
  - `repository.find_by_id(inbox_id, workspace_id)`
- secondary FK (Codex F-2 Critical, IB-7):
  - classify 의 `project_ids` 모두 `ProjectRepository.find_by_id` + `project.workspace_id == workspace_id` 검증
  - cross-workspace project_id 거부 → 404 (`ProjectNotFoundError`)
  - 사전 검증 통과한 verified_projects 만 add_meeting_link 호출 (cross-workspace meeting/project 링크 생성 차단)
- cross-tenant 응답:
  - path workspace 안에 없는 `inbox_id` → 404 (`InboxItemNotFoundError`)
  - cross-workspace `project_id` → 404 (`ProjectNotFoundError`)
- 회귀 가드: `backend/tests/integration/test_workspace_idor_matrix.py::TestInboxIDORMatrix` 4 케이스 + `tests/inbox/test_inbox_service.py` 13 케이스

---

## 8. 엣지 케이스

- AI 추천이 없는 경우 (confidence=0) → 사용자 확인 항상 필요
- 추천된 프로젝트가 삭제됨 → `ai_suggested_project_id` null 처리, 재추천 또는 사용자 선택
- 사용자가 새 프로젝트 생성하며 분류 → projects 도메인 호출 후 Inbox 확정
