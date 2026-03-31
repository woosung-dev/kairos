# AI 파이프라인 명세

## 전체 흐름

```
트랜스크립트 입력
  → [1] MEETING_SUMMARY_SYSTEM_PROMPT   → summary, key_decisions, topics, participants
  → [2] ACTION_ITEM_SYSTEM_PROMPT       → action_items[] (담당자/기한/우선순위)
  → [3] PARA_CLASSIFY_SYSTEM_PROMPT     → suggested_type, confidence
  → [4] Inbox 적재 (ai_suggested_para_type 포함, is_processed=false)
  → [5] 벡터 임베딩 저장 (계층적 청킹, rag-pipeline.md 참조)
```

**호출 순서가 중요하다:** 요약 → 액션 추출 → PARA 분류 순서로 호출.
PARA 분류는 요약 결과를 입력으로 사용하기 때문.

---

## 프롬프트 관리 규칙

- 모든 프롬프트는 `backend/src/common/prompts.py`에 **상수**로 정의
- 인라인 프롬프트 작성 **절대 금지**
- Claude 모델 고정: `claude-sonnet-4-20250514` (임의 변경 금지)
- 모든 Claude 호출은 `services/ai_processing.py`에 집중 관리
- LLM 구현체는 `BaseLLMService` 인터페이스로 추상화

---

## Claude 프롬프트 템플릿

### Template 1: 회의 요약 생성

```python
MEETING_SUMMARY_SYSTEM_PROMPT = """
당신은 회의 트랜스크립트를 구조화된 요약으로 변환하는 전문가입니다.
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

출력 JSON 스키마:
{
  "summary": "string (3~5줄 핵심 요약)",
  "key_decisions": ["string"],
  "risks_and_issues": ["string"],
  "participants": ["string"],
  "topics": ["string"],
  "next_meeting_agenda": ["string"]
}
"""
```

### Template 2: 액션 아이템 추출

```python
ACTION_ITEM_SYSTEM_PROMPT = """
당신은 회의 트랜스크립트에서 액션 아이템을 추출하는 전문가입니다.
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

출력 JSON 스키마:
{
  "action_items": [
    {
      "title": "string (동사로 시작하는 액션 아이템 제목)",
      "assignee": "string | null (트랜스크립트에서 추론, 불명확하면 null)",
      "deadline": "string | null (YYYY-MM-DD, 언급된 경우만)",
      "priority": "high | medium | low",
      "status": "todo",
      "context": "string (해당 액션 아이템의 배경 맥락 한 줄)"
    }
  ]
}
"""
```

### Template 3: PARA 자동 분류 추천

```python
PARA_CLASSIFY_SYSTEM_PROMPT = """
당신은 PARA 방법론 전문가입니다. 회의 요약을 보고 PARA 분류를 추천하세요.

PARA 분류 기준 (실행도 기반):
- project:  명확한 마감일 + 구체적 결과물이 있는 업무
- area:     지속적으로 책임져야 하는 영역 (마감 없음, 기준 유지)
- resource: 참고 자료, 관심사, 나중에 활용할 지식
- archive:  완료되었거나 중단된 항목

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

출력 JSON 스키마:
{
  "suggested_type": "project | area | resource | archive",
  "suggested_name": "string (분류될 PARA 아이템 이름)",
  "confidence": "number (0.0 ~ 1.0)",
  "reason": "string (분류 이유 한 줄, 한국어)"
}
"""
```

### Template 4: RAG 기반 Q&A 답변

```python
RAG_ANSWER_SYSTEM_PROMPT = """
당신은 프로젝트 지식 베이스를 기반으로 질문에 답변하는 AI 어시스턴트입니다.

규칙:
1. 아래 컨텍스트(회의록, 노트, 첨부파일)만을 근거로 답변하세요.
2. 컨텍스트에 없는 내용은 추측하지 말고 "해당 프로젝트 데이터에서 찾을 수 없습니다"라고 답하세요.
3. 답변 시 출처(회의명, 날짜)를 명시하세요.
4. 한국어로 답변하세요.

컨텍스트:
{context}
"""
```

---

## JSON 파싱 안전 유틸

모든 Claude 응답은 이 유틸을 통해 파싱한다. 직접 `json.loads()` 호출 금지.

```python
# backend/src/common/prompts.py 하단에 포함
import json, re

def parse_json_response(text: str) -> dict:
    """Claude 응답에서 JSON을 안전하게 파싱한다."""
    clean = re.sub(r"```json\s*|```\s*", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude 응답 JSON 파싱 실패: {e}\n원본:\n{text}") from e
```

---

## Claude API 호출 패턴

```python
import anthropic
from src.core.config import settings

client = anthropic.AsyncAnthropic(
    api_key=settings.anthropic_api_key.get_secret_value()
)

# 사용 예시
response = await client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    system=MEETING_SUMMARY_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": transcript_text}],
)
result = parse_json_response(response.content[0].text)
```

---

## 관련 테이블

| 단계 | 저장 테이블 | 주요 컬럼 |
|------|-------------|-----------|
| 요약 | `meeting_summaries` | summary, key_decisions, topics |
| 액션 | `action_items` | title, assignee_id, priority, status |
| PARA 추천 | `inbox_items` | ai_suggested_para_type, ai_confidence |
| 임베딩 | `embedding_chunks` | chunk_text, embedding(vector 1536), chunk_level, parent_chunk_id |
| 캐시 | `semantic_caches` | question, question_embedding, answer, sources |

---

## RAG 검색 파이프라인

> 이 문서는 **인제스트**(데이터 입력→임베딩 저장) 파이프라인을 다룬다.
> RAG **검색**(질문→답변 생성) 파이프라인의 상세 설계는 아래 문서를 참조:
>
> **→ [RAG 파이프라인 설계 및 고도화 방향](rag-pipeline.md)**
>
> 하이브리드 검색, 계층적 청킹, Semantic Cache, Re-ranking, 검색 범위 제어 등 Phase 3 고도화 전략 포함.
