# Backend Rules (FastAPI + SQLModel)

> ★**본 파일은 코드 스켈레톤 + 스택 함정만 소유한다.**
> `B-NN`·`I-NN` 이 붙은 **불변식은 [`CONTEXT.md`](CONTEXT.md) §5 / `/CONTEXT-MAP.md` 소유이며 여기 재진술하지 않는다.**
> 충돌하면 CONTEXT 가 맞다. 규칙을 추가하고 싶으면 여기가 아니라 `CONTEXT.md` §5 에 `B-NN` 으로 넣어라 —
> 두 곳에 같은 규칙을 쓰는 순간 다시 드리프트가 시작된다 ([ADR-029](../../docs/adr/029-ai-rules-relocation.md)).
>
> 프로젝트 전역 규칙은 `/AGENTS.md`. 본 문서는 루트를 **덮어쓰지 않고 보강만** 한다.
> 이전 이력: 구 `.ai/stacks/fastapi/backend.md` (2026-08-15 ADR-029).

---

## 1. Tech Stack

| 항목            | 기술                                                                  |
| --------------- | --------------------------------------------------------------------- |
| Framework       | FastAPI (100% Async)                                                  |
| ORM             | SQLModel + SQLAlchemy 2.0 (`asyncpg`)                                 |
| Validation      | Pydantic V2 + `pydantic-settings`                                     |
| Package Manager | `uv`                                                                  |
| Database        | PostgreSQL 17 + pgvector 0.8 (HNSW + halfvec, ADR-020)                |
| Auth            | Better Auth 발급 JWT 를 JWKS 로 검증 (ADR-031)                        |
| Storage         | Cloudflare R2 (`aioboto3`)                                            |
| AI              | Gemini `gemini-3.1-flash-lite` (`google-genai` SDK, ADR-019 Phase B)  |
| 배포            | **Oracle Cloud A1 단일 VM + Cloudflare Tunnel** (ADR-028)             |

★DB 는 2026-08-14 부터 **오라클 셀프호스팅**이다 (Neon 은 백업으로 보존). 관측은 `docker logs` —
Sentry 는 ADR-028 로 제거됐다 (ADR-021 Superseded).

---

## 2. 설정 접근

설정 접근은 **`get_settings()`** 뿐이다 (`@lru_cache`).
★`from src.core.config import settings` 같은 **모듈 레벨 싱글턴은 존재하지 않는다** — import 하면 ImportError.

```python
from src.core.config import get_settings

settings = get_settings()
api_key = settings.google_api_key.get_secret_value()
```

- NEVER — 환경 변수·API 키·시크릿을 코드에 하드코딩
- NEVER — `.env.example` 에 없는 환경 변수를 코드에서 참조
- Secret 타입·Pydantic V2 패턴·async 규약은 `CONTEXT.md` §5 (B-9 / B-11) 소유

### ★`session.exec()` 는 금지가 아니다

옛 규칙(`.ai/stacks/fastapi/backend.md` §2)이 「`session.exec()` 절대 금지」라고 썼으나
**Sprint 20 BL-054 로 정책이 뒤집혔고 코드는 이미 exec 를 표준으로 쓴다.**
어느 쪽을 쓸지는 `CONTEXT.md` §5 **B-10 의 5카테고리 allowlist** 가 정한다 — 판단이 필요하면 **B-10 을 열어라.**
(여기에 표를 복사하지 않는 이유 = 위 헤더의 비-재진술 규약)

---

## 3. Architecture (도메인 모듈러 — Router / Service / Repository)

레이어 불변식(AsyncSession 보유·`workspace_id` 필터·크로스 도메인 경계)은
`CONTEXT.md` §3 + §5 (B-1 / B-2 / B-3) 소유다. **여기서는 그 형태를 코드로만 보여준다.**

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

★`Depends()` 조립은 **`dependencies.py` 에서만** 한다. `service.py`/`repository.py` 에 `Depends` import 금지.

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

### 크로스 레포지토리 트랜잭션

여러 Repository가 하나의 트랜잭션으로 묶여야 할 때 **동일 session**을 공유한다.
개별 Repository에서 commit하지 않고, **조율하는 Service에서 한 번만 commit**한다.

```python
# dependencies.py — 동일 session을 여러 repo에 주입
async def get_order_service(
    session: AsyncSession = Depends(get_async_session),
) -> OrderService:
    return OrderService(
        order_repo=OrderRepository(session),
        payment_repo=PaymentRepository(session),  # 동일 session
    )

# service.py — 마지막에 한 번만 commit
class OrderService:
    def __init__(self, order_repo: OrderRepository, payment_repo: PaymentRepository):
        self.order_repo = order_repo
        self.payment_repo = payment_repo

    async def create_order_with_payment(self, data: CreateOrderRequest):
        order = await self.order_repo.save(Order(...))
        payment = await self.payment_repo.save(Payment(...))
        await self.order_repo.commit()  # 한 번만 — 같은 session이므로 둘 다 커밋됨
        return order
```

★크로스 **도메인**은 이 패턴으로 끝나지 않는다 — `pipeline_service.py` orchestrator 경유가 강제다
(`CONTEXT.md` B-3, ADR-014).

---

## 4. Gemini API 패턴

- LLM 구현체는 `BaseLLMService` 인터페이스로 추상화
- 모든 Gemini 호출은 `services/ai_processing.py`에 집중
- 모델 고정·프롬프트 중앙화는 `CONTEXT.md` §5 (B-4 / B-6) 소유

```python
from google import genai
from src.core.config import get_settings

client = genai.Client(
    api_key=get_settings().google_api_key.get_secret_value()
)
```

### JSON 파싱 안전 처리

```python
import json, re

def parse_json_response(text: str) -> dict:
    clean = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini 응답 JSON 파싱 실패: {e}\n원본: {text}")
```

---

## 5. Cloudflare R2

클라이언트 선택 규칙은 `CONTEXT.md` B-13 소유. 여기서는 **성능 함정 하나**만 다룬다.

★**메서드마다 client 를 새로 만들지 마라.** 세션/커넥션 재수립에 호출당 수십 ms 가 든다 (PERF-1).
`AsyncExitStack` 으로 **lazy 생성 후 재사용**하고 앱 종료 시 lifespan 에서 `close()` 한다.
정본 구현 = `src/common/r2.py`.

```python
class R2Service:
    def __init__(self) -> None:
        self._session = aioboto3.Session()
        self._client = None
        self._exit_stack: AsyncExitStack | None = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self):
        """공유 client lazy 초기화 (동시 진입 대비 lock — 중복 생성 누수 방지)."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    settings = get_settings()
                    self._exit_stack = AsyncExitStack()
                    self._client = await self._exit_stack.enter_async_context(
                        self._session.client(
                            "s3",
                            endpoint_url=self._get_endpoint_url(),
                            aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
                            aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
                            region_name="auto",
                        )
                    )
        return self._client
```

---

## 6. SSE 스트리밍 응답

응답 타입 규칙은 `CONTEXT.md` B-14 소유.

★함정 — `sse_starlette` 가 `text/event-stream` 헤더와 `data:` 포맷을 **내부적으로** 처리한다.
generator 는 event 를 **그대로 yield** 하면 된다. `f"data: {chunk}\n\n"` 수기 조립은 이중 인코딩이다.

```python
# rag/router.py
from sse_starlette.sse import EventSourceResponse

@router.post("/ask")
async def ask_rag(
    workspace_id: uuid.UUID,
    data: RagAskRequest,
    member: WorkspaceMember = Depends(require_viewer),
    pipeline: RagPipelineService = Depends(get_rag_pipeline_service),
):
    async def event_generator():
        async for event in pipeline.ask(question=data.question, workspace_id=workspace_id, ...):
            yield event

    return EventSourceResponse(event_generator())
```

---

## 7. pgvector 함정

모델·차원·청킹은 `CONTEXT.md` B-5, 컬럼 타입·인덱스는 `/CONTEXT-MAP.md` I-20/I-21 소유.
아래 둘은 어디에도 없는 **런타임 함정**이라 여기 둔다.

### ★`HalfVector` 는 `numpy.ndarray` 가 아니다 (iterable 아님)

`Vector` 컬럼은 `numpy.ndarray` 를 돌려주지만 `HALFVEC` 은 `pgvector.halfvec.HalfVector` **객체**를 돌려준다.
`[float(x) for x in value]` 같은 iteration 은 `TypeError: HalfVector object is not iterable` 로 죽는다.

```python
raw = cached.embedding
values = raw.to_list() if hasattr(raw, "to_list") else [float(x) for x in raw]
```

> Sprint 16 Stage 5 회귀 (2026-05-15) — `memory/repository.py:get_query_embedding_cache`

### ★asyncpg 에서 `:name::type` 캐스트 표기 금지

asyncpg 는 `:` 를 파라미터 prefix 로 먼저 인식해서 `::uuid` 의 `:uuid` 를 **다른 파라미터로 오인**한다
(`PostgresSyntaxError: syntax error at or near ":"`). 표준 SQL `CAST(... AS ...)` 로 쓴다.

```python
# ✗ SELECT :uid::uuid
# ✓ SELECT CAST(:uid AS uuid)
```

> Sprint 16 Stage 5 회귀 (2026-05-15) — `tests/embeddings/test_halfvec_migration.py`

---

## 8. 비동기 장기 작업 패턴

`202 Accepted` + polling 규약은 `CONTEXT.md` B-7 소유. 여기서는 스켈레톤과 세션 수명 함정만 둔다.

```python
from fastapi import BackgroundTasks

@router.post("/process", status_code=202)
async def start_processing(
    data: ProcessRequest,
    background_tasks: BackgroundTasks,
    service: ProcessService = Depends(get_process_service),
):
    task_id = await service.create_task(data)
    background_tasks.add_task(service.run_pipeline, task_id)
    return {"task_id": task_id, "status": "processing"}


@router.get("/process/{task_id}/status")
async def get_status(
    task_id: str,
    service: ProcessService = Depends(get_process_service),
):
    return await service.get_task_status(task_id)
```

### ★BackgroundTask 에 요청 `AsyncSession` 을 넘기지 마라

요청 세션은 응답이 나가는 순간 닫힌다. 백그라운드 작업은 그 뒤에도 돌기 때문에
**`session_factory` 를 주입받아 작업 안에서 새 session 을 연다.**
정본 패턴 = `meetings/pipeline_service.py`.

> Sprint 9 오디오 파이프라인 사고 (BG 세션 수명) — 요청 세션 주입 시 침묵 실패

---

## 9. DB 마이그레이션 (Alembic)

```bash
alembic revision --autogenerate -m "add action_items table"   # 생성
alembic upgrade head                                          # 적용
alembic downgrade -1                                          # 롤백
```

마이그레이션 의무·2단계 배포 원칙은 `CONTEXT.md` §8 소유.

### ★컬럼 **타입 변경**은 2단계 배포의 예외다

`CONTEXT.md` §8 의 2단계 배포는 **컬럼 타입을 유지하는** 경우 전용이다.
타입을 바꾸는 마이그레이션은 **의존 인덱스의 operator class 호환성을 먼저 확인**해야 한다 —
PG 가 `ALTER COLUMN TYPE` 자체를 거부한다.

> 실제 사고 (ADR-020): `vector` → `halfvec` ALTER 를 기존 ivfflat 인덱스(`vector_cosine_ops`)가 차단.
> `DatatypeMismatchError: operator class "vector_cosine_ops" does not accept data type halfvec`

- 사전 확인: `SELECT indexname, indexdef FROM pg_indexes WHERE tablename = '<table>'`
- 호환 불가면 **동일 revision 안에서** 구 인덱스를 drop 한다 (별도 PR 로 미루면 upgrade 가 안 돈다)
- downgrade 에서 구 타입 + 구 인덱스를 양방향 복구해 안전망을 남긴다

---

## 10. 스크립트 (`apps/api/scripts/`)

목록·안전망은 `CONTEXT.md` §9 가 정본. 아래 둘은 실행 함정이다.

### ★lifespan 밖에서 도는 CLI 는 engine 을 직접 초기화한다

FastAPI app 은 lifespan 이 `init_engine()` 을 부르므로 router/service 는 이미 초기화된 factory 를 쓴다.
그러나 bench/spike/probe 같은 **단독 CLI 는 lifespan 을 안 거친다.**
`src.common.database` 에 `async_session_factory` 라는 public 심볼은 **없다** (private `_async_session_factory`).

```python
from src.common.database import get_session_factory, init_engine
from src.core.config import get_settings

init_engine(get_settings().database_url)
session_factory = get_session_factory()
```

> Sprint 16 Stage 5 (2026-05-15) — `scripts/bench_vector_search.py` 첫 실행 ImportError

### ★장기 실행 CLI 는 출력 버퍼링을 꺼라

Python 은 stdout 이 pipe 일 때 block buffering 을 쓴다. `tee` 로 리다이렉트하면 수 분간 0 bytes 다.

```bash
PYTHONUNBUFFERED=1 uv run python -u scripts/bench_vector_search.py | tee /tmp/bench.txt
```

---

## 11. 백엔드 폴더 구조

```
apps/api/src/
├── [domain]/       # 도메인별 모듈 (router/service/repository/schemas/models)
├── auth/           # Bearer JWT 검증 + RBAC
├── common/
│   ├── database.py      # init_engine / get_session_factory
│   ├── exceptions.py
│   ├── r2.py
│   ├── prompts.py
│   ├── visibility.py    # visibility 규칙 SSOT (B-15, arch gate 강제)
│   ├── fk_guard.py      # secondary FK workspace 검증 (B-15)
│   └── pagination.py    # build_page / empty_page (B-15)
└── core/
    └── config.py        # get_settings() (@lru_cache)
```

도메인 모듈 전체 목록 + 각 책임은 [`CONTEXT.md`](CONTEXT.md) §4 표가 정본이다.
