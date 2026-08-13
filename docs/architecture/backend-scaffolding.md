# 백엔드 초기 셋업 가이드

> Kairos 백엔드(FastAPI + SQLModel + asyncpg)를 처음부터 구성하는 단계별 가이드.
> 모든 규칙은 `.ai/stacks/fastapi/backend.md`를 따른다.

---

## 1. 프로젝트 생성

```bash
# 프로젝트 초기화
cd kairos/
uv init backend --no-readme
cd apps/backend/

# 핵심 의존성
uv add fastapi "uvicorn[standard]" sqlmodel asyncpg alembic pydantic-settings

# 외부 서비스
uv add google-genai aioboto3

# 개발 의존성
uv add --dev pytest pytest-asyncio httpx
```

---

## 2. 디렉토리 구조

```
apps/backend/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py                      # async 설정 필수
│   └── versions/                   # 마이그레이션 파일
├── Dockerfile
├── .env.example
└── src/
    ├── main.py                     # FastAPI app, 라우터 등록, health
    ├── core/
    │   ├── config.py               # pydantic-settings + SecretStr
    │   └── lifespan.py             # startup / shutdown (DB pool 등)
    ├── common/
    │   ├── database.py             # AsyncSession, get_async_session
    │   ├── exceptions.py           # 공통 예외 클래스 + 글로벌 핸들러
    │   ├── pagination.py           # PaginatedResponse 제네릭
    │   ├── prompts.py              # Gemini 프롬프트 상수 (인라인 금지)
    │   └── r2.py                   # R2 presigned URL (aioboto3)
    ├── auth/                       # Sprint 1
    │   ├── router.py
    │   ├── service.py
    │   ├── dependencies.py
    │   ├── schemas.py
    │   └── exceptions.py
    ├── workspaces/                  # Sprint 1
    │   ├── router.py
    │   ├── service.py
    │   ├── repository.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── dependencies.py
    │   └── exceptions.py
    ├── meetings/                    # Sprint 1
    │   ├── router.py
    │   ├── service.py
    │   ├── pipeline_service.py     # 오케스트레이터 (크로스 도메인 유일 허용)
    │   ├── repository.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── dependencies.py
    │   └── exceptions.py
    ├── inbox/                       # Sprint 2
    │   ├── router.py, service.py, repository.py
    │   ├── models.py, schemas.py, dependencies.py, exceptions.py
    ├── projects/                    # Sprint 2
    │   ├── router.py, service.py, repository.py
    │   ├── models.py               # Project, MeetingProjectLink (N:M)
    │   ├── schemas.py, dependencies.py, exceptions.py
    ├── actions/                     # Sprint 2
    │   ├── router.py, service.py, repository.py
    │   ├── models.py, schemas.py, dependencies.py, exceptions.py
    ├── notes/                       # Sprint 3
    │   ├── router.py, service.py, repository.py
    │   ├── models.py, schemas.py, dependencies.py, exceptions.py
    ├── rag/                         # Sprint 3
    │   ├── router.py, service.py, repository.py
    │   ├── models.py               # EmbeddingChunk, SemanticCache
    │   ├── schemas.py, dependencies.py, exceptions.py
    └── services/                    # 공유 서비스 (도메인이 아닌 인프라)
        ├── ai_processing.py         # Gemini API 집중 관리
        ├── transcription.py         # Whisper + pyannote 화자 분리
        └── embedding.py             # OpenAI 임베딩 + 청킹
```

---

## 3. 도메인 모듈 구조

### 파일별 역할

| 파일 | 역할 | 핵심 규칙 |
|------|------|-----------|
| `router.py` | HTTP 수신, 스키마 검증, service 호출 | **10줄 이하**, DB 접근 금지, 비즈니스 로직 금지 |
| `service.py` | 비즈니스 로직, 트랜잭션 경계 | **AsyncSession import 절대 금지**, Repository만 생성자 주입 |
| `repository.py` | DB 접근 전담 | **AsyncSession 유일 보유자**, `commit()`은 service 요청으로만 |
| `models.py` | SQLModel 테이블 정의 | 변경 시 Alembic 마이그레이션 필수 |
| `schemas.py` | Pydantic V2 입출력 DTO | `.model_dump()` 사용 (`.dict()` 금지) |
| `dependencies.py` | `Depends()` 조립의 유일한 위치 | service.py / repository.py에서 Depends import 금지 |
| `exceptions.py` | 도메인별 예외 클래스 | `common/exceptions.py`의 기반 클래스 상속 |

### 의존성 흐름

```
Router → Service → Repository → DB
  ↑
dependencies.py 에서 Depends()로 조립

금지: 도메인 간 직접 import (예: meetings/ → inbox/ 직접 import)
허용: pipeline_service.py (오케스트레이터)만 크로스 도메인 서비스 조합 가능
```

### 크로스 레포지토리 트랜잭션

여러 Repository가 하나의 트랜잭션에 참여해야 하면, `dependencies.py`에서 **동일 AsyncSession**을 주입한다.
개별 Repository에서 `commit()`하지 않고, 조율하는 Service에서 **한 번만 commit**한다.

---

## 4. Sprint별 생성 순서

| Sprint | 생성 모듈 | 비고 |
|--------|-----------|------|
| Sprint 1 | `core/` → `common/` → `auth/` → `workspaces/` → `meetings/` → `services/` | 기본 인프라 + 핵심 도메인 |
| Sprint 2 | `inbox/` → `projects/` → `actions/` + `meetings/pipeline_service.py` 완성 | AI 처리 파이프라인 + 프로젝트 연결 워크플로우 |
| Sprint 3 | `notes/` → `rag/` | 임베딩 + RAG 검색 |
| Sprint 4 | `auth/`에 RBAC 추가 | 역할 기반 접근 제어 |

---

## 5. 핵심 설정 파일 코드 예시

### core/config.py

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_env: str = "development"
    debug: bool = False

    # Database
    database_url: SecretStr

    # Auth (Clerk)
    clerk_secret_key: SecretStr

    # Storage (Cloudflare R2)
    r2_account_id: SecretStr
    r2_access_key_id: SecretStr
    r2_secret_access_key: SecretStr
    r2_bucket_name: str = "kairos-uploads"
    r2_public_url: str = ""

    # AI
    gemini_api_key: SecretStr
    openai_api_key: SecretStr


settings = Settings()  # type: ignore[call-arg]
```

### common/database.py

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from src.core.config import settings

engine = create_async_engine(
    settings.database_url.get_secret_value(),
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

> **주의:** `session.exec()` 절대 금지. 반드시 `await session.execute(select(...))` 후 `.scalars().all()` 또는 `.scalar_one_or_none()` 사용.

### main.py

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from src.core.lifespan import lifespan


def create_app() -> FastAPI:
    app = FastAPI(
        title="Kairos API",
        description="AI 기반 미팅 & 지식 관리 플랫폼",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 라우터 등록
    # from src.auth.router import router as auth_router
    # from src.workspaces.router import router as workspaces_router
    # from src.meetings.router import router as meetings_router
    # app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
    # app.include_router(workspaces_router, prefix="/api/v1/workspaces", tags=["Workspaces"])
    # app.include_router(meetings_router, prefix="/api/v1/meetings", tags=["Meetings"])

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()
```

### core/lifespan.py

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from src.common.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # startup
    yield
    # shutdown
    await engine.dispose()
```

---

## 6. Alembic 비동기 설정

### 초기화

```bash
cd apps/backend/
alembic init alembic
```

### alembic/env.py 수정

기본 생성된 `env.py`는 동기 엔진을 사용한다. asyncpg를 사용하므로 비동기로 변경해야 한다.

핵심 변경 사항:
1. `run_migrations_online()`을 `async`로 변경
2. `create_async_engine` 사용
3. `connection.run_sync(do_run_migrations)` 패턴 적용
4. 모든 SQLModel 모델을 import하여 `target_metadata`에 반영

```python
# alembic/env.py 핵심 부분
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# 모든 모델 import (autogenerate가 인식하도록)
from src.core.config import settings
# from src.workspaces.models import *  # Sprint 1에서 추가
# from src.meetings.models import *    # Sprint 1에서 추가

target_metadata = SQLModel.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(
        settings.database_url.get_secret_value()
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


asyncio.run(run_migrations_online())
```

### alembic.ini 수정

`sqlalchemy.url`은 비워두고 `env.py`에서 `settings.database_url`을 사용한다.

```ini
# alembic.ini
sqlalchemy.url =
```

### 마이그레이션 명령어

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "initial tables"

# 마이그레이션 적용
alembic upgrade head

# 롤백
alembic downgrade -1
```

> **규칙:** `models.py` 변경 시 반드시 Alembic 마이그레이션을 생성하고 커밋에 포함한다.
> 프로덕션 배포 전 `alembic upgrade head`는 Docker entrypoint에서 자동 실행한다.

---

## 7. 실행 커맨드

```bash
# 개발 서버 실행
cd apps/backend/
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 또는 축약
uv run fastapi dev src/main.py --port 8000
```

| URL | 설명 |
|-----|------|
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/docs` | Swagger UI (OpenAPI) |
| `http://localhost:8000/redoc` | ReDoc |

---

## 8. 환경변수 (.env.example)

```bash
# App
APP_ENV=development
DEBUG=true

# Database (Neon PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname

# Auth (Clerk)
CLERK_SECRET_KEY=sk_test_...

# Storage (Cloudflare R2)
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=kairos-uploads
R2_PUBLIC_URL=

# AI
GEMINI_API_KEY=...
OPENAI_API_KEY=sk-...
```

> **주의:** 코드에 환경변수 하드코딩 절대 금지.
> 모든 API 키와 DB 패스워드는 `config.py`에서 `SecretStr` 타입으로 선언하고,
> 사용 시 `.get_secret_value()`로 접근한다.
