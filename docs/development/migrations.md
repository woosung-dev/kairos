# 마이그레이션 (Alembic)

## 1. 위치

```
apps/api/alembic.ini          script_location = %(here)s/alembic  (앱 루트 상대)
apps/api/alembic/env.py       SQLModel.metadata 등록 + URL 결정
apps/api/alembic/versions/    리비전 24개 (2026-08-16 기준)
```

## 2. 로컬 절차

```bash
mise run be-migrate                                    # = alembic upgrade head
cd apps/api && uv run alembic revision --autogenerate -m "add action_items table"
cd apps/api && uv run alembic downgrade -1         # ★ §5 를 먼저 읽어라
```

`models.py` 를 바꾸면 **같은 PR 에 리비전을 반드시 포함**한다 (`apps/api/CONTEXT.md` §8).
`tests/integration/test_alembic_upgrade.py` 가 빈 DB 에 `upgrade head` 를 돌려
SQLModel metadata 와의 schema diff 가 0 인지 검사한다 — 리비전을 빠뜨리면 여기서 잡힌다.

## 3. ★ env.py 는 `.env` 전체를 요구한다

`alembic/env.py:58-60` 은 `sqlalchemy.url` 이 비어 있을 때 `get_settings()` 를 호출한다.
`get_settings()` 는 Settings 모델 전체를 검증하므로 **`DATABASE_URL` 만 있어서는 부팅하지 못한다** —
Gemini / OpenAI / R2 키가 전부 필요하다 (CI job 이 fake 값을 전부 주입하는 이유).

URL 을 직접 주입하면 이 경로를 우회할 수 있다:

```python
alembic_cfg.set_main_option("sqlalchemy.url", async_url)  # env.py 가 get_settings() 를 건너뛴다
```

## 4. 프로덕션 적용

앱 기동과 **분리된 one-shot 컨테이너**가 적용한다.

```
deploy/oci/docker-compose.prod.yml  service: migrate  (command: ["migrate"], restart: no)
apps/api/docker-entrypoint.sh       role migrate → exec alembic upgrade head
```

분리한 이유: 앱 기동 시점에 마이그레이션을 돌리면 실패가 **crash-loop** 로 번진다
(2026-06-30 프로덕션 인시던트). one-shot 은 실패해도 API 컨테이너를 죽이지 않는다.

## 5. ★ downgrade 를 실행하지 않는다

- 프로덕션에 자동 롤백 경로는 **없다.** `mise run deploy-rollback` 은 **이미지만** 되돌리며 스키마는 그대로다
- 로컬에서도 위험하다 — `apps/api/.env` 의 `DATABASE_URL` 이 **공유 dev DB** 를 가리키기 때문에,
  워크트리에서 downgrade 를 돌리면 메인 체크아웃과 다른 워크트리에 그대로 영향이 간다
  (2026-07-30 dev DB 전 삭제 사고)
- **미머지 브랜치의 리비전을 공유 DB 에 올리지 않는다.** 올리면 다른 브랜치의 `upgrade head` 가
  존재하지 않는 리비전을 부모로 찾아 멈춘다
- dev/prod DB 분리는 아직 미해결 (BL-OCI-6)

## 6. 컬럼 삭제는 2단계 배포

`apps/api/CONTEXT.md` §8 — 사용 중단(코드에서 참조 제거) → **다음** 배포에서 컬럼 삭제.
한 번에 하면 구 이미지가 도는 롤아웃 창에서 500 이 난다.

## 7. ★ 컬럼 **타입 변경**은 2단계 배포의 예외다

2단계 배포 규칙은 **타입을 유지하는** 경우 전용이다. 타입을 바꾸면 의존 인덱스의
operator class 호환성을 먼저 확인해야 한다 — PostgreSQL 이 `ALTER COLUMN TYPE` 자체를 거부한다.

> 실제 사고 (ADR-020): `vector` → `halfvec` ALTER 를 기존 ivfflat 인덱스(`vector_cosine_ops`)가 차단.
> `DatatypeMismatchError: operator class "vector_cosine_ops" does not accept data type halfvec`

절차:

1. `SELECT indexname, indexdef FROM pg_indexes WHERE tablename = '<table>'`
2. 호환 불가면 **같은 revision 안에서** 구 인덱스를 drop (별도 PR 로 미루면 upgrade 가 아예 안 돈다)
3. downgrade 에 구 타입 + 구 인덱스 양방향 복구를 남긴다

## 8. pgvector 리비전의 헌법 구속

벡터 컬럼을 다루는 리비전은 `CONTEXT-MAP.md` 불변식에 묶여 있다.

- **I-20** — 컬럼 타입 `halfvec(1536)` 고정. `Vector(1536)` 금지. 인덱스는 HNSW(`m=16, ef_construction=64`), ivfflat 금지
- **I-21** — 검색 세션 변수 강제 (`hnsw.ef_search` 등)

재인덱싱 절차는 [`../operations/pgvector-reindex.md`](../operations/pgvector-reindex.md).
