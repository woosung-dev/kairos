# Sprint 23 D4 promote_helpers utility 단위 테스트 — 4 도메인 공통 검증/빌더 안전성
"""promote_helpers utility 단위 테스트.

scope:
- validate_promote_target: 5 cases (success / same_workspace / target_invalid / target_personal / not_member)
- build_item_promotion_audit: 2 cases (success / item_type invalid)

mock workspace_repo = SimpleNamespace 기반 lightweight (실 DB 미접근).
"""
import uuid
from types import SimpleNamespace

import pytest

from src.common.promote_helpers import (
    PromoteValidationError,
    build_item_promotion_audit,
    validate_promote_target,
)
from src.common.promote_models import (
    PROMOTABLE_ITEM_TYPES,
    ItemPromotionAudit,
)


def _ws(*, type_: str = "team") -> SimpleNamespace:
    return SimpleNamespace(type=type_)


def _member() -> SimpleNamespace:
    return SimpleNamespace(role="member")


class _RepoSuccess:
    """target 존재 + team + 멤버 모두 OK."""

    def __init__(self, *, target_type: str = "team") -> None:
        self._target_type = target_type

    async def find_by_id(self, workspace_id):  # noqa: ARG002 — 시그니처 정합
        return _ws(type_=self._target_type)

    async def find_member(self, workspace_id, user_id):  # noqa: ARG002
        return _member()


class _RepoTargetMissing:
    async def find_by_id(self, workspace_id):  # noqa: ARG002
        return None

    async def find_member(self, workspace_id, user_id):  # noqa: ARG002
        return None


class _RepoNotMember:
    async def find_by_id(self, workspace_id):  # noqa: ARG002
        return _ws()

    async def find_member(self, workspace_id, user_id):  # noqa: ARG002
        return None


@pytest.mark.asyncio
async def test_validate_promote_target_success():
    await validate_promote_target(
        source_workspace_id=uuid.uuid4(),
        target_workspace_id=uuid.uuid4(),
        promoted_by_user_id=uuid.uuid4(),
        workspace_repo=_RepoSuccess(),
    )


@pytest.mark.asyncio
async def test_validate_promote_target_same_workspace_raises():
    wid = uuid.uuid4()
    with pytest.raises(PromoteValidationError) as exc_info:
        await validate_promote_target(
            source_workspace_id=wid,
            target_workspace_id=wid,
            promoted_by_user_id=uuid.uuid4(),
            workspace_repo=_RepoSuccess(),
        )
    assert exc_info.value.code == "same_workspace"


@pytest.mark.asyncio
async def test_validate_promote_target_missing_repo_raises_runtime():
    with pytest.raises(RuntimeError, match="workspace_repo 필수"):
        await validate_promote_target(
            source_workspace_id=uuid.uuid4(),
            target_workspace_id=uuid.uuid4(),
            promoted_by_user_id=uuid.uuid4(),
            workspace_repo=None,
        )


@pytest.mark.asyncio
async def test_validate_promote_target_target_not_found_raises():
    with pytest.raises(PromoteValidationError) as exc_info:
        await validate_promote_target(
            source_workspace_id=uuid.uuid4(),
            target_workspace_id=uuid.uuid4(),
            promoted_by_user_id=uuid.uuid4(),
            workspace_repo=_RepoTargetMissing(),
        )
    assert exc_info.value.code == "target_invalid"


@pytest.mark.asyncio
async def test_validate_promote_target_personal_raises():
    with pytest.raises(PromoteValidationError) as exc_info:
        await validate_promote_target(
            source_workspace_id=uuid.uuid4(),
            target_workspace_id=uuid.uuid4(),
            promoted_by_user_id=uuid.uuid4(),
            workspace_repo=_RepoSuccess(target_type="personal"),
        )
    assert exc_info.value.code == "target_personal"


@pytest.mark.asyncio
async def test_validate_promote_target_not_member_raises():
    with pytest.raises(PromoteValidationError) as exc_info:
        await validate_promote_target(
            source_workspace_id=uuid.uuid4(),
            target_workspace_id=uuid.uuid4(),
            promoted_by_user_id=uuid.uuid4(),
            workspace_repo=_RepoNotMember(),
        )
    assert exc_info.value.code == "not_member"


def test_build_item_promotion_audit_success():
    src_id = uuid.uuid4()
    new_id = uuid.uuid4()
    src_ws = uuid.uuid4()
    tgt_ws = uuid.uuid4()
    user = uuid.uuid4()

    audit = build_item_promotion_audit(
        item_type="meeting",
        source_item_id=src_id,
        new_item_id=new_id,
        source_workspace_id=src_ws,
        target_workspace_id=tgt_ws,
        promoted_by_user_id=user,
        embedding_status="pending",
    )

    assert isinstance(audit, ItemPromotionAudit)
    assert audit.item_type == "meeting"
    assert audit.source_item_id == src_id
    assert audit.new_item_id == new_id
    assert audit.source_workspace_id == src_ws
    assert audit.target_workspace_id == tgt_ws
    assert audit.promoted_by_user_id == user
    assert audit.embedding_status == "pending"


def test_build_item_promotion_audit_invalid_item_type_raises():
    with pytest.raises(ValueError, match="item_type='memory'"):
        build_item_promotion_audit(
            item_type="memory",  # memory 는 별도 PromotionAudit 사용 — 본 utility 미지원
            source_item_id=uuid.uuid4(),
            new_item_id=uuid.uuid4(),
            source_workspace_id=uuid.uuid4(),
            target_workspace_id=uuid.uuid4(),
            promoted_by_user_id=uuid.uuid4(),
        )


def test_promotable_item_types_lock():
    """PROMOTABLE_ITEM_TYPES 가 CHECK constraint 와 일치해야 함."""
    assert PROMOTABLE_ITEM_TYPES == ("meeting", "note", "inbox", "action")
