# Phase 0 설계: API 명세 + 백엔드 셋업 가이드

> **목적:** Sprint 1 즉시 착수를 위한 Phase 0 문서 병목 해소
> **산출물:** `docs/api/endpoints.md` + `docs/architecture/backend-scaffolding.md`
> **작성일:** 2026-04-01

---

## 설계 결정 요약

| 결정 | 선택 | 근거 |
|------|------|------|
| API 명세 범위 | 전체 목록 + Sprint 1~2 상세, 3~4 목록 수준 | ERD가 전체 Phase 설계됨. 상세도만 차등 |
| 백엔드 구조 | 도메인별 완전 분리 (Router/Service/Repository) | `backend.md` 확정 패턴 + `cross-domain-pipeline.md` |
| API 응답 형식 | FastAPI 표준 (FE 나중에 수정) | 백엔드 우선. FE mock 타입은 Sprint 진행 시 수정 |
| 인증/워크스페이스 | Sprint 1에 워크스페이스 기본 CRUD 포함, RBAC는 Sprint 4 | 모든 엔티티가 workspaceId FK 보유 |
| 에러 핸들링 | MVP 전체 롤백, 나중에 단계별 재시도 확장 | Meeting.status가 이미 단계별 상태 보유 |

---

## 1. API 엔드포인트 전체 목록

### 도메인별 요약

| 도메인 | Sprint | 엔드포인트 수 |
|--------|--------|:---:|
| Health | 1 | 1 |
| Auth | 1 | 2 |
| Workspaces | 1 (+Sprint 4) | 4 (+3) |
| Storage | 1 | 1 |
| Meetings | 1 | 4 |
| Inbox | 2 | 3 |
| PARA Items | 2 | 6 |
| Action Items | 2 | 3 |
| RAG | 3 | 1 |
| Notes | 3 | 4 |
| **합계** | | **32** |

### 전체 엔드포인트

| # | Sprint | Method | Path | 설명 |
|---|--------|--------|------|------|
| 1 | 1 | `GET` | `/api/v1/health` | 헬스체크 |
| 2 | 1 | `GET` | `/api/v1/users/me` | 현재 사용자 정보 (Clerk JWT) |
| 3 | 1 | `POST` | `/api/v1/users/sync` | Clerk webhook 사용자 동기화 |
| 4 | 1 | `POST` | `/api/v1/workspaces` | 워크스페이스 생성 |
| 5 | 1 | `GET` | `/api/v1/workspaces` | 내 워크스페이스 목록 |
| 6 | 1 | `GET` | `/api/v1/workspaces/{id}` | 워크스페이스 상세 |
| 7 | 1 | `POST` | `/api/v1/workspaces/{id}/members` | 멤버 추가 |
| 8 | 1 | `POST` | `/api/v1/upload/presigned-url` | R2 프리사인드 URL 발급 |
| 9 | 1 | `POST` | `/api/v1/workspaces/{wid}/meetings` | 회의 생성 + 파이프라인 트리거 (202) |
| 10 | 1 | `GET` | `/api/v1/workspaces/{wid}/meetings` | 회의 목록 |
| 11 | 1 | `GET` | `/api/v1/workspaces/{wid}/meetings/{id}` | 회의 상세 (요약+트랜스크립트+PARA) |
| 12 | 1 | `GET` | `/api/v1/workspaces/{wid}/meetings/{id}/status` | 처리 상태 폴링 |
| 13 | 2 | `GET` | `/api/v1/workspaces/{wid}/inbox` | Inbox 목록 |
| 14 | 2 | `POST` | `/api/v1/workspaces/{wid}/inbox/{id}/classify` | PARA 분류 확정 (N:M) |
| 15 | 2 | `POST` | `/api/v1/workspaces/{wid}/inbox/{id}/dismiss` | Inbox 무시 |
| 16 | 2 | `GET` | `/api/v1/workspaces/{wid}/para-items` | PARA 목록 (카테고리 필터) |
| 17 | 2 | `GET` | `/api/v1/workspaces/{wid}/para-items/{id}` | PARA 상세 |
| 18 | 2 | `POST` | `/api/v1/workspaces/{wid}/para-items` | PARA 생성 |
| 19 | 2 | `PATCH` | `/api/v1/workspaces/{wid}/para-items/{id}` | PARA 수정 |
| 20 | 2 | `DELETE` | `/api/v1/workspaces/{wid}/para-items/{id}` | PARA 삭제 |
| 21 | 2 | `POST` | `/api/v1/workspaces/{wid}/para-items/{id}/archive` | Archive 전환 |
| 22 | 2 | `GET` | `/api/v1/workspaces/{wid}/action-items` | 액션 목록 |
| 23 | 2 | `POST` | `/api/v1/workspaces/{wid}/action-items` | 액션 생성 |
| 24 | 2 | `PATCH` | `/api/v1/workspaces/{wid}/action-items/{id}` | 액션 수정 |
| 25 | 3 | `POST` | `/api/v1/workspaces/{wid}/rag/ask` | RAG 질문 (SSE 스트리밍) |
| 26 | 3 | `GET` | `/api/v1/workspaces/{wid}/para-items/{pid}/notes` | 노트 목록 |
| 27 | 3 | `POST` | `/api/v1/workspaces/{wid}/para-items/{pid}/notes` | 노트 생성 |
| 28 | 3 | `PATCH` | `/api/v1/workspaces/{wid}/notes/{id}` | 노트 수정 (자동저장) |
| 29 | 3 | `DELETE` | `/api/v1/workspaces/{wid}/notes/{id}` | 노트 삭제 |
| 30 | 4 | `PATCH` | `/api/v1/workspaces/{id}/members/{uid}/role` | 역할 변경 |
| 31 | 4 | `DELETE` | `/api/v1/workspaces/{id}/members/{uid}` | 멤버 제거 |
| 32 | 4 | `POST` | `/api/v1/workspaces/{id}/invite` | 초대 링크 생성 |

---

## 2. Sprint 1 상세 스키마

### Health Check

```
GET /api/v1/health
→ 200: { "status": "ok", "version": "0.1.0" }
```

### Auth

```
GET /api/v1/users/me
Headers: Authorization: Bearer <clerk_jwt>
→ 200: {
    "id": "uuid",
    "clerkId": "clerk_xxx",
    "displayName": "당근",
    "email": "user@example.com",
    "avatarUrl": "https://..." | null
  }
→ 401: { "detail": "인증이 필요합니다" }

POST /api/v1/users/sync
Headers: svix-id, svix-timestamp, svix-signature (Clerk Webhook)
Body: { Clerk Webhook Payload }
→ 200: { "synced": true }
→ 400: { "detail": "잘못된 webhook 요청" }
```

### Workspaces

```
POST /api/v1/workspaces
Body: { "name": "우리팀" }
→ 201: {
    "id": "uuid",
    "name": "우리팀",
    "ownerId": "uuid",
    "createdAt": "ISO8601",
    "updatedAt": "ISO8601"
  }

GET /api/v1/workspaces
→ 200: [Workspace, ...]

GET /api/v1/workspaces/{id}
→ 200: Workspace (+ memberCount)
→ 404: { "detail": "워크스페이스를 찾을 수 없습니다" }

POST /api/v1/workspaces/{id}/members
Body: { "email": "new@example.com" }
→ 201: { "id": "uuid", "userId": "uuid", "role": "member" }
→ 404: { "detail": "해당 이메일의 사용자를 찾을 수 없습니다" }
→ 409: { "detail": "이미 멤버입니다" }
```

### Storage

```
POST /api/v1/upload/presigned-url
Body: { "filename": "meeting.mp3", "contentType": "audio/mpeg" }
→ 200: {
    "uploadUrl": "https://r2.../presigned",
    "fileKey": "uploads/uuid/meeting.mp3",
    "expiresIn": 3600
  }
```

### Meetings

```
POST /api/v1/workspaces/{wid}/meetings
Body: {
  "title": "3월 킥오프",
  "fileKey": "uploads/uuid/meeting.mp3",
  "recordedAt": "2026-03-20T10:00:00Z" | null
}
→ 202: {
    "id": "uuid",
    "status": "uploading",
    "message": "파이프라인이 시작되었습니다"
  }
내부: BackgroundTasks → MeetingPipelineService.process_meeting()

GET /api/v1/workspaces/{wid}/meetings
Query: ?page=1&pageSize=20
→ 200: {
    "items": [Meeting, ...],
    "total": 42,
    "page": 1,
    "pageSize": 20,
    "hasNext": true
  }

GET /api/v1/workspaces/{wid}/meetings/{id}
→ 200: {
    "id": "uuid",
    "workspaceId": "uuid",
    "title": "3월 킥오프",
    "recordedAt": "ISO8601",
    "durationSec": 3600,
    "status": "completed",
    "hasTranscript": true,
    "hasSummary": true,
    "actionItemCount": 5,
    "createdBy": { "id": "uuid", "displayName": "당근", "avatarUrl": null },
    "transcript": [
      { "speaker": "당근", "startSec": 0.0, "endSec": 15.5, "text": "..." }
    ],
    "summary": {
      "summary": "3~5줄 핵심 요약",
      "keyDecisions": ["CMS 3월 내 완료"],
      "topics": ["CMS", "보안"]
    },
    "paraItems": [
      { "id": "uuid", "title": "CMS 고도화", "category": "project" }
    ],
    "createdAt": "ISO8601",
    "updatedAt": "ISO8601"
  }
→ 404: { "detail": "회의를 찾을 수 없습니다" }

GET /api/v1/workspaces/{wid}/meetings/{id}/status
→ 200: {
    "status": "transcribing",
    "errorMessage": null | "STT 처리 실패"
  }
```

---

## 3. Sprint 2 상세 스키마

### Inbox

```
GET /api/v1/workspaces/{wid}/inbox
Query: ?isProcessed=false&page=1&pageSize=20
→ 200: {
    "items": [
      {
        "id": "uuid",
        "workspaceId": "uuid",
        "title": "3월 킥오프 회의 요약",
        "summary": "CMS 고도화 관련 킥오프...",
        "sourceType": "meeting",
        "sourceId": "uuid",
        "aiSuggestedParaType": "project",
        "aiSuggestedParaId": "uuid" | null,
        "aiSuggestedParaTitle": "CMS 고도화",
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

POST /api/v1/workspaces/{wid}/inbox/{id}/classify
Body: { "paraItemIds": ["uuid-1", "uuid-2"] }
→ 200: {
    "id": "uuid",
    "isProcessed": true,
    "linkedParaItems": [
      { "id": "uuid-1", "title": "CMS 고도화", "category": "project" },
      { "id": "uuid-2", "title": "보안 관리", "category": "area" }
    ]
  }
→ 404: { "detail": "Inbox 아이템을 찾을 수 없습니다" }

POST /api/v1/workspaces/{wid}/inbox/{id}/dismiss
→ 200: { "id": "uuid", "isProcessed": true }
```

### PARA Items

```
GET /api/v1/workspaces/{wid}/para-items
Query: ?category=project&status=active&page=1&pageSize=50
→ 200: {
    "items": [
      {
        "id": "uuid",
        "workspaceId": "uuid",
        "category": "project",
        "title": "CMS 고도화",
        "description": "3월 내 완료 목표",
        "status": "active",
        "paraOrder": 0,
        "createdBy": { "id": "uuid", "displayName": "당근", "avatarUrl": null },
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

GET /api/v1/workspaces/{wid}/para-items/{id}
→ 200: ParaItem
→ 404: { "detail": "PARA 아이템을 찾을 수 없습니다" }

POST /api/v1/workspaces/{wid}/para-items
Body: {
  "category": "project",
  "title": "CMS 고도화",
  "description": "3월 내 완료 목표" | null
}
→ 201: ParaItem

PATCH /api/v1/workspaces/{wid}/para-items/{id}
Body: {
  "title": "수정된 제목",
  "description": "변경된 설명",
  "category": "area",
  "status": "completed"
}
→ 200: ParaItem
모든 필드 optional

DELETE /api/v1/workspaces/{wid}/para-items/{id}
→ 204: (No Content)

POST /api/v1/workspaces/{wid}/para-items/{id}/archive
Body: { "preserveAsResource": true }
→ 200: {
    "id": "uuid",
    "status": "archived",
    "preservedResourceCount": 3
  }
```

### Action Items

```
GET /api/v1/workspaces/{wid}/action-items
Query: ?status=todo&priority=high&paraItemId=uuid&page=1&pageSize=50
→ 200: {
    "items": [
      {
        "id": "uuid",
        "meetingId": "uuid" | null,
        "paraItemId": "uuid" | null,
        "title": "CMS DB 스키마 설계",
        "description": "ERD 기반으로 테이블 생성",
        "assignee": { "id": "uuid", "displayName": "당근", "avatarUrl": null } | null,
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

POST /api/v1/workspaces/{wid}/action-items
Body: {
  "title": "CMS DB 스키마 설계",
  "description": "ERD 기반으로 테이블 생성" | null,
  "meetingId": "uuid" | null,
  "paraItemId": "uuid" | null,
  "assigneeId": "uuid" | null,
  "dueDate": "2026-04-10" | null,
  "priority": "medium"
}
→ 201: ActionItem

PATCH /api/v1/workspaces/{wid}/action-items/{id}
Body: {
  "title": "수정된 제목",
  "status": "in_progress",
  "priority": "high",
  "assigneeId": "uuid",
  "dueDate": "2026-04-15"
}
→ 200: ActionItem
모든 필드 optional
```

---

## 4. Sprint 3~4 엔드포인트 (목록 수준)

### Sprint 3: RAG + Notes

- `POST /api/v1/workspaces/{wid}/rag/ask` — SSE 스트리밍, PARA 범위/시간/소스 필터
- `GET /api/v1/workspaces/{wid}/para-items/{pid}/notes` — 노트 목록
- `POST /api/v1/workspaces/{wid}/para-items/{pid}/notes` — 노트 생성
- `PATCH /api/v1/workspaces/{wid}/notes/{id}` — 노트 수정 (debounce 자동저장)
- `DELETE /api/v1/workspaces/{wid}/notes/{id}` — 노트 삭제

> 상세 스키마는 Sprint 3 착수 시 `docs/architecture/rag-pipeline.md` 기반으로 확정

### Sprint 4: RBAC

- `PATCH /api/v1/workspaces/{id}/members/{uid}/role` — 역할 변경
- `DELETE /api/v1/workspaces/{id}/members/{uid}` — 멤버 제거
- `POST /api/v1/workspaces/{id}/invite` — 초대 링크 생성

> 상세 스키마는 Sprint 4 착수 시 확정

---

## 5. 백엔드 프로젝트 구조

### 디렉토리 맵

```
backend/
├── pyproject.toml                  # uv 패키지 관리
├── alembic.ini
├── alembic/
│   └── versions/
├── Dockerfile
├── .env.example
└── src/
    ├── main.py                     # FastAPI 앱 엔트리포인트
    ├── core/
    │   ├── config.py               # pydantic-settings (SecretStr)
    │   └── lifespan.py             # startup/shutdown (DB 풀 등)
    ├── common/
    │   ├── database.py             # AsyncSession, get_async_session
    │   ├── exceptions.py           # 공통 예외 + 핸들러
    │   ├── pagination.py           # PaginatedResponse 유틸
    │   ├── prompts.py              # Claude 프롬프트 상수 + parse_json_response
    │   └── r2.py                   # R2 presigned URL (aioboto3)
    ├── auth/
    │   ├── router.py               # GET /users/me, POST /users/sync
    │   ├── service.py
    │   ├── dependencies.py         # get_current_user (Clerk JWT)
    │   ├── schemas.py
    │   └── exceptions.py
    ├── workspaces/
    │   ├── router.py               # CRUD + /members
    │   ├── service.py
    │   ├── repository.py
    │   ├── models.py               # Workspace, WorkspaceMember
    │   ├── schemas.py
    │   ├── dependencies.py
    │   └── exceptions.py
    ├── meetings/
    │   ├── router.py               # CRUD + /status
    │   ├── service.py              # 단일 도메인 CRUD
    │   ├── pipeline_service.py     # 오케스트레이터 (크로스 도메인)
    │   ├── repository.py
    │   ├── models.py               # Meeting, TranscriptSegment, MeetingSummary
    │   ├── schemas.py
    │   ├── dependencies.py
    │   └── exceptions.py
    ├── inbox/
    │   ├── router.py               # GET /inbox, POST /classify, /dismiss
    │   ├── service.py
    │   ├── repository.py
    │   ├── models.py               # InboxItem
    │   ├── schemas.py
    │   ├── dependencies.py
    │   └── exceptions.py
    ├── para/
    │   ├── router.py               # CRUD + /archive
    │   ├── service.py
    │   ├── repository.py
    │   ├── models.py               # ParaItem, MeetingParaLink
    │   ├── schemas.py
    │   ├── dependencies.py
    │   └── exceptions.py
    ├── actions/
    │   ├── router.py               # CRUD
    │   ├── service.py
    │   ├── repository.py
    │   ├── models.py               # ActionItem
    │   ├── schemas.py
    │   ├── dependencies.py
    │   └── exceptions.py
    ├── notes/                      # Sprint 3
    │   └── (동일 구조)
    ├── rag/                        # Sprint 3
    │   ├── router.py               # POST /rag/ask (SSE)
    │   ├── service.py              # 하이브리드 검색 + Claude 생성
    │   ├── repository.py
    │   ├── models.py               # EmbeddingChunk, SemanticCache
    │   ├── schemas.py
    │   ├── dependencies.py
    │   └── exceptions.py
    └── services/                   # 공유 서비스 (도메인 아님)
        ├── ai_processing.py        # Claude API 집중 관리
        ├── transcription.py        # Whisper + pyannote
        └── embedding.py            # OpenAI 임베딩 + 청킹
```

### 의존성 흐름

```
Router → Service → Repository → DB
  ↓         ↓
Schemas   Models

규칙:
- 도메인 간 직접 import 금지
- 크로스 도메인 = pipeline_service.py (오케스트레이터)만
- AsyncSession은 Repository만 보유
- Dependencies.py에서만 Depends() 조립
```

### Sprint별 생성 순서

```
Sprint 1: core/ → common/ → auth/ → workspaces/ → meetings/ → services/
Sprint 2: inbox/ → para/ → actions/ + meetings/pipeline_service.py 완성
Sprint 3: notes/ → rag/
Sprint 4: auth/에 RBAC 추가
```

### 초기 셋업

```bash
# 프로젝트 생성
uv init backend && cd backend
uv add fastapi uvicorn sqlmodel asyncpg alembic pydantic-settings
uv add anthropic aioboto3 clerk-backend-api

# Alembic 초기화
alembic init alembic
# alembic/env.py에 async 설정 (run_async_migrations)

# 환경변수
cp .env.example .env.local

# 실행
uvicorn src.main:app --reload --port 8000
```

### main.py 라우터 등록

```python
from fastapi import FastAPI
from src.core.lifespan import lifespan

app = FastAPI(title="Kairos API", version="0.1.0", lifespan=lifespan)

# Sprint 1
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(workspace_router, prefix="/api/v1", tags=["workspaces"])
app.include_router(meeting_router, prefix="/api/v1", tags=["meetings"])
app.include_router(upload_router, prefix="/api/v1", tags=["storage"])

# Sprint 2
app.include_router(inbox_router, prefix="/api/v1", tags=["inbox"])
app.include_router(para_router, prefix="/api/v1", tags=["para"])
app.include_router(action_router, prefix="/api/v1", tags=["actions"])

# Sprint 3
app.include_router(note_router, prefix="/api/v1", tags=["notes"])
app.include_router(rag_router, prefix="/api/v1", tags=["rag"])
```

---

## 6. FE 수정 필요 사항 (참고)

백엔드 표준 우선 결정에 따라, Sprint 진행 시 FE를 수정해야 할 부분:

| FE 현재 | 백엔드 표준 | 수정 시점 |
|---------|-----------|----------|
| `ApiResponse<T>` 래퍼 | FastAPI 직접 모델 반환 | Sprint 1 API 연결 시 |
| `Meeting.paraItemId` (1:1) | `MeetingParaLink` (N:M) | Sprint 2 |
| Mock data 기반 API 호출 | Real API + React Query 연결 | Sprint 1~2 |

---

## 7. 에러 핸들링 전략

### MVP (Sprint 1~2)

- 파이프라인 실패 시 `Meeting.status = "failed"` + `errorMessage` 저장
- 사용자에게 "재시도" 버튼 제공 → 전체 파이프라인 재실행
- 개별 단계 재시도는 미지원

### 확장 (Sprint 3+, 필요 시)

- `Meeting.status`가 이미 단계별 상태를 가지므로 확장 가능
- `POST /meetings/{id}/retry` 엔드포인트 추가 검토
- 실패 단계부터 재시도 (STT 결과 재사용)
