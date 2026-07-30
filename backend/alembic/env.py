# backend/alembic/env.py
"""Alembic 비동기 마이그레이션 환경 설정."""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.core.config import get_settings

# 모든 모델을 import하여 metadata에 등록
from src.auth.models import User  # noqa: F401
from src.workspaces.models import (  # noqa: F401
    Workspace,
    WorkspaceMember,
    WorkspaceInvite,
)
from src.meetings.models import Meeting, MeetingSummary, TranscriptSegment  # noqa: F401
from src.projects.models import (  # noqa: F401
    Project,
    MeetingProjectLink,
    ProjectMember,
)
from src.actions.models import ActionItem  # noqa: F401
from src.inbox.models import InboxItem  # noqa: F401
from src.embeddings.models import EmbeddingChunk, SemanticCache  # noqa: F401
from src.notes.models import Note  # noqa: F401
from src.memory.models import (  # noqa: F401
    MemoryItem,
    MemoryAICall,
    MemoryEvent,
    PromotionAudit,
    MemoryQueryEmbeddingCache,
)
from src.integrations.models import (  # noqa: F401
    ExternalDocument,
    IntegrationConnection,
    IntegrationSyncRun,
)
from src.common.promote_models import ItemPromotionAudit  # noqa: F401

from sqlmodel import SQLModel

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

# env.py에서 동적으로 DB URL 설정.
# Sprint 19 PR #2 D7.5a (Codex v2 F-3): 외부에서 주입한 sqlalchemy.url 가 있으면 우선 (테스트 환경).
# 없으면 settings 사용 (운영 / 로컬 alembic 명령 = 기존 동작 유지).
if not config.get_main_option("sqlalchemy.url"):
    settings = get_settings()
    config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """오프라인 모드(SQL 스크립트 생성)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """비동기 엔진으로 마이그레이션 실행."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """온라인 모드 (비동기)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
