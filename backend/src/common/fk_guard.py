# workspace-scoped secondary FK 검증 헬퍼 — find + fail-closed 규약의 SSOT
"""PR-2 c3: "FK 입력 → 소유 repo 에서 (id, workspace_id) find → 없으면 도메인 404 +
repo 미주입이면 fail-closed RuntimeError" 패턴이 4개 도메인(actions/projects/notes/
inbox)에 재구현돼 있던 것을 통합한다 (헌법 I-9 cross-tenant 거부, Codex F-2).

공유 범위는 find + fail-closed 까지 — 예외 '타입' 매핑은 호출 도메인이 not_found
callable 로 소유한다 (API 404 의미 보존, codex 제약).
"""
import uuid
from collections.abc import Callable
from typing import Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)


class WorkspaceScopedFinder(Protocol[T_co]):
    async def find_by_id(
        self, entity_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> "T_co | None": ...


async def require_in_workspace(
    repo: "WorkspaceScopedFinder[T_co] | None",
    entity_id: uuid.UUID | None,
    workspace_id: uuid.UUID,
    *,
    not_found: Callable[[], Exception],
    repo_label: str,
) -> "T_co | None":
    """entity_id 가 workspace 소속인지 검증 후 엔티티 반환.

    - entity_id None → 통과 (None 반환)
    - repo None → RuntimeError (fail-closed — silent skip 금지, Codex 2차 Minor 1)
    - find 미스(cross-tenant/dangling) → not_found() raise (F-4 lock-in: 404)
    """
    if entity_id is None:
        return None
    if repo is None:
        raise RuntimeError(f"{repo_label} 필수 (F-2 검증)")
    entity = await repo.find_by_id(entity_id, workspace_id)
    if entity is None:
        raise not_found()
    return entity
