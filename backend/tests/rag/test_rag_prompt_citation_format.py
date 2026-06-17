# RAG 인용 포맷 회귀 가드 — 프롬프트가 FE([N] 렌더러)와 정합하는 [1],[2] 번호 인용을 지시하는지 검증
"""P-FIX-1: RAG_SYSTEM_PROMPT 의 인용 형식이 FE markdown-message.tsx 의 정규식
`/\\[(\\d+)\\]/` 과 정합해야 인라인 citation→SourceViewer 가 동작한다.

배경: 이전 프롬프트는 "📎 제목(날짜)" 인용을 지시했으나 FE 는 `[N]` 만 클릭 배지로
렌더 → 실 LLM 이 [N] 을 내보내지 않아 인라인 인용이 프로덕션에서 동작하지 않았다.
"""
import re

from src.common.prompts import RAG_SYSTEM_PROMPT


def test_rag_prompt_instructs_numbered_bracket_citation() -> None:
    # 인용 규칙에 [1] / [2] 형식 번호 인용 지시가 존재해야 함 (FE [N] 렌더러 정합).
    assert "[1]" in RAG_SYSTEM_PROMPT
    assert "인용" in RAG_SYSTEM_PROMPT
    # 옛 이모지(📎) 인용 예시로의 회귀 금지.
    assert "📎" not in RAG_SYSTEM_PROMPT


def test_rag_prompt_bracket_digit_pattern_present() -> None:
    # FE 가 실제로 파싱하는 패턴 `[<digit>]` 이 프롬프트 안내에 등장.
    assert re.search(r"\[\d+\]", RAG_SYSTEM_PROMPT) is not None
