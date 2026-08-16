# apps/api/src/meetings/exceptions.py
"""Meeting 도메인 예외."""
from fastapi import HTTPException

from src.common.exceptions import NotFoundError


class MeetingNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("회의")


# ── Sprint 23 D4 Task 2 Step 2.2: promote 검증 예외 (memory 패턴 정렬) ──


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


class MeetingPromoteNonTerminalError(HTTPException):
    """Sprint 23 Codex 4차 P2 fix: terminal (completed/failed) 상태가 아닌 meeting promote 시도.

    사유: uploading / transcribing / analyzing 같은 transient status 의 meeting 을 promote 하면
    target ws 의 새 meeting 이 영원히 stuck (pipeline 미실행, 동기화 없음). 거부 + 사용자 안내.
    """

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            detail="진행 중인 회의는 promote 할 수 없습니다 (완료 또는 실패 상태만 가능)",
        )


class MeetingPromoteNotEmbeddedError(HTTPException):
    """Sprint 23 Codex 8차 P2 fix: 임베딩 미완료 meeting promote 시도.

    사유: status='completed' 인 meeting 이지만 embedding step 실패로 chunk 0 → BG task 가
    audit 'n/a' silent success 반환 → target meeting 영원히 RAG/search 에서 사라짐. notes 의
    NotePromoteNotEmbeddedError 와 동일 패턴 (Codex 6차 P2). 거부 + 사용자 안내.
    """

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            detail=(
                "회의 임베딩이 아직 완료되지 않았습니다. 잠시 후 다시 시도해주세요."
            ),
        )
