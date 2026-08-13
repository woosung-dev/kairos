# Architecture gate — visibility 규칙 사본 재발 차단 (SSOT = common/visibility.py)
"""visibility 규칙(public/draft/private 분기)은 `src/common/visibility.py` 에만
존재해야 한다. 과거 이 규칙이 6개 도메인 13개 사이트에 복붙되며 private 누수
보안 버그가 사본마다 독립 재발했다 (ISSUE-040 / CAND-B / codex P2).

금지 패턴 (src/ 전체, SSOT 파일 제외):
1. `.visibility == "draft"` 류 attribute 비교 — ORM/object 레벨 rule 사본
2. raw SQL `visibility = 'public|draft|private'` 리터럴 — SQL rule 사본

주석(#)과 docstring 은 제외한다 (설명 문서는 허용, 실행 코드만 차단).
새 도메인이 visibility 게이트가 필요하면 common/visibility.py 의
apply_*/decide_project_access/project_access_clause 를 소비할 것.
"""
import ast
import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = BACKEND_ROOT / "src"
SSOT_FILE = SRC_DIR / "common" / "visibility.py"

ATTR_COMPARISON_RE = re.compile(r"\.visibility\s*==\s*[\"']")
RAW_SQL_LITERAL_RE = re.compile(r"visibility\s*=\s*'(?:public|draft|private)'")


def _docstring_line_ranges(tree: ast.Module) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                doc = body[0].value
                lines.update(range(doc.lineno, (doc.end_lineno or doc.lineno) + 1))
    return lines


def test_visibility_rule_exists_only_in_ssot() -> None:
    offenders: list[str] = []
    for path in sorted(SRC_DIR.rglob("*.py")):
        if path == SSOT_FILE:
            continue
        source = path.read_text()
        doc_lines = _docstring_line_ranges(ast.parse(source))
        for lineno, line in enumerate(source.splitlines(), start=1):
            if lineno in doc_lines:
                continue
            code = line.split("#", 1)[0]
            if ATTR_COMPARISON_RE.search(code) or RAW_SQL_LITERAL_RE.search(code):
                offenders.append(f"{path.relative_to(BACKEND_ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "visibility 규칙 사본 감지 — common/visibility.py SSOT 를 소비할 것:\n"
        + "\n".join(offenders)
    )


def test_ssot_file_still_defines_the_rule() -> None:
    """gate 자체의 형해화 방지 — SSOT 파일에는 규칙 리터럴이 실제로 존재해야 한다."""
    source = SSOT_FILE.read_text()
    assert RAW_SQL_LITERAL_RE.search(source)
    assert 'visibility == "draft"' in source or "visibility == 'draft'" in source
