# backend/src/meetings/service.py
"""Meeting 서비스 — AsyncSession import 금지. 단일 도메인 CRUD만."""
import uuid

from src.meetings.exceptions import MeetingNotFoundError
from src.meetings.models import Meeting
from src.meetings.repository import MeetingRepository


class MeetingService:
    def __init__(self, repo: MeetingRepository) -> None:
        self.repo = repo

    async def create_meeting(
        self,
        workspace_id: uuid.UUID,
        title: str,
        file_key: str,
        created_by_id: uuid.UUID,
        recorded_at=None,
    ) -> dict:
        """회의 레코드 생성 (status: uploading). 파이프라인은 router에서 BackgroundTasks로."""
        meeting = Meeting(
            workspace_id=workspace_id,
            title=title,
            file_key=file_key,
            created_by_id=created_by_id,
            recorded_at=recorded_at,
            status="uploading",
        )
        meeting = await self.repo.save(meeting)
        await self.repo.commit()

        return {
            "id": str(meeting.id),
            "status": meeting.status,
            "message": "파이프라인이 시작되었습니다",
        }

    async def list_meetings(
        self,
        workspace_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """워크스페이스 회의 목록 (페이지네이션)."""
        offset = (page - 1) * page_size
        meetings = await self.repo.find_by_workspace(workspace_id, offset, page_size)
        total = await self.repo.count_by_workspace(workspace_id)

        return {
            "items": [self._to_list_item(m) for m in meetings],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "hasNext": page * page_size < total,
        }

    async def get_meeting_detail(
        self, meeting_id: uuid.UUID
    ) -> dict:
        """회의 상세 (요약 + 트랜스크립트 포함)."""
        meeting = await self.repo.find_by_id(meeting_id)
        if meeting is None:
            raise MeetingNotFoundError()

        segments = await self.repo.get_segments(meeting_id)
        summary = await self.repo.get_summary(meeting_id)

        result = self._to_list_item(meeting)
        result["transcript"] = [
            {
                "speaker": seg.speaker,
                "startSec": seg.start_sec,
                "endSec": seg.end_sec,
                "text": seg.text,
            }
            for seg in segments
        ]
        result["summary"] = (
            {
                "summary": summary.summary,
                "keyDecisions": summary.key_decisions,
                "topics": summary.topics,
            }
            if summary
            else None
        )
        # Sprint 1: 프로젝트 연결 없음
        result["projects"] = []
        return result

    async def get_meeting_status(self, meeting_id: uuid.UUID) -> dict:
        """회의 처리 상태."""
        meeting = await self.repo.find_by_id(meeting_id)
        if meeting is None:
            raise MeetingNotFoundError()
        return {
            "status": meeting.status,
            "errorMessage": meeting.error_message,
        }

    @staticmethod
    def _to_list_item(meeting: Meeting) -> dict:
        return {
            "id": str(meeting.id),
            "workspaceId": str(meeting.workspace_id),
            "title": meeting.title,
            "recordedAt": meeting.recorded_at.isoformat() if meeting.recorded_at else None,
            "durationSec": meeting.duration_sec,
            "status": meeting.status,
            "hasTranscript": meeting.has_transcript,
            "hasSummary": meeting.has_summary,
            "actionItemCount": meeting.action_item_count,
            "createdAt": meeting.created_at.isoformat(),
            "updatedAt": meeting.updated_at.isoformat(),
        }
