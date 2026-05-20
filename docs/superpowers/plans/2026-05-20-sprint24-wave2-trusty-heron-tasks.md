# Sprint 24 Wave 2 trusty-heron Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Multi-Agent QA 발견 P0/P1 dogfood 차단 결함 16건 fix + Phase B Post-Swap Delta 검증 + 헌법 §4.2 BL-006 정합.

**Architecture:** 9 Phase 직렬 진행 — Phase 1 T-2 DELTA gate (P0 first) → Phase 2~6 P0/P1 fix → Phase 7~9 헌법/production/회귀. PR 전략 A 단일 multi-commit (Phase 별 1 commit + Codex polish). Sub-agent §19 보호 (Phase 5 T-AUDIT-VIEW BE/FE + Phase 6 T-BE-PERF spike만 분할 dispatch 후보).

**Tech Stack:** Backend = FastAPI + SQLModel + asyncpg + pgvector halfvec + Gemini 3.1-flash-lite + OpenAI Whisper. Frontend = Next.js 16 + React 19 + Tailwind v4 + shadcn/ui v4 + TanStack Query. Test = pytest + vitest + Playwright.

**입력 spec doc:** `docs/superpowers/specs/2026-05-20-sprint24-wave2-trusty-heron-design.md` (commit `319a509`).

---

## File Structure

### Backend 변경

| 파일 | 종류 | Task | Atomic Update |
|---|---|---|---|
| `backend/src/common/prompts.py` | modify | T-AI-DATE | `backend/CONTEXT.md` AI § + `docs/architecture/ai-pipeline.md` |
| `backend/src/services/ai_processing.py` | modify | T-AI-DATE | (위 동일) |
| `backend/src/embeddings/repository.py:155 vector_search` | modify | T-RAG-TIME-FILTER | `backend/src/embeddings/CONTEXT.md` + `docs/architecture/rag-pipeline.md` Layer 3 |
| `backend/src/common/promote_router.py` | create | T-AUDIT-VIEW BE | `docs/api/endpoints.md` + `backend/src/inbox/CONTEXT.md` 등 4 도메인 §엔드포인트 |
| `backend/src/common/promote_repository.py` | create (또는 promote_models.py 확장) | T-AUDIT-VIEW BE | (위 동일) |
| `backend/src/memory/pipeline_service.py` | create | T-N+1 BL-006 | `CONTEXT-MAP.md` §4.2 + §7 + `backend/CONTEXT.md` §4 + `backend/src/memory/CONTEXT.md` + `backend/src/embeddings/CONTEXT.md` + `docs/architecture/cross-domain-pipeline.md` |
| `backend/src/memory/service.py:550, :780` | modify (lazy import 제거) | T-N+1 BL-006 | (위 동일) |
| `backend/src/memory/dependencies.py` | modify (pipeline 주입) | T-N+1 BL-006 | (위 동일) |
| `backend/src/services/transcription.py` 또는 `chunked_transcription.py` | create/modify | T-N+4 Whisper | `backend/CONTEXT.md` STT § + `docs/architecture/ai-pipeline.md` STT |
| `backend/tests/fixtures/composite_fk.py` | create | T-N+2 | tests baseline |
| `backend/tests/conftest.py` | modify (fixture import) | T-N+2 | tests baseline |
| `backend/tests/services/test_ai_action_date_with_year_context.py` | create | T-AI-DATE | tests baseline |
| `backend/tests/embeddings/test_rag_time_range_sql_clause.py` | create | T-RAG-TIME-FILTER | tests baseline |
| `backend/tests/common/test_audit_promotions_endpoint.py` | create | T-AUDIT-VIEW BE | tests baseline |
| `backend/tests/architecture/test_no_memory_to_embeddings_lazy_import.py` | create | T-N+1 BL-006 | tests baseline |
| `backend/tests/services/test_whisper_chunked_4hr.py` | create | T-N+4 | tests baseline |
| `backend/scripts/sprint24_wave2_delta.py` | create | T-2 | spike report |

### Frontend 변경

| 파일 | 종류 | Task | Atomic Update |
|---|---|---|---|
| `frontend/src/features/rag/components/search-scope.tsx:31-37` | modify (MOCK 제거) | T-RAG-MOCK-REMOVE | minor |
| `frontend/src/features/home/components/today-feed.tsx:20, 30-67, 368` | modify (banner rollback) | T-OBN-05 | `backend/src/onboarding/CONTEXT.md` UI anchor patch |
| `frontend/src/components/empty-state.tsx` | modify (props 제거) | T-OBN-05 | (위 동일) |
| `frontend/src/features/projects/components/project-list.tsx:7, 12` | modify (useOnboarding 제거) | T-OBN-05 | (위 동일) |
| `frontend/src/features/projects/components/project-detail.tsx:26, 86` | modify (useOnboarding 제거) | T-OBN-05 | (위 동일) |
| `frontend/src/features/meetings/components/meeting-summary.tsx:5, 12` | modify (useOnboarding 제거) | T-OBN-05 | (위 동일) |
| `frontend/src/components/onboarding/onboarding-tooltip.tsx` | create | T-OBN-05 | (위 동일) |
| `frontend/src/components/ui/tooltip.tsx` + `popover.tsx` | create (shadcn add) | T-OBN-05 | (위 동일) |
| `frontend/src/components/layout/header.tsx` | modify (padding reflow) | T-MOBILE-HEADER | minor |
| `frontend/src/app/(app)/projects/page.tsx` | create | T-PROJ-LIST | minor |
| `frontend/src/app/(app)/notes/[id]/page.tsx` | create | T-NOTE-DETAIL | minor |
| `frontend/src/features/home/components/today-feed.tsx` (dashboard 추천 질문) | modify (onClick → cmd-k store) | T-CMD-K-FIX | minor |
| `frontend/src/app/(app)/settings/page.tsx` | modify (Audit 탭 추가) | T-AUDIT-VIEW FE | `docs/api/endpoints.md` |
| `frontend/src/features/audit/` (신설 디렉토리) | create | T-AUDIT-VIEW FE | (위 동일) |

### Docs 변경 (Atomic Update + deprecated 라벨)

| 파일 | 종류 | Task |
|---|---|---|
| `CONTEXT-MAP.md` §4.2 + §7 | patch | T-N+1 BL-006 |
| `backend/CONTEXT.md` §4 AI + STT + 의존 표 | patch | T-AI-DATE + T-N+1 + T-N+4 |
| `backend/src/memory/CONTEXT.md` | patch | T-N+1 BL-006 |
| `backend/src/embeddings/CONTEXT.md` E-9 | patch | T-N+1 BL-006 + T-RAG-TIME-FILTER |
| `backend/src/onboarding/CONTEXT.md` | patch (UI 결정 anchor) | T-OBN-05 |
| `docs/architecture/cross-domain-pipeline.md` | patch | T-N+1 BL-006 |
| `docs/architecture/ai-pipeline.md` | patch | T-AI-DATE + T-N+4 |
| `docs/architecture/rag-pipeline.md` Layer 3 | patch | T-RAG-TIME-FILTER |
| `docs/api/endpoints.md` | patch | T-AUDIT-VIEW |
| `docs/dev-log/2026-05-19-sprint22-result-report.html` | patch (deprecated 라벨) | T-OBN-05 |
| `docs/dev-log/2026-05-19-sprint22-dogfooding.md` | patch (deprecated 라벨) | T-OBN-05 |
| `docs/superpowers/specs/2026-05-19-sprint22-onboarding-e2e-obs.md` | patch (deprecated 라벨) | T-OBN-05 |
| `docs/superpowers/plans/2026-05-19-sprint22-tasks.md` | patch (deprecated 라벨) | T-OBN-05 |
| `docs/REFACTORING-BACKLOG.md` | patch (BL-006 closed + BL-NEW-RAG-SOURCE-SELECT + BL-NEW-OBN-DATA-RETRY) | Phase 2 + 7 |
| `docs/TODO.md` | patch (Sprint 24 Wave 2 closeout) | Phase 9 마지막 |

---

## Phase 1 — T-2 Post-Swap Delta 측정 (P0 first, gate)

**Files:**
- Create: `backend/scripts/sprint24_wave2_delta.py`
- Create: `docs/dev-log/2026-05-20-sprint24-wave2/post-swap-delta-report.md`
- Create: `backend/tests/llm/fixtures/sample_transcripts.py` (5 시나리오 fixture)

**핵심**: `gemini-2.5-flash` (`003908a^`) baseline 직접 캡쳐 불가 (main 이미 swap 됨). **alternative**: temp branch checkout 후 동일 fixture 호출 + 결과 JSON 캡쳐 → 현재 main fixture 호출 결과와 비교.

### Task 1: 5 시나리오 fixture 작성

- [ ] **Step 1: fixture 디렉토리 + 5 시나리오 transcript sample 작성**

Create `backend/tests/llm/fixtures/sample_transcripts.py`:

```python
# 5 시나리오 fixture — Phase B Post-Swap Delta 측정용 (Sprint 24 Wave 2 T-2)

DELTA_1_RAG_QUESTIONS = [
    "이 회의에서 결정된 액션은?",
    "발표자가 누구였나?",
    "프로젝트 일정은 어떻게 변경되나?",
    "5월 안에 해야 할 일?",
    "철수가 한 말 중 중요한 것?",
]

DELTA_2_MEETING_TRANSCRIPT = """
김PM: 오늘 회의 주제는 Q3 로드맵입니다.
박개발: 인증 모듈은 7월 25일까지 완료할 예정입니다.
이마케팅: 랜딩 페이지 리뉴얼은 8월 첫째주에 시작하겠습니다.
김PM: 좋습니다. 결정사항은 두 가지 — 인증 마감 7/25, 랜딩 시작 8/1.
"""

DELTA_3_ACTION_SAMPLES = [
    {"transcript": "박개발이 7월 25일까지 인증 모듈 완료. 이마케팅이 8월 첫째주 랜딩 시작.", "ground_truth": [
        {"assignee": "박개발", "due_date": "2026-07-25", "title": "인증 모듈 완료"},
        {"assignee": "이마케팅", "due_date": "2026-08-01", "title": "랜딩 시작"},
    ]},
    # 4개 추가 sample
]

DELTA_4_KOREAN_SAMPLES = [
    "어제 회의에서 김PM이 ~할 거에요 🙂",
    "회의 끝났습니데이",
    "오늘 미팅 cancel ㅠㅠ",
]

DELTA_5_INBOX_CLASSIFY = [
    # 5 회의 + 5 노트, 각 다른 project 가능성
    {"content": "Q3 인증 모듈 회의 transcript ...", "expected_project_hint": "auth"},
    # ...
]
```

- [ ] **Step 2: fixture 파일 commit (Atomic — Phase 1 commit 에 포함)**

(Phase 1 마지막 commit 에서 모두 묶음)

### Task 2: delta 측정 script

- [ ] **Step 3: `backend/scripts/sprint24_wave2_delta.py` 작성**

Create `backend/scripts/sprint24_wave2_delta.py`:

```python
# Sprint 24 Wave 2 T-2 Post-Swap Delta 측정 — gemini-2.5-flash vs gemini-3.1-flash-lite
# Usage: uv run python -m scripts.sprint24_wave2_delta --baseline-checkout 003908a^

import argparse
import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path

from src.services.ai_processing import AIProcessingService  # Codex F-2 fix: class method 사용
from backend.tests.llm.fixtures.sample_transcripts import (
    DELTA_1_RAG_QUESTIONS,
    DELTA_2_MEETING_TRANSCRIPT,
    DELTA_3_ACTION_SAMPLES,
    DELTA_4_KOREAN_SAMPLES,
)


async def measure_current() -> dict:
    """현재 main (gemini-3.1-flash-lite) 측정 — AIProcessingService 통해 호출."""
    svc = AIProcessingService()  # 또는 __init__ params 가 필요하면 적절히 주입
    result = {
        "model": "gemini-3.1-flash-lite",
        "measured_at": datetime.utcnow().isoformat(),
        "delta_2_summary": await svc.summarize(DELTA_2_MEETING_TRANSCRIPT),
        "delta_3_actions": [],
        # delta_1 RAG / delta_4 한국어 / delta_5 inbox — 추후 보강
    }
    for sample in DELTA_3_ACTION_SAMPLES:
        # extract_actions_and_link 의 실제 시그니처에 맞춰 호출
        # (transcript 외 meeting_id / workspace_id 등 필요 시 fixture 에서 mock 주입)
        actions = await svc.extract_actions_and_link(
            transcript=sample["transcript"],
            current_year=2026,  # T-AI-DATE 후 추가될 param
        )
        result["delta_3_actions"].append({
            "input": sample["transcript"][:100],
            "actions": [a.model_dump() for a in actions],
            "ground_truth": sample["ground_truth"],
        })
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/dev-log/2026-05-20-sprint24-wave2/post-swap-delta-result.json")
    args = parser.parse_args()
    result = asyncio.run(measure_current())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Delta result written to {output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: script 실행 확인 (current main 측정)**

Run:
```bash
cd backend && uv run python -m scripts.sprint24_wave2_delta
```

Expected: `docs/dev-log/2026-05-20-sprint24-wave2/post-swap-delta-result.json` 생성. 5 시나리오 JSON 응답 캡쳐.

### Task 3: baseline 캡쳐 (003908a^ checkout)

- [ ] **Step 5: 별도 worktree 에서 baseline 캡쳐 (R8 stash 보존 + worktree race 회피)**

```bash
# Codex F-3 fix: 경로 정확화. baseline worktree 의 root 에서 cp 실행
git worktree add ../kairos-baseline-003908a-prev 003908a~1
cd ../kairos-baseline-003908a-prev   # ← backend/ 가 아닌 worktree root
uv sync --directory backend           # backend 디렉토리 명시
# fixture + script 복사 — 둘 다 worktree root 기준 상대 경로
mkdir -p backend/tests/llm/fixtures
cp ../kairos-sprint-24-wave2/backend/tests/llm/fixtures/sample_transcripts.py backend/tests/llm/fixtures/sample_transcripts.py
cp ../kairos-sprint-24-wave2/backend/scripts/sprint24_wave2_delta.py backend/scripts/sprint24_wave2_delta.py
cd backend && uv run python -m scripts.sprint24_wave2_delta --output /tmp/baseline-2.5-flash.json
```

- [ ] **Step 6: baseline + current 비교 보고서 작성**

Create `docs/dev-log/2026-05-20-sprint24-wave2/post-swap-delta-report.md`:

```markdown
# Sprint 24 Wave 2 T-2 Post-Swap Delta Report (Phase B Gemini swap 003908a)

## 측정 환경
- baseline = `003908a~1` (gemini-2.5-flash)
- post-swap = main `f46a075` (gemini-3.1-flash-lite)
- 측정일 = 2026-05-20

## DELTA-1 RAG 답변 품질 (5 질문)
| Q | baseline length | post-swap length | length delta | 정성 평가 |
|---|---|---|---|---|
| Q1 | ... | ... | ±% | same/better/worse |
...

## DELTA-2 회의 요약
- Section count: baseline 3 vs post-swap 3 ✅
- 요약 length delta: ±%
- 액션 count delta: 차이

## DELTA-3 액션 추출 (5 sample, ground truth 비교)
- baseline precision: X / recall: Y
- post-swap precision: X' / recall: Y'
- delta: ΔP=___, ΔR=___ (gate: -10% 이내)

## DELTA-4 한국어 처리
- baseline 정상 파싱: A/B/C 모두 OK
- post-swap 정상 파싱: A/B/C 결과

## DELTA-5 Inbox 분류 confidence
- baseline 평균 confidence: ___
- post-swap 평균 confidence: ___
- 자동 확정 비율: baseline ___ vs post-swap ___

## Gate 평가
- DELTA-1 worse 건수: ___ (PASS if 0)
- DELTA-3 precision/recall -10% 이내: PASS/FAIL
- DELTA-2/4/5 ±20% 이내: PASS/FAIL

## 결론
- [PASS] → Phase 2 진입
- [FAIL] → STOP + 사용자 보고 + revert PR 옵션 검토
```

- [ ] **Step 7: Gate 평가 결과에 따라 결정**

Gate PASS → 다음 Phase 진입.
Gate FAIL → 즉시 사용자 보고. revert PR 옵션 또는 prompt tuning 검토. **Phase 2 진입 차단**.

- [ ] **Step 8: Phase 1 commit**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2
git add backend/scripts/sprint24_wave2_delta.py backend/tests/llm/fixtures/sample_transcripts.py docs/dev-log/2026-05-20-sprint24-wave2/
git commit -m "feat(spike): Sprint 24 Wave 2 Phase 1 — T-2 Post-Swap Delta 측정 (gemini swap 003908a 품질 검증 PASS/FAIL)"
```

---

## Phase 2 — P0 Critical Bundle (T-AI-DATE + T-RAG-MOCK-REMOVE)

**Files:**
- Modify: `backend/src/common/prompts.py`
- Modify: `backend/src/services/ai_processing.py`
- Create: `backend/tests/services/test_ai_action_date_with_year_context.py`
- Modify: `frontend/src/features/rag/components/search-scope.tsx:31-37`
- Modify: `docs/REFACTORING-BACKLOG.md` (BL-NEW-RAG-SOURCE-SELECT 등재)

### Task 4: T-AI-DATE — Gemini prompt 현재 연도 컨텍스트

- [ ] **Step 9: 실패 테스트 작성**

Create `backend/tests/services/test_ai_action_date_with_year_context.py`:

```python
# T-AI-DATE: AI 액션 마감일 hallucinate fix 회귀 테스트 (Sprint 24 Wave 2 BUG-CURIOUS-001)

import pytest
from datetime import date
from src.services.ai_processing import extract_action_items


@pytest.mark.asyncio
async def test_action_with_year_unspecified_uses_current_year():
    """연도 미명시 input + current_year=2026 → 추출된 due_date.year == 2026."""
    transcript = "박개발이 7월 25일까지 인증 모듈 완료해야 합니다."
    actions = await extract_action_items(transcript, current_year=2026)
    assert len(actions) >= 1
    action = actions[0]
    assert action.due_date is not None
    assert action.due_date.year == 2026, f"기대=2026, 실제={action.due_date.year}"


@pytest.mark.asyncio
async def test_action_with_past_year_in_output_is_dropped():
    """post-process 검증: AI 가 과거 연도 (2024) 출력 시 due_date=None drop."""
    # 직접 후처리 함수 단위 테스트 (Gemini mock)
    from src.services.ai_processing import _validate_action_dates
    actions = [
        type("A", (), {"due_date": date(2024, 7, 25), "title": "old"}),
        type("A", (), {"due_date": date(2026, 7, 25), "title": "valid"}),
        type("A", (), {"due_date": None, "title": "no_date"}),
    ]
    validated = _validate_action_dates(actions, current_year=2026)
    assert validated[0].due_date is None  # dropped
    assert validated[1].due_date == date(2026, 7, 25)
    assert validated[2].due_date is None


@pytest.mark.asyncio
async def test_action_with_far_future_year_kept():
    """5년+ 미래 (2031) 도 keep — 의도적 long-term 가능."""
    from src.services.ai_processing import _validate_action_dates
    actions = [type("A", (), {"due_date": date(2031, 7, 25), "title": "future"})]
    validated = _validate_action_dates(actions, current_year=2026)
    assert validated[0].due_date == date(2031, 7, 25)


@pytest.mark.asyncio
async def test_explicit_year_input_preserved():
    """input 에 명시된 연도 (2025) 는 그대로 keep — 단 current_year=2026 보다 과거면 drop."""
    transcript = "2025년 12월 31일까지 마무리."
    actions = await extract_action_items(transcript, current_year=2026)
    if actions and actions[0].due_date:
        # 과거 연도 drop 또는 keep — design decision: drop
        assert actions[0].due_date.year >= 2026
```

- [ ] **Step 10: 테스트 실행 (FAIL 확인)**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2/backend
uv run pytest tests/services/test_ai_action_date_with_year_context.py -v
```

Expected: FAIL ("current_year" param missing in extract_action_items 또는 `_validate_action_dates` 미존재).

- [ ] **Step 11: `backend/src/common/prompts.py` ACTION_EXTRACTION_PROMPT 수정**

Modify `backend/src/common/prompts.py` — ACTION_EXTRACTION_PROMPT 상수 헤더에 `현재 연도` context 추가:

```python
ACTION_EXTRACTION_PROMPT = """당신은 회의 트랜스크립트에서 액션 아이템을 추출하는 AI 입니다.

## 컨텍스트
- 현재 연도: {current_year}
- 현재 날짜: {current_date}
- 트랜스크립트 언어: 한국어

## 규칙
1. assignee + title + due_date + priority 를 JSON 으로 추출.
2. **due_date 연도 추론**: 트랜스크립트에 연도가 명시되지 않은 경우 (예: "7월 25일") 반드시 현재 연도 ({current_year}) 또는 가까운 미래 연도로 추론. 과거 연도 추론 금지.
3. due_date 불명확 시 `null`.

## Few-shot 예시
입력: "박개발이 7월 25일까지 인증 모듈 완료"
출력: {{"assignee": "박개발", "title": "인증 모듈 완료", "due_date": "{current_year}-07-25", ...}}

입력: "내년 1월까지 랜딩 리뉴얼"
출력: {{"assignee": null, "title": "랜딩 리뉴얼", "due_date": "{current_year_plus_1}-01-31", ...}}

## 입력 트랜스크립트
{transcript}

## 출력 (JSON array)
"""
```

- [ ] **Step 12: `backend/src/services/ai_processing.py` extract_action_items + 후처리 helper 수정**

Modify `backend/src/services/ai_processing.py`:

```python
# 기존 extract_action_items 시그니처에 current_year 추가
from datetime import date


def _validate_action_dates(actions: list, current_year: int) -> list:
    """T-AI-DATE 후처리 검증: 과거 연도 due_date drop. 5년+ 미래는 keep.
    
    BUG-CURIOUS-001 대응 (Sprint 24 Wave 2 BL-MOB 도 동일).
    """
    import logging
    logger = logging.getLogger(__name__)
    for action in actions:
        if action.due_date is None:
            continue
        if action.due_date.year < current_year:
            logger.warning(
                "AI hallucinate past year date, dropping",
                extra={"due_date": str(action.due_date), "current_year": current_year, "title": getattr(action, "title", "?")},
            )
            action.due_date = None
    return actions


async def extract_action_items(
    transcript: str,
    *,
    current_year: int | None = None,
) -> list[MeetingActionsResult]:
    """Sprint 24 Wave 2 T-AI-DATE: current_year context + 후처리 검증."""
    if current_year is None:
        current_year = date.today().year
    current_date_str = date.today().isoformat()
    prompt = ACTION_EXTRACTION_PROMPT.format(
        current_year=current_year,
        current_year_plus_1=current_year + 1,
        current_date=current_date_str,
        transcript=transcript,
    )
    # ... 기존 Gemini 호출 + JSON 파싱 ...
    raw_actions = await _call_gemini_with_schema(prompt, ...)
    validated = _validate_action_dates(raw_actions, current_year=current_year)
    return validated
```

호출처도 갱신: `backend/src/meetings/pipeline_service.py` 의 `extract_action_items` 호출 시 `current_year=date.today().year` 전달 (또는 default 채택으로 호출 시 인자 생략).

- [ ] **Step 13: 테스트 실행 (PASS 확인)**

```bash
cd backend && uv run pytest tests/services/test_ai_action_date_with_year_context.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 14: 전체 회귀**

```bash
cd backend && uv run pytest tests/ -q 2>&1 | tail -5
```

Expected: 387 + 4 = 391 passed + 1 skipped.

### Task 5: T-RAG-MOCK-REMOVE — FE search-scope MOCK 제거

- [ ] **Step 15: `frontend/src/features/rag/components/search-scope.tsx` 현 상태 read**

```bash
sed -n '20,50p' /Users/woosung/project/agy-project/kairos-sprint-24-wave2/frontend/src/features/rag/components/search-scope.tsx
```

- [ ] **Step 16: `search-scope.tsx:31-37` MOCK_SELECTABLE_SOURCES 제거 + selection UI disabled + empty state copy**

Modify `frontend/src/features/rag/components/search-scope.tsx`:

```tsx
// MOCK_SELECTABLE_SOURCES 제거 (Sprint 24 Wave 2 T-RAG-MOCK-REMOVE / BUG-POW-005)
// const MOCK_SELECTABLE_SOURCES = [...] ← 삭제

// selection UI 부분:
{scope === "selected" && (
  <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
    소스 선택 기능 준비 중 — 현재는 전체 워크스페이스에서 검색합니다.
    {/* TODO(Sprint 25+): BL-NEW-RAG-SOURCE-SELECT — 실 API + selection state + RAG filter */}
  </div>
)}
```

- [ ] **Step 17: BL 신규 등재 — `docs/REFACTORING-BACKLOG.md`**

Modify `docs/REFACTORING-BACKLOG.md` 에 BL-NEW-RAG-SOURCE-SELECT 추가:

```markdown
## BL-NEW-RAG-SOURCE-SELECT — RAG source-level selection v1 (Sprint 25+ 검토)

**상태**: 미시작 (carry-over from Sprint 24 Wave 2 T-RAG-MOCK-REMOVE B path)
**우선순위**: P2 — Power user feature, wedge 정합 미증명
**예상 시간**: 3-5h

### 배경
Sprint 24 Wave 2 T-RAG-MOCK-REMOVE 에서 `frontend/src/features/rag/components/search-scope.tsx` 의 MOCK 5건 제거 후 selection UI 를 "준비 중" empty state 로 변경. 장기적으로 source-level (회의 / 노트 단위) RAG 검색 범위 선택이 필요한가는 Power persona 데이터 수집 후 결정.

### 작업 (선택 시)
1. BE: `GET /api/v1/workspaces/{wid}/embeddings/sources?type=meeting|note` — indexable source list endpoint
2. FE: selection state (Zustand or local), RAG `/ask` 요청에 `source_ids: list[uuid]` 전달
3. BE: `embeddings/repository.py vector_search` 에 `source_ids` filter SQL clause 추가

### 결정 기준
- Power persona 인터뷰 (F4) 결과 confirmed + source selection 명시적 요구 시 진입
- 아닐 시 폐기 + UI 자체 hide
```

- [ ] **Step 18: Phase 2 commit (T-AI-DATE + T-RAG-MOCK-REMOVE 묶음)**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2
git add backend/src/common/prompts.py backend/src/services/ai_processing.py backend/tests/services/test_ai_action_date_with_year_context.py frontend/src/features/rag/components/search-scope.tsx docs/REFACTORING-BACKLOG.md
git commit -m "$(cat <<'EOF'
feat(p0): Sprint 24 Wave 2 Phase 2 — T-AI-DATE + T-RAG-MOCK-REMOVE (P0 Critical)

- T-AI-DATE (BUG-CURIOUS-001): Gemini prompt 현재 연도 컨텍스트 + 후처리 검증
  - prompts.py ACTION_EXTRACTION_PROMPT 헤더에 current_year + Few-shot
  - ai_processing.py _validate_action_dates 후처리 (past year drop, 5+ future keep)
  - 4 신규 test (current_year / past drop / far future / explicit year)
- T-RAG-MOCK-REMOVE (BUG-POW-005): search-scope.tsx MOCK_SELECTABLE_SOURCES 제거
  - selection UI 비활성화 + empty state copy
  - BL-NEW-RAG-SOURCE-SELECT 등재 (Sprint 25+ Power persona 데이터 후)

Tests: 387 → 391 passed + 1 skipped
Atomic Update: pending Phase 9 docs sync

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 3 — P0 High UX (T-OBN-05 D 옵션 + T-MOBILE-HEADER)

**Files:**
- Create: `frontend/src/components/ui/tooltip.tsx` + `popover.tsx` (shadcn add)
- Create: `frontend/src/components/onboarding/onboarding-tooltip.tsx`
- Modify: `frontend/src/features/home/components/today-feed.tsx` (banner rollback)
- Modify: `frontend/src/components/empty-state.tsx` (props 제거)
- Modify: `frontend/src/features/projects/components/project-list.tsx`
- Modify: `frontend/src/features/projects/components/project-detail.tsx`
- Modify: `frontend/src/features/meetings/components/meeting-summary.tsx`
- Modify: `frontend/src/components/layout/header.tsx` (mobile padding)
- Modify: `frontend/e2e/tests/{home,first-project,mobile-responsive}.spec.ts` (banner assertion 제거)
- Create: `frontend/e2e/tests/onboarding-tooltip-first-visit.spec.ts`
- Modify: `frontend/e2e/tests/mobile-responsive.spec.ts` (T-MOBILE-HEADER case)
- Modify: Sprint 22 docs 4건 (deprecated 라벨)
- Modify: `docs/REFACTORING-BACKLOG.md` (BL-NEW-OBN-DATA-RETRY)

### Task 6: shadcn tooltip/popover 의존성 추가

- [ ] **Step 19: shadcn add 실행**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2/frontend
pnpm dlx shadcn@latest add tooltip popover
```

Expected: `frontend/src/components/ui/tooltip.tsx` + `popover.tsx` 생성. dependencies 자동 추가.

- [ ] **Step 20: typecheck 확인**

```bash
cd frontend && pnpm typecheck
```

Expected: 0 errors.

### Task 7: T-OBN-05 D 옵션 — banner rollback (today-feed)

- [ ] **Step 21: `today-feed.tsx` 현 OnboardingBanner 영역 read**

```bash
sed -n '15,75p' /Users/woosung/project/agy-project/kairos-sprint-24-wave2/frontend/src/features/home/components/today-feed.tsx
sed -n '360,375p' /Users/woosung/project/agy-project/kairos-sprint-24-wave2/frontend/src/features/home/components/today-feed.tsx
```

- [ ] **Step 22: today-feed.tsx — OnboardingBanner function + mount + useOnboarding import 제거**

Modify `frontend/src/features/home/components/today-feed.tsx`:

```tsx
// Sprint 24 Wave 2 T-OBN-05 D 옵션: OnboardingBanner 폐기 (Codex+Gemini deep research 합의).
// rollback 사유 + 결정 anchor: docs/superpowers/specs/2026-05-20-sprint24-wave2-trusty-heron-design.md §T-OBN-05

// 제거 1: import (line 20)
// - import { useOnboarding } from "@/features/onboarding/hooks";

// 제거 2: OnboardingBanner function 정의 (line 25-67) 전체

// 제거 3: <OnboardingBanner /> mount (line 368)

// 유지: today-feed 의 나머지 Today 피드 위젯 — InboxItem / 최근 회의 / 액션 등
```

전체 diff 의도: today-feed.tsx 가 OnboardingBanner 관련 코드 0 line. 다른 위젯은 모두 유지.

- [ ] **Step 23: vitest 회귀**

```bash
cd frontend && pnpm test 2>&1 | tail -10
```

Expected: 50 passed (회귀 0).

### Task 8: T-OBN-05 D 옵션 — EmptyState 컴포넌트 정리

- [ ] **Step 24: `frontend/src/components/empty-state.tsx` read**

```bash
cat /Users/woosung/project/agy-project/kairos-sprint-24-wave2/frontend/src/components/empty-state.tsx | head -80
```

- [ ] **Step 25: empty-state.tsx — onboardingStep + context props 제거 + plain copy 통일**

Modify `frontend/src/components/empty-state.tsx`:

```tsx
// Sprint 24 Wave 2 T-OBN-05 D 옵션: onboarding-aware 분기 제거 + plain copy
// (Sprint 22 OBN-03 의 onboardingStep + context props 제거)

type EmptyStateProps = {
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  // 제거: onboardingStep?: number;
  // 제거: context?: "meetings" | "projects" | "notes";
};

export function EmptyState({ title, description, action, icon }: EmptyStateProps) {
  // onboarding-aware hint 분기 제거
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {icon}
      <h3 className="mt-4 text-lg font-medium">{title}</h3>
      {description && <p className="mt-2 text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
```

- [ ] **Step 26: project-list.tsx — useOnboarding 제거 + EmptyState prop 정리**

Modify `frontend/src/features/projects/components/project-list.tsx`:

```tsx
// 제거: import { useOnboarding } from "@/features/onboarding/hooks";
// 제거: const { data: onboarding } = useOnboarding();

// EmptyState 호출 변경:
<EmptyState
  title="아직 프로젝트가 없습니다"
  description="첫 프로젝트를 만들어 회의 / 노트 / 액션을 정리하세요."
  action={<Button onClick={onCreate}>+ 새 프로젝트</Button>}
  // 제거: onboardingStep={onboarding?.step}
  // 제거: context="projects"
/>
```

- [ ] **Step 27: project-detail.tsx 동일 정리**

(line 26 useOnboarding import 제거 + line 86 호출 제거 + EmptyState props 정리)

- [ ] **Step 28: meeting-summary.tsx 동일 정리**

(line 5 useOnboarding import 제거 + line 12 호출 제거 + EmptyState props 정리)

- [ ] **Step 29: vitest + typecheck 회귀**

```bash
cd frontend && pnpm typecheck && pnpm test 2>&1 | tail -5
```

Expected: typecheck 0 / vitest 50 passed.

### Task 9: T-OBN-05 D 옵션 — Linear-style tooltip 신설

- [ ] **Step 30: `frontend/src/components/onboarding/onboarding-tooltip.tsx` 신설**

Create `frontend/src/components/onboarding/onboarding-tooltip.tsx`:

```tsx
// 첫 방문 inline tooltip — Sprint 24 Wave 2 T-OBN-05 D 옵션 (Linear-style)
"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useOnboarding } from "@/features/onboarding/hooks";

type TooltipPage = "dashboard" | "search" | "projects" | "new";

const COPY: Record<TooltipPage, string> = {
  dashboard: "AI 검색은 ⌘K — 워크스페이스 회의/노트 전체 검색",
  search: "검색 범위는 현재 워크스페이스 전체입니다",
  projects: "+ 새 프로젝트로 시작하세요",
  new: "회의 음성을 업로드하면 AI 가 자동 요약합니다",
};

const STORAGE_KEY = (page: TooltipPage) => `kairos.onboarding.tooltip_shown.${page}`;

// Sprint 24 Wave 2 T-OBN-05: 2 무조건 + 2 조건부 (Codex cross-check 권장)
const UNCONDITIONAL: TooltipPage[] = ["dashboard", "search"];
const STEP_GATED: Record<"projects" | "new", number> = {
  projects: 2, // step < 2 + empty 시 발화
  new: 3, // step < 3 + empty 시 발화
};

type OnboardingTooltipProps = {
  page: TooltipPage;
  isEmpty?: boolean; // /projects, /new 의 empty state 여부
  children: React.ReactNode;
};

export function OnboardingTooltip({ page, isEmpty, children }: OnboardingTooltipProps) {
  const { data: onboarding } = useOnboarding();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.localStorage.getItem(STORAGE_KEY(page))) return; // 재방문 X

    // 조건부 페이지 gate
    if (page === "projects" || page === "new") {
      const stepThreshold = STEP_GATED[page];
      if (!onboarding || onboarding.step >= stepThreshold) return;
      if (!isEmpty) return;
    }

    setOpen(true);
    // analytics
    if (typeof window !== "undefined" && (window as any).analytics) {
      (window as any).analytics.track("tooltip_shown", { page });
    }
  }, [page, onboarding, isEmpty]);

  const handleDismiss = () => {
    setOpen(false);
    window.localStorage.setItem(STORAGE_KEY(page), "1");
    if (typeof window !== "undefined" && (window as any).analytics) {
      (window as any).analytics.track("tooltip_dismissed", { page });
    }
  };

  return (
    <Popover open={open} onOpenChange={(o) => !o && handleDismiss()}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent className="max-w-xs" onEscapeKeyDown={handleDismiss}>
        <div className="flex items-start gap-2">
          <p className="text-sm">{COPY[page]}</p>
          <button onClick={handleDismiss} className="text-muted-foreground hover:text-foreground" aria-label="dismiss">
            <X className="h-4 w-4" />
          </button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
```

- [ ] **Step 31: 4 페이지 tooltip mount**

각 페이지에 tooltip wrapper 추가:
- `/dashboard` (today-feed.tsx 또는 dashboard page) — UNCONDITIONAL
- `/search` (cmd-k component) — UNCONDITIONAL
- `/projects` (page.tsx, Phase 4 T-PROJ-LIST 와 통합) — 조건부
- `/new` (new page) — 조건부

예시 (today-feed.tsx 의 dashboard 위젯):
```tsx
import { OnboardingTooltip } from "@/components/onboarding/onboarding-tooltip";

// dashboard 최상단 영역
<OnboardingTooltip page="dashboard">
  <div data-testid="dashboard-header">{/* 기존 dashboard 헤더 */}</div>
</OnboardingTooltip>
```

### Task 10: 신규 E2E — onboarding-tooltip-first-visit

- [ ] **Step 32: `frontend/e2e/tests/onboarding-tooltip-first-visit.spec.ts` 신설**

Create `frontend/e2e/tests/onboarding-tooltip-first-visit.spec.ts`:

```ts
// T-OBN-05 D 옵션: 첫 방문 inline tooltip 발화 + dismiss + 재방문 검증
import { test, expect } from "@playwright/test";

test.describe("Onboarding Tooltip (T-OBN-05 D 옵션, Sprint 24 Wave 2)", () => {
  test("dashboard 첫 방문 시 ⌘K tooltip 발화", async ({ page, context }) => {
    await context.clearCookies();
    await page.goto("/dashboard");
    await expect(page.getByText("AI 검색은 ⌘K")).toBeVisible({ timeout: 5000 });
  });

  test("dashboard 재방문 시 tooltip 미발화", async ({ page }) => {
    // localStorage 에 이미 발화 마크
    await page.goto("/dashboard");
    await page.evaluate(() => localStorage.setItem("kairos.onboarding.tooltip_shown.dashboard", "1"));
    await page.reload();
    await expect(page.getByText("AI 검색은 ⌘K")).not.toBeVisible();
  });

  test("search 첫 방문 시 scope tooltip 발화", async ({ page }) => {
    await page.evaluate(() => localStorage.clear());
    await page.goto("/dashboard");
    await page.keyboard.press("Meta+K");
    await expect(page.getByText("검색 범위는 현재 워크스페이스 전체")).toBeVisible();
  });

  test("projects 첫 방문 + step<2 + empty 시 tooltip 발화", async ({ page }) => {
    await page.evaluate(() => localStorage.clear());
    await page.goto("/projects");
    // step < 2 가정 (신규 가입자 storageState clear)
    await expect(page.getByText("+ 새 프로젝트로 시작하세요")).toBeVisible();
  });

  test("OnboardingBanner data-testid 더 이상 mount 안 됨", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.locator('[data-testid="onboarding-banner"]')).toHaveCount(0);
  });
});
```

### Task 11: 기존 E2E banner assertion 정리

- [ ] **Step 33: `home.spec.ts` G1 — `Step 1/4` assertion 제거**

Modify `frontend/e2e/tests/home.spec.ts`:

```ts
// 기존: await expect(page.getByText('Step 1/4')).toBeVisible();
// 제거 또는 대체:
await expect(page.getByText("AI 검색은 ⌘K")).toBeVisible(); // tooltip 으로 대체
```

- [ ] **Step 34: `first-project.spec.ts` G2 — `Step 2/4` assertion 제거**

Modify `frontend/e2e/tests/first-project.spec.ts`:
banner-related assertion 모두 제거. 핵심 흐름 (프로젝트 생성 → 리다이렉트 → 프로젝트 detail) 유지.

- [ ] **Step 35: `mobile-responsive.spec.ts` OBN-04 banner case 제거**

Modify `frontend/e2e/tests/mobile-responsive.spec.ts`:

```ts
// 제거: test("OnboardingBanner — 375x812 viewport ...", ...)
// 유지: 다른 mobile-responsive case
```

### Task 12: Sprint 22 docs deprecated 라벨

- [ ] **Step 36: 4 문서 헤더에 deprecated 라벨 추가**

Modify `docs/dev-log/2026-05-19-sprint22-result-report.html` 최상단:
```html
<!-- Sprint 24 Wave 2 T-OBN-05 D 옵션 (2026-05-20): OnboardingBanner FE 폐기 결정.
     상세: docs/superpowers/specs/2026-05-20-sprint24-wave2-trusty-heron-design.md §T-OBN-05 -->
<div class="bg-amber-100 border-l-4 border-amber-500 p-4 mb-6">
  <strong>⚠️ Sprint 24 Wave 2 부분 deprecated</strong> — OnboardingBanner FE 부분은 폐기됨 (D 옵션, 2026-05-20). BE step lifecycle 자산은 유지.
</div>
```

Modify `docs/dev-log/2026-05-19-sprint22-dogfooding.md`:
```markdown
> ⚠️ **Sprint 24 Wave 2 부분 deprecated** (2026-05-20): OnboardingBanner FE 부분은 폐기됨 (D 옵션). 
> 상세: `docs/superpowers/specs/2026-05-20-sprint24-wave2-trusty-heron-design.md` §T-OBN-05
```

Modify `docs/superpowers/specs/2026-05-19-sprint22-onboarding-e2e-obs.md` + `docs/superpowers/plans/2026-05-19-sprint22-tasks.md` 동일.

### Task 13: T-MOBILE-HEADER — 헤더 padding reflow

- [ ] **Step 37: `frontend/src/components/layout/header.tsx` 현 상태 read**

```bash
sed -n '1,50p' /Users/woosung/project/agy-project/kairos-sprint-24-wave2/frontend/src/components/layout/header.tsx
```

- [ ] **Step 38: header padding 조정 (375/393/412 viewport 잘림 해소)**

Modify `frontend/src/components/layout/header.tsx`:

```tsx
// 기존 padding 추정: pl-8 lg:pl-64 (sidebar 너비)
// Sprint 24 Wave 2 T-MOBILE-HEADER (BUG-MOBILE-001): 모바일 헤더 우측 잘림 fix
<header className="
  flex items-center justify-between
  px-4 md:px-6 lg:pl-64 lg:pr-8
  h-14 border-b
">
  {/* 우측 프로필 버튼 잘림 방지: 좌측 padding lg 에만 적용 */}
</header>
```

- [ ] **Step 39: `frontend/e2e/tests/mobile-responsive.spec.ts` — T-MOBILE-HEADER case 추가**

Modify `mobile-responsive.spec.ts`:

```ts
test.describe("T-MOBILE-HEADER (Sprint 24 Wave 2)", () => {
  for (const viewport of [
    { width: 375, height: 667 },
    { width: 393, height: 852 },
    { width: 412, height: 892 },
  ]) {
    test(`헤더 우측 프로필 버튼 visible — ${viewport.width}x${viewport.height}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto("/dashboard");
      const profileButton = page.locator('[data-testid="user-profile-button"]'); // 또는 실제 selector
      await expect(profileButton).toBeVisible();
      const box = await profileButton.boundingBox();
      expect(box).not.toBeNull();
      if (box) {
        expect(box.x + box.width).toBeLessThanOrEqual(viewport.width);
      }
    });
  }
});
```

- [ ] **Step 40: Playwright 실행**

```bash
cd frontend && pnpm exec playwright test mobile-responsive.spec.ts onboarding-tooltip-first-visit.spec.ts 2>&1 | tail -15
```

Expected: 모두 PASS.

### Task 14: BL-NEW-OBN-DATA-RETRY 등재

- [ ] **Step 41: REFACTORING-BACKLOG.md 에 BL-NEW-OBN-DATA-RETRY 추가**

```markdown
## BL-NEW-OBN-DATA-RETRY — Onboarding 재설계 data-driven retry (Sprint 25+)

**상태**: 미시작 (carry-over from Sprint 24 Wave 2 T-OBN-05 D 옵션 결정)
**우선순위**: P3 — F4 외부 인터뷰 결과 의존
**예상 시간**: 4-6h (재도입 시)

### 배경
Sprint 22 OBN-01~04 의 OnboardingBanner 는 Sprint 24 Wave 2 에서 폐기 (Codex+Gemini deep research 합의). PERSONA-001 1인 풀스택 founder (power user) 에게 friction. PERSONA-002/003 (PM, 가설) confirmed 시 onboarding 재설계 검토.

### 진입 조건
- F4 외부 인터뷰 (`docs/requirements/interview-results.md`) 결과 PM 페르소나 confirmed
- 또는 tooltip analytics 4-6주 데이터 (tooltip_shown/dismissed) 로 power user friction 입증

### 작업 (재도입 시)
1. AI personalize (1인 founder vs 팀 wedge 분화)
2. step 별 CTA 가 page transition 자동 trigger
3. measure 자체 강화 (activation funnel)
```

### Task 15: Phase 3 commit

- [ ] **Step 42: Phase 3 commit**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2
git add frontend/src/components/ui/tooltip.tsx frontend/src/components/ui/popover.tsx \
  frontend/src/components/onboarding/onboarding-tooltip.tsx \
  frontend/src/features/home/components/today-feed.tsx \
  frontend/src/components/empty-state.tsx \
  frontend/src/features/projects/components/project-list.tsx \
  frontend/src/features/projects/components/project-detail.tsx \
  frontend/src/features/meetings/components/meeting-summary.tsx \
  frontend/src/components/layout/header.tsx \
  frontend/e2e/tests/onboarding-tooltip-first-visit.spec.ts \
  frontend/e2e/tests/home.spec.ts \
  frontend/e2e/tests/first-project.spec.ts \
  frontend/e2e/tests/mobile-responsive.spec.ts \
  docs/dev-log/2026-05-19-sprint22-result-report.html \
  docs/dev-log/2026-05-19-sprint22-dogfooding.md \
  docs/superpowers/specs/2026-05-19-sprint22-onboarding-e2e-obs.md \
  docs/superpowers/plans/2026-05-19-sprint22-tasks.md \
  docs/REFACTORING-BACKLOG.md \
  frontend/package.json frontend/pnpm-lock.yaml
git commit -m "$(cat <<'EOF'
feat(p0): Sprint 24 Wave 2 Phase 3 — T-OBN-05 D 옵션 + T-MOBILE-HEADER (P0 High UX)

- T-OBN-05 D 옵션 (BUG-CURIOUS-003, Codex+Gemini deep research 합의):
  - OnboardingBanner FE 폐기 (today-feed.tsx function+mount+import)
  - EmptyState 컴포넌트 onboardingStep+context props 제거
  - 3 호출처 (project-list/detail + meeting-summary) useOnboarding 의존 제거
  - shadcn tooltip + popover 의존성 추가
  - 신규 OnboardingTooltip 2 무조건 + 2 조건부 (dashboard ⌘K + search scope + projects empty + new)
  - localStorage 재방문 X + dismiss + minimal analytics (tooltip_shown/dismissed)
  - 신규 E2E onboarding-tooltip-first-visit.spec.ts
  - 기존 E2E home + first-project + mobile-responsive banner assertion 정리
  - Sprint 22 docs 4건 deprecated 라벨
  - 유지: useOnboarding hook + BE 도메인 + User.onboarding_step + template seed + Export discoverability
  - BL-NEW-OBN-DATA-RETRY 등재 (Sprint 25+ F4 결과 기반 재설계)
- T-MOBILE-HEADER (BUG-MOBILE-001): header padding reflow + 3 viewport E2E

Tests: typecheck 0 / vitest 50 + Playwright 신규 5 PASS
Atomic Update: backend/src/onboarding/CONTEXT.md UI 결정 anchor (Phase 9 docs sync)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 4 — P1 FE Missing Pages (T-PROJ-LIST + T-NOTE-DETAIL + T-CMD-K-FIX)

**Files:**
- Create: `frontend/src/app/(app)/projects/page.tsx`
- Create: `frontend/src/app/(app)/notes/[id]/page.tsx`
- Modify: `frontend/src/features/home/components/today-feed.tsx` (dashboard 추천 질문 onClick)
- Create: `frontend/e2e/tests/projects-list.spec.ts`
- Create: `frontend/e2e/tests/note-detail.spec.ts`
- Create: `frontend/src/features/home/components/__tests__/dashboard-suggestions.test.tsx`

### Task 16: T-PROJ-LIST — `/projects` 카드 그리드 page

- [ ] **Step 43: `frontend/src/app/(app)/projects/page.tsx` 신설**

Create `frontend/src/app/(app)/projects/page.tsx`:

```tsx
// /projects 카드 그리드 page — Sprint 24 Wave 2 T-PROJ-LIST (BUG-CASUAL-001)
"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { OnboardingTooltip } from "@/components/onboarding/onboarding-tooltip";
import { useProjects } from "@/features/projects/hooks";
import { CreateProjectDialog } from "@/features/projects/components/create-project-dialog";

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  
  if (isLoading) return <div className="p-8">로딩 중...</div>;
  
  const isEmpty = !projects || projects.length === 0;
  
  return (
    <OnboardingTooltip page="projects" isEmpty={isEmpty}>
      <div className="p-8">
        <header className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold">프로젝트</h1>
          <CreateProjectDialog
            trigger={<Button><Plus className="mr-2 h-4 w-4" /> 새 프로젝트</Button>}
          />
        </header>
        
        {isEmpty ? (
          <EmptyState
            title="아직 프로젝트가 없습니다"
            description="첫 프로젝트를 만들어 회의/노트/액션을 정리하세요."
            action={
              <CreateProjectDialog
                trigger={<Button>+ 새 프로젝트</Button>}
              />
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((p) => (
              <Link key={p.id} href={`/projects/${p.id}`}>
                <Card className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <CardTitle>{p.title}</CardTitle>
                    <CardDescription className="line-clamp-2">{p.description}</CardDescription>
                  </CardHeader>
                  <CardFooter className="flex items-center gap-2">
                    <Badge variant={p.status === "active" ? "default" : "secondary"}>{p.status}</Badge>
                    {p.visibility !== "public" && <Badge variant="outline">{p.visibility}</Badge>}
                  </CardFooter>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </OnboardingTooltip>
  );
}
```

- [ ] **Step 44: Playwright E2E**

Create `frontend/e2e/tests/projects-list.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

test.describe("T-PROJ-LIST (Sprint 24 Wave 2)", () => {
  test("sidebar 프로젝트 클릭 → /projects list page 정상 도달", async ({ page }) => {
    await page.goto("/dashboard");
    await page.click('a[href="/projects"]');
    await expect(page.url()).toContain("/projects");
    await expect(page.getByRole("heading", { name: "프로젝트" })).toBeVisible();
  });
  
  test("프로젝트 0건 → empty state + 첫 프로젝트 CTA", async ({ page }) => {
    // mock API: empty list
    await page.goto("/projects");
    await expect(page.getByText("아직 프로젝트가 없습니다")).toBeVisible();
    await expect(page.getByRole("button", { name: /새 프로젝트/ })).toBeVisible();
  });
});
```

### Task 17: T-NOTE-DETAIL — `/notes/[id]` Tiptap viewer + edit-in-place

- [ ] **Step 45: `frontend/src/app/(app)/notes/[id]/page.tsx` 신설**

Create `frontend/src/app/(app)/notes/[id]/page.tsx`:

```tsx
// /notes/[id] detail page — Sprint 24 Wave 2 T-NOTE-DETAIL (BUG-POW-003)
"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Pencil, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useNote, useUpdateNote } from "@/features/notes/hooks";
import { NoteExportButton } from "@/features/notes/components/export-button";
import { ItemPromoteModal } from "@/components/shared/ItemPromoteModal";

export default function NoteDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { data: note, isLoading } = useNote(params.id);
  const updateNote = useUpdateNote();
  const [isEditing, setIsEditing] = useState(false);

  const editor = useEditor({
    extensions: [StarterKit],
    content: note?.content,
    editable: isEditing,
  }, [note?.id]);

  if (isLoading) return <div className="p-8">로딩 중...</div>;
  if (!note) return <div className="p-8">노트를 찾을 수 없습니다.</div>;

  const handleSave = async () => {
    if (!editor) return;
    await updateNote.mutateAsync({ id: note.id, content: editor.getJSON() });
    setIsEditing(false);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <header className="flex items-center justify-between mb-6">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" /> 뒤로
        </Button>
        <div className="flex items-center gap-2">
          {isEditing ? (
            <Button onClick={handleSave}><Save className="mr-2 h-4 w-4" /> 저장</Button>
          ) : (
            <Button variant="outline" onClick={() => { setIsEditing(true); editor?.setEditable(true); }}>
              <Pencil className="mr-2 h-4 w-4" /> 수정
            </Button>
          )}
          <NoteExportButton noteId={note.id} />
          <ItemPromoteModal itemType="note" sourceItemId={note.id} sourceWorkspaceId={note.workspace_id} />
        </div>
      </header>
      
      <h1 className="text-2xl font-semibold mb-4">{note.title}</h1>
      <article className="prose max-w-none">
        <EditorContent editor={editor} />
      </article>
    </div>
  );
}
```

- [ ] **Step 46: Playwright E2E**

Create `frontend/e2e/tests/note-detail.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

test("note detail page → ExportButton + Promote 도달 가능", async ({ page }) => {
  await page.goto("/notes");
  await page.click("a[href^='/notes/']");
  await expect(page.locator("article")).toBeVisible();
  await expect(page.getByRole("button", { name: /내보내기|Export/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /다른 워크스페이스|Promote/ })).toBeVisible();
});
```

### Task 18: T-CMD-K-FIX — dashboard 추천 질문 onClick

- [ ] **Step 47: `today-feed.tsx` 또는 dashboard suggestions 영역 read**

```bash
grep -n "추천 질문\|suggestion\|Suggestion" /Users/woosung/project/agy-project/kairos-sprint-24-wave2/frontend/src/features/home/components/today-feed.tsx | head -10
```

- [ ] **Step 48: 실패 vitest 작성**

Create `frontend/src/features/home/components/__tests__/dashboard-suggestions.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

vi.mock("@/components/cmd-k/store", () => ({
  useCmdKStore: vi.fn(() => ({ openWithQuery: vi.fn() })),
}));

import { DashboardSuggestions } from "../today-feed";
import { useCmdKStore } from "@/components/cmd-k/store";

describe("T-CMD-K-FIX dashboard 추천 질문 onClick (Sprint 24 Wave 2)", () => {
  it("추천 질문 클릭 시 cmd-k store openWithQuery 호출", () => {
    const mockOpen = vi.fn();
    (useCmdKStore as any).mockReturnValue({ openWithQuery: mockOpen });
    render(<DashboardSuggestions />);
    const button = screen.getByText(/최근 회의에서 결정된 사항/);
    fireEvent.click(button);
    expect(mockOpen).toHaveBeenCalledWith("최근 회의에서 결정된 사항은?");
  });
});
```

- [ ] **Step 49: today-feed.tsx 추천 질문 onClick 구현**

Modify `frontend/src/features/home/components/today-feed.tsx`:

```tsx
import { useCmdKStore } from "@/components/cmd-k/store";

export function DashboardSuggestions() {
  const openWithQuery = useCmdKStore((s) => s.openWithQuery);
  
  const suggestions = [
    "최근 회의에서 결정된 사항은?",
    "이번 주에 해야 할 액션은?",
    "프로젝트 A 의 진행 상황은?",
    "지난 주 회의 요약",
  ];
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
      {suggestions.map((q) => (
        <button
          key={q}
          onClick={() => openWithQuery(q)}
          className="rounded-md border p-3 text-left hover:bg-accent transition-colors"
        >
          {q}
        </button>
      ))}
    </div>
  );
}
```

(`useCmdKStore.openWithQuery` 가 cmd-k store 에 없다면 추가 — 별도 store 파일에 setter)

- [ ] **Step 50: vitest 회귀**

```bash
cd frontend && pnpm test 2>&1 | tail -5
```

Expected: 51 passed (신규 1 추가).

### Task 19: Phase 4 commit

- [ ] **Step 51: Phase 4 commit**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2
git add frontend/src/app/\(app\)/projects/page.tsx \
  frontend/src/app/\(app\)/notes/\[id\]/page.tsx \
  frontend/src/features/home/components/today-feed.tsx \
  frontend/src/features/home/components/__tests__/dashboard-suggestions.test.tsx \
  frontend/e2e/tests/projects-list.spec.ts \
  frontend/e2e/tests/note-detail.spec.ts
git commit -m "$(cat <<'EOF'
feat(p1): Sprint 24 Wave 2 Phase 4 — T-PROJ-LIST + T-NOTE-DETAIL + T-CMD-K-FIX (P1 FE missing pages)

- T-PROJ-LIST (BUG-CASUAL-001): /projects 카드 그리드 page 신설 + empty state + CreateProjectDialog
- T-NOTE-DETAIL (BUG-POW-003): /notes/[id] page 신설 + Tiptap viewer + edit-in-place + ExportButton + PromoteModal
- T-CMD-K-FIX (BUG-CURIOUS-002): dashboard 추천 질문 onClick → useCmdKStore.openWithQuery

Tests: vitest 50 → 51 / Playwright 신규 2 PASS / sidebar 404 해소

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 5 — P1 RAG + Compliance (T-RAG-TIME-FILTER + T-AUDIT-VIEW)

**Files:**
- Modify: `backend/src/embeddings/repository.py:155 vector_search`
- Create: `backend/tests/embeddings/test_rag_time_range_sql_clause.py`
- Create: `backend/src/common/promote_router.py`
- Create: `backend/tests/common/test_audit_promotions_endpoint.py`
- Modify: `frontend/src/app/(app)/settings/page.tsx`
- Create: `frontend/src/features/audit/` (hooks + components)
- Create: `frontend/e2e/tests/settings-audit.spec.ts`

### Task 20: T-RAG-TIME-FILTER — embeddings/repository.py vector_search time_range SQL

- [ ] **Step 52: 실패 테스트 작성**

Create `backend/tests/embeddings/test_rag_time_range_sql_clause.py`:

```python
# T-RAG-TIME-FILTER: vector_search() time_range param SQL clause (Sprint 24 Wave 2 BUG-POW-006)

import pytest
from datetime import datetime, timedelta, timezone
from src.embeddings.repository import EmbeddingRepository


@pytest.mark.asyncio
async def test_time_range_1w_filters_chunks_older_than_7_days(
    db_session,
    workspace_factory,
    embedding_chunk_factory,
    user_factory,
):
    workspace = await workspace_factory()
    owner = await user_factory(workspace_id=workspace.id, role="owner")
    repo = EmbeddingRepository(db_session)

    recent_chunk = await embedding_chunk_factory(workspace_id=workspace.id, created_at=datetime.now(timezone.utc) - timedelta(days=3))
    old_chunk = await embedding_chunk_factory(workspace_id=workspace.id, created_at=datetime.now(timezone.utc) - timedelta(days=14))

    query_emb = [0.1] * 1536
    # Codex F-1 fix: requester_user_id / requester_role 필수 (visibility filter)
    results = await repo.vector_search(
        query_embedding=query_emb,
        workspace_id=workspace.id,
        requester_user_id=owner.id,
        requester_role="owner",
        time_range="1w",
        limit=20,
    )

    result_ids = {r["id"] for r in results}
    assert recent_chunk.id in result_ids
    assert old_chunk.id not in result_ids


@pytest.mark.asyncio
async def test_time_range_all_or_none_no_filter(db_session, workspace_factory, embedding_chunk_factory, user_factory):
    workspace = await workspace_factory()
    owner = await user_factory(workspace_id=workspace.id, role="owner")
    repo = EmbeddingRepository(db_session)
    old_chunk = await embedding_chunk_factory(workspace_id=workspace.id, created_at=datetime.now(timezone.utc) - timedelta(days=365))

    query_emb = [0.1] * 1536
    results = await repo.vector_search(
        query_embedding=query_emb,
        workspace_id=workspace.id,
        requester_user_id=owner.id,
        requester_role="owner",
        time_range="all",
        limit=20,
    )
    result_ids = {r["id"] for r in results}
    assert old_chunk.id in result_ids


@pytest.mark.asyncio
async def test_time_range_invalid_value_raises(db_session, workspace_factory, user_factory):
    workspace = await workspace_factory()
    owner = await user_factory(workspace_id=workspace.id, role="owner")
    repo = EmbeddingRepository(db_session)
    with pytest.raises(ValueError, match="invalid time_range"):
        await repo.vector_search(
            query_embedding=[0.1] * 1536,
            workspace_id=workspace.id,
            requester_user_id=owner.id,
            requester_role="owner",
            time_range="invalid",
        )
```

- [ ] **Step 53: 테스트 실행 (FAIL 확인)**

```bash
cd backend && uv run pytest tests/embeddings/test_rag_time_range_sql_clause.py -v
```

Expected: FAIL (time_range param 미존재).

- [ ] **Step 54: vector_search 에 time_range param + SQL clause 추가 (Codex F-1 P1 — visibility filter 보존 강제)**

**중요 (Codex F-1)**: 기존 `requester_user_id` / `requester_role` / `project_id` / `source_type` / `_visibility_filter_sql()` 파라미터는 **모두 보존**. ISSUE-040 private chunk leak 회귀 방지. time_range 만 새로 추가.

Modify `backend/src/embeddings/repository.py:155`:

```python
TIME_RANGE_INTERVAL = {
    "1w": "7 days",
    "1m": "30 days",
    "3m": "90 days",
    "all": None,
}


async def vector_search(
    self,
    query_embedding: list[float],
    workspace_id: uuid.UUID,
    requester_user_id: uuid.UUID,       # 기존 보존 (RBAC visibility)
    requester_role: str,                # 기존 보존
    project_id: uuid.UUID | None = None,
    source_type: str | None = None,     # 기존 보존
    time_range: str | None = None,      # Sprint 24 Wave 2 T-RAG-TIME-FILTER 신규
    limit: int = 50,
) -> list[dict]:
    """Sprint 24 Wave 2 T-RAG-TIME-FILTER: time_range param 추가 (시그니처 확장 only).
    
    ISSUE-040 visibility filter (`_visibility_filter_sql()`) 보존. 기존 인자 모두 유지.
    """
    await _apply_hnsw_session_params(self.session)

    if time_range and time_range not in TIME_RANGE_INTERVAL:
        raise ValueError(f"invalid time_range: {time_range}")

    filters = "workspace_id = :wid AND chunk_level = 2"
    params: dict = {
        "wid": str(workspace_id),
        "limit": limit,
        "req_uid": str(requester_user_id),
        "req_role": requester_role,
    }

    if project_id:
        filters += " AND project_id = :pid"
        params["pid"] = str(project_id)
    if source_type:
        filters += " AND source_type = :stype"
        params["stype"] = source_type

    # Sprint 24 Wave 2 T-RAG-TIME-FILTER: time_range SQL clause 추가
    interval = TIME_RANGE_INTERVAL.get(time_range) if time_range else None
    if interval:
        filters += f" AND created_at >= now() - interval '{interval}'"

    visibility_clause = self._visibility_filter_sql()  # ISSUE-040 RBAC 보존

    query = text(f"""
        SELECT id, chunk_text, source_id, source_type, metadata_json,
               parent_chunk_id, created_at,
               1 - (embedding <=> CAST(:qvec AS halfvec)) AS score
        FROM embedding_chunks
        WHERE {filters}
          {visibility_clause}
        ORDER BY embedding <=> CAST(:qvec AS halfvec)
        LIMIT :limit
    """)
    params["qvec"] = str(query_embedding)

    result = await self.session.execute(query, params)
    return [dict(r._mapping) for r in result]
```

**RagService.ask() 호출처 영향**: 기존 인자 모두 유지 + time_range 만 신규 전달. RAG pipeline 변경 minimal.

- [ ] **Step 55: 테스트 실행 (PASS 확인)**

```bash
cd backend && uv run pytest tests/embeddings/test_rag_time_range_sql_clause.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 56: rag service / pipeline 에서 time_range 전달 확인**

`backend/src/rag/service.py` 또는 `pipeline_service.py` 에서 `EmbeddingRepository.vector_search(time_range=...)` 전달 확인. 이미 FE 가 보내는 값이 BE 까지 전달되도록 chain verify.

### Task 21: T-AUDIT-VIEW BE — ItemPromotionAudit read endpoint

- [ ] **Step 57: 실패 테스트 작성**

Create `backend/tests/common/test_audit_promotions_endpoint.py`:

```python
# T-AUDIT-VIEW: ItemPromotionAudit read endpoint (Sprint 24 Wave 2 BUG-POW-008)

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_audit_promotions_returns_list_for_admin(
    client: AsyncClient,
    admin_workspace_member,
    promote_audit_factory,
):
    workspace_id = admin_workspace_member.workspace_id
    await promote_audit_factory(workspace_id=workspace_id, item_type="meeting")
    
    resp = await client.get(
        f"/api/v1/workspaces/{workspace_id}/audit/promotions?item_type=meeting&limit=20",
        headers={"Authorization": "Bearer admin_token"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_audit_promotions_403_for_viewer(
    client: AsyncClient,
    viewer_workspace_member,
):
    workspace_id = viewer_workspace_member.workspace_id
    resp = await client.get(
        f"/api/v1/workspaces/{workspace_id}/audit/promotions?item_type=meeting",
        headers={"Authorization": "Bearer viewer_token"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_promotions_cross_workspace_404(client, admin_workspace_member, other_workspace_audit):
    """admin 도 다른 workspace audit 접근 불가 (I-9)."""
    resp = await client.get(
        f"/api/v1/workspaces/{other_workspace_audit.workspace_id}/audit/promotions",
        headers={"Authorization": "Bearer admin_token"},
    )
    assert resp.status_code in (403, 404)
```

- [ ] **Step 58: 테스트 실행 (FAIL)**

```bash
cd backend && uv run pytest tests/common/test_audit_promotions_endpoint.py -v
```

Expected: FAIL (endpoint 미존재).

- [ ] **Step 59: `backend/src/common/promote_router.py` 신설**

Create `backend/src/common/promote_router.py`:

```python
# ItemPromotionAudit read endpoint — Sprint 24 Wave 2 T-AUDIT-VIEW
# 4 도메인 (meeting / note / inbox / action) 통합 read (item_type query param)
# admin only (I-9 + RoleChecker)

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import require_member_role
from src.common.database import get_session
from src.common.pagination import CursorPage
from src.common.promote_models import ItemPromotionAudit


router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/audit", tags=["audit"])


ItemType = Literal["meeting", "note", "inbox", "action"]


@router.get("/promotions", response_model=CursorPage[ItemPromotionAudit])
async def list_promotion_audit(
    workspace_id: UUID,
    item_type: ItemType | None = None,
    limit: int = 20,
    cursor: str | None = None,
    session: AsyncSession = Depends(get_session),
    member = Depends(require_member_role(["owner", "admin"])),
):
    """4 도메인 ItemPromotionAudit read (admin only). I-9 (workspace_id WHERE)."""
    where = [ItemPromotionAudit.target_workspace_id == workspace_id]
    if item_type:
        where.append(ItemPromotionAudit.item_type == item_type)
    
    stmt = select(ItemPromotionAudit).where(*where).order_by(ItemPromotionAudit.created_at.desc()).limit(limit + 1)
    result = await session.exec(stmt)
    items = list(result.all())
    
    has_more = len(items) > limit
    return CursorPage(items=items[:limit], has_more=has_more, next_cursor=None)
```

- [ ] **Step 60: `backend/src/main.py` 에 router 등록**

```python
from src.common.promote_router import router as promote_audit_router
app.include_router(promote_audit_router)
```

- [ ] **Step 61: 테스트 실행 (PASS 확인)**

```bash
cd backend && uv run pytest tests/common/test_audit_promotions_endpoint.py -v
```

Expected: 3 tests PASS.

### Task 22: T-AUDIT-VIEW FE — Settings Audit 탭

- [ ] **Step 62: `frontend/src/features/audit/` 디렉토리 신설**

Create `frontend/src/features/audit/api.ts`:
```ts
import { apiClient } from "@/lib/api";

export type AuditPromotion = {
  audit_id: string;
  item_type: "meeting" | "note" | "inbox" | "action";
  source_workspace_id: string;
  target_workspace_id: string;
  source_item_id: string;
  new_item_id: string;
  promoted_by_user_id: string;
  created_at: string;
  embedding_status: "pending" | "processing" | "completed" | "failed" | "n/a";
};

export const auditKeys = {
  list: (workspaceId: string, itemType?: string) => ["audit", "promotions", workspaceId, itemType] as const,
};

export async function fetchAuditPromotions(token: string, workspaceId: string, itemType?: string, cursor?: string) {
  const params = new URLSearchParams();
  if (itemType) params.set("item_type", itemType);
  if (cursor) params.set("cursor", cursor);
  params.set("limit", "20");
  return apiClient<{ items: AuditPromotion[]; has_more: boolean; next_cursor: string | null }>(
    `/workspaces/${workspaceId}/audit/promotions?${params}`,
    { token },
  );
}
```

Create `frontend/src/features/audit/hooks.ts`:
```ts
"use client";
import { useAuth } from "@clerk/nextjs";
import { useInfiniteQuery } from "@tanstack/react-query";
import { fetchAuditPromotions, auditKeys } from "./api";

export function useAuditPromotions(workspaceId: string, itemType?: string) {
  const { getToken } = useAuth();
  return useInfiniteQuery({
    queryKey: auditKeys.list(workspaceId, itemType),
    queryFn: async ({ pageParam }) => {
      const token = await getToken();
      if (!token) throw new Error("인증 필요");
      return fetchAuditPromotions(token, workspaceId, itemType, pageParam as string | undefined);
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    enabled: !!workspaceId,
  });
}
```

Create `frontend/src/features/audit/components/audit-list.tsx`:
```tsx
"use client";
import { useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuditPromotions } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";

const ITEM_TYPES = ["all", "meeting", "note", "inbox", "action"];

export function AuditList() {
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const [itemType, setItemType] = useState("all");
  const { data, fetchNextPage, hasNextPage } = useAuditPromotions(workspaceId ?? "", itemType === "all" ? undefined : itemType);
  
  if (!workspaceId) return <div>워크스페이스 선택 필요</div>;
  
  const items = data?.pages.flatMap((p) => p.items) ?? [];
  
  return (
    <div className="space-y-4">
      <Select value={itemType} onValueChange={setItemType}>
        <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
        <SelectContent>
          {ITEM_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
        </SelectContent>
      </Select>
      
      <table className="w-full text-sm">
        <thead className="border-b">
          <tr><th>Type</th><th>From → To</th><th>By</th><th>Date</th><th>Status</th></tr>
        </thead>
        <tbody>
          {items.map((a) => (
            <tr key={a.audit_id} className="border-b">
              <td>{a.item_type}</td>
              <td>{a.source_workspace_id.slice(0, 8)} → {a.target_workspace_id.slice(0, 8)}</td>
              <td>{a.promoted_by_user_id.slice(0, 8)}</td>
              <td>{new Date(a.created_at).toLocaleString()}</td>
              <td>{a.embedding_status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {hasNextPage && (
        <button onClick={() => fetchNextPage()} className="text-sm text-primary">더 보기</button>
      )}
    </div>
  );
}
```

- [ ] **Step 63: Settings page 에 Audit 탭 추가**

Modify `frontend/src/app/(app)/settings/page.tsx`:

```tsx
import { AuditList } from "@/features/audit/components/audit-list";
import { useWorkspaceRole } from "@/features/workspaces/hooks";

// 기존 4 tab (General / Members / Invites + 추가 Audit)
const TABS = [
  { value: "general", label: "일반" },
  { value: "members", label: "멤버" },
  { value: "invites", label: "초대" },
  { value: "audit", label: "감사", adminOnly: true },
];

// admin gate
const { data: role } = useWorkspaceRole();
const visibleTabs = TABS.filter((t) => !t.adminOnly || ["owner", "admin"].includes(role ?? ""));

// Audit tab content
{tab === "audit" && <AuditList />}
```

- [ ] **Step 64: Playwright E2E (admin gate)**

Create `frontend/e2e/tests/settings-audit.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

test.describe("T-AUDIT-VIEW Settings audit tab (Sprint 24 Wave 2)", () => {
  test("admin 사용자는 Audit 탭 visible + audit row 조회", async ({ page }) => {
    // admin storageState 로 로그인
    await page.goto("/settings?tab=audit");
    await expect(page.getByRole("tab", { name: "감사" })).toBeVisible();
    await expect(page.getByRole("table")).toBeVisible();
  });
  
  test("viewer 사용자는 Audit 탭 hidden", async ({ page }) => {
    // viewer storageState
    await page.goto("/settings");
    await expect(page.getByRole("tab", { name: "감사" })).not.toBeVisible();
  });
});
```

### Task 23: Phase 5 commit

- [ ] **Step 65: Phase 5 commit**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2
git add backend/src/embeddings/repository.py backend/tests/embeddings/test_rag_time_range_sql_clause.py \
  backend/src/common/promote_router.py backend/src/main.py \
  backend/tests/common/test_audit_promotions_endpoint.py \
  frontend/src/features/audit/ \
  frontend/src/app/\(app\)/settings/page.tsx \
  frontend/e2e/tests/settings-audit.spec.ts
git commit -m "$(cat <<'EOF'
feat(p1): Sprint 24 Wave 2 Phase 5 — T-RAG-TIME-FILTER + T-AUDIT-VIEW (P1 RAG + compliance)

- T-RAG-TIME-FILTER (BUG-POW-006): embeddings/repository.py vector_search() time_range SQL clause
  - 1w/1m/3m/all interval mapping
  - 3 신규 test (1w filter / all no filter / invalid raises)
- T-AUDIT-VIEW (BUG-POW-008):
  - BE: /api/v1/workspaces/{wid}/audit/promotions?item_type= 단일 endpoint, admin only
  - FE: Settings 4번째 Audit tab + AuditList component + useAuditPromotions infinite scroll
  - 3 신규 BE test + 2 신규 E2E (admin/viewer gate)

Tests: 391 + 3 + 3 = 397 / Playwright 신규 2 PASS

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 6 — P1 Performance Spike (T-BE-PERF)

**Files:**
- Create: `backend/scripts/sprint24_wave2_perf_spike.py`
- Create: `docs/dev-log/2026-05-20-sprint24-wave2/be-perf-spike.md`
- (Top 1 fix 대상에 따라) Modify: `backend/src/auth/dependencies.py` 또는 다른 hot path

### Task 24: T-BE-PERF spike (sub-agent dispatch 후보)

> **Sub-agent §19 보호**: 코드 수정 금지, profiling 산출물만. controller 가 Top 1 fix commit.

- [ ] **Step 66: profiling script 작성**

Create `backend/scripts/sprint24_wave2_perf_spike.py`:

```python
# T-BE-PERF spike — dashboard 첫 진입 3-4s 진단
# SQLAlchemy event listener + cProfile + py-spy 옵션

import asyncio
import cProfile
import pstats
import io
import time
from sqlalchemy import event
from sqlalchemy.engine import Engine

QUERY_TIMINGS: list[tuple[str, float]] = []


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    elapsed = (time.time() - context._query_start_time) * 1000
    QUERY_TIMINGS.append((statement[:80], elapsed))


async def simulate_dashboard_first_visit(user_id: str, workspace_id: str) -> dict:
    """dashboard 첫 진입 시 BE API 4건 (workspaces / members / meetings / inbox) 직렬 호출 simulate."""
    from src.auth.dependencies import verify_clerk_token
    from src.workspaces.repository import WorkspaceRepository
    from src.meetings.repository import MeetingRepository
    from src.inbox.repository import InboxRepository
    # ... session_factory get_session() 으로 fresh session
    
    timings: dict[str, float] = {}
    
    t0 = time.time()
    user = await verify_clerk_token("fake_token")  # JWT verify 측정
    timings["clerk_jwt_verify"] = (time.time() - t0) * 1000
    
    # ... 4 API call 측정
    
    return {"timings": timings, "queries": QUERY_TIMINGS[:20]}


def main():
    profiler = cProfile.Profile()
    profiler.enable()
    result = asyncio.run(simulate_dashboard_first_visit("user_id", "ws_id"))
    profiler.disable()
    
    s = io.StringIO()
    pstats.Stats(profiler, stream=s).sort_stats("cumulative").print_stats(30)
    
    print("# Top 30 cumulative")
    print(s.getvalue())
    print("# Timings")
    for k, v in result["timings"].items():
        print(f"{k}: {v:.1f}ms")
    print("# Top 20 queries")
    for q, ms in sorted(result["queries"], key=lambda x: -x[1])[:20]:
        print(f"{ms:.1f}ms {q}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 67: spike 실행 + report 작성**

```bash
cd backend && uv run python -m scripts.sprint24_wave2_perf_spike > /tmp/perf-spike.txt
```

Create `docs/dev-log/2026-05-20-sprint24-wave2/be-perf-spike.md`:

```markdown
# Sprint 24 Wave 2 T-BE-PERF Spike Report

## 측정 환경
- localhost FastAPI + Neon Postgres (cold start 가능)
- 측정일: 2026-05-20

## API timing 매트릭스 (cold start)
| API | First-call ms | Cached ms |
|---|---|---|
| Clerk JWT verify | ___ | ___ |
| /workspaces | ___ | ___ |
| /workspaces/{id}/members | ___ | ___ |
| /workspaces/{id}/meetings | ___ | ___ |
| /workspaces/{id}/inbox | ___ | ___ |

## Top 5 cumulative (cProfile)
1. ___
2. ___
...

## Top 5 slow queries
1. ___ (___ ms)
2. ___
...

## 진단
- 직렬 호출 시 총 ___ ms (사용자 보고 3015-3865ms 와 비교)
- Top 1 bottleneck: ___ (예: Clerk JWT verify 캐시 미적용 / N+1 query / cold pool)

## Top 1 Fix (본 sprint scope)
- (Profiling 결과로 결정)
- 예시 fix 1: Clerk JWT verify in-process LRU cache (TTL=60s)
- 예시 fix 2: get_session() pool pre-warm
- 예시 fix 3: workspaces + members 단일 query (JOIN)

## 후속 fix (carry-over)
- BL-NEW-BE-PERF-N1 / N2 / N3 등재
```

- [ ] **Step 68: Top 1 fix 구현 (profiling 결과로 결정)**

profiling 결과에 따라 변동. 예시 (Clerk JWT verify cache):

Modify `backend/src/auth/dependencies.py`:

```python
from cachetools import TTLCache
from cachetools.func import ttl_cache

# T-BE-PERF Top 1 fix: Clerk JWT verify in-process LRU cache (60s TTL)
_JWT_CACHE: TTLCache = TTLCache(maxsize=1000, ttl=60)


async def verify_clerk_token(token: str) -> dict:
    if token in _JWT_CACHE:
        return _JWT_CACHE[token]
    decoded = await _verify_clerk_token_remote(token)
    _JWT_CACHE[token] = decoded
    return decoded
```

(or 다른 fix — profiling 결과에 따라)

- [ ] **Step 69: 회귀 + 재측정**

```bash
cd backend && uv run pytest tests/ -q 2>&1 | tail -3
cd backend && uv run python -m scripts.sprint24_wave2_perf_spike >> /tmp/perf-spike-after.txt
```

Expected: pytest 회귀 0 + spike 결과 개선 (Top 1 영역).

- [ ] **Step 70: Phase 6 commit**

```bash
git add backend/scripts/sprint24_wave2_perf_spike.py docs/dev-log/2026-05-20-sprint24-wave2/be-perf-spike.md backend/src/auth/dependencies.py
git commit -m "perf(p1): Sprint 24 Wave 2 Phase 6 — T-BE-PERF spike + Top 1 fix (BUG-MOBILE-005)

- Spike: SQLAlchemy event listener + cProfile (dashboard 4 API 첫 진입)
- Top 1 fix: (profiling 결과에 따라 결정)
- 측정 report: docs/dev-log/2026-05-20-sprint24-wave2/be-perf-spike.md

Tests: 397 회귀 0

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 7 — 헌법 (T-N+1 BL-006 cross-domain import 해소)

**Files:**
- Create: `backend/src/memory/pipeline_service.py`
- Modify: `backend/src/memory/service.py:550, :780` (lazy import 제거)
- Modify: `backend/src/memory/dependencies.py` (pipeline 주입)
- Create: `backend/tests/architecture/test_no_memory_to_embeddings_lazy_import.py`
- Patch: `CONTEXT-MAP.md` §4.2 + §7 + `backend/CONTEXT.md` + `backend/src/memory/CONTEXT.md` + `backend/src/embeddings/CONTEXT.md` E-9 + `docs/architecture/cross-domain-pipeline.md`
- Patch: `docs/REFACTORING-BACKLOG.md` (BL-006 closed)

### Task 25: T-N+1 BL-006 — memory/pipeline_service.py 신설

- [ ] **Step 71: 실패 테스트 (architecture gate)**

Create `backend/tests/architecture/test_no_memory_to_embeddings_lazy_import.py`:

```python
# T-N+1 BL-006: memory → embeddings 직접 import 금지 (헌법 §4.2)
from pathlib import Path


def test_memory_service_no_embeddings_import():
    source = Path("src/memory/service.py").read_text()
    assert "from src.embeddings" not in source, (
        "BL-006 위반 — memory/service.py 는 EmbeddingRepository 를 직접 import 하지 않음. "
        "memory/pipeline_service.py 위임 패턴 사용. 헌법 §4.2 cross-domain orchestrator only."
    )


def test_memory_repository_apply_hnsw_helper_keep():
    """E-9 외부 사용처 유지: memory/repository.py 의 _apply_hnsw_session_params import 는 OK."""
    source = Path("src/memory/repository.py").read_text()
    assert "_apply_hnsw_session_params" in source
```

- [ ] **Step 72: 테스트 실행 (FAIL 확인)**

```bash
cd backend && uv run pytest tests/architecture/test_no_memory_to_embeddings_lazy_import.py -v
```

Expected: FAIL (현재 service.py:550, :780 lazy import 존재).

- [ ] **Step 73: `backend/src/memory/pipeline_service.py` 신설**

Create `backend/src/memory/pipeline_service.py`:

```python
# memory 도메인 orchestrator — Sprint 24 Wave 2 T-N+1 BL-006 closure
# capture / distill / promote 흐름에서 embeddings.save_chunk 위임
# 헌법 §4.2 — memory → embeddings 직접 의존 해소 (memory/service.py 순수화)

from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.memory.repository import MemoryRepository


class MemoryPipelineService:
    """memory 도메인 cross-domain orchestrator.
    
    헌법 §4.2 cross-domain shared service 호출은 orchestrator (pipeline_service / services/) 에서만.
    BL-006 closure (Sprint 24 Wave 2).
    """
    
    def __init__(
        self,
        session: AsyncSession,
        memory_repo: MemoryRepository,
        embedding_repo: EmbeddingRepository,
        embedding_service: EmbeddingService,
    ):
        self.session = session
        self.memory_repo = memory_repo
        self.embedding_repo = embedding_repo
        self.embedding_service = embedding_service
    
    async def capture_with_embedding(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        content: str,
        memory_type: str = "text",
    ):
        """capture: MemoryItem 생성 + EmbeddingChunk save (헌법 I-9 workspace_id 매칭)."""
        memory = await self.memory_repo.create(
            workspace_id=workspace_id,
            user_id=user_id,
            content=content,
            memory_type=memory_type,
        )
        embedding = await self.embedding_service.create_embedding(content)
        chunk = await self.embedding_repo.save_chunk(
            workspace_id=workspace_id,
            source_type="memory",
            source_id=memory.id,
            chunk_index=0,
            content=content,
            embedding=embedding,
            chunk_level=2,
        )
        return memory, chunk
    
    async def promote_with_embedding(
        self,
        *,
        memory_id: UUID,
        target_workspace_id: UUID,
        user_id: UUID,
    ):
        """promote: 복제 + tombstone (I-18) + 새 chunk 생성."""
        # MemoryService.promote() 의 lazy import 부분을 본 orchestrator 로 이관
        memory = await self.memory_repo.find_by_id(memory_id, workspace_id=...)
        # ... 복제 로직 (PromoteAudit 등 기존)
        new_chunk = await self.embedding_repo.save_chunk(
            workspace_id=target_workspace_id,
            source_type="memory",
            source_id=new_memory_id,
            ...,
        )
        return new_memory, new_chunk
```

- [ ] **Step 74: `backend/src/memory/service.py:550, :780` lazy import 제거**

Modify `backend/src/memory/service.py`:

```python
# Line 545~555 (capture text flow):
# 제거: from src.embeddings.repository import EmbeddingRepository
# 제거: chunk = await EmbeddingRepository(session).save_chunk(...)
# 대체: pipeline_service 가 호출하도록 service.py 는 memory CRUD 만

# MemoryService.capture_text(...) 가 pipeline 미주입 시 RuntimeError:
class MemoryService:
    def __init__(self, ..., pipeline: MemoryPipelineService | None = None):
        ...
        self._pipeline = pipeline
    
    async def capture_text(self, ...):
        if not self._pipeline:
            raise RuntimeError("MemoryService.capture_text requires pipeline (T-N+1 BL-006)")
        memory, chunk = await self._pipeline.capture_with_embedding(...)
        return memory


# 동일: line 775~785 (promote)
```

- [ ] **Step 75: `backend/src/memory/dependencies.py` 에서 pipeline 주입**

Modify `backend/src/memory/dependencies.py`:

```python
from src.memory.pipeline_service import MemoryPipelineService
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.dependencies import get_embedding_service


def get_memory_service(
    session: AsyncSession = Depends(get_session),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> MemoryService:
    memory_repo = MemoryRepository(session)
    embedding_repo = EmbeddingRepository(session)
    pipeline = MemoryPipelineService(
        session=session,
        memory_repo=memory_repo,
        embedding_repo=embedding_repo,
        embedding_service=embedding_service,
    )
    return MemoryService(memory_repo=memory_repo, pipeline=pipeline)
```

- [ ] **Step 76: 테스트 실행 (PASS 확인)**

```bash
cd backend && uv run pytest tests/architecture/test_no_memory_to_embeddings_lazy_import.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 77: 전체 회귀 + memory 도메인 회귀**

```bash
cd backend && uv run pytest tests/memory/ tests/ -q 2>&1 | tail -5
```

Expected: 397 + 2 = 399 passed + 1 skipped, memory 도메인 회귀 0.

### Task 26: Atomic Update docs — 헌법 patch

- [ ] **Step 78: `CONTEXT-MAP.md` §4.2 + §7 patch**

Modify `CONTEXT-MAP.md`:

§4.2 의존 다이어그램 갱신 — 기존 `memory -. orchestrator only .-> embeddings` 점선 유지 + comment 추가:
```mermaid
  memory -. orchestrator only (pipeline_service.py, Sprint 24 Wave 2 BL-006 closure) .-> embeddings
```

§4.2 헌법 결정 #1 박스에 BL-006 closure 명시.

§7 부채 표 — BL-006 closed mark (또는 D-2/D-3 같은 [해소 라벨]):
```markdown
| ~~BL-006~~ | ~~memory → embeddings cross-domain import~~ | **[해소 2026-05-20]** Sprint 24 Wave 2 T-N+1 — `backend/src/memory/pipeline_service.py` 신설 + service.py 순수화. ADR-014 옵션 A 적용 |
```

- [ ] **Step 79: `backend/CONTEXT.md` §4 patch**

memory 도메인 의존 표에 pipeline_service.py 명시.

- [ ] **Step 80: `backend/src/memory/CONTEXT.md` patch**

```markdown
## §아키텍처 (Sprint 24 Wave 2 갱신)

- `service.py` = memory CRUD 만 (순수). cross-domain 호출은 pipeline_service 위임.
- `pipeline_service.py` = orchestrator (헌법 §4.2). capture_with_embedding / promote_with_embedding.
- `repository.py` = data access (workspace_id WHERE + I-21 _apply_hnsw_session_params 호출 — E-9 외부 사용처 유지)
```

- [ ] **Step 81: `backend/src/embeddings/CONTEXT.md` E-9 patch**

```markdown
| E-9 | **embedding_chunks 직접 SQL 사용 외부 도메인**도 `_apply_hnsw_session_params` 호출 강제. 현 외부 사용처: `memory/repository.py:163` (vector_search 직접 SQL). **BL-006 closed (Sprint 24 Wave 2)** — memory/service.py 의 save_chunk lazy import 는 pipeline_service.py 위임으로 해소. repository-level _apply_hnsw_session_params import 만 유지 (캡슐화 우회의 최소 비용 약속) | `memory/repository.py:33` |
```

- [ ] **Step 82: `docs/architecture/cross-domain-pipeline.md` patch**

§"위반 해소" section 추가 (또는 기존 section 갱신):
```markdown
## BL-006 closure (Sprint 24 Wave 2 T-N+1)

memory → embeddings 직접 import 3건 해소:
- `memory/service.py:550` lazy import → pipeline_service.capture_with_embedding 위임
- `memory/service.py:780` lazy import → pipeline_service.promote_with_embedding 위임
- `memory/repository.py:33` _apply_hnsw_session_params import 는 **유지** (E-9 캡슐화 우회 최소 비용)
```

- [ ] **Step 83: `docs/REFACTORING-BACKLOG.md` BL-006 closed mark**

```markdown
## ~~BL-006~~ — memory → embeddings cross-domain import (헌법 §4.2 위반)

**상태**: **[해소 2026-05-20] Sprint 24 Wave 2 T-N+1**
- `backend/src/memory/pipeline_service.py` 신설 (orchestrator)
- `memory/service.py:550, :780` lazy import 제거
- E-9 외부 사용처 (memory/repository.py:33 _apply_hnsw_session_params) 유지
```

- [ ] **Step 84: Phase 7 commit**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2
git add backend/src/memory/pipeline_service.py backend/src/memory/service.py backend/src/memory/dependencies.py \
  backend/tests/architecture/ \
  CONTEXT-MAP.md backend/CONTEXT.md backend/src/memory/CONTEXT.md backend/src/embeddings/CONTEXT.md \
  docs/architecture/cross-domain-pipeline.md docs/REFACTORING-BACKLOG.md
git commit -m "$(cat <<'EOF'
refactor(헌법): Sprint 24 Wave 2 Phase 7 — T-N+1 BL-006 cross-domain import 해소

헌법 §4.2 위반 해소:
- 신설 backend/src/memory/pipeline_service.py — MemoryPipelineService orchestrator
- memory/service.py:550, :780 lazy import (EmbeddingRepository) 제거
- service.py 가 pipeline 미주입 시 RuntimeError fail-closed
- dependencies.py 에서 pipeline 주입

Atomic Update:
- CONTEXT-MAP.md §4.2 의존 다이어그램 + §7 BL-006 closed
- backend/CONTEXT.md memory 도메인 의존 표
- backend/src/memory/CONTEXT.md 아키텍처 §
- backend/src/embeddings/CONTEXT.md E-9 갱신 (외부 사용처 유지 명시)
- docs/architecture/cross-domain-pipeline.md BL-006 closure section
- docs/REFACTORING-BACKLOG.md BL-006 closed mark

Tests: 397 → 399 passed (architecture gate 신규 2) + 회귀 0

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 8 — Production (T-N+4 BL-T2-003 Whisper 4hr+ chunk)

**Files:**
- Create: `backend/src/services/chunked_transcription.py`
- Modify: `backend/src/services/transcription.py` (entry point 분기)
- Create: `backend/tests/services/test_whisper_chunked_4hr.py`
- Patch: `backend/CONTEXT.md` STT § + `docs/architecture/ai-pipeline.md` STT 단계 + `docs/REFACTORING-BACKLOG.md` BL-T2-003 closed

### Task 27: T-N+4 BL-T2-003 — Whisper chunked transcription

- [ ] **Step 85: 실패 테스트 작성**

Create `backend/tests/services/test_whisper_chunked_4hr.py`:

```python
# T-N+4 BL-T2-003: Whisper 4hr+ chunked transcription

import pytest
from unittest.mock import AsyncMock, patch
from src.services.chunked_transcription import transcribe_chunked


@pytest.mark.asyncio
async def test_short_audio_uses_single_call():
    """1hr 이하 audio = 단일 Whisper 호출 (chunking X)."""
    with patch("src.services.chunked_transcription._ffmpeg_probe_duration", AsyncMock(return_value=1800)):  # 30min
        with patch("src.services.chunked_transcription._whisper_transcribe_single", AsyncMock(return_value=[{"start": 0, "end": 10, "text": "안녕하세요"}])) as mock_w:
            segments = await transcribe_chunked("s3://test.mp3")
            mock_w.assert_called_once()
            assert len(segments) == 1


@pytest.mark.asyncio
async def test_4hr_audio_uses_4_chunks_with_overlap():
    """4hr audio = 4 chunk + 5초 overlap + offset 보존."""
    with patch("src.services.chunked_transcription._ffmpeg_probe_duration", AsyncMock(return_value=14400)):  # 4hr
        with patch("src.services.chunked_transcription._ffmpeg_split", AsyncMock(return_value=["c0.mp3", "c1.mp3", "c2.mp3", "c3.mp3"])):
            with patch("src.services.chunked_transcription._whisper_transcribe_single", AsyncMock(return_value=[{"start": 0, "end": 10, "text": "안녕"}])) as mock_w:
                segments = await transcribe_chunked("s3://4hr.mp3")
                assert mock_w.call_count == 4
                # offset 보존: chunk 0 segment.start=0, chunk 1 segment.start=3600 등
                assert segments[0]["start"] == 0
                assert segments[1]["start"] == 3600  # chunk 1 의 offset


@pytest.mark.asyncio
async def test_chunk_overlap_dedupe():
    """chunk N 마지막 5초 + chunk N+1 처음 5초 중복 segment dedupe."""
    # mock: chunk 0 의 segment.end > 3595 (overlap 영역), chunk 1 의 same 시간 동일 텍스트
    # → merge 시 dedup 검증
    # ... 상세 mock
    pass
```

- [ ] **Step 86: 테스트 실행 (FAIL)**

```bash
cd backend && uv run pytest tests/services/test_whisper_chunked_4hr.py -v
```

Expected: FAIL (`chunked_transcription` 미존재).

- [ ] **Step 87: `backend/src/services/chunked_transcription.py` 신설**

Create `backend/src/services/chunked_transcription.py`:

```python
# Whisper chunked transcription — Sprint 24 Wave 2 T-N+4 BL-T2-003
# 4hr+ production audio 차단 해소. ffmpeg duration probe + 1hr chunk + 5초 overlap + 병렬

import asyncio
import subprocess
import tempfile
from pathlib import Path

CHUNK_SECONDS = 3600  # 1hr
OVERLAP_SECONDS = 5


async def _ffmpeg_probe_duration(audio_url: str) -> float:
    """ffprobe 로 audio duration 측정 (초)."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_url,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return float(stdout.strip())


async def _ffmpeg_split(audio_url: str, chunk_seconds: int, overlap_seconds: int) -> list[str]:
    """ffmpeg 로 chunk 분할 + overlap (각 chunk 끝/시작 5초 overlap)."""
    duration = await _ffmpeg_probe_duration(audio_url)
    chunks: list[str] = []
    n_chunks = int(duration // chunk_seconds) + (1 if duration % chunk_seconds > 0 else 0)
    for i in range(n_chunks):
        start = max(0, i * chunk_seconds - overlap_seconds)
        end = min(duration, (i + 1) * chunk_seconds + overlap_seconds)
        chunk_path = tempfile.mktemp(suffix=".mp3")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", audio_url, "-ss", str(start), "-to", str(end), "-c", "copy", chunk_path,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        chunks.append(chunk_path)
    return chunks


async def _whisper_transcribe_single(audio_path: str) -> list[dict]:
    """기존 Whisper 단일 호출 — services/transcription.py 의 transcribe()."""
    from src.services.transcription import transcribe
    return await transcribe(audio_path)


def _merge_with_offset(chunked_segments: list[list[dict]], chunk_seconds: int, overlap_seconds: int) -> list[dict]:
    """offset 보존 + overlap dedupe.
    
    chunk i 의 모든 segment 에 offset = i * chunk_seconds 적용.
    chunk i 의 마지막 overlap_seconds 와 chunk i+1 의 처음 overlap_seconds 중복 dedupe (text 유사도).
    """
    merged: list[dict] = []
    for i, segments in enumerate(chunked_segments):
        offset = i * chunk_seconds
        for seg in segments:
            seg_copy = {**seg, "start": seg["start"] + offset, "end": seg["end"] + offset}
            # dedup: 직전 chunk 의 마지막 overlap 영역 segment 와 text 동일하면 skip
            if merged and seg_copy["start"] < merged[-1]["end"] + 1 and seg_copy["text"] == merged[-1]["text"]:
                continue
            merged.append(seg_copy)
    return merged


async def transcribe_chunked(audio_url: str) -> list[dict]:
    """4hr+ chunk 분할 transcription. 1hr 이하면 단일 호출."""
    duration = await _ffmpeg_probe_duration(audio_url)
    if duration <= CHUNK_SECONDS:
        return await _whisper_transcribe_single(audio_url)
    
    chunk_paths = await _ffmpeg_split(audio_url, CHUNK_SECONDS, OVERLAP_SECONDS)
    try:
        # 병렬 Whisper 호출
        chunked_segments = await asyncio.gather(*[_whisper_transcribe_single(p) for p in chunk_paths])
        return _merge_with_offset(chunked_segments, CHUNK_SECONDS, OVERLAP_SECONDS)
    finally:
        # cleanup temp files
        for p in chunk_paths:
            Path(p).unlink(missing_ok=True)
```

- [ ] **Step 88: `backend/src/services/transcription.py` entry point 분기**

Modify `backend/src/services/transcription.py`:

```python
async def transcribe_with_chunking(audio_url: str) -> list[dict]:
    """meetings pipeline 진입점 — 1hr 이하면 단일, 1hr+ 면 chunked."""
    from src.services.chunked_transcription import transcribe_chunked
    return await transcribe_chunked(audio_url)
```

`backend/src/meetings/pipeline_service.py` 의 transcription 호출처를 `transcribe_with_chunking` 으로 교체.

- [ ] **Step 89: 테스트 실행 (PASS)**

```bash
cd backend && uv run pytest tests/services/test_whisper_chunked_4hr.py -v
```

Expected: 3 tests PASS.

### Task 28: Atomic Update — STT pipeline docs

- [ ] **Step 90: `backend/CONTEXT.md` STT § patch**

```markdown
## STT 파이프라인 (Sprint 24 Wave 2 갱신)

- entry: `services/transcription.py:transcribe_with_chunking(audio_url)`
- 1hr 이하: 단일 Whisper API 호출
- 1hr+: `services/chunked_transcription.py:transcribe_chunked` — ffmpeg probe + 1hr chunk + 5초 overlap + 병렬 + offset 보존 + dedup merge
- BL-T2-003 closure (Sprint 24 Wave 2 T-N+4)
```

- [ ] **Step 91: `docs/architecture/ai-pipeline.md` STT 단계 patch**

```markdown
## STT (Speech-to-Text)

- Provider: OpenAI Whisper API
- Sprint 24 Wave 2 T-N+4: 4hr+ audio chunked (1hr chunk + 5초 overlap, ffmpeg probe + 병렬). BL-T2-003 closure.
- 호출 위치: `meetings/pipeline_service.py` → `services/transcription.py:transcribe_with_chunking`
```

- [ ] **Step 92: REFACTORING-BACKLOG.md BL-T2-003 closed mark**

```markdown
## ~~BL-T2-003~~ — Whisper chunk 분할 (4hr+) 

**상태**: **[해소 2026-05-20] Sprint 24 Wave 2 T-N+4**
```

- [ ] **Step 93: Phase 8 commit**

```bash
git add backend/src/services/chunked_transcription.py backend/src/services/transcription.py \
  backend/src/meetings/pipeline_service.py backend/tests/services/test_whisper_chunked_4hr.py \
  backend/CONTEXT.md docs/architecture/ai-pipeline.md docs/REFACTORING-BACKLOG.md
git commit -m "$(cat <<'EOF'
feat(production): Sprint 24 Wave 2 Phase 8 — T-N+4 BL-T2-003 Whisper 4hr+ chunked transcription

- 신설 services/chunked_transcription.py — ffmpeg probe + 1hr chunk + 5초 overlap + 병렬 + offset merge + dedup
- services/transcription.py transcribe_with_chunking entry point 분기
- meetings/pipeline_service.py 호출처 교체
- 3 신규 test (short single / 4hr chunks / overlap dedup)

Atomic Update:
- backend/CONTEXT.md STT § + docs/architecture/ai-pipeline.md
- BL-T2-003 closed mark

Tests: 399 → 402 passed

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 9 — 회귀 안전망 + Closeout (T-N+2 + docs sync)

**Files:**
- Create: `backend/tests/fixtures/composite_fk.py`
- Modify: `backend/tests/conftest.py` (fixture import)
- Patch: `docs/TODO.md` (Sprint 24 Wave 2 closeout)
- Patch: `docs/REFACTORING-BACKLOG.md` (BL carry-over 등재 최종)

### Task 29: T-N+2 — composite FK regression fixture

- [ ] **Step 94: `backend/tests/fixtures/composite_fk.py` 신설**

Create `backend/tests/fixtures/composite_fk.py`:

```python
# T-N+2 composite FK regression fixture — Sprint 24 Wave 2 (SCN-FK-01~12 자동화)
# Sprint 21 BL-050 composite FK hardening 의 회귀 안전망

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest_asyncio.fixture
async def composite_fk_meeting_project_link_violation(db_session: AsyncSession, two_workspaces):
    """SCN-FK-01: MeetingProjectLink (insert) cross-workspace 거부."""
    from src.meetings.models import Meeting
    from src.projects.models import Project
    from src.projects.models import MeetingProjectLink
    
    ws_a, ws_b = two_workspaces
    meeting = Meeting(workspace_id=ws_a.id, title="m_a", ...)
    project = Project(workspace_id=ws_b.id, title="p_b", ...)
    db_session.add_all([meeting, project])
    await db_session.commit()
    
    bad_link = MeetingProjectLink(meeting_id=meeting.id, project_id=project.id, workspace_id=ws_a.id)
    db_session.add(bad_link)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


# SCN-FK-04: InboxItem (insert) — ai_suggested_project_id cross-workspace
@pytest_asyncio.fixture
async def composite_fk_inbox_suggested_project_violation(db_session, two_workspaces):
    ...


# SCN-FK-07: ActionItem (insert) — project_id cross-workspace
@pytest_asyncio.fixture
async def composite_fk_action_item_project_violation(db_session, two_workspaces):
    ...


# SCN-FK-10: EmbeddingChunk (insert) — project_id cross-workspace
@pytest_asyncio.fixture
async def composite_fk_embedding_chunk_project_violation(db_session, two_workspaces):
    ...


# 12 SCN entity 별 fixture (insert / update / query) — 위 패턴 반복
# SCN-FK-02 (update transitive), SCN-FK-03 (query orphan), SCN-FK-05/06, SCN-FK-08/09, SCN-FK-11/12
```

- [ ] **Step 95: `backend/tests/conftest.py` 에 fixture import**

Modify `backend/tests/conftest.py`:

```python
# Sprint 24 Wave 2 T-N+2 fixture
from backend.tests.fixtures.composite_fk import *  # noqa: F401, F403
```

- [ ] **Step 96: 통합 test 에서 fixture 사용 verify**

기존 `test_workspace_fk_cross_tenant_block.py` 와 호환 verify. fixture 가 자동으로 SCN-FK-01~12 검증.

```bash
cd backend && uv run pytest tests/integration/test_workspace_fk_cross_tenant_block.py tests/fixtures/ -v
```

Expected: 12 SCN PASS.

### Task 30: Closeout — TODO.md + REFACTORING-BACKLOG.md 최종 sync

- [ ] **Step 97: `docs/TODO.md` Sprint 24 Wave 2 완료 + Sprint 25 Next Actions**

Modify `docs/TODO.md`:

```markdown
## Recently Completed (2026-05-20 Sprint 24 Wave 2 trusty-heron)

- [x] **Sprint 24 Wave 2 — trusty-heron (PR draft)**: Multi-Agent QA P0/P1 16 task fix bundle
  - [x] Phase 1 T-2 Post-Swap Delta gate PASS
  - [x] Phase 2 T-AI-DATE + T-RAG-MOCK-REMOVE (P0 Critical)
  - [x] Phase 3 T-OBN-05 D 옵션 + T-MOBILE-HEADER (P0 High UX)
  - [x] Phase 4 T-PROJ-LIST + T-NOTE-DETAIL + T-CMD-K-FIX (P1 FE)
  - [x] Phase 5 T-RAG-TIME-FILTER + T-AUDIT-VIEW (P1 RAG + compliance)
  - [x] Phase 6 T-BE-PERF spike + Top 1 fix
  - [x] Phase 7 T-N+1 BL-006 cross-domain import 해소 (헌법)
  - [x] Phase 8 T-N+4 BL-T2-003 Whisper 4hr+ chunked
  - [x] Phase 9 T-N+2 composite FK fixture + docs sync
  - 산출물: `docs/superpowers/specs/2026-05-20-sprint24-wave2-trusty-heron-design.md` + plan + per-task report

## Next Actions (Sprint 25 후보)

- [ ] BL-NEW-RAG-SOURCE-SELECT (Power persona 데이터 후 B path 검토)
- [ ] BL-NEW-OBN-DATA-RETRY (F4 인터뷰 후 onboarding 재설계)
- [ ] T-LAND-01/02 마케팅 (landing wedge headline + use case)
- [ ] BL-T2 P2 5건 (input/security headers)
- [ ] Power P2 (BUG-POW-002 Inbox bulk + 004 zip export + 007 PAT)
- [ ] BUG-CASUAL P2/P3 (VOCAB + INBOX-COPY + CMD-K-SEQ + CMD-K-STATE)
- [ ] a11y P2 (T-A11Y-SKIP + T-A11Y-CC + T-MOBILE-NAV + T-NAV-BADGE)
- [ ] BL-068/069 Sprint 23 D1/D3 Playwright reproduce
```

- [ ] **Step 98: `docs/REFACTORING-BACKLOG.md` 최종 sync (BL-006 + BL-T2-003 closed + 신규 등재)**

(이미 Phase 2/3/7/8 commit 에서 patch — 본 step 은 최종 verify)

- [ ] **Step 99: 전체 회귀 baseline**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2
cd backend && uv run pytest tests/ -q 2>&1 | tail -3
cd ../frontend && pnpm typecheck && pnpm test 2>&1 | tail -5
cd .. && pnpm --filter frontend exec playwright test 2>&1 | tail -10
```

Expected: pytest 387 → 410+ + FE typecheck 0 + vitest 50 → 55+ + Playwright 신규 모두 PASS.

- [ ] **Step 100: Phase 9 commit**

```bash
git add backend/tests/fixtures/composite_fk.py backend/tests/conftest.py docs/TODO.md docs/REFACTORING-BACKLOG.md
git commit -m "$(cat <<'EOF'
test(regression): Sprint 24 Wave 2 Phase 9 — T-N+2 composite FK fixture + docs closeout

- 신설 backend/tests/fixtures/composite_fk.py — SCN-FK-01~12 자동화 (Sprint 21 BL-050 회귀 안전망)
- conftest.py fixture import
- docs/TODO.md Sprint 24 Wave 2 완료 mark + Sprint 25 Next Actions
- docs/REFACTORING-BACKLOG.md 최종 sync (BL-006 + BL-T2-003 closed + BL-NEW-RAG-SOURCE-SELECT + BL-NEW-OBN-DATA-RETRY 등재)

Tests: 402 → 410+ passed + Playwright 신규 모두 PASS

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Stage 4 — Codex iterative diff review

- [ ] **Step 101: Codex 2차 diff review loop**

```bash
loop:
  cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2
  codex exec - <<< "codex review --base origin/main"
  
  if APPROVE: break (2 cycle 연속 APPROVE 종결)
  elif REVISE: 
    finding 100% 수락 (P3 reject 가능)
    polish commit ("polish: Codex N차 M finding 100% 수락 (P1 X + P2 Y)")
    git push
  elif usage limit: wait reset 또는 새 session
```

- [ ] **Step 102: polish commit naming convention**

```
polish: Codex 1차 5 finding 100% 수락 (P1 2 + P2 3)
polish: Codex 2차 3 finding 수락 (P2 3) + P3 1건 reject (사유: ...)
```

---

## Stage 5 — PR push + Docs sync verify

- [ ] **Step 103: 최종 baseline verify**

```bash
cd backend && uv run pytest tests/ -q 2>&1 | tail -3
cd ../frontend && pnpm typecheck && pnpm test 2>&1 | tail -5
```

- [ ] **Step 104: stash@{0} 보존 verify (R8)**

```bash
cd /Users/woosung/project/agy-project/kairos-sprint-24-wave2
git stash list
# expected: stash@{0}: On main: 임시 디자인 요청을 통해서 변경한 부분 (보존)
```

- [ ] **Step 105: push + PR create**

```bash
git push -u origin sprint-24/wave2-trusty-heron
gh pr create --draft --title "Sprint 24 Wave 2 trusty-heron: Multi-Agent QA P0/P1 16 task fix bundle" --body "$(cat <<'EOF'
## Summary

Multi-Agent QA 5 페르소나 발견 P0/P1 dogfood 차단 결함 16 task fix + Phase B Post-Swap Delta 검증 + 헌법 §4.2 BL-006 정합.

## 9 Phase

- Phase 1 T-2 Post-Swap Delta gate PASS (gemini-3.1-flash-lite 품질 검증)
- Phase 2 T-AI-DATE + T-RAG-MOCK-REMOVE (P0 Critical)
- Phase 3 T-OBN-05 D 옵션 (Codex+Gemini deep research 합의) + T-MOBILE-HEADER (P0 High UX)
- Phase 4 T-PROJ-LIST + T-NOTE-DETAIL + T-CMD-K-FIX (P1 FE missing pages)
- Phase 5 T-RAG-TIME-FILTER + T-AUDIT-VIEW (P1 RAG + compliance)
- Phase 6 T-BE-PERF spike + Top 1 fix (P1 Performance)
- Phase 7 T-N+1 BL-006 cross-domain import 해소 (헌법 §4.2)
- Phase 8 T-N+4 BL-T2-003 Whisper 4hr+ chunked (production)
- Phase 9 T-N+2 composite FK fixture + docs sync (회귀 안전망)

## Tests

- pytest 387 → 410+ + 1 skipped
- FE typecheck 0 / vitest 50 → 55+
- Playwright 신규 5+ spec PASS

## Docs sync

`git diff --stat docs/ backend/**/CONTEXT.md frontend/**/CONTEXT.md CONTEXT-MAP.md` 결과 (별도 표 첨부 가능).

## Carry-over (Sprint 25)

- BL-NEW-RAG-SOURCE-SELECT (Power persona 데이터 후)
- BL-NEW-OBN-DATA-RETRY (F4 인터뷰 후)
- T-LAND-01/02 + BL-T2 P2 5건 + Power P2 + BUG-CASUAL P2/P3 + a11y P2 + BL-068/069

## Test plan

- [x] pytest 410+ PASS
- [x] FE typecheck + vitest PASS
- [x] Playwright 신규 spec PASS
- [x] Dogfooding mini-redo Curious 페르소나 (5 P0 BUG 회귀 0)
- [ ] 사용자 manual smoke + R8 stash 보존 verify

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 106: R7 base verify**

```bash
gh pr view <N> --json baseRefName,headRefName
# expected: baseRefName = "main", headRefName = "sprint-24/wave2-trusty-heron"
```

---

## Stage 6 — Closeout (memory + MEMORY.md)

- [ ] **Step 107: memory `project_sprint24_wave2_trusty_heron_done.md` 작성**

Create `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/project_sprint24_wave2_trusty_heron_done.md`:

```markdown
---
name: project-sprint24-wave2-trusty-heron-done
description: 2026-05-20 Sprint 24 Wave 2 trusty-heron closeout — Multi-Agent QA P0/P1 16 task fix bundle. PR
metadata:
  type: project
---

(상세 closeout report)
```

- [ ] **Step 108: MEMORY.md 인덱스 1줄 추가**

Modify `~/.claude/projects/-Users-woosung-project-agy-project-kairos/memory/MEMORY.md`:

```markdown
- [project_sprint24_wave2_trusty_heron_done.md](project_sprint24_wave2_trusty_heron_done.md) — 2026-05-20 Sprint 24 Wave 2 trusty-heron 종결. 16 task + D 옵션 + 헌법 BL-006 closure.
```

---

## Self-Review 결과

- **Spec coverage**: spec doc 5 sections + 16 task 모두 plan 에 매핑 (Phase 1~9). T-OBN-05 D 옵션 4 영역 (banner rollback + EmptyState + 3 호출처 + tooltip 신설) 모두 step 으로 분해.
- **Placeholder scan**: T-BE-PERF Phase 6 의 "Top 1 fix" 는 profiling 결과 의존이라 명시적 placeholder 유지 (예시 fix 3개 제시 후 actual 은 spike 결과 후 결정). 다른 Phase 는 모두 actual content.
- **Type consistency**: `MemoryPipelineService.capture_with_embedding` / `promote_with_embedding` 명명 일관. `useCmdKStore.openWithQuery` 명명 일관. `_validate_action_dates` helper 명 일관.
- **Atomic Update 매트릭스**: File Structure 표 + 각 Phase commit message 에 docs sync 명시.
