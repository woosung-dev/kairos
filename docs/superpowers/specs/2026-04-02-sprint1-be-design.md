# Sprint 1 BE 설계: 인프라 + AI 파이프라인

> **목적:** FastAPI 백엔드 셋업 + 12개 API + Whisper STT + Claude 요약. End-to-End "업로드 → 요약" 동작.
> **작성일:** 2026-04-02
> **범위:** BE만. FE API 연결은 별도 Sub-project.

---

## 설계 결정

| 결정 | 선택 | 근거 |
|------|------|------|
| Sprint 1 분해 | BE 전체 → FE 연결 (별도) | BE 내부 순차 의존. FE는 BE 완성 후. |
| STT | Whisper API만 (화자 분리 없음) | MVP는 요약 검증. 화자 분리는 Sprint 2+. |
| DB | Neon PostgreSQL (클라우드) | pgvector 포함. 계정 있음. |
| 에러 핸들링 | 전체 롤백 (status: failed) | MVP 단순화. 단계별 재시도는 나중에. |

---

## 1. 프로젝트 초기화

```bash
cd kairos/
uv init backend --no-readme && cd backend/
uv add fastapi "uvicorn[standard]" sqlmodel asyncpg alembic pydantic-settings
uv add anthropic aioboto3 clerk-backend-api openai
uv add --dev pytest pytest-asyncio httpx
```

### 환경변수 (.env.example)

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
CLERK_SECRET_KEY=sk_test_xxx
CLERK_WEBHOOK_SECRET=whsec_xxx
R2_ACCOUNT_ID=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET_NAME=kairos-uploads
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
APP_ENV=development
```

---

## 2. 디렉토리 구조

```
backend/src/
├── main.py
├── core/
│   ├── config.py           # Settings (pydantic-settings + SecretStr)
│   └── lifespan.py         # startup: DB 엔진 생성 / shutdown: 엔진 dispose
├── common/
│   ├── database.py         # create_async_engine + async_sessionmaker + get_async_session
│   ├── exceptions.py       # 공통 예외 (NotFound, AlreadyExists 등) + 핸들러
│   ├── pagination.py       # PaginatedResponse 유틸
│   ├── prompts.py          # MEETING_SUMMARY_SYSTEM_PROMPT + parse_json_response
│   └── r2.py               # get_presigned_url (aioboto3)
├── auth/
│   ├── router.py           # GET /users/me, POST /users/sync
│   ├── service.py          # 사용자 조회/생성
│   ├── models.py           # User (SQLModel)
│   ├── schemas.py          # UserResponse, WebhookPayload
│   ├── dependencies.py     # get_current_user (Clerk JWT 검증)
│   ├── repository.py       # UserRepository
│   └── exceptions.py
├── workspaces/
│   ├── router.py           # POST/GET /workspaces, GET /{id}, POST /{id}/members
│   ├── service.py
│   ├── models.py           # Workspace, WorkspaceMember
│   ├── schemas.py          # CreateWorkspace, WorkspaceResponse, AddMember
│   ├── dependencies.py
│   ├── repository.py
│   └── exceptions.py
├── meetings/
│   ├── router.py           # POST /meetings (202), GET /meetings, GET /{id}, GET /{id}/status
│   ├── service.py          # 단일 도메인 CRUD
│   ├── pipeline_service.py # 오케스트레이터 (STT → 요약 → 완료)
│   ├── models.py           # Meeting, TranscriptSegment, MeetingSummary
│   ├── schemas.py          # CreateMeeting, MeetingResponse, MeetingDetailResponse, StatusResponse
│   ├── dependencies.py
│   ├── repository.py
│   └── exceptions.py
└── services/
    ├── ai_processing.py    # Claude API: summarize(transcript) → MeetingSummary
    └── transcription.py    # Whisper API: transcribe(audio_url) → TranscriptSegment[]
```

---

## 3. DB 모델 (Sprint 1 테이블)

### User

```python
class User(SQLModel, table=True):
    __tablename__ = "users"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    clerk_id: str = Field(unique=True, index=True)
    display_name: str
    email: str
    avatar_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Workspace + WorkspaceMember

```python
class Workspace(SQLModel, table=True):
    __tablename__ = "workspaces"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    owner_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class WorkspaceMember(SQLModel, table=True):
    __tablename__ = "workspace_members"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    user_id: uuid.UUID = Field(foreign_key="users.id")
    role: str = "member"  # owner | admin | member | viewer
```

### Meeting + TranscriptSegment + MeetingSummary

```python
class Meeting(SQLModel, table=True):
    __tablename__ = "meetings"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    title: str
    file_key: str  # R2 저장 경로
    recorded_at: datetime | None = None
    duration_sec: int | None = None
    status: str = "uploading"  # uploading|transcribing|summarizing|completed|failed
    error_message: str | None = None
    has_transcript: bool = False
    has_summary: bool = False
    action_item_count: int = 0
    created_by_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TranscriptSegment(SQLModel, table=True):
    __tablename__ = "transcript_segments"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    meeting_id: uuid.UUID = Field(foreign_key="meetings.id")
    speaker: str = "Speaker"  # Sprint 1: 화자 분리 없음, 기본값
    start_sec: float
    end_sec: float
    text: str

class MeetingSummary(SQLModel, table=True):
    __tablename__ = "meeting_summaries"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    meeting_id: uuid.UUID = Field(foreign_key="meetings.id", unique=True)
    summary: str
    key_decisions: dict = Field(default_factory=list, sa_type=JSON)
    topics: dict = Field(default_factory=list, sa_type=JSON)
```

---

## 4. API 엔드포인트 상세

### Health

```
GET /api/v1/health → { "status": "ok", "version": "0.1.0" }
```

### Auth (2개)

```
GET /api/v1/users/me
  Headers: Authorization: Bearer <jwt>
  → 200: { id, clerkId, displayName, email, avatarUrl }
  → 401: { detail: "인증이 필요합니다" }

POST /api/v1/users/sync
  Headers: svix-id, svix-timestamp, svix-signature
  Body: Clerk Webhook Payload
  → 200: { synced: true }
```

### Workspaces (4개)

```
POST /api/v1/workspaces
  Body: { name: "우리팀" }
  → 201: Workspace

GET /api/v1/workspaces
  → 200: [Workspace, ...]

GET /api/v1/workspaces/{id}
  → 200: Workspace + memberCount
  → 404

POST /api/v1/workspaces/{id}/members
  Body: { email: "user@example.com" }
  → 201: { id, userId, role: "member" }
  → 404: 사용자 없음
  → 409: 이미 멤버
```

### Storage (1개)

```
POST /api/v1/upload/presigned-url
  Body: { filename: "meeting.mp3", contentType: "audio/mpeg" }
  → 200: { uploadUrl, fileKey, expiresIn: 3600 }
```

### Meetings (4개)

```
POST /api/v1/workspaces/{wid}/meetings
  Body: { title, fileKey, recordedAt? }
  → 202: { id, status: "uploading", message: "파이프라인이 시작되었습니다" }
  내부: BackgroundTasks → pipeline_service.process_meeting()

GET /api/v1/workspaces/{wid}/meetings
  Query: ?page=1&pageSize=20
  → 200: PaginatedResponse<Meeting>

GET /api/v1/workspaces/{wid}/meetings/{id}
  → 200: MeetingDetail (+ transcript + summary)
  → 404

GET /api/v1/workspaces/{wid}/meetings/{id}/status
  → 200: { status, errorMessage? }
```

---

## 5. 파이프라인 (MeetingPipelineService)

```python
class MeetingPipelineService:
    """회의 처리 오케스트레이터. BackgroundTasks에서 실행."""

    async def process_meeting(self, meeting_id: UUID) -> None:
        try:
            # [1] STT
            await self.meeting_repo.update_status(meeting_id, "transcribing")
            audio_url = await self.r2.get_download_url(meeting.file_key)
            segments = await self.transcription.transcribe(audio_url)
            await self.meeting_repo.save_segments(meeting_id, segments)
            await self.meeting_repo.set_has_transcript(meeting_id, True)

            # [2] 요약
            await self.meeting_repo.update_status(meeting_id, "summarizing")
            transcript_text = "\n".join(s.text for s in segments)
            summary = await self.ai_processing.summarize(transcript_text)
            await self.meeting_repo.save_summary(meeting_id, summary)
            await self.meeting_repo.set_has_summary(meeting_id, True)

            # [3] 완료
            await self.meeting_repo.update_status(meeting_id, "completed")
            await self.meeting_repo.commit()

        except Exception as e:
            await self.meeting_repo.update_status(
                meeting_id, "failed", error_message=str(e)
            )
            await self.meeting_repo.commit()
```

---

## 6. 외부 서비스

### Whisper API (transcription.py)

```python
from openai import AsyncOpenAI

class TranscriptionService:
    async def transcribe(self, audio_url: str) -> list[TranscriptSegment]:
        """Whisper API로 오디오 → 트랜스크립트 변환. 화자 분리 없음 (MVP)."""
        # R2에서 오디오 다운로드 → Whisper API 전송
        # response.segments → TranscriptSegment 변환
        # speaker는 모두 "Speaker" (Sprint 2에서 pyannote 추가)
```

### Claude API (ai_processing.py)

```python
import anthropic
from src.common.prompts import MEETING_SUMMARY_SYSTEM_PROMPT, parse_json_response

class AIProcessingService:
    async def summarize(self, transcript: str) -> dict:
        """Claude로 트랜스크립트 → 구조화된 요약."""
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=MEETING_SUMMARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": transcript}],
        )
        return parse_json_response(response.content[0].text)
```

### R2 Presigned URL (r2.py)

```python
import aioboto3

class R2Service:
    async def get_presigned_url(self, filename: str, content_type: str) -> dict:
        """업로드용 presigned URL 발급."""

    async def get_download_url(self, file_key: str) -> str:
        """다운로드용 presigned URL 발급 (파이프라인 내부용)."""
```

---

## 7. 완료 기준

- `uvicorn src.main:app --reload` 실행 가능
- `/api/v1/health` → 200
- `/api/v1/docs` (Swagger) 접근 가능
- Alembic 마이그레이션 → Neon DB에 테이블 생성
- Clerk JWT로 `/users/me` 인증 동작
- 워크스페이스 CRUD 동작
- R2 presigned URL 발급 동작
- `POST /meetings` → 202 + BackgroundTasks → STT → 요약 → completed
- `GET /meetings/{id}/status` 폴링으로 상태 확인 가능
- `GET /meetings/{id}` 요약 + 트랜스크립트 반환

---

## 8. 범위 외

- FE API 연결 (별도 Sub-project)
- 화자 분리 (Sprint 2+)
- 액션 아이템 추출 (Sprint 2)
- 프로젝트 연결 + Inbox (Sprint 2)
- 임베딩 + RAG (Sprint 3)
- RBAC (Sprint 4)
