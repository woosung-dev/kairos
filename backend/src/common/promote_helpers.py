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
