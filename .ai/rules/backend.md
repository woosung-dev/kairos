---
paths: ["backend/**/*"]
---

# Backend Rules (FastAPI + SQLModel + Kairos)

---

## 1. Tech Stack

| 항목 | 기술 |
|------|------|
| Framework | FastAPI (100% Async) |
| ORM | SQLModel + SQLAlchemy 2.0 (`asyncpg`) |
| Validation | Pydantic V2 + `pydantic-settings` |
| Package Manager | `uv` |
| Database | PostgreSQL on Neon |
| Auth | Clerk JWT 검증 |
| Storage | Cloudflare R2 (boto3 S3 호환 API) |
| AI | Anthropic Claude API (`anthropic` SDK) |
| STT | OpenAI Whisper API + pyannote-audio |
| 배포 | GCP Cloud Run + Docker |

---

## 2. 핵심 제약 사항 (Strict Rules)

### Pydantic V2 필수 패턴

- `BaseSettings`는 반드시 `pydantic_settings`에서 임포트 (pydantic 내부 금지)
- `.dict()` 대신 `.model_dump()`, `.model_dump_json()`
- `@root_validator` 대신 `@model_validator(mode="after")`

### 100% 비동기 SQLModel

- `session.exec()` 절대 금지
- `await session.execute(select(...))` 후 `.scalars().all()` 또는 `.scalar_one_or_none()`
- N+1 방지: `options(selectinload(...))`

### SecretStr

- API 키, DB 패스워드 등 → `SecretStr` 타입
- 사용 시 `.get_secret_value()`

### Clerk JWT 검증

```python
# auth/dependencies.py
from clerk_backend_api import Clerk
from fastapi import Depends, HTTPException, Header

async def get_current_user(authorization: str = Header(...)) -> dict:
    token = authorization.replace("Bearer ", "")
    # Clerk SDK로 토큰 검증
    ...
```

---

## 3. Architecture (도메인 모듈러 — Router / Service / Repository)

**핵심: AsyncSession은 Repository만 보유한다.**

```
[domain]/
├── router.py        # HTTP 전용 (10줄 이하)
├── service.py       # 비즈니스 로직 (AsyncSession 보유 금지)
├── repository.py    # DB 접근 전담 (AsyncSession 유일 보유자)
├── schemas.py       # Pydantic V2 입출력
├── models.py        # SQLModel 테이블
├── dependencies.py  # Depends() 조립 (repo → service)
└── exceptions.py    # 도메인 예외
```

### 레이어 규칙

- **Router** — HTTP 수신, 스키마 검증, service 호출만. DB 접근/비즈니스 로직 금지.
- **Service** — 비즈니스 로직 + 트랜잭션 경계. AsyncSession import 절대 금지. Repository만 생성자 주입.
- **Repository** — AsyncSession 유일 보유. DB 접근만. commit()은 service 요청으로만.
- **Dependencies** — Depends() 조립의 유일한 위치. service.py/repository.py에 Depends import 금지.

### 필수 코드 패턴

```python
# router.py
@router.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(
    data: CreateItemRequest,
    service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    return await service.create_item(data)

# service.py — AsyncSession import 금지
class ItemService:
    def __init__(self, repo: ItemRepository) -> None:
        self.repo = repo

    async def create_item(self, data: CreateItemRequest) -> ItemResponse:
        item = Item.model_validate(data)
        saved = await self.repo.save(item)
        await self.repo.commit()
        return ItemResponse.model_validate(saved)

# repository.py
class ItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, item: Item) -> Item:
        self.session.add(item)
        await self.session.flush()
        return item

    async def commit(self) -> None:
        await self.session.commit()

# dependencies.py
async def get_item_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ItemRepository:
    return ItemRepository(session)

async def get_item_service(
    repo: ItemRepository = Depends(get_item_repository),
) -> ItemService:
    return ItemService(repo)
```

### 아키텍처 원칙

- 크로스 도메인 호출은 **오케스트레이터 서비스**(`pipeline_service.py`)로만. 도메인 간 직접 import 금지.
- 장기 작업(STT, AI 처리)은 **BackgroundTasks + 202 Accepted + status polling**. HTTP 블로킹 금지.
- R2는 `aioboto3` 비동기 사용. 동기 `boto3` 직접 사용 금지 (불가피 시 `run_in_executor`).
- DB 스키마 변경 시 **Alembic 마이그레이션 필수**. models.py만 수정하고 마이그레이션 생략 금지.
- 여러 Repository가 하나의 트랜잭션이면 **동일 session 공유** + 마지막에 한 번만 commit.

> 상세 구현 패턴: `docs/architecture/` 참조

---

## 4. Kairos AI Pipeline

### Claude API 사용 규칙

- 모델명 고정: `claude-sonnet-4-20250514` (임의 변경 금지)
- LLM 구현체는 `BaseLLMService` 인터페이스로 추상화
- 모든 Claude 호출은 `services/ai_processing.py`에 집중 관리

```python
import anthropic
from src.core.config import settings

client = anthropic.AsyncAnthropic(
    api_key=settings.anthropic_api_key.get_secret_value()
)
```

### LLM Prompt Templates

프롬프트는 `src/common/prompts.py`에 상수로 정의. 인라인 작성 금지.

- `ACTION_ITEM_SYSTEM_PROMPT` — 트랜스크립트 → 액션 아이템 추출
- `MEETING_SUMMARY_SYSTEM_PROMPT` — 트랜스크립트 → 구조화 요약
- `PARA_CLASSIFY_SYSTEM_PROMPT` — 회의 요약 → PARA 분류 추천
- `RAG_ANSWER_SYSTEM_PROMPT` — 컨텍스트 기반 Q&A

### JSON 파싱 안전 처리

```python
import json, re

def parse_json_response(text: str) -> dict:
    clean = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude 응답 JSON 파싱 실패: {e}\n원본: {text}")
```

---

## 5. STT 파이프라인

- Whisper API 호출: `services/transcription.py`에 집중
- 화자 분리: `pyannote-audio` 로컬 처리 후 Whisper 결과와 병합
- 오디오 파일: R2 업로드 후 URL 참조 (로컬 저장 금지)

---

## 6. 벡터 임베딩 & RAG 검색

- 임베딩 모델: OpenAI `text-embedding-3-small` (1536차원)
- 검색 방식: 하이브리드 검색 (Full-text + Vector + RRF)
- 청킹: 계층적 청킹 (회의→화자 구간→문단, 부모 참조)
- 캐시: Semantic Cache (유사 질문 즉시 반환)
- 저장/검색: `services/embedding.py`, `rag/` 도메인에 집중

> 상세 설계: `docs/architecture/rag-pipeline.md` 참조

---

## 7. Cloudflare R2

```python
import boto3
from src.core.config import settings

def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id.get_secret_value()}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
        region_name="auto",
    )
```

---

## 8. 스트리밍 응답 (RAG 채팅)

```python
from fastapi.responses import StreamingResponse

@router.post("/rag/ask")
async def ask_project(
    data: AskRequest,
    service: RAGService = Depends(get_rag_service),
):
    async def generate():
        async for chunk in service.stream_answer(data):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## 9. Kairos 도메인 폴더 구조

```
backend/src/
├── inbox/          # Inbox 적재 + 분류
├── para/           # PARA CRUD + N:M 링크
├── meetings/       # 회의 인제스트, STT, AI 파이프라인
├── actions/        # 액션 아이템
├── notes/          # Tiptap 노트
├── rag/            # RAG 검색 + Claude 답변
├── auth/           # Clerk JWT 검증
├── common/
│   ├── database.py
│   ├── exceptions.py
│   ├── r2.py
│   ├── prompts.py
│   └── pagination.py
└── core/
    └── config.py
```
