"""IntegrationRepository 질의의 WHERE 절 회귀 가드.

★왜 이 파일이 따로 있는가 — `tests/integrations/test_pipeline_service.py` 의
fake repository 는 필터를 **스스로 재구현**한다. 그래서 실제
`IntegrationRepository.find_documents_by_connection` 의 `connection_id` 조건을
지워도 pipeline 테스트는 전부 통과한다 (2026-09-11 독립 리뷰에서 실측).

testcontainers 기반 통합 테스트는 Docker 가 필요한데, 여기서 보려는 것은
"질의가 어떤 컬럼으로 좁히는가" 뿐이므로 **컴파일된 SQL** 을 직접 단언한다.
DB 없이 돌고, 필터 삭제 변이를 확실히 잡는다.
"""
import uuid

import pytest

from src.integrations.repository import IntegrationRepository


class _StatementCapturingSession:
    """`exec()` 에 넘어온 statement 를 잡아두는 최소 세션 스텁."""

    def __init__(self) -> None:
        self.statements: list[object] = []

    async def exec(self, statement: object) -> "_EmptyResult":
        self.statements.append(statement)
        return _EmptyResult()


class _EmptyResult:
    def all(self) -> list[object]:
        return []


def _compiled_sql(statement: object) -> str:
    return str(statement.compile())  # type: ignore[attr-defined]


@pytest.fixture
def session() -> _StatementCapturingSession:
    return _StatementCapturingSession()


async def test_find_documents_by_connection_filters_workspace_and_connection(
    session: _StatementCapturingSession,
) -> None:
    """연결 한정 조회 — 두 컬럼 **모두** 로 좁혀야 한다.

    `connection_id` 조건이 빠지면 두 번째 provider 가 생겼을 때 연결 해제가
    남의 provider 문서까지 파기한다 (repository docstring 참조). workspace 전량
    조회판을 두지 않기로 한 결정도 같은 이유다.
    """
    repository = IntegrationRepository(session)  # type: ignore[arg-type]

    await repository.find_documents_by_connection(uuid.uuid4(), uuid.uuid4())

    sql = _compiled_sql(session.statements[0])
    assert "external_documents.workspace_id = " in sql
    assert "external_documents.connection_id = " in sql


async def test_find_documents_by_connection_defers_plain_text(
    session: _StatementCapturingSession,
) -> None:
    """목록 경로는 본문을 싣지 않는다 — defer 가 빠지면 응답에 전문이 실린다."""
    repository = IntegrationRepository(session)  # type: ignore[arg-type]

    await repository.find_documents_by_connection(uuid.uuid4(), uuid.uuid4())

    assert "external_documents.plain_text" not in _compiled_sql(session.statements[0])
