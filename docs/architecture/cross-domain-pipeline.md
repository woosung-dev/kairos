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
