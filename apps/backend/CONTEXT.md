<!-- Kairos 백엔드 전역 헌법 — FastAPI + SQLModel + 도메인 모듈러 + 오케스트레이터 -->

# Backend CONTEXT (전역)

> 루트 헌법: `/CONTEXT-MAP.md` 우선. 도메인별 상세는 `apps/backend/src/<domain>/CONTEXT.md`.

---

## 1. 책임

- REST API (FastAPI, async) + SSE 스트리밍 (RAG)
- AI 파이프라인 조율 (STT / Gemini / OpenAI 임베딩)
- DB 영속화 (PostgreSQL 17 + pgvector — 2026-08-14 부터 오라클 셀프호스팅, Neon 은 백업. ADR-028)
- 외부 스토리지 (Cloudflare R2)
- Clerk JWT 검증

## 2. 비책임

- UI / 렌더링 (FE 책임)
- 외부 인증 발급 (Clerk SaaS)

---

## 3. 레이어

```
Router    (router.py)         HTTP I/O — 입력 검증 + 응답 직렬화 (10줄 이하 가이드)
   ↓
Service   (service.py)        비즈니스 로직 — 단일 도메인 한정. AsyncSession import 금지
   ↓
Repository (repository.py)    데이터 접근 — AsyncSession 보유 유일층. commit()은 service 요청으로만
   ↓
Models    (models.py)         SQLModel 테이블

Pipeline Service (pipeline_service.py)  ← 크로스 도메인 오케스트레이터 (도메인 안)
External Service (services/*.py)        ← 외부 API wrapper (transcription, ai_processing)
```

---

## 4. 도메인 모듈 (Sprint 24 Wave 2 memory 행 명시 추가, 2026-07-01 arch-verification — feedback 행 + auth/notes/upload/workspaces CONTEXT.md 경로 정정)

| 모듈 | CONTEXT.md | 책임 요약 |
|---|---|---|
| auth | `src/auth/CONTEXT.md` | Clerk JWT 검증 + User 매핑. **prefix 예외**: `/api/v1/users` |
| workspaces | `src/workspaces/CONTEXT.md` | Workspace + WorkspaceMember + WorkspaceInvite + `inbox_threshold` |
| projects | `src/projects/CONTEXT.md` | Project CRUD, MeetingProjectLink, ProjectMember (Sprint 6 L-6), visibility 권한 분기 (Sprint 6 BE-T8), 태그, 인사이트 |
| inbox | `src/inbox/CONTEXT.md` | Inbox 적재 + AI 분류 추천 |
| meetings | `src/meetings/CONTEXT.md` | Meeting 인제스트, STT, 파이프라인 (orchestrator 표준 패턴) |
| notes | `src/notes/CONTEXT.md` | Tiptap Note CRUD + NotePipelineService(embedding 위임 + 권한 검증, Sprint 6 ADR-014 옵션 A) + Sprint 24 BL-064 promote chunk 0 BG re-embedding |
| actions | `src/actions/CONTEXT.md` | ActionItem CRUD (nullable 부모) |
| feedback | `src/feedback/CONTEXT.md` | dogfooding 피드백 수집 (user-level, workspace nullable). **prefix 예외**: `/api/v1/feedback` |
| upload | `src/upload/CONTEXT.md` | R2 업로드 (presigned URL, aioboto3) |
| embeddings | `src/embeddings/CONTEXT.md` | EmbeddingChunk + SemanticCache 저장/검색 (pgvector HNSW + halfvec). cross-domain shared service — 호출은 호출자 도메인 `pipeline_service.py` 경유 (ADR-014) |
| memory | `src/memory/CONTEXT.md` | Sprint 15 Recall-first wedge — MemoryItem capture(text+voice) / Distill / Recall / Promote. Sprint 24 Wave 2 BL-006: `MemoryPipelineService.save_memory_chunk` 가 embeddings 호출 격리 (헌법 §4.2) |
| rag | `src/rag/CONTEXT.md` | RAG 6-Layer + Gemini 답변 (SSE 스트리밍) |
| onboarding | `src/onboarding/CONTEXT.md` | User.onboarding_step (0~4) lifecycle — workspaces/projects/meetings/rag 가 hook 호출 (Sprint 22 OBN-02) |
| common | — | database / r2 / pagination / exceptions / prompts / **promote_models** + **promote_helpers** (Sprint 23 D4 — ItemPromotionAudit 4 도메인 audit + validate_promote_target/build_item_promotion_audit utility) |
| core | — | config (pydantic-settings) |

> `services/` 폴더는 외부 API wrapper: `transcription.py` (Whisper+pyannote), `ai_processing.py` (Gemini).

---

## 5. 핵심 불변식 (전역)

> 헌법 §6과 정합. 백엔드 특화 보강 포함.

| # | 불변식 | 강제 |
|---|---|---|
| B-1 | **AsyncSession은 Repository만 보유** — Service에 `from sqlalchemy.ext.asyncio import AsyncSession` 금지 | code review |
| B-2 | **모든 Repository는 `workspace_id` 필터 강제** (멀티테넌시) | `.where(... .workspace_id == workspace_id)` |
| B-3 | **크로스 도메인 트랜잭션은 `pipeline_service.py` 또는 `services/`** — 같은 session 공유, dependencies.py에서 조립. Repository 직접 read는 허용 (CONTEXT-MAP §4.2 #1). **embeddings·ai_processing·transcription = cross-domain shared service** — 직접 호출은 orchestrator 경계 내부에서만 (Sprint 6 ADR-014, 헌법 결정 #1) | code review |
| B-4 | **AI 모델 고정**: Gemini `gemini-3.1-flash-lite` (ADR-019 Phase B, 2026-05-15 swap. 이전: `gemini-2.5-flash` EOL 2026-06-17) | `core/config.py` |
| B-5 | **임베딩 모델 고정**: OpenAI `text-embedding-3-small` (1536d), 청킹 512토큰/오버랩 50토큰 | `embeddings/service.py` |
| B-6 | **프롬프트 중앙 관리**: `common/prompts.py` 상수만, 인라인 프롬프트 금지 | code review |
| B-7 | **장기 작업**: `BackgroundTasks` + `202 Accepted` + `GET .../status` polling | `meetings/router.py` 패턴 |
| B-8 | **트랜잭션 commit 원칙**: 같은 BackgroundTask 내 단일 commit이 이상. 진행 보고용 status 전이 commit은 현재 예외 (현재 부채 §7 D-9 — 단일 commit 리팩토링 vs 헌법 명시 결정 보류) | `pipeline_service.py` |
| B-9 | **Pydantic V2**: `.dict()` 대신 `.model_dump()`, `@root_validator` 대신 `@model_validator(mode="after")`, `BaseSettings`는 `pydantic_settings`에서 import | code review |
| B-10 | **100% async + SQLModel typed query (Sprint 20 BL-054 갱신, 2026-05-18)**: SQLModel `AsyncSession` + manifest 기반 exec/execute allowlist. **(G1)** typed scalar select → `(await session.exec(stmt)).all() / .first() / .one_or_none() / .one()`. **(G2/G4)** raw `text()` / multi-column tuple / SET LOCAL / healthcheck → `await session.execute(text(...))` 유지 (SM exec 가 text/dialect 미수용). **(G3-convert)** DML w/o rowcount → `await session.exec(update/delete(...))`. **(G3-keep)** DML w/ `.rowcount` → `await session.execute()` 유지 (rowcount contract). **(G3-keep-dialect)** `pg_insert(...).on_conflict_do_nothing()` → `await session.execute()` 영구 유지 (SQLModel 미 re-export). N+1 방지 `options(selectinload(...))` 동일. (manifest 는 위 G1~G3-keep-dialect 5 카테고리 그대로 — Sprint 26 부터 dev-log/notes 폐지) | code review |
| B-11 | **Secret은 `SecretStr`**: 사용 시 `.get_secret_value()` | `core/config.py` |
| B-12 | **에러는 도메인별 `exceptions.py` + 전역 핸들러** (`common/exceptions.py`) | 도메인 모듈마다 |
| B-13 | **R2 클라이언트는 aioboto3** (boto3 동기 사용 금지). 불가피한 경우 `run_in_executor` | `common/r2.py` |
| B-14 | **SSE 스트리밍 응답**: `EventSourceResponse` (`sse_starlette.sse`) — 내부적으로 `text/event-stream` 헤더, `data:` 포맷. `StreamingResponse` 직접 사용하지 않음 (RAG에서 사용) | `rag/router.py:6,40` |
| B-15 | **read-path 공용 규약 SSOT (2026-07-13)**: ① visibility 규칙 = `common/visibility.py` 만 (arch gate 강제) ② 페이지 응답 조립 = `common/pagination.py` `build_page`/`empty_page` (`"hasNext"` 손조립 금지, list/count 는 동일 필터 계약) ③ secondary FK workspace 검증 = `common/fk_guard.py` `require_in_workspace` (예외 타입 매핑은 도메인 소유) | `tests/architecture/test_visibility_single_source.py` + code review |

---

## 6. API 컨벤션

- **Prefix 강제 (I-13)**: `/api/v1/workspaces/{workspace_id}/<resource>`
  - 예외: `auth → /api/v1/users`, `workspaces 루트 → /api/v1/workspaces` (워크스페이스 자체 CRUD)
  - 리소스 이름은 케밥 케이스 (`action-items`, 단일어는 그대로 `inbox`/`meetings`/`notes`)
- Status code: 생성 201, 비동기 인제스트 202, 삭제 204
- 페이지네이션: `common/pagination.py` 표준
- 인증: 모든 엔드포인트는 Clerk JWT 검증 (auth dependency)
- **응답 직렬화 (I-16)**: DB snake_case → API camelCase Pydantic alias 변환 (`schemas.py` 책임)
- 권한: `require_admin` / `require_member` 데코레이터 또는 dependency로 명시 (특히 archive/delete)

---

## 7. 환경

- Python 3.12+, FastAPI, SQLModel, asyncpg, pgvector
- 패키지 매니저: `uv`
- 비동기 100% (sync 코드 금지)
- 외부: Clerk, Gemini, OpenAI, Whisper API, Cloudflare R2 (DB 는 오라클 VM 셀프호스팅 — ADR-028)
- 상세 규칙: [`AGENTS.md`](AGENTS.md) (같은 디렉터리 — `CLAUDE.md` 가 본 파일과 함께 자동 로드, ADR-029)

---

## 8. 마이그레이션 (Alembic)

- `models.py` 변경 시 반드시 Alembic 마이그레이션 생성 + 커밋 포함
- 프로덕션 배포 entrypoint에서 `alembic upgrade head` 자동 실행
- 컬럼 삭제는 2단계 배포 (사용 중단 → 다음 배포에서 삭제)

---

## 9. 스크립트 (apps/backend/scripts/)

운영 전용 단독 실행 스크립트. router/service/repository 아닌 독립 entry point.

| 파일 | 목적 | 호출 패턴 |
|---|---|---|
| `dogfood_smoke.py` | 일일 dogfood 자동 검증 (JWT 직접 입력 패턴) | manual |
| `reindex_vectors.py` | EmbeddingService 통한 청크 재인덱싱 | manual |
| `samples/` | Sprint 15 Day 0 음성 sample (gitignore) | manual upload |
| `seed_qa_fixtures.py` | Multi-Agent QA 시드 fixture 생성 + cleanup (Sprint 18 → 19) | `--env <credentials.env> --out <fixtures.json>` / `--dry-run-cleanup` / `--cleanup` |

**seed_qa_fixtures.py 안전망**:
- WS_PREFIX 매칭 (`WS-QA-...`) — cleanup 대상 식별
- `KAIROS_FOUNDER_CLERK_ID` ENV — founder 워크스페이스 매칭 시 ABORT
- User row 보존 (Clerk dashboard 수동 정리)
- R2 object 별도 정리

---

## 10. STT 파이프라인 (Sprint 24 Wave 2 갱신 — BL-T2-003 closure)

- **entry**: `services/transcription.py:TranscriptionService.transcribe_with_chunking(audio_bytes, filename)` — pipeline `meetings/pipeline_service.py` 가 호출.
- **임계값**: `chunked_transcription.CHUNK_SECONDS = 3600` (1시간).
- **1hr 이하**: 단일 Whisper API 호출 (`TranscriptionService.transcribe` 경로 그대로 — Whisper `whisper-1`, verbose_json, segment timestamps).
- **1hr 초과**: `services/chunked_transcription.py:transcribe_chunked` —
  1. `_ffmpeg_probe_duration` 으로 duration 측정
  2. `_ffmpeg_split` 으로 1hr chunk + 5초 overlap 분할 (chunk 경계 문장 잘림 방지)
  3. `asyncio.gather` 로 chunk 병렬 Whisper 호출
  4. `_merge_with_offset` 으로 chunk index 기반 offset (i * 3600) 적용 + 양쪽 overlap 영역 동일 text segment dedup
- BL-T2-003 closure (Sprint 24 Wave 2 T-N+4, 2026-05-20). production 4hr+ recording 처리 차단 해소.
