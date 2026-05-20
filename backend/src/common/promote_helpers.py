# 4 도메인 cross-workspace promote 공통 헬퍼 — 검증 + audit row 빌더
"""Sprint 23 D4 — Promotable 도메인 공통 헬퍼 (utility 패턴).

scope (memory 외 4 도메인 — meeting / note / inbox / action 공통):
- validate_promote_target: workspace_repo 통한 target 검증 (memory.service.promote 의 검증 패턴 추출)
- build_item_promotion_audit: ItemPromotionAudit row 빌더 (commit 은 호출자)

도메인별 service.promote 가 본 헬퍼 호출 + 도메인 metadata 복제 + embedding 복제
hook 자체 구현. 헌법 I-18 (Promotion = 복제 + tombstone, 이동 금지) 강제.

abstract base 대신 utility 채택 사유:
- 도메인별 metadata 복제 + 임베딩 복제는 매우 다양 (transcript+chunks / note_chunks / 없음 / meeting ref)
- abstract method override 패턴은 도메인 코드를 부자연스럽게 만듦
- utility = 도메인 service.promote 가 명시적으로 호출 = 의존 명확 + test 단순

memory 도메인은 본 헬퍼 미사용 (memory.PromotionAudit 별도 + 기존 안정 코드 보존).
"""
import uuid
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .promote_models import PROMOTABLE_ITEM_TYPES, ItemPromotionAudit


class PromoteValidationError(Exception):
    """promote validation 실패 — 도메인 service 가 잡아 도메인별 예외로 변환.

    code:
    - 'same_workspace': source/target 동일
    - 'target_invalid': target workspace 미존재
    - 'target_personal': target = personal workspace (I-19 강제)
    - 'not_member': promoter 가 target workspace 멤버 아님
    """

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


async def validate_promote_target(
    *,
    source_workspace_id: uuid.UUID,
    target_workspace_id: uuid.UUID,
    promoted_by_user_id: uuid.UUID,
    workspace_repo: Any,
) -> None:
    """promote target 검증 — 4 도메인 동일 로직.

    Args:
        source_workspace_id: 원본 workspace ID
        target_workspace_id: 대상 workspace ID
        promoted_by_user_id: promote 수행 user ID
        workspace_repo: WorkspaceRepository instance — None 이면 fail-closed RuntimeError

    Raises:
        PromoteValidationError: 검증 실패 — 도메인 service 가 도메인별 예외로 변환
        RuntimeError: workspace_repo 미주입 (Codex F-4 fail-closed 패턴)
    """
    if source_workspace_id == target_workspace_id:
        raise PromoteValidationError(
            "same_workspace", "source/target workspace 동일"
        )

    if workspace_repo is None:
        raise RuntimeError(
            "workspace_repo 필수 (I-18 promote target 검증, fail-closed)"
        )

    target = await workspace_repo.find_by_id(target_workspace_id)
    if target is None:
        raise PromoteValidationError(
            "target_invalid",
            f"target workspace {target_workspace_id} not found",
        )

    # Sprint 23 Codex 8차 P2 fix: membership 확인을 personal/type 검증 보다 먼저 수행 →
    # cross-tenant workspace 존재/type 정보 leak 차단. target_personal 은 멤버 확인 후에만 노출.
    member = await workspace_repo.find_member(
        target_workspace_id, promoted_by_user_id
    )
    if member is None:
        raise PromoteValidationError(
            "not_member", "promoter 가 target workspace 멤버 아님"
        )

    # Sprint 23 Codex 3차 P1 fix: target ws viewer role 거부 (RBAC bypass 차단).
    # 사유: route 의 require_member 는 source workspace_id 만 적용 → target 의 viewer 도
    # 통과 가능했으나, promote 는 target ws insert 작업이라 member 이상 write 권한 필요.
    if getattr(member, "role", None) == "viewer":
        raise PromoteValidationError(
            "not_member",
            "target workspace viewer role 은 promote 불가 (write 권한 필요)",
        )

    # 멤버 확인 후에만 type 검증 (personal info leak 차단, Codex 8차 P2)
    if getattr(target, "type", "team") == "personal":
        raise PromoteValidationError(
            "target_personal", "personal workspace 로 promote 불가"
        )


def build_item_promotion_audit(
    *,
    item_type: str,
    source_item_id: uuid.UUID,
    new_item_id: uuid.UUID,
    source_workspace_id: uuid.UUID,
    target_workspace_id: uuid.UUID,
    promoted_by_user_id: uuid.UUID,
    embedding_status: str = "pending",
) -> ItemPromotionAudit:
    """ItemPromotionAudit row 빌드 (commit 은 호출자 책임).

    item_type 은 PROMOTABLE_ITEM_TYPES 중 하나 — 호출 시점 검증
    (DB CHECK constraint 와 정합, fail-fast).
    """
    if item_type not in PROMOTABLE_ITEM_TYPES:
        raise ValueError(
            f"item_type='{item_type}' is not in {PROMOTABLE_ITEM_TYPES}"
        )

    return ItemPromotionAudit(
        item_type=item_type,
        source_item_id=source_item_id,
        new_item_id=new_item_id,
        source_workspace_id=source_workspace_id,
        target_workspace_id=target_workspace_id,
        promoted_by_user_id=promoted_by_user_id,
        embedding_status=embedding_status,
    )


# ── Sprint 24 Task 2 (BL-063): Meeting promote 의 ActionItem 자동 복제 helper ──


async def clone_action_items_for_promote(
    *,
    source_meeting_id: uuid.UUID,
    target_meeting_id: uuid.UUID,
    target_workspace_id: uuid.UUID,
    target_project_id: uuid.UUID | None,
    session: AsyncSession,
) -> int:
    """Meeting promote 의 source ActionItem rows 자동 복제 (Sprint 24 BL-063).

    Sprint 23 D4 (Codex 3차 P3) 임시 fix 의 `action_item_count=0` reset 보강:
    source ActionItem rows 를 target meeting_id 로 remap 복제하여 target meeting 의
    action 탭에 source 와 동일한 행들이 노출되도록 한다.

    Args:
        source_meeting_id: 원본 Meeting id
        target_meeting_id: 복제본 Meeting id
        target_workspace_id: 복제본 workspace id (composite FK + WorkspaceMember 검증용)
        target_project_id: 복제본 project id (현재는 None — cross-ws project 제약, 추후 사용자 수동 연결)
        session: parent SAVEPOINT 안에서 활성 AsyncSession (commit 은 호출자)

    Returns:
        실제 복제된 ActionItem row count (Meeting.action_item_count 갱신용)

    정책:
    - assignee_id: target ws WorkspaceMember 멤버 검증 → 부재 시 None reset
      (cross-workspace 누출 차단, 사용자 결정 게이트 #5)
    - composite FK: workspace_id + project_id + meeting_id 모두 target 으로 remap
      (Sprint 19 PR #2 / Sprint 21 BL-050 헌법 I-9 (9))
    - 트랜잭션: parent SAVEPOINT 활용 — flush() 실패 시 entire promote rollback

    Sprint 23 4 도메인 promote 패턴과 동일하게 utility 함수로 제공 (abstract base 회피).
    """
    # 순환 import 회피 — 함수 내 import (Sprint 23 cross-domain pattern 정렬)
    from src.actions.models import ActionItem
    from src.workspaces.models import WorkspaceMember

    # 1. source ActionItem rows fetch
    source_result = await session.exec(
        select(ActionItem).where(ActionItem.meeting_id == source_meeting_id)
    )
    source_items = list(source_result.all())
    if not source_items:
        return 0

    # 2. target ws member user_id set fetch — assignee 누출 차단 (사용자 결정 게이트 #5)
    member_result = await session.exec(
        select(WorkspaceMember.user_id).where(
            WorkspaceMember.workspace_id == target_workspace_id
        )
    )
    target_member_ids: set[uuid.UUID] = set(member_result.all())

    # 3. remap (composite FK + assignee None reset)
    # ActionItem 실 fields (Codex 1차 P2-2 정합):
    # id(default) / workspace_id / meeting_id / project_id / title / description /
    # assignee_id / due_date / priority / status / created_at(default) / updated_at(default)
    # created_by_id 필드 부재 — ActionItem 모델은 promoter 추적 미보유
    # (audit.promoted_by_user_id 로 ledger 분리, docs/api/endpoints.md §45 참조).
    cloned: list[ActionItem] = []
    for src in source_items:
        cloned.append(
            ActionItem(
                workspace_id=target_workspace_id,
                project_id=target_project_id,
                meeting_id=target_meeting_id,
                assignee_id=(
                    src.assignee_id
                    if src.assignee_id is not None
                    and src.assignee_id in target_member_ids
                    else None
                ),
                title=src.title,
                description=src.description,
                status=src.status,
                priority=src.priority,
                due_date=src.due_date,
            )
        )

    # 4. bulk save — parent SAVEPOINT 활용. flush() 로 FK error 즉시 발견.
    session.add_all(cloned)
    await session.flush()
    return len(cloned)
