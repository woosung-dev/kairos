# Kairos REST API 명세

> ⚠️ **2026-08-13 동결 (ADR-027)** — 이 수기 명세는 `contracts/openapi/v1/openapi.json`
> (코드 생성물, CI `contract-check` drift 게이트)로 대체되었다. **갱신 금지**, 참조용으로만 유지.
> 최신 계약 = `just contracts` 재생성 또는 dev 서버 `/api/v1/docs`.

> **버전:** v1 (0.1.0)
> **Base URL:** `https://<host>/api/v1`
> **인증:** Clerk JWT Bearer Token
> **작성일:** 2026-04-01

---

## 공통 규칙

### 인증

모든 엔드포인트(Health Check, Clerk Webhook 제외)에 Clerk JWT 인증이 필요하다.

```
Authorization: Bearer <clerk_jwt_token>
```

인증 실패 시:

```json
{ "detail": "인증이 필요합니다" }
```

### 에러 응답 형식

FastAPI 표준 `HTTPException`을 사용한다. `ApiResponse<T>` 래퍼를 사용하지 않는다.

```json
{
  "detail": "에러 메시지"
}
```

| HTTP 상태 코드 | 의미 |
|:-:|------|
| 400 | 잘못된 요청 (유효성 검증 실패) |
| 401 | 인증 필요 |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 409 | 충돌 (중복 등) |
| 422 | 요청 바디 유효성 검증 실패 (FastAPI 기본) |
| 500 | 서버 내부 오류 |

### 페이지네이션

목록 조회 엔드포인트는 오프셋 기반 페이지네이션을 사용한다.

**Query Parameters:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|:------:|------|
| `page` | int | 1 | 페이지 번호 (1부터 시작) |
| `pageSize` | int | 20 | 페이지당 항목 수 |

**Response:**

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "pageSize": 20,
  "hasNext": true
}
```

### 날짜/시간 형식

- 모든 날짜/시간은 **ISO 8601** 형식 (`2026-04-01T10:00:00Z`)
- 날짜만 필요한 경우 `YYYY-MM-DD` (`2026-04-10`)
- 서버 응답의 `createdAt`, `updatedAt`은 UTC 기준

---

## 엔드포인트 전체 목록

| # | Sprint | Method | Path | 설명 |
|:-:|:------:|--------|------|------|
| 1 | 1 | `GET` | `/api/v1/health` | 헬스체크 |
| 2 | 1 | `GET` | `/api/v1/users/me` | 현재 사용자 정보 (Clerk JWT) |
| ~~3~~ | ~~1~~ | ~~`POST`~~ | ~~`/api/v1/users/sync`~~ | ~~Clerk webhook 사용자 동기화~~ — Sprint 25 T-SEC-1로 제거 (BUG-SENTINEL-005) |
| 4 | 1 | `POST` | `/api/v1/workspaces` | 워크스페이스 생성 |
| 5 | 1 | `GET` | `/api/v1/workspaces` | 내 워크스페이스 목록 |
| 6 | 1 | `GET` | `/api/v1/workspaces/{id}` | 워크스페이스 상세 |
| 7 | 1 | `POST` | `/api/v1/workspaces/{id}/members` | 멤버 추가 |
| 8 | 1 | `POST` | `/api/v1/upload/presigned-url` | R2 프리사인드 URL 발급 |
| 9 | 1 | `POST` | `/api/v1/workspaces/{wid}/meetings` | 회의 생성 + 파이프라인 트리거 |
| 10 | 1 | `GET` | `/api/v1/workspaces/{wid}/meetings` | 회의 목록 |
| 11 | 1 | `GET` | `/api/v1/workspaces/{wid}/meetings/{id}` | 회의 상세 (요약+트랜스크립트+프로젝트) |
| 12 | 1 | `GET` | `/api/v1/workspaces/{wid}/meetings/{id}/status` | 처리 상태 폴링 |
| 13 | 2 | `GET` | `/api/v1/workspaces/{wid}/inbox` | Inbox 목록 |
| 14 | 2 | `POST` | `/api/v1/workspaces/{wid}/inbox/{id}/classify` | 프로젝트 연결 확정 (N:M) |
| 15 | 2 | `POST` | `/api/v1/workspaces/{wid}/inbox/{id}/dismiss` | Inbox 무시 |
| 16 | 2 | `GET` | `/api/v1/workspaces/{wid}/projects` | 프로젝트 목록 (태그/상태 필터) |
| 17 | 2 | `GET` | `/api/v1/workspaces/{wid}/projects/{id}` | 프로젝트 상세 |
| 18 | 2 | `POST` | `/api/v1/workspaces/{wid}/projects` | 프로젝트 생성 |
| 19 | 2 | `PATCH` | `/api/v1/workspaces/{wid}/projects/{id}` | 프로젝트 수정 |
| 20 | 2 | `DELETE` | `/api/v1/workspaces/{wid}/projects/{id}` | 프로젝트 삭제 |
| 21 | 2 | `POST` | `/api/v1/workspaces/{wid}/projects/{id}/archive` | Archive 전환 |
| 22 | 2 | `GET` | `/api/v1/workspaces/{wid}/action-items` | 액션 목록 |
| 23 | 2 | `POST` | `/api/v1/workspaces/{wid}/action-items` | 액션 생성 |
| 24 | 2 | `PATCH` | `/api/v1/workspaces/{wid}/action-items/{id}` | 액션 수정 |
| 25 | 2 | `POST` | `/api/v1/workspaces/{wid}/meetings/{mid}/projects` | 회의-프로젝트 연결 |
| 26 | 2 | `DELETE` | `/api/v1/workspaces/{wid}/meetings/{mid}/projects/{pid}` | 회의-프로젝트 연결 해제 |
| 27 | 3 | `POST` | `/api/v1/workspaces/{wid}/rag/ask` | RAG 질문 (SSE 스트리밍) |
| 28 | 3 | `GET` | `/api/v1/workspaces/{wid}/projects/{pid}/notes` | 노트 목록 |
| 29 | 3 | `POST` | `/api/v1/workspaces/{wid}/projects/{pid}/notes` | 노트 생성 |
| 30 | 3 | `PATCH` | `/api/v1/workspaces/{wid}/notes/{id}` | 노트 수정 (자동저장) |
| 31 | 3 | `DELETE` | `/api/v1/workspaces/{wid}/notes/{id}` | 노트 삭제 — require_member + **BL-NOTE-DELETE-POLICY-1 (2026-08-02)**: 작성자 본인 또는 admin/owner 만. 비-작성자 member → **403**, project visibility 불가·cross-tenant → 404 (게이트 순서: visibility 먼저) |
| 32 | 4 | `PATCH` | `/api/v1/workspaces/{id}/members/{uid}/role` | 역할 변경 |
| 33 | 4 | `DELETE` | `/api/v1/workspaces/{id}/members/{uid}` | 멤버 제거 |
| 34 | 4 | `POST` | `/api/v1/workspaces/{id}/invite` | 초대 링크 생성 (Sprint 6: `defaultProjectVisibility` 필드 추가) |
| 35 | 6 | `GET` | `/api/v1/workspaces/{wid}/projects/{pid}/members` | 프로젝트 멤버 목록 (viewer+) |
| 36 | 6 | `POST` | `/api/v1/workspaces/{wid}/projects/{pid}/members` | 프로젝트 멤버 추가 (admin+). 403 — cross-workspace 차단 (추가 대상 user가 해당 워크스페이스 멤버가 아님, Sprint 7 AD-33) |
| 37 | 6 | `DELETE` | `/api/v1/workspaces/{wid}/projects/{pid}/members/{uid}` | 프로젝트 멤버 제거 (admin+) |
| 38 | 15 | `POST` | `/api/v1/workspaces/{wid}/memory` | 메모 capture (text Form 또는 audio multipart, 202 + BG task) — require_member |
| 39 | 15 | `GET` | `/api/v1/workspaces/{wid}/memory/recall?q=...` | Recall (vector + keyword fallback Top 3) — require_viewer |
| 40 | 15 | `GET` | `/api/v1/workspaces/{wid}/memory/metrics` | R7 metrics (capture/recall/promote count + recall p50/p95) — require_viewer |
| 41 | 15 | `GET` | `/api/v1/workspaces/{wid}/memory/{memory_id}` | 단일 메모 polling (status + distilled_json) — require_viewer |
| 42 | 15 | `POST` | `/api/v1/workspaces/{wid}/memory/{memory_id}/promote` | 메모 → team workspace 복제 (I-18 복제+tombstone, 202 + BG) — require_member |
| 43 | 15 | `POST` | `/api/v1/admin/memory/r2-cleanup` | 30일 경과 voice R2 객체 cleanup (X-Cron-Token header, GCP Cloud Scheduler 호출) |
| 44 | 23 | `POST` | `/api/v1/workspaces/{wid}/meetings/{mid}/promote` | 회의 → team workspace 복제 (Meeting/Summary/Segments + **ActionItem 자동 복제 (Sprint 24 BL-063, assignee_id target ws 비멤버는 None reset, composite FK remap)** + EmbeddingChunk BG 복제, I-18, 202) — require_member. 응답 `actionItemCount` = 실 복제된 row count (Sprint 23 의 0 reset 보강). |
| 45 | 23 | `POST` | `/api/v1/workspaces/{wid}/notes/{nid}/promote` | 노트 → team workspace 복제 (Note + EmbeddingChunk BG 복제, project_id=None 복제본, I-18, 202) — require_member. **Sprint 24 BL-064**: 응답에 `embedding_status` 필드 추가 (snake_case 보존, pending/processing/completed/failed/n/a). chunk 0 + plain_text → 400 대신 BG re-embedding schedule (audit lifecycle pending→processing→completed/failed). plain_text 부재 → 400 회귀 가드. |
| 45b | 24 | `GET` | `/api/v1/workspaces/{wid}/notes/{nid}/embedding-status` | **Sprint 24 BL-064 (NEW)**: target note 의 embedding 진행 상태 polling — require_viewer. 응답 `{status, chunkCount}` (status = audit raw value, chunkCount = 실 EmbeddingChunk 개수). FE ItemPromoteModal 가 chunk 0 분기 BG 완료 polling. |
| 46 | 23 | `POST` | `/api/v1/workspaces/{wid}/inbox/{iid}/promote` | Inbox 아이템 → team workspace 복제 (InboxItem 복제, ai_suggested_project_id=None + is_processed=False reset, BG embedding 없음 — audit.embedding_status='n/a', I-18, 202) — require_member |
| 47 | 23 | `POST` | `/api/v1/workspaces/{wid}/action-items/{aid}/promote` | 액션 아이템 → team workspace 복제 (ActionItem 복제, meeting_id/project_id/assignee_id=None reset, BG embedding 없음 — audit.embedding_status='n/a', I-18, 202) — require_member |
| 48 | 5 | `GET` | `/api/v1/workspaces/{wid}/meetings/{mid}/export` | 회의 내보내기 — `?format=md\|json` (기본 md) — require_viewer. `Content-Disposition: attachment` (UTF-8 filename). MD/JSON 구현, PDF 미구현 (ADR-006 §5, Phase 4+ 이연). adr006-remaining (2026-04-05). |
| 49 | 5 | `GET` | `/api/v1/workspaces/{wid}/notes/{nid}/export` | 노트 내보내기 — `?format=md\|json` (기본 md) — require_viewer. `Content-Disposition: attachment`. adr006-remaining. |
| 50 | 5 | `PATCH` | `/api/v1/workspaces/{wid}/settings` | 워크스페이스 설정 변경 — `inbox_threshold` (0.5~1.0, Inbox 자동확정 임계값) — require_owner. adr006-remaining. |

> **Sprint 15 변경 (Memory 모듈 신설)** — ADR-016 Personal↔Team IA + Recall-first wedge:
> - 38~43: 신규 6 endpoint (memory 도메인). 38/39/40/41/42는 `/api/v1/workspaces/{ws_id}/memory*` 패턴 (I-13 정합). 43은 admin 예외.
> - workspace.type 신설: `personal` (1인 격리, I-19) / `team`. 38/42 RBAC = require_member (write), 39/40/41 = require_viewer (read).
> - 42 promote: I-18 강제 (복제 + tombstone). target=personal/존재X/non-member 시 422 / 404. PromotionAudit row 생성.
> - 43 admin: `X-Cron-Token` header gate (hmac.compare_digest, Codex P1 fix #2 + Review C3 timing-safe).
> - capture 입력 제약: `text` max_length=10000 (TextTooLongError) + text/audio 둘 다 보내면 422 (BothInputsProvidedError, Review C2/C3).
> - Personal workspace는 초대/멤버 추가 차단 (PersonalWorkspaceProtected 403, Review C1 I-19 가드).

> **Sprint 6 변경 (visibility + ProjectMember)**:
> - 16/17/18/19: Project 응답에 `visibility` 필드 추가 (`public` | `draft` | `private`).
> - 18 POST: `visibility` (optional, default `public`) 필드 수신.
> - 19 PATCH: `visibility` 변경은 admin 이상만 (BE-T15, 403 응답). 일반 update는 require_member.
> - 16 GET 목록 + 17 GET 상세: visibility 필터링 적용 (admin 우회 / member 본인 작성 draft / private은 ProjectMember 매핑된 사용자만 노출).
> - 27 RAG: visibility 검증을 SSE 스트리밍 시작 *전*에 수행 (ADR-014 옵션 A, RagPipelineService).
> - 35/36/37: ProjectMember CRUD endpoint (Sprint 6 BE-T7).
> - 34 POST invite: `defaultProjectVisibility` 필드 추가 (Sprint 6 L-8, default `public`).

---

## Sprint 1 상세

### Health

#### `GET /api/v1/health`

헬스체크. 인증 불필요.

**Response:**

```
200 OK
```

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

### Auth

#### `GET /api/v1/users/me`

현재 인증된 사용자 정보를 반환한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |

**Response:**

```
200 OK
```

```json
{
  "id": "uuid",
  "clerkId": "clerk_xxx",
  "displayName": "당근",
  "email": "user@example.com",
  "avatarUrl": "https://..." | null
}
```

**에러:**

| 상태 | 응답 |
|:----:|------|
| 401 | `{ "detail": "인증이 필요합니다" }` |

---

#### ~~`POST /api/v1/users/sync`~~ — Sprint 25 T-SEC-1로 제거 (ADR-022)

**삭제됨** (Sprint 25, BUG-SENTINEL-005, ADR-022). 2026-05-21 사용자 결정으로
Clerk Production 인스턴스 미발급 + Clerk webhook SKIP lock-in
(memory `project_gcp_migration_jetaime_dev_done.md`, ADR-022 archeology).
이전 핸들러는 인증/Svix 서명 검증 부재로 임의 user row 생성·덮어쓰기
가능 PoC 실측 (Multi-Agent QA 2026-05-21 Sentinel P0). 현재 POST
요청 시 404/405 반환. GA launch 시 Svix 검증 추가 + 재도입은 별도
sprint. 회귀 가드: `apps/api/tests/auth/test_auth_sync_disabled.py`.

---

### Workspaces

#### `POST /api/v1/workspaces`

워크스페이스를 생성한다. 생성자가 자동으로 owner가 된다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Body | `{ "name": "우리팀" }` |

**Response:**

```
201 Created
```

```json
{
  "id": "uuid",
  "name": "우리팀",
  "ownerId": "uuid",
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601"
}
```

---

#### `GET /api/v1/workspaces`

현재 사용자가 속한 워크스페이스 목록을 반환한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |

**Response:**

```
200 OK
```

```json
[Workspace, ...]
```

---

#### `GET /api/v1/workspaces/{id}`

워크스페이스 상세 정보를 반환한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `id` — 워크스페이스 UUID |

**Response:**

```
200 OK
```

```json
{
  "id": "uuid",
  "name": "우리팀",
  "ownerId": "uuid",
  "memberCount": 5,
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601"
}
```

**에러:**

| 상태 | 응답 |
|:----:|------|
| 404 | `{ "detail": "워크스페이스를 찾을 수 없습니다" }` |

---

#### `POST /api/v1/workspaces/{id}/members`

워크스페이스에 멤버를 추가한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `id` — 워크스페이스 UUID |
| Body | `{ "email": "new@example.com" }` |

**Response:**

```
201 Created
```

```json
{
  "id": "uuid",
  "userId": "uuid",
  "role": "member"
}
```

**에러:**

| 상태 | 응답 |
|:----:|------|
| 404 | `{ "detail": "해당 이메일의 사용자를 찾을 수 없습니다" }` |
| 409 | `{ "detail": "이미 멤버입니다" }` |

---

### Storage

> **Validation (Sprint 25 T-SEC-3, BUG-SENTINEL-003)**: `POST .../upload/file`
> 프록시 업로드 endpoint 에 4계층 검증 적용 — size (env `MAX_UPLOAD_BYTES`,
> 기본 500MB) / MIME 화이트리스트 (env `ALLOWED_UPLOAD_MIMES`, audio/* +
> application/pdf + text/*) / 확장자 정합 / content signature sniff. 위반 시
> 400/413/415 응답. 회귀 가드: `apps/api/tests/upload/test_upload_validation.py`.

#### `POST /api/v1/upload/presigned-url`

Cloudflare R2 프리사인드 업로드 URL을 발급한다. 클라이언트는 이 URL로 직접 파일을 업로드한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Body | `{ "filename": "meeting.mp3", "contentType": "audio/mpeg" }` |

**Response:**

```
200 OK
```

```json
{
  "uploadUrl": "https://r2.../presigned",
  "fileKey": "uploads/uuid/meeting.mp3",
  "expiresIn": 3600
}
```

---

### Meetings

> **Tenant boundary (Sprint 19 PR #1, Codex F-1/F-4/F-6 반영)**: 모든 endpoint 는 `require_member` (POST) / `require_viewer` (GET) 통과. service / repository / pipeline 모든 호출이 path `workspace_id` 동반. cross-tenant `meeting_id` 시도 → 404 (NotFound). pipeline 진입점 (`process_meeting`, `capture_text`) + 내부 mutation (`update_status` / `set_has_*` / `save_*`) 시그니처 모두 workspace_id 필수. secondary FK 없음 (meeting 자체는 workspace 직접 FK). 회귀 가드: `apps/api/tests/integration/test_workspace_idor_matrix.py::TestMeetingsIDORMatrix`.

#### `POST /api/v1/workspaces/{wid}/meetings`

회의를 생성하고 AI 처리 파이프라인을 트리거한다. 비동기 처리이므로 `202 Accepted`를 반환한다.

내부적으로 `BackgroundTasks`를 통해 `MeetingPipelineService.process_meeting()`을 실행한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID |
| Body | 아래 참조 |

```json
{
  "title": "3월 킥오프",
  "fileKey": "uploads/uuid/meeting.mp3",
  "recordedAt": "2026-03-20T10:00:00Z" | null
}
```

**Response:**

```
202 Accepted
```

```json
{
  "id": "uuid",
  "status": "uploading",
  "message": "파이프라인이 시작되었습니다"
}
```

---

#### `GET /api/v1/workspaces/{wid}/meetings`

워크스페이스의 회의 목록을 반환한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID |
| Query | `page` (기본 1), `pageSize` (기본 20) |

**Response:**

```
200 OK
```

```json
{
  "items": [Meeting, ...],
  "total": 42,
  "page": 1,
  "pageSize": 20,
  "hasNext": true
}
```

---

#### `GET /api/v1/workspaces/{wid}/meetings/{id}`

회의 상세 정보를 반환한다. 요약, 트랜스크립트, 연결된 프로젝트을 포함한다.

Meeting과 Project은 N:M 관계이며 `MeetingProjectLink` 중간 테이블을 통해 연결된다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID, `id` — 회의 UUID |

**Response:**

```
200 OK
```

```json
{
  "id": "uuid",
  "workspaceId": "uuid",
  "title": "3월 킥오프",
  "recordedAt": "ISO8601",
  "durationSec": 3600,
  "status": "completed",
  "hasTranscript": true,
  "hasSummary": true,
  "actionItemCount": 5,
  "createdBy": {
    "id": "uuid",
    "displayName": "당근",
    "avatarUrl": null
  },
  "transcript": [
    {
      "speaker": "당근",
      "startSec": 0.0,
      "endSec": 15.5,
      "text": "..."
    }
  ],
  "summary": {
    "summary": "3~5줄 핵심 요약",
    "keyDecisions": ["CMS 3월 내 완료"],
    "topics": ["CMS", "보안"]
  },
  "projects": [
    {
      "id": "uuid",
      "title": "CMS 고도화"
    }
  ],
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601"
}
```

**에러:**

| 상태 | 응답 |
|:----:|------|
| 404 | `{ "detail": "회의를 찾을 수 없습니다" }` |

---

#### `GET /api/v1/workspaces/{wid}/meetings/{id}/status`

회의 AI 처리 파이프라인의 현재 상태를 폴링한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID, `id` — 회의 UUID |

**Response:**

```
200 OK
```

```json
{
  "status": "transcribing",
  "errorMessage": null
}
```

`status` 값: `uploading` | `transcribing` | `analyzing` | `embedding` | `completed` | `failed`

실패 시:

```json
{
  "status": "failed",
  "errorMessage": "STT 처리 실패"
}
```

---

## Sprint 2 상세

### Inbox

> **Tenant boundary (Sprint 19 PR #1, Codex F-1/F-2/F-4/F-6 반영)**: `require_member` (POST classify/dismiss) / `require_viewer` (GET) 통과. service / repository 호출에 path `workspace_id` 필수 (`classify(inbox_id, workspace_id, project_ids)` / `dismiss(inbox_id, workspace_id)` / `find_by_id(inbox_id, workspace_id)`). secondary FK 검증 (Codex F-2 Critical): classify 의 `project_ids` 모두 같은 workspace 내인지 검증 후 거부 시 404 (`ProjectNotFoundError`). cross-tenant `inbox_id` / `project_id` 시도 → 404. 회귀 가드: `apps/api/tests/integration/test_workspace_idor_matrix.py::TestInboxIDORMatrix` 4 케이스.

#### `GET /api/v1/workspaces/{wid}/inbox`

Inbox 아이템 목록을 반환한다. AI가 자동 생성한 미분류 항목을 확인할 수 있다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID |
| Query | `isProcessed` (boolean, 기본 false), `page` (기본 1), `pageSize` (기본 20) |

**Response:**

```
200 OK
```

```json
{
  "items": [
    {
      "id": "uuid",
      "workspaceId": "uuid",
      "title": "3월 킥오프 회의 요약",
      "summary": "CMS 고도화 관련 킥오프...",
      "sourceType": "meeting",
      "sourceId": "uuid",
      "aiSuggestedProjectId": "uuid" | null,
      "aiSuggestedProjectTitle": "CMS 고도화",
      "aiSuggestedTags": ["CMS", "개발"],
      "aiConfidence": 0.87,
      "isProcessed": false,
      "createdAt": "ISO8601",
      "updatedAt": "ISO8601"
    }
  ],
  "total": 5,
  "page": 1,
  "pageSize": 20,
  "hasNext": false
}
```

---

#### `POST /api/v1/workspaces/{wid}/inbox/{id}/classify`

Inbox 아이템을 프로젝트에 분류 확정한다. N:M 관계로 여러 프로젝트에 동시에 연결할 수 있다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID, `id` — Inbox 아이템 UUID |
| Body | `{ "projectIds": ["uuid-1", "uuid-2"] }` |

**Response:**

```
200 OK
```

```json
{
  "id": "uuid",
  "isProcessed": true,
  "linkedProjects": [
    { "id": "uuid-1", "title": "CMS 고도화" },
    { "id": "uuid-2", "title": "보안 관리" }
  ]
}
```

**에러:**

| 상태 | 응답 |
|:----:|------|
| 404 | `{ "detail": "Inbox 아이템을 찾을 수 없습니다" }` |

---

#### `POST /api/v1/workspaces/{wid}/inbox/{id}/dismiss`

Inbox 아이템을 무시(dismiss) 처리한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID, `id` — Inbox 아이템 UUID |

**Response:**

```
200 OK
```

```json
{
  "id": "uuid",
  "isProcessed": true
}
```

---

#### `POST /api/v1/workspaces/{wid}/inbox/{id}/promote`

> **Sprint 23 D4 (Task 2 Step 2.4)** — 헌법 I-18 (Promotion = 복제 + tombstone, 이동 금지) 강제.

Inbox 아이템을 team workspace 로 복제한다. 원본 InboxItem 은 source workspace 에 보존되고, target workspace 에 새 InboxItem 복제본 + `ItemPromotionAudit(item_type='inbox')` row 가 생성된다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — source 워크스페이스 UUID, `id` — Inbox 아이템 UUID |
| Body | `{ "targetWorkspaceId": "uuid" }` |
| RBAC | `require_member` (source ws) + promoter 가 target ws 멤버 |

**Response:**

```
202 Accepted
```

```json
{
  "new_inbox_id": "uuid",
  "audit_id": "uuid",
  "status": "completed"
}
```

**복제 정책:**

- `title`, `summary`, `source_type`, `source_id`, `ai_suggested_project_title`, `ai_suggested_tags`, `ai_confidence` 는 그대로 복제.
- `ai_suggested_project_id`=None reset (composite FK `fk_inbox_suggested_project_workspace` 가 (workspace_id, ai_suggested_project_id) 정합 강제 — target ws 와 무관).
- `is_processed`=False reset (복제본은 target ws 사용자 재분류 대기).
- `source_id` 는 soft reference (FK 미강제) — cross-workspace transitive 참조 그대로 보존.
- BG embedding 복제 없음 (InboxItem 은 source_type='inbox' EmbeddingChunk 가 실제 인서트되지 않음 — `_ALLOWED_SOURCE_TYPES` whitelist 만 존재). audit.embedding_status='n/a' + 응답 status='completed' (notes/meetings 의 'embedding_pending' 과 차이).

**에러:**

| 상태 | 사유 | 응답 |
|:----:|------|------|
| 400 | source == target | `같은 워크스페이스로는 promote 할 수 없습니다` |
| 400 | target.type='personal' | `개인 워크스페이스로는 promote 할 수 없습니다` |
| 403 | target ws 미존재 또는 promoter 가 target ws 멤버 아님 | `대상 워크스페이스가 유효하지 않습니다` |
| 404 | source inbox_id 미존재 | `Inbox 아이템을 찾을 수 없습니다` |

---

### Projects

#### `GET /api/v1/workspaces/{wid}/projects`

프로젝트 목록을 반환한다. 태그, 상태로 필터링할 수 있다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID |
| Query | `tag` (string), `status` (active\|completed\|archived), `page` (기본 1), `pageSize` (기본 50) |

**Response:**

```
200 OK
```

```json
{
  "items": [
    {
      "id": "uuid",
      "workspaceId": "uuid",
      "title": "CMS 고도화",
      "description": "3월 내 완료 목표",
      "status": "active",
      "tags": ["CMS", "개발"],
      "sortOrder": 0,
      "createdBy": {
        "id": "uuid",
        "displayName": "당근",
        "avatarUrl": null
      },
      "contentCount": 3,
      "meetingCount": 2,
      "actionItemCount": 5,
      "createdAt": "ISO8601",
      "updatedAt": "ISO8601"
    }
  ],
  "total": 8,
  "page": 1,
  "pageSize": 50,
  "hasNext": false
}
```

---

#### `GET /api/v1/workspaces/{wid}/projects/{id}`

프로젝트 상세 정보를 반환한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID, `id` — 프로젝트 UUID |

**Response:**

```
200 OK
```

```json
Project
```

**에러:**

| 상태 | 응답 |
|:----:|------|
| 404 | `{ "detail": "프로젝트을 찾을 수 없습니다" }` |
| 404 | workspace mismatch — 해당 프로젝트가 path workspace_id에 속하지 않음 (BE-T12) |

---

#### `POST /api/v1/workspaces/{wid}/projects`

프로젝트을 생성한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID |
| Body | 아래 참조 |

```json
{
  "title": "CMS 고도화",
  "description": "3월 내 완료 목표" | null
}
```

**Response:**

```
201 Created
```

```json
Project
```

---

#### `PATCH /api/v1/workspaces/{wid}/projects/{id}`

프로젝트을 수정한다. 모든 필드는 optional이다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID, `id` — 프로젝트 UUID |
| Body | 아래 참조 |

```json
{
  "title": "수정된 제목",
  "description": "변경된 설명",
  "status": "completed"
}
```

**Response:**

```
200 OK
```

```json
Project
```

---

#### `DELETE /api/v1/workspaces/{wid}/projects/{id}`

프로젝트을 삭제한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID, `id` — 프로젝트 UUID |

**Response:**

```
204 No Content
```

---

#### `POST /api/v1/workspaces/{wid}/projects/{id}/archive`

프로젝트을 Archive로 전환한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID, `id` — 프로젝트 UUID |

**Response:**

```
200 OK
```

```json
{
  "id": "uuid",
  "status": "archived"
}
```

---

### Meeting-Project Link

#### `POST /api/v1/workspaces/{wid}/meetings/{mid}/projects`

회의에 프로젝트를 연결한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID, `mid` — 회의 UUID |
| Body | `{ "projectId": "uuid" }` |

**Response:**

```
201 Created
```

```json
{
  "meetingId": "uuid",
  "projectId": "uuid"
}
```

**에러:**

| 상태 | 응답 |
|:----:|------|
| 404 | `{ "detail": "회의 또는 프로젝트를 찾을 수 없습니다" }` |
| 409 | `{ "detail": "이미 연결되어 있습니다" }` |

---

#### `DELETE /api/v1/workspaces/{wid}/meetings/{mid}/projects/{pid}`

회의-프로젝트 연결을 해제한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID, `mid` — 회의 UUID, `pid` — 프로젝트 UUID |

**Response:**

```
204 No Content
```

**에러:**

| 상태 | 응답 |
|:----:|------|
| 404 | `{ "detail": "연결을 찾을 수 없습니다" }` |

---

### Action Items

> **Tenant boundary (Sprint 19 PR #1, Codex F-1/F-2/F-4/F-6 반영, 3 secondary FK 가장 큰 분량)**: `require_member` (POST/PATCH) / `require_viewer` (GET) 통과. service / repository 호출에 path `workspace_id` 필수 (`update_action_item(action_id, workspace_id, ...)` / `find_by_id(action_id, workspace_id)`). secondary FK 3건 검증 (Codex F-2 Critical): create + update 양쪽 모두 `project_id` (ProjectRepository.find_by_id + workspace_id 일치) + `meeting_id` (MeetingRepository.find_by_id(meeting_id, workspace_id)) + `assignee_id` (WorkspaceRepository.find_member(workspace_id, assignee_id)) 검증 후 거부 시 404. dependencies 에서 3 repo 동반 주입. 회귀 가드: `apps/api/tests/integration/test_workspace_idor_matrix.py::TestActionsIDORMatrix` 5 케이스.

#### `GET /api/v1/workspaces/{wid}/action-items`

액션 아이템 목록을 반환한다. 상태, 우선순위, 프로젝트으로 필터링할 수 있다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID |
| Query | `status` (todo\|in_progress\|done), `priority` (high\|medium\|low), `projectId` (UUID), `page` (기본 1), `pageSize` (기본 50) |

**Response:**

```
200 OK
```

```json
{
  "items": [
    {
      "id": "uuid",
      "meetingId": "uuid" | null,
      "projectId": "uuid" | null,
      "title": "CMS DB 스키마 설계",
      "description": "ERD 기반으로 테이블 생성",
      "assignee": {
        "id": "uuid",
        "displayName": "당근",
        "avatarUrl": null
      } | null,
      "dueDate": "2026-04-10" | null,
      "priority": "high",
      "status": "todo",
      "createdAt": "ISO8601",
      "updatedAt": "ISO8601"
    }
  ],
  "total": 12,
  "page": 1,
  "pageSize": 50,
  "hasNext": false
}
```

---

#### `POST /api/v1/workspaces/{wid}/action-items`

액션 아이템을 생성한다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID |
| Body | 아래 참조 |

```json
{
  "title": "CMS DB 스키마 설계",
  "description": "ERD 기반으로 테이블 생성" | null,
  "meetingId": "uuid" | null,
  "projectId": "uuid" | null,
  "assigneeId": "uuid" | null,
  "dueDate": "2026-04-10" | null,
  "priority": "medium"
}
```

**Response:**

```
201 Created
```

```json
ActionItem
```

---

#### `PATCH /api/v1/workspaces/{wid}/action-items/{id}`

액션 아이템을 수정한다. 모든 필드는 optional이다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — 워크스페이스 UUID, `id` — 액션 아이템 UUID |
| Body | 아래 참조 |

```json
{
  "title": "수정된 제목",
  "status": "in_progress",
  "priority": "high",
  "assigneeId": "uuid",
  "dueDate": "2026-04-15"
}
```

**Response:**

```
200 OK
```

```json
ActionItem
```

---

#### `POST /api/v1/workspaces/{wid}/action-items/{id}/promote`

> **Sprint 23 D4 (Task 2 Step 2.5)** — 헌법 I-18 (Promotion = 복제 + tombstone, 이동 금지) 강제.

액션 아이템을 team workspace 로 복제한다. 원본 ActionItem 은 source workspace 에 보존되고, target workspace 에 새 ActionItem 복제본 + `ItemPromotionAudit(item_type='action')` row 가 생성된다.

**Request:**

| 항목 | 값 |
|------|-----|
| Headers | `Authorization: Bearer <clerk_jwt>` |
| Path | `wid` — source 워크스페이스 UUID, `id` — 액션 아이템 UUID |
| Body | `{ "targetWorkspaceId": "uuid" }` |
| RBAC | `require_member` (source ws) + promoter 가 target ws 멤버 |

**Response:**

```
202 Accepted
```

```json
{
  "new_action_id": "uuid",
  "audit_id": "uuid",
  "status": "completed"
}
```

**복제 정책:**

- `title`, `description`, `priority`, `status`, `due_date` 는 그대로 복제 (history 의미 보존).
- `meeting_id`=None reset — Sprint 21 BL-050 composite FK `fk_action_items_meeting_workspace` 가 (workspace_id, meeting_id) → meetings(workspace_id, id) 정합 강제. target ws 는 source meeting 미보유.
- `project_id`=None reset — Sprint 19 PR #2 composite FK `fk_action_items_project_workspace` 가 (workspace_id, project_id) → projects(workspace_id, id) 정합 강제. target ws 는 source project 미보유 (사용자가 target ws 에서 별도 분류 권장).
- `assignee_id`=None reset — 단순화 정책. assignee 는 user FK (workspace 무관) 이지만 헌법 A-3 (assignee 는 워크스페이스 멤버만) + cross-workspace 사용자 책임 모호 → None reset. 사용자가 target ws 에서 재할당.
- BG embedding 복제 없음 (ActionItem 임베딩 ledger 부재 — actions 도메인 임베딩 미적용). audit.embedding_status='n/a' + 응답 status='completed' (inbox 와 동일, notes/meetings 의 'embedding_pending' 과 차이).
- ActionItem 모델은 created_by_id 필드 없음 → audit.promoted_by_user_id 로 promoter 추적.

**에러:**

| 상태 | 사유 | 응답 |
|:----:|------|------|
| 400 | source == target | `같은 워크스페이스로는 promote 할 수 없습니다` |
| 400 | target.type='personal' | `개인 워크스페이스로는 promote 할 수 없습니다` |
| 403 | target ws 미존재 또는 promoter 가 target ws 멤버 아님 | `대상 워크스페이스가 유효하지 않습니다` |
| 404 | source action_id 미존재 | `액션 아이템을 찾을 수 없습니다` |

---

## Sprint 3: RAG + Notes (구현 완료)

> 설계 문서: `git history`

| # | Method | Path | 설명 |
|:-:|--------|------|------|
| 27 | `POST` | `/api/v1/workspaces/{wid}/rag/ask` | RAG 질문 (SSE 스트리밍, `sse-starlette`) |
| 28 | `GET` | `/api/v1/workspaces/{wid}/notes` | 노트 목록 (`?projectId=` 필터) |
| 29 | `GET` | `/api/v1/workspaces/{wid}/notes/{id}` | 노트 상세 |
| 30 | `POST` | `/api/v1/workspaces/{wid}/notes` | 노트 생성 (`projectId` 선택적) |
| 31 | `PATCH` | `/api/v1/workspaces/{wid}/notes/{id}` | 노트 수정 (debounce 자동저장) |
| 32 | `DELETE` | `/api/v1/workspaces/{wid}/notes/{id}` | 노트 삭제 (204) |
| 45 | `POST` | `/api/v1/workspaces/{wid}/notes/{id}/promote` | Sprint 23 D4: 노트 → team workspace 복제 (I-18, 202 + BG embedding). target=personal/존재X/non-member 시 400 / 403. ItemPromotionAudit(item_type='note') row 생성. |

### RAG Ask (`POST /rag/ask`)

```
Request: { "question": str, "projectId?": UUID, "timeRange?": "1m"|"3m"|"6m", "sourceType?": "meeting"|"note" }
Response: SSE stream (event: thinking → search_results → answer → done)
```

### Notes

- `project_id` nullable (CODE 철학 마찰 최소화)
- 생성/수정 시 BackgroundTasks로 비동기 임베딩
- Tiptap JSON content + plain_text (임베딩용)

> **Tenant boundary (Sprint 19 PR #1, Codex F-1/F-2/F-4/F-6 반영)**: 모든 endpoint 가 `require_member` (POST/PATCH/DELETE) / `require_viewer` (GET) 통과. service / repository / pipeline 모든 호출이 path `workspace_id` 동반. secondary FK 검증: `create_note` / `update_note` 의 `project_id` 가 같은 workspace 내인지 `ProjectRepository.find_by_id` 검증 후 거부 시 404 (Codex F-2 Critical). pipeline 옵션 A (Codex H2): `embed_note_async(note_id, workspace_id)` / `delete_note_with_cleanup(note_id, workspace_id)` — pipeline 우회 IDOR 차단. cross-tenant `note_id` 또는 `project_id` 시도 → 404. 회귀 가드: `apps/api/tests/integration/test_workspace_idor_matrix.py::TestNotesIDORMatrix` 7 케이스. notes 도메인 CONTEXT 신설: `apps/api/src/notes/CONTEXT.md`.

---

## Sprint 4: RBAC (목록 수준)

> 상세 스키마는 Sprint 4 착수 시 확정한다.

| # | Method | Path | 설명 |
|:-:|--------|------|------|
| 32 | `PATCH` | `/api/v1/workspaces/{id}/members/{uid}/role` | 역할 변경 |
| 33 | `DELETE` | `/api/v1/workspaces/{id}/members/{uid}` | 멤버 제거 |
| 34 | `POST` | `/api/v1/workspaces/{id}/invite` | 초대 링크 생성 |

## Sprint 22 — Onboarding funnel (OBN-02)

| # | Method | Path | 설명 |
|:-:|--------|------|------|
| 35 | `GET` | `/api/v1/users/me/onboarding` | 현재 user 의 onboarding 진행도 (`{ step, totalSteps: 4, onboardedAt, isCompleted }`). step lifecycle: 가입(1) → 첫 project(2) → 첫 meeting distillation(3) → 첫 RAG ask(4). |

---

## ADR-026 — 외부 소스 ingest 레일 v0

> Drive v0는 Google Docs `text/plain` export만 지원하고 Drive → Kairos 단방향 읽기 전용이다.

| Method | Path | 권한 | 성공 | 주요 오류 / 비고 |
|--------|------|------|------|------------------|
| `POST` | `/api/v1/workspaces/{workspace_id}/integrations/google-drive/authorize` | owner | `200 OK` `{ authorizationUrl }` | `403` owner 아님, `503` Google OAuth 설정 누락 또는 암호화 키 오류. FE가 OAuth 팝업·redirect를 제어한다. 호출마다 단명 `nonce` 행을 저장하고 자기 workspace의 만료 행을 정리한다. |
| `GET` | `/api/v1/integrations/google-drive/callback` | 서명 state의 요청자(owner) | `302 Found` 설정 화면 복귀 | I-13 예외: 고정 redirect URI에는 `workspace_id`를 둘 수 없으므로 state의 workspace·요청자·nonce·PKCE·만료를 검증한다. **`nonce`는 `DELETE ... RETURNING` 단문으로 1회만 소비되며, 소비는 Google 토큰 교환보다 앞이다** — 재사용·만료 state는 외부 호출 없이 `400`으로 차단된다(성공한 callback의 브라우저 재전송도 같은 `400`). `403` 요청자가 더 이상 owner가 아님, `503` 암호화 키 설정 오류. |
| `GET` | `/api/v1/workspaces/{workspace_id}/integrations/google-drive` | owner | `200 OK` connection 상태와 마지막 동기화. 연결이 없으면 `null` | `403` owner 아님. |
| `POST` | `/api/v1/workspaces/{workspace_id}/integrations/google-drive/documents` | owner | `202 Accepted` `{ syncRunId }` | 선택 file IDs와 `projectId`를 받아 BackgroundTask import 시작. `404` 연결 또는 같은 workspace의 Project 없음, `403` owner 아님, `503` Google OAuth 설정 누락. 지원하지 않는 MIME은 pipeline이 문서별 `failed`로 기록한다. |
| `GET` | `/api/v1/workspaces/{workspace_id}/integrations/sync-runs/{sync_run_id}` | owner | `200 OK` 파일별 status polling | `403` owner 아님, `404` 같은 workspace의 sync run 없음. |
| `POST` | `/api/v1/workspaces/{workspace_id}/integrations/google-drive/documents/{document_id}/sync` | owner | `202 Accepted` | 단일 문서 수동 재동기화. `403` owner 아님, `404` 같은 workspace의 문서 없음, `503` Google OAuth 설정 누락. |
| `DELETE` | `/api/v1/workspaces/{workspace_id}/integrations/google-drive/documents/{document_id}` | owner | `204 No Content` | RAG 발행 취소와 파생 데이터 cleanup. `403` owner 아님, `404` 같은 workspace의 문서 없음, `503` Google OAuth 설정 누락. |
| `GET` | `/api/v1/workspaces/{workspace_id}/external-documents/{document_id}` | 접근 가능한 멤버 | `200 OK` Source Viewer full content | 기존 Project visibility 규칙을 따른다. 접근 불가는 존재성 누출 방지를 위해 `404`, 같은 workspace의 문서 없음도 `404`. |
