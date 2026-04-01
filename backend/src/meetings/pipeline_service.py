# backend/src/meetings/pipeline_service.py
"""회의 처리 오케스트레이터. BackgroundTasks에서 실행.

도메인 간 직접 import 금지 원칙을 준수:
- MeetingRepository (meetings 도메인)
- TranscriptionService (services/)
- AIProcessingService (services/)
- R2Service (common/)
모두 dependencies.py에서 주입받는다.
"""
import uuid

from src.common.r2 import R2Service
from src.meetings.repository import MeetingRepository
from src.services.ai_processing import AIProcessingService
from src.services.transcription import TranscriptionService


class MeetingPipelineService:
    """STT → 요약 → 완료 파이프라인."""

    def __init__(
        self,
        meeting_repo: MeetingRepository,
        r2_service: R2Service,
        transcription_service: TranscriptionService,
        ai_service: AIProcessingService,
    ) -> None:
        self.meeting_repo = meeting_repo
        self.r2_service = r2_service
        self.transcription_service = transcription_service
        self.ai_service = ai_service

    async def process_meeting(self, meeting_id: uuid.UUID) -> None:
        """회의 처리 전체 파이프라인. 실패 시 status: failed로 롤백."""
        try:
            meeting = await self.meeting_repo.find_by_id(meeting_id)
            if meeting is None:
                return

            # [1] STT
            await self.meeting_repo.update_status(meeting_id, "transcribing")
            await self.meeting_repo.commit()

            audio_url = await self.r2_service.get_download_url(meeting.file_key)
            audio_bytes = await self.transcription_service.download_audio(audio_url)
            # file_key에서 파일명 추출 (예: "uploads/uuid/meeting.m4a" → "meeting.m4a")
            filename = meeting.file_key.split("/")[-1] if "/" in meeting.file_key else meeting.file_key
            segments, duration = await self.transcription_service.transcribe(audio_bytes, filename)

            await self.meeting_repo.save_segments(meeting_id, segments)
            await self.meeting_repo.set_has_transcript(meeting_id, True)

            # duration 업데이트
            meeting = await self.meeting_repo.find_by_id(meeting_id)
            if meeting:
                meeting.duration_sec = int(duration)
                await self.meeting_repo.commit()

            # [2] 요약
            await self.meeting_repo.update_status(meeting_id, "summarizing")
            await self.meeting_repo.commit()

            transcript_text = "\n".join(seg.text for seg in segments)
            summary_data = await self.ai_service.summarize(transcript_text)
            await self.meeting_repo.save_summary(meeting_id, summary_data)
            await self.meeting_repo.set_has_summary(meeting_id, True)

            # [3] 완료
            await self.meeting_repo.update_status(meeting_id, "completed")
            await self.meeting_repo.commit()

        except Exception as e:
            await self.meeting_repo.update_status(
                meeting_id, "failed", error_message=str(e)
            )
            await self.meeting_repo.commit()
