# Architecture gate — I-4/B-6: Gemini 프롬프트 상수는 common/prompts.py 에만 정의 (BUG-S28-ARCH-5)
"""헌법 I-4 / backend B-6 회귀 방지.

모든 Gemini 프롬프트는 `common/prompts.py` 의 UPPER_SNAKE 상수로 중앙 관리한다.
service / pipeline_service / services 등 어디에도 인라인 프롬프트 상수 정의 금지.
"""
import re
from pathlib import Path

# apps/api/tests/architecture/* → apps/api/ 까지 3-up
BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = BACKEND_ROOT / "src"
PROMPTS_FILE = SRC_DIR / "common" / "prompts.py"

# 상수명이 `_PROMPT` 로 끝나고 문자열 리터럴을 할당하는 정의만 매칭.
# (MAX_PROMPT_LENGTH / ENABLE_PROMPT_LOGGING 같은 비-프롬프트 상수 오탐 방지 — 끝이 _PROMPT 아님.)
PROMPT_DEF = re.compile(r'''^[A-Z][A-Z0-9_]*_PROMPT\s*=\s*[rf]?["']''', re.MULTILINE)


def test_all_prompt_constants_live_in_common_prompts() -> None:
    """`*_PROMPT` 상수 정의는 common/prompts.py 외부에 존재하지 않는다."""
    offenders = []
    for path in SRC_DIR.rglob("*.py"):
        if path == PROMPTS_FILE:
            continue
        if PROMPT_DEF.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(SRC_DIR)))
    assert offenders == [], (
        f"I-4 위반: common/prompts.py 외부에 *_PROMPT 상수 정의 발견. "
        f"프롬프트 인라인 금지 — common/prompts.py 로 이동. offenders={offenders}"
    )
