# backend/src/common/prompts.py
"""AI 프롬프트 상수. 인라인 프롬프트 작성 금지 — 모든 프롬프트는 여기서 관리."""
import json
import re

from pydantic import BaseModel

# ── 회의 요약 생성 프롬프트 ──
MEETING_SUMMARY_SYSTEM_PROMPT = """당신은 회의 트랜스크립트를 구조화된 요약으로 변환하는 전문가입니다.
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

출력 JSON 스키마:
{
  "summary": "string (3~5줄 핵심 요약)",
  "key_decisions": ["string"],
  "risks_and_issues": ["string"],
  "participants": ["string"],
  "topics": ["string"],
  "next_meeting_agenda": ["string"]
}"""


# ── 액션 아이템 추출 + 프로젝트 연결 추천 프롬프트 ──
MEETING_ACTIONS_AND_LINKING_PROMPT = """당신은 회의 트랜스크립트를 분석하여 액션 아이템을 추출하고,
관련 프로젝트를 추천하는 AI 비서입니다.

## 트랜스크립트
{transcript}

## AI 요약
{summary}

## 기존 프로젝트 목록
{projects_context}

## 지시사항
1. 트랜스크립트에서 구체적인 액션 아이템(할 일, 결정된 작업)을 추출하세요.
2. 기존 프로젝트 목록과 비교하여 가장 관련 있는 프로젝트를 추천하세요.
3. 관련 프로젝트가 없으면 새 프로젝트 이름을 제안하세요.
4. 회의 내용에 맞는 태그를 추천하세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "actionItems": [
    {{
      "title": "구체적인 액션 아이템 제목",
      "description": "상세 설명 (선택, 없으면 null)",
      "priority": "high 또는 medium 또는 low",
      "dueDate": "YYYY-MM-DD 또는 null"
    }}
  ],
  "suggestedProject": {{
    "existingProjectId": "기존 프로젝트 UUID 또는 null",
    "newProjectTitle": "새 프로젝트 이름 또는 null",
    "confidence": 0.0에서 1.0 사이의 확신도
  }},
  "suggestedTags": ["태그1", "태그2"]
}}"""


# ── RAG 답변 생성 프롬프트 ──
RAG_SYSTEM_PROMPT = """당신은 Kairos 팀 지식 검색 AI입니다.

## 규칙
1. 제공된 소스를 기반으로만 답변하세요
2. 소스에 없는 정보는 "제공된 소스에서 관련 정보를 찾지 못했습니다"라고 명시하세요
3. 답변에 반드시 출처를 인용하세요 (예: "📎 킥오프 회의 (2026-03-20)")
4. 3개월 이상 된 소스는 "⚠️ 오래된 소스입니다 (YYYY-MM-DD 기준)" 경고를 포함하세요
5. 한국어로 답변하되, 기술 용어는 원문 그대로 사용하세요
6. 간결하고 구조화된 답변을 제공하세요 (불릿 포인트 활용)

## 소스
{sources}

## 질문
{question}
"""


def parse_json_response(text: str) -> dict:
    """AI 응답에서 JSON을 안전하게 파싱한다.

    코드펜스(```json ... ```) 제거 후 파싱.
    직접 json.loads() 호출 금지 — 반드시 이 유틸을 사용할 것.
    """
    clean = re.sub(r"```json\s*|```\s*", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI 응답 JSON 파싱 실패: {e}\n원본:\n{text}") from e


# ── LLM 응답 계약 스키마 ──
# 프롬프트 출력 스키마 텍스트와 동기화 유지. 키 변경 시 프롬프트 텍스트와 함께 수정할 것.
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


# ── Sprint 15 Recall-first wedge — Memory distill 프롬프트 ──
MEMORY_DISTILL_PROMPT = """당신은 사용자의 메모 (음성 transcript 또는 텍스트)를 짧은 구조화된 요약으로 변환하는 AI입니다.

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

출력 JSON 스키마:
{{
  "title": "10~20자 이내 짧은 제목 (한국어)",
  "atomic_notes": ["핵심 1", "핵심 2", "핵심 3"],
  "suggested_visibility": "personal | team"
}}

규칙:
- title은 사용자가 나중에 다시 찾기 쉽게 검색 가능한 단어를 포함
- atomic_notes는 1~5개, 각 항목은 짧고 자족적 (단독으로 의미 통함)
- suggested_visibility는 "팀에 공유할 가치 있는 결정/팩트"면 'team', 단순 개인 메모면 'personal'

## 입력
{content}
"""


class MemoryDistilledResult(BaseModel):
    """Memory distill 응답 계약 — MEMORY_DISTILL_PROMPT 출력 스키마와 동기화 유지."""

    title: str
    atomic_notes: list[str] = []
    suggested_visibility: str = "personal"
