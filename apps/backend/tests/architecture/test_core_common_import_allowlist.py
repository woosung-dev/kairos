# Architecture gate — core ↔ common cycle 악화 방지 (BUG-S28-ARCH-4 / BUG-S28-ARCH-5)
"""`core` 는 최하위 레이어 — `common` 의존을 최소화한다.

현재 유일하게 허용된 core→common edge: `core/lifespan.py` 가 DB 엔진 lifecycle
(`init_engine` / `dispose_engine`)을 `common/database.py` 에서 import. 엔진이 `common` 에
있어 생긴 layered cycle (directory-map.md, BL-S27e-F BUG-S28-ARCH-4). architecture
deepening sprint 에서 `common/database.py` → `core/database.py` 이동으로 구조 해소 예정.

본 게이트는 그 전까지 *새* core→common edge 추가를 차단해 cycle 이 악화되지 않게 한다.
"""
import re
from pathlib import Path

# apps/backend/tests/architecture/* → apps/backend/ 까지 3-up
BACKEND_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = BACKEND_ROOT / "src" / "core"

# (파일명, 허용 import 모듈) — 문서화된 유일 edge.
ALLOWED_CORE_TO_COMMON = {("lifespan.py", "src.common.database")}

IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(src\.common[\w.]*)\s+import|import\s+(src\.common[\w.]*))",
    re.MULTILINE,
)


def test_core_does_not_import_common_beyond_allowlist() -> None:
    """core/*.py 의 src.common import 는 문서화된 allowlist 와 정확히 일치한다."""
    offenders = []
    for path in CORE_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for match in IMPORT_RE.finditer(source):
            module = match.group(1) or match.group(2)
            if (path.name, module) not in ALLOWED_CORE_TO_COMMON:
                offenders.append(f"{path.name} → {module}")
    assert offenders == [], (
        f"core→common cycle 악화: 허용되지 않은 core→common import. "
        f"allowlist={sorted(ALLOWED_CORE_TO_COMMON)}. offenders={offenders}"
    )
