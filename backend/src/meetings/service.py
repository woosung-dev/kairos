# backend/src/meetings/service.py
"""Meeting 서비스 — AsyncSession import 금지. 단일 도메인 CRUD만."""
import json
import uuid

from src.actions.repository import ActionItemRepository
from src.meetings.exceptions import MeetingNotFoundError
from src.meetings.models import Meeting
from src.meetings.repository import MeetingRepository


class MeetingService:
    def __init__(self, repo: MeetingRepository, action_repo: ActionItemRepository | None = None) -> None:
        self.repo = repo
        self.action_repo = action_repo

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
        project_id: uuid.UUID | None = None,
    ) -> dict:
        """워크스페이스 회의 목록 (페이지네이션, project_id 필터 옵션)."""
        offset = (page - 1) * page_size
        meetings = await self.repo.find_by_workspace(
            workspace_id, offset, page_size, project_id
        )
        total = await self.repo.count_by_workspace(workspace_id, project_id)

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

    async def export_meeting(self, meeting_id: uuid.UUID, fmt: str) -> tuple[str, str, str]:
        """회의 내보내기. (content, filename, media_type) 반환."""
        meeting = await self.repo.find_by_id(meeting_id)
        if meeting is None:
            raise MeetingNotFoundError()

        segments = await self.repo.get_segments(meeting_id)
        summary = await self.repo.get_summary(meeting_id)

        # 액션 아이템 조회
        actions = []
        if self.action_repo:
            actions = await self.action_repo.find_by_meeting(meeting_id)

        if fmt == "md":
            content = self._to_markdown(meeting, summary, segments, actions)
            return content, f"{meeting.title}.md", "text/markdown; charset=utf-8"
        else:
            detail = await self.get_meeting_detail(meeting_id)
            detail["actionItems"] = [
                {
                    "title": a.title,
                    "description": a.description,
                    "status": a.status,
                    "priority": a.priority,
                    "dueDate": a.due_date.isoformat() if a.due_date else None,
                }
                for a in actions
            ]
            content = json.dumps(detail, ensure_ascii=False, indent=2)
            return content, f"{meeting.title}.json", "application/json; charset=utf-8"

    @staticmethod
    def _to_markdown(meeting, summary, segments, actions=None) -> str:
        lines = [f"# {meeting.title}"]
        if meeting.recorded_at:
            lines.append(f"> {meeting.recorded_at.strftime('%Y-%m-%d')}")
        lines.append("")

        if summary:
            lines.append("## 요약")
            lines.append(summary.summary)
            lines.append("")
            if summary.key_decisions:
                lines.append("## 핵심 결정사항")
                for d in summary.key_decisions:
                    lines.append(f"- {d}")
                lines.append("")

        if actions:
            lines.append("## 액션 아이템")
            for a in actions:
                checkbox = "[x]" if a.status == "done" else "[ ]"
                line = f"- {checkbox} {a.title}"
                if a.due_date:
                    line += f" (기한: {a.due_date.isoformat()})"
                lines.append(line)
            lines.append("")

        if segments:
            lines.append("## 트랜스크립트")
            for seg in segments:
                mins = int(seg.start_sec // 60)
                secs = int(seg.start_sec % 60)
                lines.append(f"**{seg.speaker}** ({mins:02d}:{secs:02d}): {seg.text}")
            lines.append("")

        return "\n".join(lines)

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
