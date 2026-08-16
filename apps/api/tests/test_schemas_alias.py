# apps/backend/tests/test_schemas_alias.py
"""헌법 I-16 회귀 차단 — 모든 Request* 스키마의 snake_case 필드는 camelCase alias + populate_by_name 강제.

Sprint 14 T-5 (BUG-H03) 도입. UpdateWorkspaceSettingsRequest 회귀를 잡지 못한 원인이
introspection 검증 부재였기 때문에 본 테스트로 모든 도메인을 일괄 audit.
"""
import ast
import pathlib

SCHEMAS_ROOT = pathlib.Path(__file__).parent.parent / "src"


def _to_camel(snake: str) -> str:
    head, *rest = snake.split("_")
    return head + "".join(seg[:1].upper() + seg[1:] for seg in rest)


def _audit_request_classes() -> list[dict]:
    """모든 schemas.py 의 Request* 클래스 introspection.

    위반 = snake_case 필드가 있는데 alias 누락 또는 populate_by_name 미설정.
    """
    violations: list[dict] = []
    for f in sorted(SCHEMAS_ROOT.rglob("schemas.py")):
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not node.name.endswith("Request"):
                continue

            # populate_by_name 설정 여부 (model_config 대입식 검사)
            has_populate = False
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "model_config":
                            if "populate_by_name" in ast.unparse(stmt.value):
                                has_populate = True

            snake_fields: list[str] = []
            snake_with_alias: list[str] = []
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    fname = stmt.target.id
                    # _ 접두사(private) 는 제외, snake_case 식별
                    if "_" in fname and not fname.startswith("_"):
                        snake_fields.append(fname)
                        if stmt.value and "alias" in ast.unparse(stmt.value):
                            snake_with_alias.append(fname)

            missing_alias = [f_ for f_ in snake_fields if f_ not in snake_with_alias]
            if snake_fields and (missing_alias or not has_populate):
                violations.append({
                    "file": str(f.relative_to(SCHEMAS_ROOT.parent)),
                    "class": node.name,
                    "snake_fields": snake_fields,
                    "missing_alias": missing_alias,
                    "has_populate_by_name": has_populate,
                    "expected_aliases": {f_: _to_camel(f_) for f_ in missing_alias},
                })
    return violations


def test_all_request_schemas_have_camelcase_alias_and_populate_by_name():
    """헌법 I-16: 모든 Request 스키마는 snake_case 필드에 camelCase alias + populate_by_name=True."""
    violations = _audit_request_classes()
    assert not violations, (
        "헌법 I-16 위반 — 다음 Request 스키마에 alias/populate_by_name 누락:\n"
        + "\n".join(
            f"  - {v['file']}::{v['class']} (missing: {v['missing_alias']}, "
            f"populate_by_name: {v['has_populate_by_name']}, "
            f"expected: {v['expected_aliases']})"
            for v in violations
        )
    )


def test_audit_helper_finds_zero_violations_baseline():
    """기준선 — Sprint 14 T-5 fix 직후 위반 0건. 미래에 새 Request 추가 시 회귀 즉시 차단."""
    violations = _audit_request_classes()
    assert len(violations) == 0, (
        f"새 Request 스키마 도입 시 alias/populate_by_name 누락. {len(violations)}건 위반."
    )
