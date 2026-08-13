# Architecture gate — I-1/B-1: Service 계층은 AsyncSession 인스턴스를 보유하지 않는다 (BUG-S28-ARCH-5)
"""헌법 I-1 / backend B-1 회귀 방지.

AsyncSession 은 Repository 만 보유한다. Service 는 단일 도메인 비즈니스 로직만 담당하고
DB 세션 접근은 Repository 에 위임한다. 오케스트레이터(`pipeline_service.py`)는 cross-domain
트랜잭션을 위해 `session_factory` 를 받는 것이 허용되므로 본 게이트는 `pipeline_service.py`
오케스트레이터를 제외한 도메인 service 파일(`service.py` + `invite_service.py` 등 `*_service.py`)을 검사한다.

allowlist: `onboarding/service.py` 는 다른 도메인 트랜잭션에 합류하는 보조 service 로
session 을 그대로 받아 commit/flush 없이 사용한다 (문서화된 예외, BL-F6 / ARCH-r2-2).
architecture deepening sprint(BL-S27e-F)에서 LazySeedService 추출 시 본 allowlist 제거.
"""
import re
from pathlib import Path

# apps/backend/tests/architecture/* → apps/backend/ 까지 3-up
BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = BACKEND_ROOT / "src"

# session 인스턴스 보유가 허용된 파일 (문서화된 예외).
SESSION_HOLD_ALLOWLIST = {"onboarding/service.py"}


def _domain_service_files() -> list[Path]:
    """도메인 service 파일 (`service.py` + `*_service.py`), pipeline_service.py 오케스트레이터 제외.

    invite_service.py 등 보조 도메인 service 도 I-1 대상 (자체 docstring 이 규칙 선언).
    pipeline_service.py 는 cross-domain 오케스트레이터로 session_factory 수령이 허용(I-2)되어 제외.
    """
    files = set(SRC_DIR.glob("*/service.py")) | set(SRC_DIR.glob("*/*_service.py"))
    return sorted(f for f in files if f.name != "pipeline_service.py")


def test_no_sqlalchemy_asyncsession_import_in_service() -> None:
    """service.py 가 `from sqlalchemy.ext.asyncio import AsyncSession` 0건 (I-1 literal)."""
    pattern = re.compile(
        r"^\s*from\s+sqlalchemy\.ext\.asyncio\s+import\s+.*AsyncSession",
        re.MULTILINE,
    )
    offenders = [
        str(p.relative_to(SRC_DIR))
        for p in _domain_service_files()
        if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == [], (
        f"I-1 위반: service 계층이 sqlalchemy.ext.asyncio.AsyncSession 를 import. "
        f"AsyncSession 은 Repository 만 보유. offenders={offenders}"
    )


def test_no_session_instance_held_in_service() -> None:
    """service.py 가 단일 세션 인스턴스(`self._session`)를 미보유 — onboarding 예외 allowlist.

    `self._session_factory` 패턴은 word-boundary 로 제외된다 (`self._session\\b` 는
    `_factory` 가 word char 라 매칭되지 않음).
    """
    pattern = re.compile(r"self\._session\b")
    offenders = []
    for path in _domain_service_files():
        rel = str(path.relative_to(SRC_DIR))
        if rel in SESSION_HOLD_ALLOWLIST:
            continue
        if pattern.search(path.read_text(encoding="utf-8")):
            offenders.append(rel)
    assert offenders == [], (
        f"I-1 위반: service 가 AsyncSession 인스턴스(self._session)를 보유. "
        f"session_factory 패턴 또는 Repository 위임 필요. offenders={offenders}"
    )
