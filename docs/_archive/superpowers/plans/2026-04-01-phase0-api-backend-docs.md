# Phase 0 문서 완성 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase 0의 남은 두 문서(API 명세 + 백엔드 셋업 가이드)를 완성하여 Sprint 1 즉시 착수 가능 상태로 만든다.

**Architecture:** 설계 스펙(`docs/superpowers/specs/2026-04-01-phase0-api-backend-design.md`)에서 확정된 32개 엔드포인트와 도메인 모듈러 구조를 문서화한다. API 명세는 Sprint 1~2 상세 + Sprint 3~4 목록 수준. 백엔드 가이드는 `backend.md` 규칙 기반 프로젝트 구조 + 초기 셋업 절차.

**Tech Stack:** FastAPI, SQLModel, asyncpg, Alembic, Pydantic V2, Clerk, aioboto3, Anthropic SDK

**참조 문서:**
- 설계 스펙: `docs/superpowers/specs/2026-04-01-phase0-api-backend-design.md`
- ERD: `docs/architecture/erd.md`
- AI 파이프라인: `docs/architecture/ai-pipeline.md`
- 크로스 도메인: `docs/architecture/cross-domain-pipeline.md`
- 백엔드 규칙: `.ai/stacks/fastapi/backend.md`
- PRD: `docs/requirements/prd.md`

---

## File Structure

| 작업 | 파일 | 역할 |
|------|------|------|
| 생성 | `docs/api/endpoints.md` | 32개 REST API 명세 (Sprint 1~2 상세, 3~4 목록) |
| 생성 | `docs/architecture/backend-scaffolding.md` | 백엔드 초기 셋업 가이드 (구조, 의존성, 커맨드) |
| 수정 | `docs/requirements/prd.md:85-88` | Phase 0 체크리스트 완료 표시 |
| 수정 | `docs/README.md` | 새 문서 2개 목차 추가 |

---

### Task 1: API 명세 문서 작성

**Files:**
- Create: `docs/api/endpoints.md`

- [ ] **Step 1: docs/api/ 디렉토리 생성**

Run: `mkdir -p docs/api`

- [ ] **Step 2: API 명세 문서 작성**

`docs/api/endpoints.md`를 생성한다. 내용은 설계 스펙의 섹션 1~4를 문서 형태로 재구성:

```markdown
# Kairos REST API 명세

> **버전:** 0.1.0
> **Base URL:** `/api/v1`
> **인증:** Clerk JWT Bearer Token (별도 명시 없는 한 모든 엔드포인트에 필요)
>
> **범위:** Sprint 1~2는 Request/Response 스키마 포함 상세 명세.
> Sprint 3~4는 엔드포인트 목록 + 한 줄 설명 수준.
> 상세는 해당 Sprint 착수 시 확정.

---

## 공통 규칙

### 인증
- 모든 요청에 `Authorization: Bearer <clerk_jwt>` 헤더 필요
- 예외: `GET /health`, `POST /users/sync` (Webhook)

### 에러 응답
- FastAPI 표준 `HTTPException` 사용
- 형식: `{ "detail": "에러 메시지" }`
- 상태 코드: 400 (잘못된 요청), 401 (인증 실패), 403 (권한 없음), 404 (미존재), 409 (충돌)

### 페이지네이션
- Query: `?page=1&pageSize=20`
- 응답: `{ "items": [...], "total": N, "page": 1, "pageSize": 20, "hasNext": true|false }`

### 날짜/시간
- ISO 8601 형식: `"2026-03-20T10:00:00Z"`
- 날짜만: `"2026-03-20"`

---

## 엔드포인트 전체 목록

| # | Sprint | Method | Path | 설명 |
|---|--------|--------|------|------|
| 1 | 1 | GET | /health | 헬스체크 |
| 2 | 1 | GET | /users/me | 현재 사용자 정보 |
| 3 | 1 | POST | /users/sync | Clerk webhook 동기화 |
| 4 | 1 | POST | /workspaces | 워크스페이스 생성 |
| 5 | 1 | GET | /workspaces | 내 워크스페이스 목록 |
| 6 | 1 | GET | /workspaces/{id} | 워크스페이스 상세 |
| 7 | 1 | POST | /workspaces/{id}/members | 멤버 추가 |
| 8 | 1 | POST | /upload/presigned-url | R2 프리사인드 URL |
| 9 | 1 | POST | /workspaces/{wid}/meetings | 회의 생성 (202) |
| 10 | 1 | GET | /workspaces/{wid}/meetings | 회의 목록 |
| 11 | 1 | GET | /workspaces/{wid}/meetings/{id} | 회의 상세 |
| 12 | 1 | GET | /workspaces/{wid}/meetings/{id}/status | 처리 상태 |
| 13 | 2 | GET | /workspaces/{wid}/inbox | Inbox 목록 |
| 14 | 2 | POST | /workspaces/{wid}/inbox/{id}/classify | PARA 분류 확정 |
| 15 | 2 | POST | /workspaces/{wid}/inbox/{id}/dismiss | Inbox 무시 |
| 16 | 2 | GET | /workspaces/{wid}/para-items | PARA 목록 |
| 17 | 2 | GET | /workspaces/{wid}/para-items/{id} | PARA 상세 |
| 18 | 2 | POST | /workspaces/{wid}/para-items | PARA 생성 |
| 19 | 2 | PATCH | /workspaces/{wid}/para-items/{id} | PARA 수정 |
| 20 | 2 | DELETE | /workspaces/{wid}/para-items/{id} | PARA 삭제 |
| 21 | 2 | POST | /workspaces/{wid}/para-items/{id}/archive | Archive 전환 |
| 22 | 2 | GET | /workspaces/{wid}/action-items | 액션 목록 |
| 23 | 2 | POST | /workspaces/{wid}/action-items | 액션 생성 |
| 24 | 2 | PATCH | /workspaces/{wid}/action-items/{id} | 액션 수정 |
| 25 | 3 | POST | /workspaces/{wid}/rag/ask | RAG 질문 (SSE) |
| 26 | 3 | GET | /workspaces/{wid}/para-items/{pid}/notes | 노트 목록 |
| 27 | 3 | POST | /workspaces/{wid}/para-items/{pid}/notes | 노트 생성 |
| 28 | 3 | PATCH | /workspaces/{wid}/notes/{id} | 노트 수정 |
| 29 | 3 | DELETE | /workspaces/{wid}/notes/{id} | 노트 삭제 |
| 30 | 4 | PATCH | /workspaces/{id}/members/{uid}/role | 역할 변경 |
| 31 | 4 | DELETE | /workspaces/{id}/members/{uid} | 멤버 제거 |
| 32 | 4 | POST | /workspaces/{id}/invite | 초대 링크 |

---
```

이후 설계 스펙의 섹션 2(Sprint 1 상세), 섹션 3(Sprint 2 상세), 섹션 4(Sprint 3~4 목록)를 도메인별로 재구성하여 추가한다.

각 도메인 섹션 구조:
```markdown
## [도메인명]

### [METHOD] [Path]

**설명:** 한 줄 설명

**Request:**
- Headers: (필요 시)
- Query: (필요 시)
- Body:
\```json
{ ... }
\```

**Response:**
- 성공 (200|201|202|204):
\```json
{ ... }
\```
- 에러:
  - 404: `{ "detail": "..." }`
```

전체 내용은 설계 스펙 `2026-04-01-phase0-api-backend-design.md`의 섹션 2~4에서 가져온다. **그대로 복사가 아닌, API 문서 형식으로 재구성.**

- [ ] **Step 3: 커밋**

```bash
git add docs/api/endpoints.md
git commit -m "docs: API 명세 작성 (32개 엔드포인트, Sprint 1~2 상세)"
```

---

### Task 2: 백엔드 셋업 가이드 작성

**Files:**
- Create: `docs/architecture/backend-scaffolding.md`

- [ ] **Step 1: 백엔드 셋업 가이드 작성**

`docs/architecture/backend-scaffolding.md`를 생성한다. 내용은 설계 스펙의 섹션 5를 가이드 형태로 확장:

```markdown
# 백엔드 초기 셋업 가이드

> FastAPI + SQLModel + Alembic 기반 백엔드 프로젝트 구조 및 초기 셋업 절차.
> 상세 규칙: `.ai/stacks/fastapi/backend.md` 참조.

---

## 1. 프로젝트 생성

\```bash
# backend/ 디렉토리 생성
uv init backend && cd backend

# 핵심 의존성
uv add fastapi uvicorn[standard] sqlmodel asyncpg alembic pydantic-settings

# 외부 서비스
uv add anthropic aioboto3 clerk-backend-api

# 개발 의존성
uv add --dev pytest pytest-asyncio httpx
\```

## 2. 디렉토리 구조

\```
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py                      # async 설정 필수
│   └── versions/
├── Dockerfile
├── .env.example
└── src/
    ├── main.py
    ├── core/
    │   ├── config.py               # pydantic-settings (SecretStr)
    │   └── lifespan.py             # startup/shutdown
    ├── common/
    │   ├── database.py             # AsyncSession, get_async_session
    │   ├── exceptions.py           # 공통 예외 + 핸들러
    │   ├── pagination.py           # PaginatedResponse
    │   ├── prompts.py              # Claude 프롬프트 상수
    │   └── r2.py                   # R2 presigned URL (aioboto3)
    ├── auth/
    │   ├── router.py
    │   ├── service.py
    │   ├── dependencies.py         # get_current_user (Clerk JWT)
    │   ├── schemas.py
    │   └── exceptions.py
    ├── workspaces/
    │   ├── router.py
    │   ├── service.py
    │   ├── repository.py
    │   ├── models.py               # Workspace, WorkspaceMember
    │   ├── schemas.py
    │   ├── dependencies.py
    │   └── exceptions.py
    ├── meetings/
    │   ├── router.py
    │   ├── service.py
    │   ├── pipeline_service.py     # 오케스트레이터 (크로스 도메인)
    │   ├── repository.py
    │   ├── models.py               # Meeting, TranscriptSegment, MeetingSummary
    │   ├── schemas.py
    │   ├── dependencies.py
    │   └── exceptions.py
    ├── inbox/                      # Sprint 2
    │   └── (동일 구조)
    ├── para/                       # Sprint 2
    │   ├── models.py               # ParaItem, MeetingParaLink
    │   └── (동일 구조)
    ├── actions/                    # Sprint 2
    │   └── (동일 구조)
    ├── notes/                      # Sprint 3
    │   └── (동일 구조)
    ├── rag/                        # Sprint 3
    │   ├── models.py               # EmbeddingChunk, SemanticCache
    │   └── (동일 구조)
    └── services/                   # 공유 서비스 (도메인 아님)
        ├── ai_processing.py        # Claude API 집중 관리
        ├── transcription.py        # Whisper + pyannote
        └── embedding.py            # OpenAI 임베딩 + 청킹
\```

## 3. 도메인 모듈 구조

각 도메인 모듈은 아래 파일을 포함한다:

| 파일 | 역할 | 핵심 규칙 |
|------|------|----------|
| router.py | HTTP 수신, 스키마 검증 | 10줄 이하, DB 접근/비즈니스 로직 금지 |
| service.py | 비즈니스 로직 + 트랜잭션 경계 | AsyncSession import 금지 |
| repository.py | DB 접근 전담 | AsyncSession 유일 보유자 |
| models.py | SQLModel 테이블 정의 | |
| schemas.py | Pydantic V2 입출력 | |
| dependencies.py | Depends() 조립 | 유일한 DI 위치 |
| exceptions.py | 도메인 예외 | |

### 의존성 흐름

\```
Router → Service → Repository → DB
  ↓         ↓
Schemas   Models

금지: 도메인 간 직접 import
허용: pipeline_service.py (오케스트레이터)만 크로스 도메인
\```

## 4. Sprint별 생성 순서

\```
Sprint 1: core/ → common/ → auth/ → workspaces/ → meetings/ → services/
Sprint 2: inbox/ → para/ → actions/ + meetings/pipeline_service.py 완성
Sprint 3: notes/ → rag/
Sprint 4: auth/에 RBAC 추가
\```

## 5. 핵심 설정 파일

### core/config.py

\```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: SecretStr

    # Auth
    clerk_secret_key: SecretStr

    # Storage
    r2_account_id: SecretStr
    r2_access_key_id: SecretStr
    r2_secret_access_key: SecretStr
    r2_bucket_name: str
    r2_public_url: str

    # AI
    anthropic_api_key: SecretStr
    openai_api_key: SecretStr

    # App
    app_env: str = "development"

    model_config = {"env_file": ".env.local"}

settings = Settings()
\```

### common/database.py

\```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.core.config import settings

engine = create_async_engine(
    settings.database_url.get_secret_value(),
    echo=settings.app_env == "development",
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_session():
    async with async_session() as session:
        yield session
\```

### main.py

\```python
from fastapi import FastAPI
from src.core.lifespan import lifespan

app = FastAPI(title="Kairos API", version="0.1.0", lifespan=lifespan)

# Sprint 1
from src.auth.router import router as auth_router
from src.workspaces.router import router as workspace_router
from src.meetings.router import router as meeting_router

app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(workspace_router, prefix="/api/v1", tags=["workspaces"])
app.include_router(meeting_router, prefix="/api/v1", tags=["meetings"])

@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
\```

## 6. Alembic 비동기 설정

\```bash
alembic init alembic
\```

`alembic/env.py`에서 `run_async_migrations()` 패턴 적용 필요.
모든 `models.py` 변경 시 마이그레이션 생성 필수:

\```bash
alembic revision --autogenerate -m "설명"
alembic upgrade head
\```

## 7. 실행

\```bash
# 개발 서버
uvicorn src.main:app --reload --port 8000

# API 문서
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
\```

## 8. 환경변수 (.env.example)

\```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname

# Auth (Clerk)
CLERK_SECRET_KEY=sk_test_xxx

# Storage (Cloudflare R2)
R2_ACCOUNT_ID=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET_NAME=kairos-uploads
R2_PUBLIC_URL=https://xxx.r2.dev

# AI
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx

# App
APP_ENV=development
\```
```

- [ ] **Step 2: 커밋**

```bash
git add docs/architecture/backend-scaffolding.md
git commit -m "docs: 백엔드 초기 셋업 가이드 작성"
```

---

### Task 3: 기존 문서 업데이트

**Files:**
- Modify: `docs/requirements/prd.md:85-88`
- Modify: `docs/README.md`

- [ ] **Step 1: PRD Phase 0 체크리스트 업데이트**

`docs/requirements/prd.md`에서 Phase 0 체크리스트를 완료 표시:

```markdown
# 변경 전 (라인 85-88)
- [ ] `docs/api/endpoints.md` — 16개 REST API 명세 (Request/Response 스키마 포함)
- [ ] `docs/architecture/backend-scaffolding.md` — 백엔드 초기 셋업 가이드
- [ ] 본 PRD Sprint 분해 완료 (이 섹션)

# 변경 후
- [x] `docs/api/endpoints.md` — 32개 REST API 명세 (Sprint 1~2 상세)
- [x] `docs/architecture/backend-scaffolding.md` — 백엔드 초기 셋업 가이드
- [x] 본 PRD Sprint 분해 완료 (이 섹션)
```

- [ ] **Step 2: docs/README.md에 새 문서 추가**

`docs/README.md`의 문서 목차에 아래 두 항목 추가:

```markdown
- `api/endpoints.md` — REST API 명세 (32개 엔드포인트)
- `architecture/backend-scaffolding.md` — 백엔드 초기 셋업 가이드
```

정확한 위치는 `docs/README.md`를 읽고 기존 구조에 맞춰 삽입한다.

- [ ] **Step 3: 커밋**

```bash
git add docs/requirements/prd.md docs/README.md
git commit -m "docs: Phase 0 완료 표시 및 문서 목차 업데이트"
```

---

### Task 4: Phase 0 완료 검증

- [ ] **Step 1: Phase 0 체크리스트 확인**

```bash
# 세 파일 모두 존재하는지 확인
ls docs/api/endpoints.md docs/architecture/backend-scaffolding.md
```

Expected: 두 파일 모두 존재

- [ ] **Step 2: PRD Phase 0 체크리스트 확인**

```bash
grep -c "\[x\]" docs/requirements/prd.md
```

Expected: Phase 0 항목 3개 모두 `[x]`

- [ ] **Step 3: 최종 커밋 확인**

```bash
git log --oneline -5
```

Expected: Task 1~3의 커밋 3개가 보임
