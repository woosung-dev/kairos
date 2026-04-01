# backend/src/common/prompts.py
"""AI 프롬프트 상수. 인라인 프롬프트 작성 금지 — 모든 프롬프트는 여기서 관리."""
import json
import re

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


def parse_json_response(text: str) -> dict:
    """Claude 응답에서 JSON을 안전하게 파싱한다.

    코드펜스(```json ... ```) 제거 후 파싱.
    직접 json.loads() 호출 금지 — 반드시 이 유틸을 사용할 것.
    """
    clean = re.sub(r"```json\s*|```\s*", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude 응답 JSON 파싱 실패: {e}\n원본:\n{text}") from e
