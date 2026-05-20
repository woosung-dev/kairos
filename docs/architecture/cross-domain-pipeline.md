# 크로스 도메인 호출 규칙

## 문제

Kairos의 회의 처리 파이프라인은 여러 도메인 서비스를 순차적으로 호출해야 한다:

```
MeetingService
  → TranscriptionService (STT + 화자 분리)
  → AIProcessingService (요약 + 액션 추출 + 프로젝트 연결 추천)
  → InboxService (Inbox 적재)
  → EmbeddingService (벡터 임베딩 저장)
```

각 도메인은 독립적인 모듈이지만, 파이프라인에서는 서로 의존한다.

---

## 채택 패턴: 오케스트레이터 서비스

크로스 도메인 호출은 **오케스트레이터 서비스**를 통해 조율한다.
도메인 서비스 간 직접 import는 금지하고, 파이프라인 전용 서비스가 조합한다.

```
meetings/
├── router.py
├── service.py              ← 단일 도메인 CRUD
├── pipeline_service.py     ← 오케스트레이터 (크로스 도메인 조합)
├── repository.py
└── dependencies.py
```

### 구현 예시

```python
# meetings/pipeline_service.py — 오케스트레이터
class MeetingPipelineService:
    def __init__(
        self,
        meeting_repo: MeetingRepository,
        transcription: TranscriptionService,
        ai_processing: AIProcessingService,
        inbox_service: InboxService,
        embedding_service: EmbeddingService,
    ):
        self.meeting_repo = meeting_repo
        self.transcription = transcription
        self.ai_processing = ai_processing
        self.inbox_service = inbox_service
        self.embedding_service = embedding_service

    async def process_meeting(self, meeting_id: str) -> None:
        """회의 처리 파이프라인 전체를 오케스트레이션한다."""
        meeting = await self.meeting_repo.get_by_id(meeting_id)

        # [1] STT
        await self.meeting_repo.update_status(meeting_id, "transcribing")
        transcript = await self.transcription.transcribe(meeting.audio_url)

        # [2] AI 처리
        await self.meeting_repo.update_status(meeting_id, "summarizing")
        summary = await self.ai_processing.summarize(transcript)
        actions = await self.ai_processing.extract_actions(transcript)
        project_suggestion = await self.ai_processing.classify_project(summary)

        # [3] Inbox 적재
        await self.inbox_service.create_from_meeting(
            meeting_id=meeting_id,
            suggested_project_id=project_suggestion["suggested_project_id"],
            suggested_tags=project_suggestion["suggested_tags"],
            confidence=project_suggestion["confidence"],
        )

        # [4] 임베딩 저장
        await self.embedding_service.embed_transcript(meeting_id, transcript)

        # [5] 완료
        await self.meeting_repo.update_status(meeting_id, "completed")
        await self.meeting_repo.commit()
```

### DI 조립

```python
# meetings/dependencies.py
async def get_meeting_pipeline_service(
    session: AsyncSession = Depends(get_async_session),
) -> MeetingPipelineService:
    return MeetingPipelineService(
        meeting_repo=MeetingRepository(session),
        transcription=TranscriptionService(),
        ai_processing=AIProcessingService(),
        inbox_service=InboxService(InboxRepository(session)),
        embedding_service=EmbeddingService(EmbeddingRepository(session)),
    )
```

---

## 규칙

| 규칙 | 설명 |
|------|------|
| 도메인 서비스 간 직접 import 금지 | `inbox/service.py`가 `meetings/service.py`를 import하지 않음 |
| 오케스트레이터만 크로스 도메인 | `pipeline_service.py`만 여러 도메인 서비스를 조합 |
| DI로 조립 | `dependencies.py`에서 모든 의존성 주입 |
| 동일 session 공유 | 트랜잭션 일관성을 위해 같은 AsyncSession 사용 |
| **Cross-domain shared service 호출은 orchestrator 내부에서만** (Sprint 6 ADR-014 옵션 A) | `embeddings.service` / `services/ai_processing` / `services/transcription` 직접 호출은 `pipeline_service.py` 또는 `services/` 안에서만 허용. 일반 도메인 service.py는 cross-domain shared service 호출 금지 |
| **권한 검증 일원화** (Sprint 6 ADR-014) | 진입 메서드(예: `RagPipelineService.ask`, `NotePipelineService.delete_note_with_cleanup`)에서 visibility/member 검증 후 도메인 service에 위임. SSE 스트리밍 시작 *전*에 검증 완료 |

---

## Sprint 6 추가 적용 (ADR-014 옵션 A, BE-T9~T14)

D-2/D-3 부채 해소 — `notes`와 `rag` 도메인도 meetings 패턴 따라 orchestrator 도입:

```
notes/                              rag/
├── service.py     순수 노트 CRUD   ├── service.py     6-Layer 비즈니스 로직
├── pipeline_service.py             ├── pipeline_service.py
│   ← embed_note_async              │   ← ask (visibility 검증 + RagService.ask 위임)
│   ← delete_note_with_cleanup      │   ← AsyncGenerator wrapping
│   ← check_project_access
└── dependencies.py                 └── dependencies.py
    get_note_service                    get_rag_service
    get_note_pipeline_service           get_rag_pipeline_service
```

- `notes/router.py`: BackgroundTasks의 embed/delete 호출이 `service.embed_note_async` → `pipeline.embed_note_async`로 변경.
- `rag/router.py`: `/ask` endpoint가 `service.ask` → `pipeline.ask`로 변경. SSE 스트리밍 시작 전에 visibility 검증.
- 권한 위반 시 `error` + `done` SSE 이벤트로 종료 (스트리밍 시작 안 함, ADR-014 검증 기준 C-6).
- 헌법 §4.2 갱신: "embeddings.service 호출은 orchestrator 내부에서만 허용" 행 추가, D-2/D-3 ⚠️ 행 제거.

---

## Sprint 24 BL-064 추가 적용 — Note promote chunk 0 분기 BG re-embedding

Sprint 23 D4 의 Note promote 흐름은 source chunk 가 0 일 때 `NotePromoteNotEmbeddedError(400)` 로 거부 (race 회피). Sprint 24 BL-064 는 **plain_text 존재 + chunk 0** 케이스만 분리해 BG 재생성 흐름 추가.

```
POST /workspaces/{wid}/notes/{id}/promote
  └─ NoteService.promote(..., pipeline=NotePipelineService) [pipeline DI 추가]
       ├─ source.plain_text 부재               → 400 NotePromoteNotEmbeddedError (회귀 유지)
       ├─ source.plain_text 존재 + chunk N>0  → BackgroundTasks(_bg_promote_embed_note) [Sprint 23 흐름]
       │     └─ source EmbeddingChunk → target ws 복제 + audit pending→processing→completed/failed
       └─ source.plain_text 존재 + chunk 0    → BackgroundTasks(_bg_regenerate_embed_with_audit) [Sprint 24 신규]
             ├─ audit: pending → processing 마크
             ├─ pipeline.embed_note_async(new_note_id, target_workspace_id) 호출 (자체 session)
             │     ↓ EmbeddingService.embed_note (chunk L1/L2 신규 생성 + OpenAI embedding)
             │     ↓ EmbeddingService.invalidate_cache (target ws RAG cache 무효화)
             ├─ 성공: audit → completed 마크
             └─ 예외: rollback → audit → failed 마크

응답 (snake_case 보존, Codex 2차 P2-3):
  { new_note_id, audit_id, status: "embedding_pending", embedding_status: "pending" }

GET /workspaces/{wid}/notes/{id}/embedding-status  (NEW, require_viewer)
  └─ NoteService.get_embedding_status
       ├─ audit row 존재 → { status: audit.embedding_status, chunkCount: count_note_chunks }
       └─ audit row 부재 (promote 외 흐름) → chunkCount 기반 status 추론
            ├─ chunk > 0 → "completed"
            └─ chunk == 0 → "pending"
```

**핵심 규칙**:
- `_bg_regenerate_embed_with_audit` wrapper 가 audit lifecycle 책임 (Codex 2차 P1). `pipeline.embed_note_async` 단독 호출 시 audit pending stuck.
- Sprint 23 D4 `_bg_promote_embed_note` 와 같은 session_factory 패턴. 부분 실패 시 rollback 먼저 (Codex 4차 P2-2).
- pipeline DI 는 router → service → BG task 로 전달 (instance binding 보존).

**FE 흐름** (ItemPromoteModal):
- `embedding_status === "pending" | "processing"` → 5s × 3회 polling (`GET embedding-status`)
- `status === "completed"` → toast success + close, `"failed"` → toast error + close, 3회 후에도 진행 중이면 "잠시 후 확인" + close.

---

## Sprint 24 Wave 2 BL-006 추가 적용 — Memory orchestrator 분리 (2026-05-20)

Sprint 15 신설 당시 `memory/service.py` 는 `_bg_distill_and_embed` (capture flow) 와 module-level `_bg_promote_embed` (R6 promote flow) 안에서 `from src.embeddings.repository import EmbeddingRepository` 를 lazy import 후 직접 `save_chunk` 호출. CONTEXT-MAP §4.2 + ADR-014 옵션 A 위반.

```
backend/src/memory/
├── service.py               capture/recall/promote + BG task — `embeddings.*` 직접 import 금지 (architecture gate 강제)
├── pipeline_service.py      MemoryPipelineService (Sprint 24 Wave 2 신설)
│   └── save_memory_chunk(session, ...) — EmbeddingRepository.save_chunk 호출 캡슐화
│       (session 은 호출자 BG task 가 보유 — 단일 트랜잭션 정합)
└── dependencies.py          MemoryPipelineService 동반 주입 (fail-closed)
```

**해소 흐름**:
- `_bg_distill_and_embed` (capture) → `self._pipeline.save_memory_chunk(session, workspace_id=..., source_workspace_id=..., source_id=memory_id, ...)`
- `_bg_promote_embed` (promote) → 모듈-level 함수 시그니처에 `pipeline: MemoryPipelineService` 추가, BackgroundTasks.add_task 시 `self._pipeline` 전달.
- `MemoryService.__init__` `pipeline: MemoryPipelineService | None = None` — `_bg_*` 진입 전 None 가드 → `RuntimeError` (fail-closed, BL-006 §4.2 위반 차단).
- `source_type='memory'` 는 orchestrator 가 고정 — service 가 임의로 다른 타입 인서트 불가.

**E-9 예외 (유지 결정)**:
- `memory/repository.py:33` 의 `from src.embeddings.repository import _apply_hnsw_session_params` 1 hit 는 벡터 검색 트랜잭션 진입 HNSW SET LOCAL 위해 유지 (Sprint 16 capsule 우회 최소 비용 약속, embeddings/CONTEXT.md E-9).
- vector_search 자체를 embeddings 도메인으로 흡수하는 작업은 LOC vs 가치 비대칭 → 후속 sprint.

**회귀 방지 (architecture gate)**:
- `backend/tests/architecture/test_no_memory_to_embeddings_lazy_import.py` — 2 케이스:
  - `test_memory_service_no_embeddings_import` — `memory/service.py` 에 `from src.embeddings.*` 0 hit assertion (lazy import 회귀 차단).
  - `test_memory_repository_apply_hnsw_helper_keep` — `memory/repository.py` 에 `_apply_hnsw_session_params` import 1 hit 유지 (E-9 예외 침해 차단).

---

## 호출 흐름도

```
[Router]
  POST /meetings/{id}/process
    → BackgroundTasks.add_task(pipeline.process_meeting, id)
    → 202 Accepted + {"status": "processing"}

[BackgroundTask]
  MeetingPipelineService.process_meeting(id)
    → TranscriptionService.transcribe()        # 외부 API (Whisper)
    → AIProcessingService.summarize()           # 외부 API (Gemini)
    → AIProcessingService.extract_actions()     # 외부 API (Gemini)
    → AIProcessingService.classify_project()    # 외부 API (Gemini)
    → InboxService.create_from_meeting()        # DB 쓰기
    → EmbeddingService.embed_transcript()       # 외부 API (OpenAI) + DB 쓰기
    → MeetingRepository.update_status()         # DB 쓰기
    → commit()                                  # 한 번만

[Client Polling]
  GET /meetings/{id}/status
    → {"status": "transcribing" | "summarizing" | "completed" | "failed"}
```
