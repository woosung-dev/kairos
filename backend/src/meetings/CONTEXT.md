<!-- meetings 도메인 — STT + 화자 분리 + AI 요약 + 액션 추출 파이프라인 -->

# meetings CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- 회의 음성 인제스트 (R2 업로드 후 처리 트리거)
- STT + 화자 분리 (Whisper API + pyannote)
- AI 요약 / 결정사항 추출 (Gemini)
- 액션 아이템 추출 → `actions/repository`에 저장
- 프로젝트 자동 분류 추천 → `inbox/service`에 위임 (orchestrator 안)
- 회의 데이터 임베딩 트리거 → `embeddings/service`에 위임

## 2. 비책임

- 액션 CRUD 자체 (`actions` 도메인)
- 임베딩 저장/검색 (`embeddings`/`rag`)
- Inbox 자동 확정 로직 (`inbox`)

---

## 3. 엔티티 (소유)

- **Meeting** — 회의 메타 + status
  - status: `uploading` → `transcribing` → `analyzing` → `completed` / `failed`
  - `file_key` (R2 저장 경로), `error_message`, `has_transcript`, `has_summary`, `action_item_count`
- **TranscriptSegment** — 화자별 문장
  - `speaker` 기본값 `"Speaker"` (Sprint 1 화자 분리 미적용)
- **MeetingSummary** — 1:1 AI 요약 + `key_decisions` (JSON list) + `topics` (JSON list)

> **MeetingProjectLink**는 `projects` 도메인 소유. meetings는 read만.

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 | 비고 |
|---|---|---|---|
| out | `actions/repository` | Repository | 추출된 액션 저장 |
| out | `projects/repository` | Repository (read-only) | `get_meeting_detail` projects 필드 채움 (Sprint 14 T-8 BUG-H04, MeetingProjectLink 읽기) |
| out | `workspaces/repository` | Repository (read-only) | promote target 검증 (Sprint 23 D4 — find_by_id / find_member) |
| out | `services/transcription` | external wrapper | Whisper + pyannote |
| out | `services/ai_processing` | external wrapper | Gemini 요약/분류 |
| out | `inbox/service` | via pipeline | Inbox 적재 (`MeetingPipelineService` 안) |
| out | `embeddings/service` | via pipeline | 트랜스크립트 임베딩 |
| out | `common/promote_helpers` | utility | promote target 검증 + audit row 빌더 (Sprint 23 D4 Task 2 Step 2.2) + `clone_action_items_for_promote` (Sprint 24 BL-063, ActionItem 자동 복제) |
| out | `common/promote_models` | model | ItemPromotionAudit 저장 (Sprint 23 D4 — 4 도메인 공통) |
| in | (외부 호출) | — | upload 모듈에서 트리거 |

---

## 5. 핵심 흐름 — `MeetingPipelineService`

```
1. upload 완료 → POST /api/v1/workspaces/{wid}/meetings (202 Accepted)
2. BackgroundTask: pipeline.process_meeting(id)
   ├─ status=transcribing                     (commit — 진행 보고, 줄 71)
   ├─ Whisper → TranscriptSegment[]
   ├─ duration_sec 업데이트                   (commit — 줄 86)
   ├─ status=analyzing                        (commit — 진행 보고, 줄 90)
   ├─ Gemini summarize → MeetingSummary
   ├─ Gemini extract_actions → ActionItem[]   (via actions.repository, nullable project_id OK)
   ├─ Gemini classify_project → InboxItem 적재 (via inbox.service)
   ├─ Embedding 저장                          (via embeddings.service, 실패해도 비차단)
   └─ status=completed                        (commit — 최종, 줄 215)
   (실패 시 status=failed                     commit — 줄 222)
3. Client polling: GET /api/v1/workspaces/{wid}/meetings/{id}/status
```

> **현재 commit 횟수 (D-9)**: 5회 (status 전이 4회 + duration 보고 1회). 줄번호: 71/86/90/215/222. 헌법 I-2 "마지막 1회" 원칙과 불일치 — 진행 보고용 commit으로 명시 허용 vs 단일 commit 리팩토링 결정 보류.

---

## 6. 핵심 불변식

| # | 불변식 |
|---|---|
| M-1 | **status 머신 단방향 + 멱등 status 업데이트** (재시도 시 동일 상태 OK) |
| M-2 | **commit은 status 전이마다 + duration 보고 + 최종 1회** (총 5회, 줄 71/86/90/215/222. D-9 — 진행 보고용. 단일 commit 리팩토링은 ADR 후보) |
| M-3 | **외부 API 실패 시 status=`failed`** + `error_message` 저장 + 사용자 재시도 트리거 (retry 정책 자체는 Phase B) |
| M-4 | **트랜스크립트는 검색 가능 단위(L2)로 청킹 후 임베딩** |
| M-5 | **MeetingSummary는 회의당 1개 (덮어쓰기)** — 재처리 시 기존 요약 교체 |
| M-6 | **임베딩 단계는 비차단** — 임베딩 실패해도 파이프라인은 `completed`로 종료 (트랜스크립트/요약은 보존) |
| M-7 | **헌법 I-9 (Sprint 19 PR #1, Codex F-1)** — service/repository/pipeline 진입점 + 모든 내부 호출이 `workspace_id` 필수 수신. `find_by_id` / `get_segments` / `get_summary` / `update_status` / `set_has_*` / `save_*` 모두 `(meeting_id, workspace_id, ...)` 시그니처. `BackgroundTasks.add_task` 도 path `workspace_id` 동반 전달. cross-tenant 시도 → 404 (F-4) |

---

## 7. 엔드포인트

> 모두 `/api/v1/workspaces/{workspace_id}/meetings` prefix.

```
POST   /                  인제스트 (202)
POST   /capture           텍스트 캡처 인제스트 (STT 없이 분석 진입, 202)
GET    /                  목록
GET    /{id}              디테일 (요약 + 트랜스크립트)
GET    /{id}/export       내보내기
GET    /{id}/status       진행상태 polling
POST   /{id}/promote      cross-workspace 복제 (I-18, 202 + BG embedding 복제, Sprint 23 D4)
```

### Tenant boundary (Sprint 19 PR #1, Codex F-1/F-4/F-6 반영)

- 인증/인가: 모든 endpoint 가 `require_member` (POST) 또는 `require_viewer` (GET/PATCH) 의존성 통과 — workspace 비멤버 접근 403
- service / repository: 모든 호출 시 path `workspace_id` 필수 전달 (헌법 I-9)
  - `service.get_meeting_detail(meeting_id, workspace_id)`
  - `service.export_meeting(meeting_id, workspace_id, fmt)`
  - `service.get_meeting_status(meeting_id, workspace_id)`
  - `repository.find_by_id(meeting_id, workspace_id)` / `get_segments` / `get_summary` (read)
  - `repository.update_status(meeting_id, workspace_id, status, error_message=None)` (write)
  - `repository.set_has_transcript(meeting_id, workspace_id, value)` / `set_has_summary`
  - `repository.save_segments(meeting_id, workspace_id, segments)` / `save_summary`
- Pipeline 진입점 (Codex F-1 Critical):
  - `pipeline.process_meeting(meeting_id, workspace_id)`
  - `pipeline.capture_text(meeting_id, workspace_id, transcript_text)`
  - router `BackgroundTasks.add_task` 에서 path `workspace_id` 동반 전달
- cross-tenant 응답: path workspace 안에 없는 `meeting_id` → 404 (NotFound). `require_*` 거부 → 403. (F-4 lock-in)
- secondary FK: meeting 자체는 secondary FK 없음 (workspace 직접 FK). 단 `service.export_meeting` 의 `action_repo.find_by_meeting(meeting_id)` 는 actions 도메인 workspace 격리에 의존 (Phase 5 commit C4 에서 강제)
- 회귀 가드: `backend/tests/integration/test_workspace_idor_matrix.py::TestMeetingsIDORMatrix` 6 케이스 + `tests/meetings/test_pipeline.py` 4 케이스 + `tests/meetings/test_meeting_service.py` 3 케이스

---

## 8. 엣지 케이스

- 화자 식별 실패 (단일 화자 회의) → `speaker = "Speaker"` (현재 기본값)
- 무음 구간 / 짧은 회의 (< 30초) → AI 요약 스킵 옵션 (Phase B)
- 외부 API timeout → status=`failed`, `error_message` 저장, 사용자에게 재시도 버튼
- 같은 파일 재업로드 → 중복 검출 부재 (CONTEXT-MAP §7 D-8) — R2 hash 비교 미구현

---

## 9. cross-workspace promote (Sprint 23 D4 Task 2 Step 2.2)

`POST /{meeting_id}/promote` — I-18 (복제 + tombstone, 이동 금지).

**검증 (`common/promote_helpers.validate_promote_target`)**:
- source != target → 400 `CannotPromoteToSameWorkspaceError`
- target workspace 미존재 또는 promoter 가 멤버 아님 → 403 `TargetWorkspaceInvalidError`
- target type='personal' → 400 `CannotPromoteToPersonalError`

**복제 산출물 (동일 트랜잭션)**:
- 신규 `Meeting` (target workspace_id, 새 UUID, `status=source.status`, `created_by_id=promoter`).
  - `action_item_count` 은 아래 ActionItem 자동 복제 후 실 row count 로 갱신 (Sprint 24 BL-063).
- 1:1 `MeetingSummary` 복제 (있는 경우).
- N개 `TranscriptSegment` 복제 (있는 경우).
- **N개 `ActionItem` 자동 복제 (Sprint 24 BL-063)** — `clone_action_items_for_promote` 호출.
  - composite FK remap (workspace_id + meeting_id + project_id 모두 target).
  - `assignee_id` 은 target ws `WorkspaceMember` 멤버 검증 후 부재 시 `None` reset (cross-workspace 누출 차단, 사용자 결정 게이트 #5).
  - `target_project_id=None` — cross-ws project 제약, 추후 사용자 수동 연결.
  - parent SAVEPOINT 활용 — 부분 실패 시 entire promote rollback (transactional).
- `ItemPromotionAudit` row (item_type='meeting', source_item_id / new_item_id, embedding_status='pending').

**BG embedding 복제 (`_bg_promote_embed_meeting`)**:
- source workspace 의 `EmbeddingChunk` 들을 target workspace 로 복제 (vector 그대로 — Gemini cost 절감).
- L1/L2 hierarchy 보존: `parent_chunk_id` 매핑 (old → new UUID).
- audit `embedding_status`: pending → processing → completed / failed / n/a (chunk 0개).
- 실패는 비차단 — Meeting/Summary/Segments 는 이미 INSERT 완료.

**원본 보존**: source Meeting/Summary/Segments/Chunks 모두 변경 없음.
