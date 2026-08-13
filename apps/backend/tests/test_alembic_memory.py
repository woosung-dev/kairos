# Sprint 15 Stage 4 R2 alembic migration 스키마 검증 테스트
"""memory_items + workspaces.type + 보조 테이블 스키마 검증.

conftest.SQLModel.metadata.create_all 로 테이블이 생성되므로
information_schema 조회로 컬럼/테이블 존재 여부를 확인한다.
"""
import pytest
from sqlmodel import text


@pytest.mark.asyncio
async def test_memory_items_table_exists(integration_session):
    """memory_items 테이블 + 필수 컬럼 12개 존재."""
    result = await integration_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'memory_items'"
        )
    )
    columns = {row[0] for row in result.all()}
    expected = {
        "id",
        "user_id",
        "workspace_id",
        "type",
        "raw_content",
        "distilled_json",
        "r2_audio_key",
        "embedding_chunk_id",
        "status",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert expected.issubset(columns), f"missing: {expected - columns}"


@pytest.mark.asyncio
async def test_workspaces_type_column(integration_session):
    """workspaces.type 컬럼 추가 확인."""
    result = await integration_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'workspaces' AND column_name = 'type'"
        )
    )
    assert result.scalar_one_or_none() == "type"


@pytest.mark.asyncio
async def test_promotion_audit_table(integration_session):
    """promotion_audit 테이블 + memory_id/embedding_status 컬럼 존재."""
    result = await integration_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'promotion_audit'"
        )
    )
    columns = {row[0] for row in result.all()}
    assert "memory_id" in columns
    assert "embedding_status" in columns


@pytest.mark.asyncio
async def test_memory_ai_calls_table(integration_session):
    """memory_ai_calls 테이블 + call_type/elapsed_ms/input_tokens 컬럼 존재."""
    result = await integration_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'memory_ai_calls'"
        )
    )
    columns = {row[0] for row in result.all()}
    assert {"call_type", "elapsed_ms", "input_tokens"}.issubset(columns)


@pytest.mark.asyncio
async def test_memory_query_embedding_cache_table(integration_session):
    """memory_query_embedding_cache 테이블 + workspace_id/normalized_query/embedding 컬럼 존재."""
    result = await integration_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'memory_query_embedding_cache'"
        )
    )
    columns = {row[0] for row in result.all()}
    assert {"workspace_id", "normalized_query", "embedding"}.issubset(columns)


@pytest.mark.asyncio
async def test_memory_events_table(integration_session):
    """memory_events 테이블 + event_type/latency_ms/event_metadata 컬럼 존재."""
    result = await integration_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'memory_events'"
        )
    )
    columns = {row[0] for row in result.all()}
    assert {"event_type", "latency_ms", "event_metadata"}.issubset(columns)
