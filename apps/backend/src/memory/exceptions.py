# Memory 도메인 예외 정의
"""Memory 도메인 HTTPException 집합."""
from fastapi import HTTPException


class AudioTooLargeError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=413,
            detail="오디오 파일이 너무 큽니다 (최대 25MB)",
        )


class EmptyMemoryError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=422,
            detail="텍스트 또는 오디오 중 하나는 필요합니다",
        )


class BothInputsProvidedError(HTTPException):
    """text와 audio 양쪽 동시 입력 — 한 가지만 허용 (silent drop 차단)."""

    def __init__(self):
        super().__init__(
            status_code=422,
            detail="text와 audio 중 하나만 보낼 수 있습니다",
        )


class TextTooLongError(HTTPException):
    """text 입력이 max_length 초과 — Gemini cost 폭주 차단."""

    def __init__(self, max_length: int):
        super().__init__(
            status_code=422,
            detail=f"text 길이는 {max_length}자 이하여야 합니다",
        )


class MemoryNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="메모를 찾을 수 없습니다")


class WorkspaceMembershipError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=403,
            detail="해당 워크스페이스 멤버가 아닙니다",
        )


class TargetWorkspaceInvalidError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=422,
            detail="대상 워크스페이스가 유효하지 않습니다",
        )


class CannotPromoteToPersonalError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=422,
            detail="개인 워크스페이스로는 promote 할 수 없습니다",
        )


class CannotPromoteToSameWorkspaceError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=422,
            detail="같은 워크스페이스로는 promote 할 수 없습니다",
        )
