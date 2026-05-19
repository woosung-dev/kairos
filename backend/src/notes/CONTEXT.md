<!-- notes 도메인 — Capture→Organize→Distill 의 텍스트 노트 책임 + embedding orchestrator -->

# notes CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- 텍스트 노트 CRUD (Tiptap JSON content + plain_text)
- 노트 → 임베딩 트리거 (NotePipelineService 경유, BackgroundTasks)
- 프로젝트 visibility 권한 동적 검증 (`check_project_access`)
- embedding chunk cleanup 동반 삭제 (orchestrator 옵션 A)

## 2. 비책임

- 임베딩 저장/검색 자체 (`embeddings`/`rag`)
- AI 분석/요약 (notes 는 단순 capture, 분석 대상 아님)
- Inbox 적재 (현재 — meetings 만 Inbox 적재)

---

## 3. 엔티티 (소유)

- **Note** — Tiptap JSON content, plain_text, workspace_id, project_id (nullable)

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 | 비고 |
|---|---|---|---|
| out | `embeddings/service` | via pipeline | 임베딩 생성 + 캐시 무효화 |
| out | `projects/repository` | Repository (read) | project visibility 검증 + Codex F-2 secondary FK 검증 |
| out | `embeddings/repository` | direct (orchestrator) | chunk delete (ADR-014 §1 cross-domain shared service) |
| out | `workspaces/repository` | Repository (read) | Sprint 23 D4: promote target 검증 (find_by_id / find_member) |
| out | `common/promote_helpers` | Utility | Sprint 23 D4: validate_promote_target + build_item_promotion_audit (4 도메인 공통) |
| out | `common/promote_models` | Model (write) | Sprint 23 D4: ItemPromotionAudit row 적재 (item_type='note') |
| out | `embeddings/models` (EmbeddingChunk) | direct (BG copy) | Sprint 23 D4: promote BG embedding 복제 (source_type='note' 한정) |

---

## 5. 핵심 흐름

```
1. POST /notes → NoteService.create_note (workspace_id, project_id F-2 검증)
   → BackgroundTask: pipeline.embed_note_async(note_id, workspace_id)
2. PATCH /notes/{id} → NoteService.update_note (workspace_id, project_id F-2 검증)
   → BackgroundTask: pipeline.embed_note_async (content 변경 시)
3. DELETE /notes/{id} → pipeline.delete_note_with_cleanup(note_id, workspace_id)
   → embedding chunk delete → note delete → cache invalidate (옵션 A)
4. GET /notes/{id}, /export → NoteService.get_note / export_note (workspace_id 필수)
```

---

## 6. 핵심 불변식

| # | 불변식 |
|---|---|
| N-1 | **NoteService 는 embeddings.service 직접 호출 금지** — pipeline orchestrator 경유만 (헌법 §4.2, ADR-014 옵션 A) |
| N-2 | **delete 는 pipeline.delete_note_with_cleanup 경유** — embedding cleanup + cache invalidation 묶음 (옵션 A, Codex H2) |
| N-3 | **Note.project_id 변경 시 같은 workspace 내 project 만 허용** (Codex F-2 Critical secondary FK) |
| N-4 | **헌법 I-9 (Sprint 19 PR #1, Codex F-1)** — service / repository / pipeline 모든 메서드 workspace_id 필수. find_by_id(note_id, workspace_id), get_note(note_id, workspace_id), update_note / delete_note / export_note 동일, pipeline embed_note_async / delete_note_with_cleanup 도 동일 |
| N-5 | **cross-tenant 시도 응답: 404** (path workspace 안에 없는 note_id = NotFound, Codex F-4 lock-in) |
| N-6 | **Sprint 23 D4 promote = 복제 + tombstone (헌법 I-18)** — 원본 Note 변경 없음. target ws 에 새 Note + EmbeddingChunk 복제 (BG) + ItemPromotionAudit (item_type='note') |
| N-7 | **promote 복제본 project_id = None** — source.project_id 는 source ws 의 project 라 cross-workspace 제약 (secondary FK ck). target ws 에서 PATCH 로 별도 연결 |
| N-8 | **promote 검증 — same_workspace/target_personal → 400, target_invalid/not_member → 403** (CannotPromoteToSameWorkspaceError / CannotPromoteToPersonalError / TargetWorkspaceInvalidError) |
| N-9 | **Sprint 24 BL-064: chunk 0 + plain_text 분기는 BG re-embedding schedule** — 400 거부 대신 `_bg_regenerate_embed_with_audit` wrapper BG task 가 `pipeline.embed_note_async` 호출 + audit `pending → processing → completed/failed` lifecycle 갱신. plain_text 부재 case 만 400 회귀 가드 유지 |
| N-10 | **Sprint 24 BL-064: PromoteNoteOut snake_case 보존** — `new_note_id` / `audit_id` / `embedding_status` 모두 snake_case (alias 추가 X). FE ItemPromoteModal 의 NEW_ID_KEY snake_case read 호환성 (Codex 2차 P2-3) |

---

## 7. 엔드포인트 (8)

> 모두 `/api/v1/workspaces/{workspace_id}/notes` prefix.

```
GET    /                          목록 (project_id 필터 옵션)
GET    /{id}                      디테일
GET    /{id}/export               내보내기 (md / json)
POST   /                          create
PATCH  /{id}                      update (title / content / project_id)
DELETE /{id}                      delete (pipeline cleanup 동반)
POST   /{id}/promote              Sprint 23 D4 + Sprint 24 BL-064: team workspace 복제 (I-18, 202)
                                  - 응답: new_note_id / audit_id / status / embedding_status (snake_case 보존)
                                  - chunk N>0 → 기존 BG EmbeddingChunk 복제 (Sprint 23)
                                  - chunk 0 + plain_text → BG embed_note_async 재생성 (Sprint 24 BL-064)
                                  - plain_text 부재 → 400 (Sprint 23 6차 P2 회귀 가드)
GET    /{id}/embedding-status     Sprint 24 BL-064: embedding 진행 상태 polling (NEW)
                                  - RBAC: viewer 이상 (read-only)
                                  - 응답: status (pending/processing/completed/failed/n/a) + chunkCount
```

### Tenant boundary (Sprint 19 PR #1, Codex F-1/F-2/F-4/F-6 반영)

- 인증/인가: `require_member` (POST/PATCH/DELETE) / `require_viewer` (GET) 통과
- service / repository: 모든 호출 시 path `workspace_id` 필수 (헌법 I-9)
  - `service.get_note(note_id, workspace_id)`
  - `service.update_note(note_id, workspace_id, title=, content=, project_id=)`
  - `service.export_note(note_id, workspace_id, fmt)`
  - `service.delete_note(note_id, workspace_id)` (현재 router 경로는 pipeline 직접 호출)
  - `repository.find_by_id(note_id, workspace_id)`
- pipeline (옵션 A, Codex H2 — pipeline 우회 IDOR 차단):
  - `pipeline.embed_note_async(note_id, workspace_id)`
  - `pipeline.delete_note_with_cleanup(note_id, workspace_id)`
  - router `BackgroundTasks.add_task` 에서 path `workspace_id` 동반 전달
- secondary FK (Codex F-2 Critical):
  - `create_note` / `update_note` 의 `project_id` 가 같은 workspace 내인지 `ProjectRepository.find_by_id` + `project.workspace_id == workspace_id` 검증
  - 다른 workspace project_id 거부 → 404 (`ProjectNotFoundError`)
- cross-tenant 응답:
  - path workspace 안에 없는 `note_id` → 404 (`NoteNotFoundError`)
  - cross-workspace `project_id` → 404 (`ProjectNotFoundError`)
- 회귀 가드: `backend/tests/integration/test_workspace_idor_matrix.py::TestNotesIDORMatrix` 7 케이스 + `tests/notes/test_notes_api.py` + `tests/notes/test_export.py`

---

## 8. 엣지 케이스

- Tiptap content 가 빈 `{}` → plain_text 빈 문자열 → embedding skip (embed_note_async 가 plain_text 없으면 return)
- update 시 project_id sentinel `...` → 필드 안 건드림 (router L98 sentinel 처리)
- delete 시 embedding chunk 없음 → cleanup no-op (delete_by_source 가 0 rows affected)
