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


class MemoryNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="메모를 찾을 수 없습니다")


class WorkspaceMembershipError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=403,
            detail="해당 워크스페이스 멤버가 아닙니다",
        )
