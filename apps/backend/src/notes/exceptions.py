# backend/src/notes/exceptions.py
from fastapi import HTTPException

from src.common.exceptions import NotFoundError


class NoteNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("노트")


class NoteDeleteForbiddenError(HTTPException):
    """BL-NOTE-DELETE-POLICY-1: 작성자 본인 또는 admin 이상만 노트를 삭제할 수 있다.

    404 가 아니라 403 인 이유 — 이 요청자는 그 노트를 이미 GET/list 로 읽을 수 있다.
    존재를 숨길 실익이 없고, GET 200 / DELETE 404 는 모순된 계약이다.
    보이지 않는 노트(cross-tenant / private·draft 비-멤버)는 기존대로 404 를 유지한다.
    """

    def __init__(self) -> None:
        super().__init__(
            status_code=403, detail="작성자 또는 admin 이상만 삭제할 수 있습니다"
        )


# ── Sprint 23 D4 Task 2 Step 2.3: promote 검증 예외 (meetings 패턴 정렬) ──


class TargetWorkspaceInvalidError(HTTPException):
    """target workspace 미존재 또는 promoter 가 멤버 아님."""

    def __init__(self) -> None:
        super().__init__(status_code=403, detail="대상 워크스페이스가 유효하지 않습니다")


class CannotPromoteToPersonalError(HTTPException):
    """personal workspace 로 promote 시도."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400, detail="개인 워크스페이스로는 promote 할 수 없습니다"
        )


class CannotPromoteToSameWorkspaceError(HTTPException):
    """source/target workspace 동일."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400, detail="같은 워크스페이스로는 promote 할 수 없습니다"
        )


class NotePromoteNotEmbeddedError(HTTPException):
    """Sprint 23 Codex 6차 P2 fix: 임베딩 미완료 note promote 시도.

    사유: source note 가 embed_note_async 비동기 임베딩 끝나기 전 promote 되면 chunk 0 →
    target ws 에 chunk 미복제 → 영원히 RAG/search 에서 사라짐. 거부 + 사용자가 잠시 후 재시도.
    """

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            detail=(
                "노트 임베딩이 아직 완료되지 않았습니다. 잠시 후 다시 시도해주세요."
            ),
        )
