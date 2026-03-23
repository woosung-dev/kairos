# 🚀 Backend Rules (FastAPI + SQLModel + AI Stack)

Kairos 백엔드 개발의 전역 설정이다.
코드를 생성하거나 수정할 때 반드시 아래의 최신 문법과 아키텍처 규칙을 준수한다.

---

## 1. Tech Stack (확정)

| 항목            | 기술                                   |
| --------------- | -------------------------------------- |
| Framework       | FastAPI (100% Async)                   |
| ORM             | SQLModel + SQLAlchemy 2.0 (`asyncpg`)  |
| Validation      | Pydantic V2 + `pydantic-settings`      |
| Package Manager | `uv`                                   |
| Database        | PostgreSQL on Neon + pgvector 확장     |
| Auth            | Clerk JWT 검증                         |
| Storage         | Cloudflare R2 (boto3 S3 호환 API)      |
| AI              | Anthropic Claude API (`anthropic` SDK) |
| STT             | OpenAI Whisper API + pyannote-audio    |
| 배포            | GCP Cloud Run + Docker                 |

---

## 2. 🚫 AI가 자주 틀리는 핵심 제약 (Strict Rules)

### Pydantic V2 문법 강제

- `BaseSettings`는 반드시 `pydantic_settings`에서 임포트한다. (pydantic 내부 임포트 금지)
- `.dict()` 대신 `.model_dump()`, `.model_dump_json()`을 사용한다.
- `@root_validator` 대신 `@model_validator(mode="after")`를 사용한다.

### 100% 비동기 SQLModel

- 동기 함수인 `session.exec()` 사용을 절대 금지한다.
- 반드시 `await session.execute(select(...))` 후 `.scalars().all()` 또는 `.scalar_one_or_none()` 패턴을 사용한다.
- 관계 데이터 로딩 시 `options(selectinload(...))` 를 활용하여 N+1 문제를 방지한다.

### SecretStr 활용

- API 키, DB 패스워드 등 민감한 환경 변수는 `SecretStr` 타입으로 선언한다.
- 값 사용 시 반드시 `.get_secret_value()`로 접근한다.

### Clerk JWT 검증

- `fastapi` 의존성 주입으로 Clerk JWT를 검증한다.
- 직접 JWT 구현 금지 — 반드시 Clerk의 공개 키로 검증한다.

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

## 3. Architecture (도메인 모듈러 구조)

**핵심 규칙: AsyncSession은 Repository만 보유한다.**
Service는 AsyncSession을 직접 보유하지 않으며, Repository를 생성자 주입으로 받는다.

### 폴더 구조

```
backend/
└── src/
    ├── inbox/
    │   ├── router.py        # HTTP 요청/응답 전용
    │   ├── service.py       # 비즈니스 로직 (AsyncSession 보유 금지)
    │   ├── repository.py    # DB 접근 전담 (AsyncSession 유일 보유자)
    │   ├── schemas.py       # Pydantic V2 입출력 스키마
    │   ├── models.py        # SQLModel 테이블 매핑
    │   ├── dependencies.py  # Depends() 조립 전용
    │   └── exceptions.py    # 도메인 전용 예외
    ├── para/                # PARA 아이템 CRUD + N:M 링크
    ├── meetings/            # 회의 인제스트, STT, AI 파이프라인
    ├── actions/             # 액션 아이템 관리
    ├── notes/               # Tiptap 노트
    ├── rag/                 # RAG 검색 + Claude 답변
    ├── auth/                # Clerk JWT 검증
    ├── common/
    │   ├── database.py      # AsyncSession 팩토리
    │   ├── exceptions.py    # 전역 예외 핸들러
    │   ├── r2.py            # Cloudflare R2 클라이언트
    │   └── pagination.py
    └── core/
        └── config.py        # pydantic-settings 전역 설정
```

### 레이어 규칙

**Router** — HTTP 요청 수신, 스키마 검증, service 호출, 응답 반환만 담당한다.
DB 접근과 비즈니스 로직 작성을 금지한다. 함수는 10줄 이하로 유지한다.

**Service** — 비즈니스 로직과 트랜잭션 경계만 담당한다.
`AsyncSession` 직접 보유 및 import를 절대 금지한다.
`repository`만 생성자 인자로 받으며, `commit()`은 `repo.commit()`으로 위임한다.

**Repository** — `AsyncSession`을 보유하는 유일한 레이어다. DB 접근만 담당한다.
비즈니스 로직 작성을 금지한다. `commit()`은 service의 요청으로만 실행한다.

**Dependencies** — `Depends()` 조립의 유일한 위치다. `repo → service` 순서로 조립한다.
`service.py`와 `repository.py`에 `from fastapi import Depends` import를 절대 금지한다.

---

## 4. 필수 코드 패턴

```python
# router.py
@router.post("/meetings", response_model=MeetingResponse, status_code=201)
async def create_meeting(
    data: CreateMeetingRequest,
    service: MeetingService = Depends(get_meeting_service),
) -> MeetingResponse:
    return await service.create_meeting(data)


# service.py — AsyncSession import 금지
class MeetingService:
    def __init__(self, repo: MeetingRepository) -> None:
        self.repo = repo

    async def create_meeting(self, data: CreateMeetingRequest) -> MeetingResponse:
        meeting = Meeting.model_validate(data)
        saved = await self.repo.save(meeting)
        await self.repo.commit()
        return MeetingResponse.model_validate(saved)


# repository.py — AsyncSession 유일 보유자, session.exec() 금지
class MeetingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, meeting_id: UUID) -> Meeting | None:
        result = await self.session.execute(
            select(Meeting)
            .where(Meeting.id == meeting_id)
            .options(selectinload(Meeting.action_items))  # N+1 방지
        )
        return result.scalar_one_or_none()

    async def save(self, meeting: Meeting) -> Meeting:
        self.session.add(meeting)
        await self.session.flush()
        return meeting

    async def commit(self) -> None:
        await self.session.commit()


# dependencies.py — repo → service 순서로 조립
async def get_meeting_repository(
    session: AsyncSession = Depends(get_async_session),
) -> MeetingRepository:
    return MeetingRepository(session)

async def get_meeting_service(
    repo: MeetingRepository = Depends(get_meeting_repository),
) -> MeetingService:
    return MeetingService(repo)
```

---

## 5. Kairos AI Pipeline Rules (AI 통합 규칙)

### Claude API 사용 규칙

- 모델명 고정: `claude-sonnet-4-20250514` (임의 변경 금지)
- LLM 구현체는 `BaseLLMService` 인터페이스로 추상화하여 벤더 교체 가능하게 설계
- 모든 Claude 호출은 `services/ai_processing.py`에 집중 관리

```python
# services/ai_processing.py
import anthropic
from src.core.config import settings

client = anthropic.AsyncAnthropic(
    api_key=settings.anthropic_api_key.get_secret_value()
)

async def extract_action_items(transcript: str) -> list[dict]:
    """트랜스크립트에서 액션 아이템을 추출한다."""
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=ACTION_ITEM_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": transcript}],
    )
    # JSON 파싱
    return parse_json_response(response.content[0].text)
```

### LLM Prompt Templates (반드시 이 구조로 관리)

프롬프트는 `src/common/prompts.py`에 상수로 정의한다. 인라인 작성 금지.

```python
# src/common/prompts.py

ACTION_ITEM_SYSTEM_PROMPT = """
당신은 회의 트랜스크립트에서 액션 아이템을 추출하는 전문가입니다.
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

출력 형식:
{
  "action_items": [
    {
      "title": "액션 아이템 제목",
      "assignee": "담당자 이름 (트랜스크립트에서 추론, 없으면 null)",
      "deadline": "YYYY-MM-DD 형식 (언급된 경우만, 없으면 null)",
      "priority": "high | medium | low",
      "status": "todo"
    }
  ]
}
"""

MEETING_SUMMARY_SYSTEM_PROMPT = """
당신은 회의 트랜스크립트를 구조화된 요약으로 변환하는 전문가입니다.
반드시 아래 JSON 형식으로만 응답하세요.

출력 형식:
{
  "summary": "3~5줄 회의 요약",
  "key_decisions": ["결정사항1", "결정사항2"],
  "participants": ["참석자1", "참석자2"],
  "topics": ["주제1", "주제2"]
}
"""

PARA_CLASSIFY_SYSTEM_PROMPT = """
당신은 PARA 방법론 전문가입니다. 회의 요약을 보고 PARA 분류를 추천하세요.

PARA 기준:
- project: 명확한 마감일과 결과물이 있는 업무
- area: 지속적으로 책임져야 하는 영역 (마감 없음)
- resource: 참고 자료, 관심사
- archive: 완료/중단된 항목

반드시 아래 JSON 형식으로만 응답하세요.

출력 형식:
{
  "suggested_type": "project | area | resource | archive",
  "suggested_name": "분류될 PARA 아이템 이름",
  "confidence": 0.0 ~ 1.0,
  "reason": "분류 이유 한 줄"
}
"""

RAG_ANSWER_SYSTEM_PROMPT = """
당신은 프로젝트 지식 베이스를 기반으로 질문에 답변하는 AI 어시스턴트입니다.
아래 컨텍스트(회의록, 노트, 첨부파일 내용)만을 근거로 답변하세요.
컨텍스트에 없는 내용은 "해당 프로젝트 데이터에서 찾을 수 없습니다"라고 답하세요.

컨텍스트:
{context}
"""
```

### JSON 파싱 안전 처리

````python
import json
import re

def parse_json_response(text: str) -> dict:
    """Claude 응답에서 JSON을 안전하게 파싱한다."""
    # 마크다운 코드블록 제거
    clean = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude 응답 JSON 파싱 실패: {e}\n원본: {text}")
````

### STT 파이프라인 규칙

- Whisper API 호출은 `services/transcription.py`에 집중
- 화자 분리는 `pyannote-audio` 로컬 처리 후 Whisper 결과와 병합
- 오디오 파일은 R2에 업로드 후 URL 참조 (로컬 저장 금지)

### pgvector 임베딩 규칙

- 임베딩 차원: `1536` (OpenAI text-embedding-3-small 기준)
- 청킹 전략: 최대 512 토큰, 50 토큰 오버랩
- 모든 임베딩 저장은 `services/embedding.py`에 집중

### Cloudflare R2 사용 규칙

```python
# common/r2.py
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

### 스트리밍 응답 (RAG 채팅)

RAG 채팅 응답은 `StreamingResponse` + 비동기 제너레이터 패턴으로 구현한다.

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

## 6. Formatting (응답 형식)

- 복잡한 로직이나 DB 설계 제안 시 `Mermaid.js`를 사용해 시각화한다.
- 불필요하고 장황한 설명은 생략하고, 코드와 핵심 원리(불릿 포인트) 위주로 답변한다.
