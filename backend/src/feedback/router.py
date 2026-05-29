# 사용자 dogfooding 피드백 제출 엔드포인트 (user-level, 워크스페이스 비종속)
from fastapi import APIRouter, BackgroundTasks, Depends, Request

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.feedback.dependencies import get_feedback_service
from src.feedback.schemas import FeedbackCreate
from src.feedback.service import FeedbackService

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("", status_code=201)
async def submit_feedback(
    data: FeedbackCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
):
    """로그인 사용자의 피드백 제출. user_id 는 서버에서 강제, user_agent 는 헤더에서 추출."""
    user_agent = request.headers.get("user-agent")
    return await service.submit(
        user_id=user.id,
        body=data.body,
        rating=data.rating,
        is_anonymous=data.is_anonymous,
        workspace_id=data.workspace_id,
        page_url=data.page_url,
        user_agent=user_agent,
        display_name=user.display_name,
        background_tasks=background_tasks,
    )
