# Kairos API (FastAPI)

Kairos 의 백엔드 애플리케이션. REST + SSE, AI 파이프라인 조율(STT / Gemini / 임베딩), DB 영속화.
OCI 단일 VM 위 컨테이너로 배포된다 ([ADR-028](../../docs/adr/028-oci-selfhosting.md) · [ADR-030](../../docs/adr/030-apps-api-rename.md)).

## 실행

명령은 루트 `justfile` 이 단일 진입점이다.

```bash
just install      # uv sync --frozen
just be-migrate   # alembic upgrade head
just be-dev       # uvicorn :8000
just be-test      # pytest (CI 와 문자 동일 호출)
just contracts    # OpenAPI 계약 + FE 타입 재생성
```

환경변수는 `.env.example` → `.env`. 전체 매트릭스는
[`docs/development/secrets.md`](../../docs/development/secrets.md), 셋업 전체는
[`docs/development/getting-started.md`](../../docs/development/getting-started.md).

## 구조

```
src/
├── main.py            FastAPI app + 라우터 조립
├── core/              config(get_settings) · lifespan
├── common/            visibility · pagination · prompts · r2 · fk_guard · audit/promote
├── services/          외부 API wrapper (transcription · ai_processing · ai_resilience)
└── <domain>/          router · service · repository · schemas · models · dependencies · exceptions
                       (+ cross-domain 이 필요한 도메인만 pipeline_service.py)
```

도메인 목록과 각 책임은 [`CONTEXT.md`](CONTEXT.md) §4, 전체 트리는
[`docs/architecture/directory-map.md`](../../docs/architecture/directory-map.md).

## ★ 운영자가 알아야 하는 제약

- **`uvicorn --workers` 를 1 에서 늘리지 않는다.** `services/ai_resilience.py` 의 circuit breaker 와
  `auth` 의 JWT/User 캐시가 **in-process 싱글턴**이라 멀티워커에서 상태가 파편화된다
- **`BackgroundTasks` 는 재시도가 없다.** 프로세스가 교체되면 진행 중이던 회의가 중간 상태로 남는다 →
  배포 전 `just deploy-preflight` 필수. 복구 절차는
  [런북](../../docs/operations/runbooks/stuck-pipeline.md)
- 마이그레이션은 앱 기동과 분리된 one-shot 컨테이너가 적용한다 (crash-loop 방지)

## 규칙

- 스택 함정 + 코드 스켈레톤: [`AGENTS.md`](AGENTS.md)
- 불변식 (B-NN) + 레이어 + 도메인 표: [`CONTEXT.md`](CONTEXT.md)
- 도메인 헌법: [`/CONTEXT-MAP.md`](../../CONTEXT-MAP.md)
- 테스트 게이트: [`docs/development/testing.md`](../../docs/development/testing.md)
