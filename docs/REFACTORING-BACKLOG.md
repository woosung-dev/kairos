# Kairos 리팩토링 백로그

> deepen-modules audit 산출물. 각 BL 항목은 사용자 승인 후 등재.
> 형식: BL-NNN + 우선순위(★) + Sprint 권고

---

## BL-001 — meetings 파이프라인 status commit 단일화 (D-9 장기 개선)

**현 상태:**
`MeetingPipelineService.process_meeting` / `capture_text` 각각 4회 commit (transcribing, duration, analyzing, completed/failed). I-2 예외 조항으로 현재 허용 결정이지만 partial commit state가 존재함.

**목표 인터페이스:**
```python
# status progress 전용 테이블 분리 (예시)
class MeetingProgress(SQLModel, table=True):
    meeting_id: UUID
    step: str          # "transcribing" | "analyzing" | "completed" | "failed"
    created_at: datetime
    metadata: dict     # duration, error_message 등

# pipeline_service.py 는 meeting status를 한 번만 commit
# progress는 별도 insert (non-blocking, fire-and-forget 가능)
async def _report_progress(meeting_id, step, **meta): ...
```

**영향 파일:**
- `backend/src/meetings/models.py` — MeetingProgress 모델 추가
- `backend/src/meetings/pipeline_service.py` — commit 횟수 감소
- `alembic/versions/` — 마이그레이션 추가

**예상 LOC delta:** +50 (모델) / -30 (pipeline_service 단순화)

**Risk:** 🟡 중간 — polling API(`GET /status`)가 새 테이블을 읽도록 변경 필요

**Test harness:** 현 test 3개 존재. 마이그레이션 + polling API 테스트 추가 권고.

**우선순위:** ★★★☆☆

**Sprint 묶음 권고:** 단독 (Sprint 11+, F4 외부 인터뷰 완료 후)

**근거:** deepen-modules audit 2026-05-12 (docs/dev-log/2026-05-12-meetings-deepen.md)

---

## BL-002 — process_meeting / capture_text 공통 로직 추출 ✅ **완료 (Sprint 11 PR3, 2026-05-12)**

**현 상태:**
`MeetingPipelineService`의 두 함수(360 LOC)가 요약 → 액션 추출 → Inbox 적재 → 임베딩 로직을 중복 작성. STT 이후 로직이 거의 동일.

**목표 인터페이스:**
```python
class MeetingPipelineService:
    async def process_meeting(self, meeting_id: UUID) -> None:
        """STT → 분석."""
        segments, duration = await self._transcribe(meeting_id)
        await self._analyze_and_store(meeting_id, segments, duration=duration)

    async def capture_text(self, meeting_id: UUID, transcript_text: str) -> None:
        """텍스트 입력 → 분석."""
        segments = await self._save_text_segment(meeting_id, transcript_text)
        await self._analyze_and_store(meeting_id, segments)

    async def _analyze_and_store(
        self,
        meeting_id: UUID,
        segments: list,
        duration: float | None = None,
    ) -> None:
        """공통: 요약 + 액션 + Inbox + 임베딩."""
        ...
```

**영향 파일:**
- `backend/src/meetings/pipeline_service.py` (360 LOC → ~250 LOC 예상)

**예상 LOC delta:** -100 ~ -110

**Risk:** 🟡 중간 — 파이프라인 핵심 코드, 테스트 3개로 회귀 검증 가능

**Test harness:** test_pipeline.py 3 테스트 존재. `_analyze_and_store` 단위 테스트 추가 권고.

**우선순위:** ★★★☆☆

**Sprint 묶음 권고:** BL-001과 묶어서 (Sprint 11+)

**근거:** deepen-modules audit 2026-05-12 (docs/dev-log/2026-05-12-meetings-deepen.md)

---

## BL-003 — RAG `_enrich_context` N+1 → 배치 쿼리 ✅ **완료 (Sprint 13 PR #21, 2026-05-12)**

**현 상태:**
`RagService._enrich_context()`가 결과 수(최대 10)만큼 `find_chunk_by_id()`를 루프 호출. `EmbeddingRepository`에 `find_chunks_by_ids(ids)` 배치 메서드가 없어 N+1 발생.

```python
# 현재 (N+1)
for r in results:
    parent_id = r.get("parent_chunk_id")
    if parent_id:
        parent = await self.embedding_repo.find_chunk_by_id(parent_id)
```

**목표 인터페이스:**
```python
# embeddings/repository.py 신규 메서드
async def find_chunks_by_ids(self, ids: list[UUID]) -> dict[UUID, EmbeddingChunk]:
    result = await self.session.execute(
        select(EmbeddingChunk).where(EmbeddingChunk.id.in_(ids))
    )
    chunks = result.scalars().all()
    return {c.id: c for c in chunks}

# rag/service.py 변경
parent_ids = [UUID(r["parent_chunk_id"]) for r in results if r.get("parent_chunk_id")]
parents = await self.embedding_repo.find_chunks_by_ids(parent_ids)
enriched = [
    {**r, "parent_text": parents.get(UUID(r["parent_chunk_id"]), None) and parents[UUID(r["parent_chunk_id"])].chunk_text or ""}
    for r in results
]
```

**영향 파일:**
- `backend/src/embeddings/repository.py` — `find_chunks_by_ids` 메서드 추가
- `backend/src/rag/service.py` — `_enrich_context` 배치 호출로 변경

**예상 LOC delta:** +12 (repository) / -8 (service)

**Risk:** 🟢 낮음 — 기존 메서드 제거 없음, 신규 추가만. 배치 반환 타입이 dict라 service 로직 소폭 변경 필요.

**Test harness:** 현 RAG service 단위 테스트 없음 (coverage ~0%). 마이그레이션 시 `test_rag_service.py` 신설 권고 — `_enrich_context` 단위 테스트 2건 (parent 있는 경우 / 없는 경우).

**우선순위:** ★★★★☆

**Sprint 묶음 권고:** 단독 (Sprint 12+). BL-001 meetings 상태 commit 단일화와 독립적. 저위험·고가치라 조기 처리 적합.

**근거:** deepen-modules audit 2026-05-12 Round 1 (docs/dev-log/2026-05-12-rag-deepen.md)

---

## BL-004 — LLM 응답 계약 명시화 (암묵적 JSON 스키마 → Pydantic 검증) ✅ **완료 (Sprint 13 PR #21, 2026-05-12)**

**현 상태:**
`common/prompts.py`에 Gemini 응답 JSON 스키마가 프롬프트 텍스트 안에 문자열로만 존재. `ai_processing.py`는 `parse_json_response()` 결과를 타입 검증 없이 그대로 반환. `pipeline_service.py`는 `actions_data.get("actionItems", [])` 같은 문자열 키 접근에 의존.

프롬프트 스키마 변경 시 (`"key_decisions"` → `"decisions"` 등) 파싱 에러 없이 조용히 빈 값으로 저장됨. co-change 분석으로 발견: `ai_processing.py` 5회 변경 중 3회 이상이 `common/prompts.py` 동시 변경 — 수동으로 키 이름 일치 여부를 확인해온 패턴.

**목표 인터페이스:**
```python
# common/prompts.py 하단에 추가 (또는 common/llm_schemas.py 신설)
from pydantic import BaseModel

class MeetingSummaryResult(BaseModel):
    summary: str
    key_decisions: list[str] = []
    risks_and_issues: list[str] = []
    participants: list[str] = []
    topics: list[str] = []
    next_meeting_agenda: list[str] = []

class MeetingActionsResult(BaseModel):
    actionItems: list[dict] = []
    suggestedProject: dict = {}
    suggestedTags: list[str] = []

# ai_processing.py — 반환 타입 유지, 경계에서 검증 추가
async def summarize(self, transcript: str) -> dict:
    raw = parse_json_response(response.text)
    MeetingSummaryResult.model_validate(raw)   # 스키마 위반 시 즉시 ValidationError
    return raw                                  # caller 변경 없음

async def extract_actions_and_link(self, ...) -> dict:
    raw = parse_json_response(response.text)
    MeetingActionsResult.model_validate(raw)
    return raw
```

**영향 파일:**
- `backend/src/common/prompts.py` — Pydantic 모델 2개 추가 (또는 `common/llm_schemas.py` 신설)
- `backend/src/services/ai_processing.py` — 검증 2줄 추가 (summarize, extract_actions_and_link)

**예상 LOC delta:** +30 (스키마 모델) / +4 (검증 줄)

**Risk:** 🟢 낮음 — caller 변경 없음. `model_validate` 실패 시 Gemini 응답 파싱 에러로 처리 (현재도 ValueError로 처리 중, 에러 경로 동일).

**Test harness:** 현 ai_processing 단위 테스트 없음. 마이그레이션 시 `test_ai_processing.py` 신설 권고 — 스키마 불일치 시 ValidationError 발생 케이스 포함.

**우선순위:** ★★★☆☆

**Sprint 묶음 권고:** BL-003과 묶어서 (Sprint 12+). 둘 다 서비스 레이어 안전성 강화 방향으로 묶을 수 있음.

**근거:** deepen-modules audit 2026-05-12 Round 2 co-change 분석 (docs/dev-log/2026-05-12-services-deepen.md)

---

## BL-005 — memory.service.promote() Service Session 직접 접근 제거 (I-1 / Backend Rules §3 위반)

**현 상태:**
`backend/src/memory/service.py:420, 431` — `MemoryService.promote`가 `self.repo.session.execute(target_q)` / `self.repo.session.execute(member_q)` 직접 호출. Backend Rules §3 (AsyncSession은 Repository만 보유) 위반. Workspace + WorkspaceMember 조회를 repo 위임 없이 inline.

**목표 인터페이스:**
```python
# workspaces/repository.py 확장
async def get_workspace(self, workspace_id: UUID) -> Workspace | None: ...
async def get_member(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMember | None: ...

# memory/service.py promote()
target_ws = await self.workspace_repo.get_workspace(target_workspace_id)
member = await self.workspace_repo.get_member(target_workspace_id, promoted_by_user_id)
```

**영향 파일:**
- `backend/src/workspaces/repository.py` — 메서드 2개 추가 (이미 있을 가능성 있음, 확인 후 재사용)
- `backend/src/memory/service.py` — promote() session 호출 제거
- `backend/src/memory/dependencies.py` — WorkspaceRepository 주입

**예상 LOC delta:** +20 (repository) / -10 (service)

**Risk:** 🟢 낮음 — 동작 동일, 레이어 분리만

**Test harness:** `test_promote.py` 5 케이스 그대로 통과해야 함

**우선순위:** ★★★★★ (P0 헌법 위반)

**Sprint 묶음 권고:** BL-006과 묶어 Sprint 17 우선 처리

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-006 — memory → embeddings.create_chunk 직접 호출 → pipeline_service.py 분리 (ADR-014 위반)

**현 상태:**
`backend/src/memory/service.py:724` — `_create_memory_embedding_chunk`에서 `from src.embeddings.service import create_chunk` 직접 호출. CONTEXT-MAP §4.2 + ADR-014 위반 (cross-domain shared service는 orchestrator 경유 필수). memory 모듈에 `pipeline_service.py` 부재.

**목표 인터페이스:**
```python
# memory/pipeline_service.py 신설
class MemoryPipelineService:
    def __init__(self, memory_service, embeddings_service): ...
    async def distill_and_embed(self, memory_id, transcript): ...
    async def transcribe_distill_embed(self, memory_id, r2_key): ...
    async def promote_embed(self, new_memory_id, source_text): ...

# memory/service.py는 enqueue + status 전이만, BG task는 PipelineService 위임
```

**영향 파일:**
- `backend/src/memory/pipeline_service.py` — 신설
- `backend/src/memory/service.py` — `_bg_*` 3 메서드 + `_create_memory_embedding_chunk` 제거 (또는 위임)
- `backend/src/memory/dependencies.py` — PipelineService 주입

**예상 LOC delta:** +200 (pipeline_service) / -180 (service)

**Risk:** 🟡 중간 — BG task 흐름 재배치. 기존 6 테스트 그대로 통과 필요.

**Test harness:** `test_service.py` 7 케이스 + `test_recall.py` 6 케이스 그대로

**우선순위:** ★★★★★ (P0 헌법 위반)

**Sprint 묶음 권고:** BL-005와 묶어 Sprint 17 우선 처리

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-007 — memory AI 호출 helper (`_call_distill` / `_call_embedding` / `_call_transcribe`) → services/memory_ai_calls.py 통합

**현 상태:**
`backend/src/memory/service.py:637~709` — module-level helper 3개에서 Gemini / OpenAI / Whisper client 직접 생성. 주석 "테스트 monkeypatch 진입점"이지만 BG task session_factory 컨텍스트와 AI 호출 시간 블로킹 분리 X. session orphan 위험.

**목표 인터페이스:**
```python
# services/memory_ai_calls.py 신설 (또는 services/ai_processing.py 확장)
class MemoryAiCallsService:
    async def distill(self, transcript: str) -> MemoryDistillResult: ...
    async def transcribe(self, r2_key: str) -> str: ...
    async def embed(self, text: str) -> list[float]: ...
```

**영향 파일:**
- `backend/src/services/memory_ai_calls.py` — 신설 (또는 ai_processing.py 확장)
- `backend/src/memory/service.py` — helper 제거

**예상 LOC delta:** +120 (services) / -75 (memory/service)

**Risk:** 🟢 낮음 — interface 변경 없음, 위치만 이동

**Test harness:** 신규 test_memory_ai_calls.py 필요

**우선순위:** ★★★☆☆ (P1, Seam 보강)

**Sprint 묶음 권고:** Sprint 18+ (BL-005/006 이후)

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-008 — memory R2 boto3 client 재생성 → R2Service 메서드로 상향

**현 상태:**
`backend/src/memory/service.py:602, 620` — `_upload_audio_to_r2` / `_download_audio_from_r2`가 R2Service 주입받지만 `self.r2_service._session.client(...)` non-public API 우회. Backend Rules §5 권장 (`aioboto3` async session 패턴) 위반.

**목표 인터페이스:**
```python
# common/r2.py R2Service 확장
class R2Service:
    async def upload_audio(self, key: str, body: bytes, content_type: str) -> None: ...
    async def download_audio(self, key: str) -> bytes: ...
    async def delete_audio(self, key: str) -> None: ...
```

**영향 파일:**
- `backend/src/common/r2.py` — 메서드 3개 추가
- `backend/src/memory/service.py` — helper 2개 → R2Service 메서드 호출

**예상 LOC delta:** +60 (r2.py) / -30 (memory/service)

**Risk:** 🟢 낮음 — interface 단순화. 기존 동작 동일.

**Test harness:** R2Service mock 테스트 추가

**우선순위:** ★★★☆☆ (P1)

**Sprint 묶음 권고:** Sprint 18+ (BL-007과 묶을 수 있음, 두 건 다 service.py LOC 감소)

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-009 — memory MemoryItem status state machine 분리 (3 BG task 중복 제거)

**현 상태:**
`backend/src/memory/service.py:515~549, 568~588, 755~787` — `processing → embedding_pending → active` (또는 embedding_failed) 전이 로직이 3개 BG task에 유사 중복. status 열거형은 `models.py:48~49`에 있지만 transition 검증 X. status 추가/변경 시 grep 3곳 수정 필요 (locality 낮음).

**목표 인터페이스:**
```python
# memory/status_flow.py 신설
class MemoryStatusFlow:
    @staticmethod
    def transition(current: str, event: str) -> str: ...   # valid 전이만 허용
    @staticmethod
    def is_terminal(status: str) -> bool: ...
```

**영향 파일:**
- `backend/src/memory/status_flow.py` — 신설
- `backend/src/memory/service.py` — 3개 BG task에서 사용

**예상 LOC delta:** +60 (status_flow) / -40 (service)

**Risk:** 🟢 낮음 — 행동 동일

**Test harness:** status_flow unit test 신설 + 기존 service 테스트 통과 유지

**우선순위:** ★★☆☆☆ (P2)

**Sprint 묶음 권고:** Sprint 19+ (BL-006 pipeline_service 분리 후 자연스럽게 결합)

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-010 — memory MemoryQueryEmbeddingCache race condition 정책 결정

**현 상태:**
`backend/src/memory/service.py:335~355` — `_get_query_embedding` cache lookup 후 저장 (line 354). 동시 호출 시 UNIQUE 충돌 무시 (`repository.py:269` "race condition은 무시"). 두 workspace가 동일 normalized_query 입력 시 cache 공유 여부 deterministic X.

**목표 인터페이스:**
정책 결정 필요:
- 옵션 A: workspace_id 기반 strict 격리 (현재 의도, 명시화)
- 옵션 B: cross-workspace shared cache (cost 절감 + 의미적 동일 query)
- 옵션 C: 둘 다 + 사용자 opt-in 플래그

ADR 신설 (ADR-020 후보) — Sprint 18+ wedge 검증 후 결정.

**영향 파일:**
- 정책 결정 후 `service.py:335~355` + `repository.py` 수정 또는 그대로

**예상 LOC delta:** TBD

**Risk:** 🟢 낮음 — 의미적 결정 ADR

**Test harness:** 정책에 따라 추가

**우선순위:** ★☆☆☆☆ (P2, 의미 결정)

**Sprint 묶음 권고:** Sprint 18+ (Recall demand 검증 N 충분 후)

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-011 — memory 모듈 test coverage 일괄 보강 (Stage 5-5 Testing specialist 9 critical)

**현 상태:**
Sprint 15 stage 5-5 testing specialist 9 CRITICAL + 4 INFORMATIONAL 미커버 경로 식별. 기존 6 test file (test_api/service/recall/promote/metrics/admin_cleanup)는 happy path 위주 — BG task 실행 / cross-ws isolation / status transition / RBAC 회귀 / lazy seed 회귀 미보호.

**목표 인터페이스:**
신규 또는 확장 test file 9개:
1. `test_promote.py` — target=personal/존재X/non-member 3 negative path
2. `test_api.py` — voice capture + oversized (413) + empty bytes (422)
3. `test_service.py` — _bg_distill_and_embed / _bg_transcribe_distill_embed / _bg_promote_embed 직접 await + status transition 검증 (성공+실패 분기)
4. `test_recall.py` — vector hit path (_call_embedding monkeypatch return fake 1536d) + cache hit + concurrent insert (ON CONFLICT 검증)
5. `test_promote.py` — cross-workspace memory_id isolation (404 보장)
6. `tests/auth/test_personal_workspace_seed.py` 신설 — lazy seed idempotent + 동시 호출
7. `test_memory_router_rbac.py` 신설 — viewer/member 차이 + 비-멤버 403
8. `test_admin_cleanup.py` — R2 delete monkeypatch + expired item 실제 row 갱신
9. `test_service.py` — PromotionAudit.embedding_status='failed' 분기 + Memory.status='embedding_failed'

추가 informational (P1):
- `test_dogfood_smoke_import.py` — scripts/dogfood_smoke.py import smoke
- `test_metrics.py` — percentile edge (NULL latency / 1건 / 다수)
- `test_api.py` — status state machine (5 status seed + GET)
- `test_service.py` — _normalize_audio ffmpeg 부재 fallback

**예상 LOC delta:** +700 (테스트 전체)

**Risk:** 🟢 낮음 — 테스트 추가만, 코드 변경 X

**Test harness:** 기존 conftest fixtures 재사용 (memory_client, seed_memory). RBAC fixture는 신규 (viewer / member / non-member user).

**우선순위:** ★★★★☆ (회귀 방지)

**Sprint 묶음 권고:** Sprint 16 첫 주 (Phase B Gemini swap과 묶음, BG task 변경 시 회귀 안전망 필수)

**근거:** Stage 5-5 testing specialist 2026-05-14

---

## BL-012 — memory 모듈 hygiene cleanup (Stage 5-5 Maintainability 18건)

**현 상태:**
Stage 5-5 maintainability specialist 18 INFORMATIONAL. dead code / magic constants / long methods / function-scope imports / DI bypass / silent failure. 각각 단독으로는 minor지만 누적 시 service.py 844 lines가 더 두꺼워짐.

**목표 인터페이스:**
1. Dead code: `WorkspaceMembershipError` 제거 (memory/exceptions.py:27 — 사용 X)
2. Dead field: `PromotionAudit.promoted_note_id` 제거 또는 사용 lock-in
3. Duplicate imports 정리 (service.py:202 timedelta, R2Service)
4. DI bypass: cleanup_expired_r2_audio가 `R2Service()` 재생성 -> `self.r2_service` 사용
5. Silent failure: R2 delete except에 `logger.warning` 추가
6. Magic constants: GEMINI_MODEL/WHISPER_MODEL/EMBEDDING_MODEL을 core/config.py로 이관 (ADR-019 Phase B와 묶기 적절)
7. ttl_days=7 / 30 / 365 named constants
8. Long methods: recall (90 lines) + promote (99 lines) helper 분리
9. Function-scope imports (service.py:406 select/Workspace/WorkspaceMember) module-level 이관
10. stale comment 정리 (service.py:598)

**예상 LOC delta:** -150 (cleanup) / +50 (helpers)

**Risk:** 🟢 낮음 — interface 변경 없음

**Test harness:** 기존 테스트 그대로 통과 + BL-011 보강된 회귀 안전망 활용

**우선순위:** ★★★☆☆ (P2 hygiene)

**Sprint 묶음 권고:** Sprint 17 (BL-005~010 본 묶음과 함께 — service.py 전체 리팩토링 1 PR)

**근거:** Stage 5-5 maintainability specialist 2026-05-14

---

## BL-013 — alembic migration FK ondelete + 2-phase deploy + downgrade safety

**현 상태:**
Stage 5-5 data-migration specialist 6 CRITICAL. Sprint 15 migration `a1b2c3d4e5f6_sprint15_memory_workspace_type.py`가:
1. 모든 FK에 `ondelete` 명시 X (default RESTRICT) — workspace 삭제 시 memory_items가 차단
2. Schema + backfill 단일 migration — 2단계 배포 위반 (.ai/stacks/fastapi/backend.md §9)
3. CREATE INDEX without CONCURRENTLY — prod scale에서 workspaces 테이블 ACCESS EXCLUSIVE lock
4. Downgrade가 데이터 손실 (DROP TABLE) — 사용자 확인 가드 부재
5. `workspaces.type` server_default='team'이 기존 solo workspace를 잘못 misclassify (founder 시나리오에서는 무영향이나 multi-tenant 시 surprise)

**목표 인터페이스:**
신규 migration 2~3개로 분리:
- `aXXX_alter_memory_fk_ondelete.py` — memory_items/ai_calls/events workspace FK -> CASCADE / promotion_audit -> RESTRICT
- `aYYY_split_workspace_type_backfill.py` — DDL과 DML 분리 (이미 적용된 상태이므로 2단계 deploy는 사후 documentation)
- downgrade에 `ALLOW_DESTRUCTIVE_DOWNGRADE` env 가드

**예상 LOC delta:** +120 (신규 migration 2~3개)

**Risk:** 🟡 중간 — prod DB 마이그레이션 추가 실행 필요

**Test harness:** test_alembic_memory.py 확장 — FK behavior 시뮬레이션 (workspace 삭제 -> memory_items CASCADE 검증)

**우선순위:** ★★★☆☆ (prod 배포 안정성)

**Sprint 묶음 권고:** Sprint 17 (multi-tenant 시점 이전 필수, 또는 첫 외부 user team 시점)

**근거:** Stage 5-5 data-migration specialist 2026-05-14

---

## BL-014 — Workspace switcher UI 누락 (Sprint 15 R5 spec gap)

**현 상태:**
Stage 5-4 design-review (Playwright MCP) 2026-05-14. Sprint 15 R5에서 Personal workspace lazy seed 구현됨 (Lock vs Users 타입). BUT FE에 사용자가 Personal ↔ Team 사이 전환할 수 있는 switcher UI 부재.

- Topbar: 현재 워크스페이스명 "Kairos" + Users icon + member count "1" — 클릭 불가능한 plain text + badge
- Avatar dropdown: 유저 메뉴만 (다크 모드 / 설정 / 로그아웃) — workspace 전환 옵션 없음
- 사이드바: 프로젝트 트리만 — 워크스페이스 선택 없음

영향: Personal workspace seed가 되어도 사용자가 진입 불가. Sprint 15 R5 의도 부분 좌절.

**목표 인터페이스:**
- 옵션 A: Topbar workspace badge → dropdown switcher (DESIGN.md §Workspace Types "Workspace switcher dropdown options에 type badge inline")
- 옵션 B: Sidebar 상단 workspace selector 추가
- 옵션 C: `/workspace/[id]/...` route param 명시 (current = active workspace store만 기반)

**예상 LOC delta:** +80~120 (신규 컴포넌트 + store wiring)

**Risk:** 🟡 중간 — workspace store + RBAC 분기 영향

**Test harness:** E2E (Playwright) — Personal ws 진입 + 전환 + memory isolation 검증

**우선순위:** ★★★★☆ (P1 — Sprint 15 R5 spec 완결)

**Sprint 묶음 권고:** Sprint 16 (Best/Medium 분기 시 Promotion build와 묶기, Min 분기 시 별도 우선순위 평가)

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-41

---

## BL-015 — Workspace type badge (Lock/Users) 일관성 적용

**현 상태:**
Stage 5-4 design-review. DESIGN.md §Workspace Types lock-in (Sprint 15 patch):
- Personal: `Lock` icon + text-muted
- Team: `Users` icon + text-accent + bg-accent-subtle

BUT 실제 렌더 상태:
1. Topbar: Team workspace 진입 시 `Users` icon ✅ (단일 워크스페이스 case 정상)
2. Recall result card: type badge 누락 — 대신 "🔍 의미 매칭" semantic label
3. Memory item card 좌상단 corner: type badge 누락
4. PromoteModal dropdown option: Users icon ✅ (Team만 후보로 노출, 정상)

원인: BL-014 (switcher 없음) + Personal workspace에 가 본 적이 없어 Lock 분기 미검증.

**목표 인터페이스:**
- `<WorkspaceTypeBadge type="personal" | "team" />` shared component (`frontend/src/features/workspaces/components/`)
- 사용 위치: switcher dropdown / topbar / recall card top-right / promote modal option

**예상 LOC delta:** +60 (신규 컴포넌트 + 4 호출처)

**Risk:** 🟢 낮음 — visual only

**Test harness:** Storybook or visual regression (없으면 design-review 재실행으로 검증)

**우선순위:** ★★★☆☆ (P2 polish — BL-014에 종속)

**Sprint 묶음 권고:** BL-014 후속 Sprint 16~17

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-1/F-17/F-40

---

## BL-016 — PromoteModal 동명 workspace 구분 (UX 모호성)

**현 상태:**
Stage 5-4 design-review. PromoteModal combobox에 동일한 name "E2E 테스트 워크스페이스" 4개 표시 (founder test data 결과). 코드는 `workspace.name` 그대로 렌더 → workspace.id로 distinct 하나 사용자는 4개 동일 옵션 사이 구분 불가.

**목표 인터페이스:**
- Option label에 secondary info 추가: `{name} · {membersCount}명` 또는 `{name} · {idSuffix-4}` 또는 `{name} · {createdAtRelative}`
- 또는 동명 그룹화 (헤더 + indent)

**예상 LOC delta:** +20 (PromoteModal option label)

**Risk:** 🟢 낮음

**Test harness:** Storybook fixture 또는 design-review 재실행

**우선순위:** ★★☆☆☆ (P2 — multi-tenant 시점 이전 필수, founder 1인 시점 무영향)

**Sprint 묶음 권고:** Sprint 17 (multi-tenant 진입 시)

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-23

---

## BL-017 — Mobile FAB collision with bottom nav

**현 상태:**
Stage 5-4 design-review mobile viewport (375x667). /memory FAB (bottom-8 right-8 h-14 w-14)와 mobile bottom navigation bar 충돌. FAB가 nav 위에 떠있어 시각적으로 부딪힘, 또는 nav가 FAB 일부를 가림.

**목표 인터페이스:**
- Mobile `md:hidden` 분기에서 FAB `bottom-{nav-height + 16px}` 적용
- 또는 FAB → bottom nav "+ 추가" 통합 (이미 nav에 "+ 추가" 있음)
- 또는 FAB mobile에서 숨김, bottom nav "+ 추가"가 /new 대신 CaptureSheet 트리거

**예상 LOC delta:** +30 (FAB margin 조건부 또는 nav rewire)

**Risk:** 🟢 낮음

**Test harness:** design-review mobile viewport 재실행

**우선순위:** ★★★☆☆ (P2 — mobile 사용성)

**Sprint 묶음 권고:** Sprint 16/17 mobile polish

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-33

---

## BL-018 — DESIGN.md Sprint 15 patch drift (capture row + tabs + bottom nav 5th)

**현 상태:**
Stage 5-4 design-review. DESIGN.md §Recall UI Layout이 Sprint 15 plan §3.4 Q1 A3 "B3 search-first FAB" 결정 이전 spec 그대로 유지:

```
[capture row: Mic button (lg) + Textarea (autosize, multi-line)]
[search bar: input + Cmd+K hint]
[tabs: Personal | Team]
```

실제 = search-first FAB layout (Mic row, search bar, tabs 미존재). Atomic Update §2 매트릭스 누락 retrofit 필요. Bottom nav 5th item DESIGN.md = "[검색]" but 실제 = "메모".

**목표 인터페이스:**
- DESIGN.md §Recall UI 갱신:
  - capture row 제거 (FAB로 통합)
  - tabs 제거 (single feed)
  - 또는 옵션 = Sprint 16 Best 분기 시 tabs 재도입 명시
- DESIGN.md Bottom Nav: "[검색]" → "[메모]" + 하단에 "Sprint 15 patch 2026-05-14" 기록

**예상 LOC delta:** +40 (DESIGN.md doc)

**Risk:** 🟢 낮음 (doc only)

**Test harness:** N/A (design-review에서 DESIGN.md 기준점이므로 fix 후 재실행 시 0 finding)

**우선순위:** ★★★☆☆ (P2 — atomic update 회수)

**Sprint 묶음 권고:** Sprint 16 첫 doc commit (Phase B와 묶음)

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-2/F-5/F-34

---

## BL-019 — Recall metrics 신선도 + sparkline

**현 상태:**
Stage 5-4 design-review /admin/recall-metrics. `30초마다 자동 갱신` description 있으나 last-updated timestamp 미노출. 4 metric tile만, trend (7일) sparkline 없음. p95 4934ms = p50 4934ms (단일 데이터 포인트) — sparse data 표시 없음.

**목표 인터페이스:**
- header에 last-updated `{relative time}` 표시
- 각 metric tile에 7일 sparkline (memory_events 테이블에서 일별 aggregation)
- p95=p50 일치 시 "데이터 부족" badge
- BE: GET /workspaces/{ws}/memory/metrics?range=7d 옵션

**예상 LOC delta:** +200 (BE aggregation + FE sparkline)

**Risk:** 🟡 중간 (BE 신규 endpoint)

**Test harness:** test_memory_metrics_aggregation.py

**우선순위:** ★★☆☆☆ (P2 polish — founder admin)

**Sprint 묶음 권고:** Sprint 17+ (R7 metrics 정식 build)

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-30/F-31

---

## BL-020 — Recall result card / mobile placeholder polish (3건 묶음)

**현 상태:**
Stage 5-4 design-review 잡다한 polish 3건:
1. Mobile (375px) search placeholder "무엇을 다시 찾고 싶으세요? (예: Sprint 15 wedge)" 트런케이션 — viewport edge 잘림
2. Recall result card 날짜 format "2026. 5. 14." trailing period (Korean convention but uncommon for app UI)
3. Recall result card 우상단 "🔍 의미 매칭" label 위치 — title과 경쟁

**목표 인터페이스:**
1. Placeholder 단축: "무엇을 다시 찾고 싶으세요?" (예시 제거 또는 별도 hint)
2. Date format: relative ("오늘" / "어제" / "3일 전") 또는 ISO ("2026-05-14")
3. 의미 매칭 label: 우하단 corner로 이동 또는 icon-only tooltip

**예상 LOC delta:** +30

**Risk:** 🟢 낮음

**Test harness:** design-review 재실행

**우선순위:** ★☆☆☆☆ (P3 polish)

**Sprint 묶음 권고:** Sprint 17+ (polish bundle)

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-18/F-21/F-37

---

## BL-021 — e2e auth.setup Clerk koKR label selector mismatch

**현 상태:**
PR #29 CI e2e job fail (5m timeout). main에서 이미 같은 fail inherit (run 25825914554, 2026-05-13 push sha 8311620 이후). 본 PR 책임 아님 — auth.setup.ts 본 PR diff 0 (Sprint 14에서 마지막 수정).

직접 원인:
- Clerk SignIn component label = "이메일 주소" (koKR localization 적용 `9ea1a78 fix(auth): T-3 Clerk koKR localization + /dashboard force redirect`)
- e2e selector = `getByLabel(/email/i)` 영문 정규식만
- 한국어 label "이메일 주소" → `/email/i` 매치 0 → 60초 timeout → 3 retry fail → 7 후속 test "did not run"

증거:
- 사용자 local sign-in 페이지 스크린샷 (2026-05-14) — embedded SignIn form 정상 렌더, label "이메일 주소", continue button "계속"
- main last fail (25825914554) + PR #29 fail (25850407909) 동일 step / 동일 line / 동일 error message
- auth.setup.ts:42 `getByRole("button", { name: /continue|계속/i })` 이미 한국어 매치 ✅. line 39만 누락

**목표 인터페이스:**

가장 robust 옵션 (locale-independent):
```ts
// before
await page.getByLabel(/email/i).fill(email);
// after — Clerk SignIn component standard input name (locale 변화 무관)
await page.locator('input[name="identifier"]').fill(email);
```

대안 (regex 확장):
```ts
await page.getByLabel(/email|이메일/i).fill(email);
```

추천: `input[name="identifier"]` (Clerk SDK standard, 향후 locale 추가 시 미영향).

**예상 LOC delta:** +1/-1 (auth.setup.ts:39 1줄 patch)

**Risk:** 🟢 낮음 (test file only)

**Test harness:** PR push 후 GitHub Actions e2e job 재실행 통과 확인

**우선순위:** ★★★★☆ (P1 — CI 통과 정상화. main + 모든 후속 PR에 영향)

**Sprint 묶음 권고:** 별도 hotfix PR 또는 Sprint 16 첫 commit. Sprint 15 PR #29 직전 분리 권고 (PR #29 머지 무관, e2e fail은 동일 상태 유지).

**근거:** Sprint 15 Stage 5-6 qa Exhaustive 후속 진단 2026-05-14 — 사용자 화면 증거로 root cause 정정 (Clerk Account Portal redirect 아님, koKR label mismatch 확정).
