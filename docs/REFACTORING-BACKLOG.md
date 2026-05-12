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

## BL-002 — process_meeting / capture_text 공통 로직 추출

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
