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


def test_rag_prompt_forbids_citation_when_information_is_missing() -> None:
    assert "이 경우 인용 번호를 붙이지 마세요" in RAG_SYSTEM_PROMPT


def test_rag_prompt_bracket_digit_pattern_present() -> None:
    # FE 가 실제로 파싱하는 패턴 `[<digit>]` 이 프롬프트 안내에 등장.
    assert re.search(r"\[\d+\]", RAG_SYSTEM_PROMPT) is not None


def test_rag_prompt_does_not_instruct_stale_source_warning() -> None:
    # freshness 표시는 결정론적 source metadata 경로만 소유한다.
    assert "오래된 소스입니다" not in RAG_SYSTEM_PROMPT


def test_rag_prompt_forbids_source_selection_narration() -> None:
    """BL-RAG-PROMPT-HYGIENE-1: 소스 선정 과정을 답변 본문에 서술하지 말라는 제약.

    관측된 답변에 "…는 보안 정책에 따라 제외되었습니다" 가 나왔다. 프롬프트에 그런
    지시는 없었고(규칙 4는 PR #146 에서 제거됨) _format_sources_for_prompt 도
    visibility 를 넘기지 않으므로, LLM 이 자발적으로 붙인 메타 서술이다.
    제거할 규칙이 없으니 제약을 더한다.

    ⚠ 제약 문구에 "제외" 같은 단어를 쓰면 오히려 그 서술을 프라이밍한다. 쓰지 않는다.
    """
    assert "질문에 대한 내용만" in RAG_SYSTEM_PROMPT
    assert "소스가 어떻게 선정" in RAG_SYSTEM_PROMPT
    for priming_word in ("제외", "보안", "정책", "기밀"):
        assert priming_word not in RAG_SYSTEM_PROMPT
