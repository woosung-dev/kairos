# 웹 푸시 도메인 예외 (B-12)
"""HTTP 로 매핑되는 도메인 예외는 없다 — API-003 은 없음·타인 것도 204(멱등), 입력 오류는 Pydantic 422.

발송 쪽 예외는 파이프라인 훅(`meetings/pipeline_service._notify_meeting_finished`)이
전부 삼킨다 (best-effort, pwa.md §5.3).
"""


class PushPayloadTooLargeError(Exception):
    """직렬화한 페이로드가 상한(512B, pwa.md §5.4)을 넘음 — 페이로드에 필드를 더한 회귀를 막는다."""

    def __init__(self, size: int, limit: int) -> None:
        self.size = size
        self.limit = limit
        super().__init__(f"push payload is {size} bytes (limit {limit})")
