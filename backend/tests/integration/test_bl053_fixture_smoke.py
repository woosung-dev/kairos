# BL-053 E4 — integration_session fixture 가 SM AsyncSession 인지 + 의존 fixture cascade 정상 동작 검증
"""Codex 1차 plan review MINOR-4 finding 수락 — fixture smoke test.

tests/conftest.py 의 integration_session fixture 의 inline ctor
`AsyncSession(engine, expire_on_commit=False)` 가 SM AsyncSession 의 ctor 호환을
직접 검증한다. 의존 fixture (auth_user / personal_ws) 까지 cascade 가 깨지지
않음을 동일 commit 에 묶어서 통합 테스트 실패로만 발견하는 위험을 제거.

근거: ~/.claude/plans/sprint-20-pure-wozniak.md E4 row + Codex MINOR-4.
"""
import pytest
from sqlalchemy import literal_column
from sqlmodel import select, text
from sqlmodel.ext.asyncio.session import AsyncSession as SMAsyncSession


@pytest.mark.asyncio
async def test_integration_session_is_smodel_async_session(integration_session) -> None:
    """integration_session 이 SQLModel AsyncSession 인스턴스이고 execute(text()) 동작."""
    assert isinstance(integration_session, SMAsyncSession), (
        f"integration_session 이 SM AsyncSession 이 아닙니다: {type(integration_session).__name__}"
    )

    # raw text 는 execute() 로 (BL-054 manifest G4)
    result = await integration_session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_integration_session_supports_exec(integration_session) -> None:
    """integration_session 이 SM 의 typed exec() 메서드를 지원 (BL-054 manifest G1 선행)."""
    result = await integration_session.exec(select(literal_column("1")))
    assert result.one() == 1


@pytest.mark.asyncio
async def test_dependent_fixtures_cascade_intact(
    integration_session,
    auth_user,
    personal_ws,
) -> None:
    """integration_session type 변경 후 의존 fixture (auth_user/personal_ws) cascade 정상.

    SM AsyncSession 가 SA AsyncSession 의 subclass 라 fixture cascade 가 깨지지 않는다.
    plan E4 fail-closed gate: 이 test fail = 사용자 정의 fixture 에 type 의존 cascade
    문제 → 즉시 stop + root-cause.
    """
    assert auth_user is not None
    assert auth_user.id is not None
    assert personal_ws is not None
    assert personal_ws.id is not None
