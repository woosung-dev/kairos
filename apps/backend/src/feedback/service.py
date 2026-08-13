# 피드백 제출 비즈니스 로직 — 저장 + Slack 알림(best-effort, BackgroundTask)
import uuid

from fastapi import BackgroundTasks

from src.common.notifications import send_slack_message
from src.feedback.models import FeedbackEntry
from src.feedback.repository import FeedbackRepository


class FeedbackService:
    def __init__(self, feedback_repo: FeedbackRepository) -> None:
        self.feedback_repo = feedback_repo

    async def submit(
        self,
        *,
        user_id: uuid.UUID,
        body: str,
        rating: int | None,
        is_anonymous: bool,
        workspace_id: uuid.UUID | None,
        page_url: str | None,
        user_agent: str | None,
        display_name: str,
        background_tasks: BackgroundTasks,
    ) -> dict:
        """피드백 1건 저장 후 Slack 알림을 백그라운드로 예약한다.

        Slack 전송은 best-effort (미설정 시 no-op) + BackgroundTask 라
        응답 지연 0. user_id 는 라우터에서 get_current_user 로 강제됨.
        """
        entry = FeedbackEntry(
            user_id=user_id,
            workspace_id=workspace_id,
            rating=rating,
            body=body,
            is_anonymous=is_anonymous,
            page_url=page_url,
            user_agent=user_agent,
        )
        await self.feedback_repo.save(entry)
        await self.feedback_repo.commit()

        background_tasks.add_task(
            send_slack_message, _format_slack_message(
                display_name=display_name,
                is_anonymous=is_anonymous,
                rating=rating,
                body=body,
                page_url=page_url,
            )
        )

        return {
            "id": str(entry.id),
            "status": "received",
            "createdAt": entry.created_at.isoformat(),
        }


def _format_slack_message(
    *,
    display_name: str,
    is_anonymous: bool,
    rating: int | None,
    body: str,
    page_url: str | None,
) -> str:
    who = "익명" if is_anonymous else display_name
    stars = f"{'★' * rating}{'☆' * (5 - rating)} " if rating else ""
    return (
        f":speech_balloon: *Kairos 피드백* ({who})\n"
        f"{stars}{body}\n"
        f"_page: {page_url or '-'}_"
    )
