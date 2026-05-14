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
