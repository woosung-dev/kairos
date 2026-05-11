# backend/src/meetings/pipeline_service.py
"""회의 처리 오케스트레이터. BackgroundTasks에서 실행.

도메인 간 직접 import 금지 원칙을 준수:
- 모든 Repository는 process_meeting / capture_text 실행 시 세션 팩토리로 직접 생성
- R2Service, TranscriptionService, AIProcessingService는 생성자 주입
"""
import logging
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.actions.models import ActionItem
from src.actions.repository import ActionItemRepository
from src.meetings.models import TranscriptSegment
from src.common.r2 import R2Service
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.inbox.models import InboxItem
from src.inbox.repository import InboxRepository
from src.meetings.repository import MeetingRepository
from src.projects.repository import ProjectRepository
from src.workspaces.repository import WorkspaceRepository
from src.services.ai_processing import AIProcessingService
from src.services.transcription import TranscriptionService

logger = logging.getLogger(__name__)


class MeetingPipelineService:
    """STT → 요약 → 액션 추출 → Inbox 적재 → 자동 확정 → 임베딩 파이프라인."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        r2_service: R2Service,
        transcription_service: TranscriptionService,
        ai_service: AIProcessingService,
    ) -> None:
        self._session_factory = session_factory
        self.r2_service = r2_service
        self.transcription_service = transcription_service
        self.ai_service = ai_service

    async def process_meeting(self, meeting_id: uuid.UUID) -> None:
        """회의 처리 전체 파이프라인. 실패 시 status: failed로 롤백."""
        async with self._session_factory() as session:
            meeting_repo = MeetingRepository(session)
            project_repo = ProjectRepository(session)
            action_repo = ActionItemRepository(session)
            inbox_repo = InboxRepository(session)
            workspace_repo = WorkspaceRepository(session)
            embedding_service = EmbeddingService(EmbeddingRepository(session))

            try:
                meeting = await meeting_repo.find_by_id(meeting_id)
                if meeting is None:
                    return

                # workspace에서 임계값 조회
                workspace = await workspace_repo.find_by_id(meeting.workspace_id)
                threshold = workspace.inbox_threshold if workspace else 0.9

                # [1] STT
                await meeting_repo.update_status(meeting_id, "transcribing")
                await meeting_repo.commit()

                audio_url = await self.r2_service.get_download_url(meeting.file_key)
                audio_bytes = await self.transcription_service.download_audio(audio_url)
                # file_key에서 파일명 추출 (예: "uploads/uuid/meeting.m4a" → "meeting.m4a")
                filename = meeting.file_key.split("/")[-1] if "/" in meeting.file_key else meeting.file_key
                segments, duration = await self.transcription_service.transcribe(audio_bytes, filename)

                await meeting_repo.save_segments(meeting_id, segments)
                await meeting_repo.set_has_transcript(meeting_id, True)

                # duration 업데이트
                meeting = await meeting_repo.find_by_id(meeting_id)
                if meeting:
                    meeting.duration_sec = int(duration)
                    await meeting_repo.commit()

                # [2] 분석 (요약 + 액션 추출 + Inbox 적재 + 자동 확정)
                await meeting_repo.update_status(meeting_id, "analyzing")
                await meeting_repo.commit()

                transcript_text = "\n".join(seg.text for seg in segments)

                # [2-1] 요약
                summary_data = await self.ai_service.summarize(transcript_text)
                await meeting_repo.save_summary(meeting_id, summary_data)
                await meeting_repo.set_has_summary(meeting_id, True)

                # [2-2] 액션 추출 + 프로젝트 연결
                existing_projects = await project_repo.find_by_workspace(
                    meeting.workspace_id
                )
                project_list = [
                    {"id": str(p.id), "title": p.title, "status": p.status}
                    for p in existing_projects
                ]

                actions_data = await self.ai_service.extract_actions_and_link(
                    transcript_text, summary_data.get("summary", ""), project_list
                )

                # [2-3] ActionItem DB 저장
                action_count = 0
                for ai_action in actions_data.get("actionItems", []):
                    action_item = ActionItem(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        title=ai_action["title"],
                        description=ai_action.get("description"),
                        priority=ai_action.get("priority", "medium"),
                    )
                    # dueDate 파싱
                    due_date_str = ai_action.get("dueDate")
                    if due_date_str:
                        try:
                            action_item.due_date = date.fromisoformat(due_date_str)
                        except ValueError:
                            logger.warning(
                                "dueDate 파싱 실패: %s (meeting=%s)", due_date_str, meeting_id
                            )
                    await action_repo.save(action_item)
                    action_count += 1

                # action_item_count 업데이트
                meeting = await meeting_repo.find_by_id(meeting_id)
                if meeting:
                    meeting.action_item_count = action_count

                logger.info(
                    "액션 아이템 %d개 추출 완료 (meeting=%s)", action_count, meeting_id
                )

                # [2-4] InboxItem 생성
                suggested = actions_data.get("suggestedProject", {})
                confidence = suggested.get("confidence", 0.0)
                existing_project_id_str = suggested.get("existingProjectId")

                inbox_item = InboxItem(
                    workspace_id=meeting.workspace_id,
                    title=f"{meeting.title} 요약",
                    summary=summary_data.get("summary", ""),
                    source_type="meeting",
                    source_id=meeting.id,
                    ai_suggested_project_id=(
                        uuid.UUID(existing_project_id_str)
                        if existing_project_id_str
                        else None
                    ),
                    ai_suggested_project_title=suggested.get("newProjectTitle"),
                    ai_suggested_tags=actions_data.get("suggestedTags", []),
                    ai_confidence=confidence,
                    is_processed=confidence >= threshold,
                )
                await inbox_repo.save(inbox_item)

                # [2-5] 자동 확정: confidence >= threshold이고 기존 프로젝트가 있으면 MeetingProjectLink 생성
                if confidence >= threshold and existing_project_id_str:
                    await project_repo.add_meeting_link(
                        meeting.id, uuid.UUID(existing_project_id_str)
                    )
                    logger.info(
                        "자동 확정: meeting=%s → project=%s (confidence=%.2f)",
                        meeting_id,
                        existing_project_id_str,
                        confidence,
                    )

                # [2-6] 임베딩 생성 (비치명적 — 실패해도 파이프라인은 완료)
                try:
                    project_id = None
                    if confidence >= threshold and existing_project_id_str:
                        project_id = uuid.UUID(existing_project_id_str)

                    segments_data = [
                        {
                            "speaker": seg.speaker,
                            "text": seg.text,
                            "start_sec": seg.start_sec,
                            "end_sec": seg.end_sec,
                        }
                        for seg in segments
                    ]
                    chunk_count = await embedding_service.embed_meeting(
                        meeting_id=meeting.id,
                        workspace_id=meeting.workspace_id,
                        project_id=project_id,
                        title=meeting.title,
                        segments=segments_data,
                    )
                    await embedding_service.invalidate_cache(
                        meeting.workspace_id, project_id
                    )
                    logger.info(
                        "임베딩 %d개 생성 (meeting=%s)", chunk_count, meeting_id
                    )
                except Exception as emb_err:
                    logger.warning(
                        "임베딩 생성 실패 (비치명적, meeting=%s): %s",
                        meeting_id,
                        emb_err,
                    )

                # [3] 완료
                await meeting_repo.update_status(meeting_id, "completed")
                await meeting_repo.commit()

            except Exception as e:
                logger.exception("파이프라인 실패 (meeting=%s): %s", meeting_id, e)
                try:
                    await session.rollback()
                    await meeting_repo.update_status(
                        meeting_id, "failed", error_message=str(e)
                    )
                    await meeting_repo.commit()
                except Exception as rollback_err:
                    logger.exception(
                        "상태 failed 업데이트 실패 (meeting=%s): %s", meeting_id, rollback_err
                    )

    async def capture_text(self, meeting_id: uuid.UUID, transcript_text: str) -> None:
        """텍스트 캡처 파이프라인 — STT 건너뛰고 분석부터 시작."""
        async with self._session_factory() as session:
            meeting_repo = MeetingRepository(session)
            project_repo = ProjectRepository(session)
            action_repo = ActionItemRepository(session)
            inbox_repo = InboxRepository(session)
            workspace_repo = WorkspaceRepository(session)
            embedding_service = EmbeddingService(EmbeddingRepository(session))

            try:
                meeting = await meeting_repo.find_by_id(meeting_id)
                if meeting is None:
                    return

                workspace = await workspace_repo.find_by_id(meeting.workspace_id)
                threshold = workspace.inbox_threshold if workspace else 0.9

                await meeting_repo.update_status(meeting_id, "analyzing")
                await meeting_repo.commit()

                # 트랜스크립트 세그먼트 1개로 저장
                segment = TranscriptSegment(
                    meeting_id=meeting_id,
                    speaker="텍스트",
                    start_sec=0.0,
                    end_sec=0.0,
                    text=transcript_text,
                )
                await meeting_repo.save_segments(meeting_id, [segment])
                await meeting_repo.set_has_transcript(meeting_id, True)

                # 요약
                summary_data = await self.ai_service.summarize(transcript_text)
                await meeting_repo.save_summary(meeting_id, summary_data)
                await meeting_repo.set_has_summary(meeting_id, True)

                # 액션 추출 + 프로젝트 연결
                existing_projects = await project_repo.find_by_workspace(meeting.workspace_id)
                project_list = [
                    {"id": str(p.id), "title": p.title, "status": p.status}
                    for p in existing_projects
                ]
                actions_data = await self.ai_service.extract_actions_and_link(
                    transcript_text, summary_data.get("summary", ""), project_list
                )

                action_count = 0
                for ai_action in actions_data.get("actionItems", []):
                    action_item = ActionItem(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        title=ai_action["title"],
                        description=ai_action.get("description"),
                        priority=ai_action.get("priority", "medium"),
                    )
                    due_date_str = ai_action.get("dueDate")
                    if due_date_str:
                        try:
                            action_item.due_date = date.fromisoformat(due_date_str)
                        except ValueError:
                            pass
                    await action_repo.save(action_item)
                    action_count += 1

                meeting = await meeting_repo.find_by_id(meeting_id)
                if meeting:
                    meeting.action_item_count = action_count

                # InboxItem 생성
                suggested = actions_data.get("suggestedProject", {})
                confidence = suggested.get("confidence", 0.0)
                existing_project_id_str = suggested.get("existingProjectId")

                inbox_item = InboxItem(
                    workspace_id=meeting.workspace_id,
                    title=f"{meeting.title} 요약",
                    summary=summary_data.get("summary", ""),
                    source_type="meeting",
                    source_id=meeting.id,
                    ai_suggested_project_id=(
                        uuid.UUID(existing_project_id_str) if existing_project_id_str else None
                    ),
                    ai_suggested_project_title=suggested.get("newProjectTitle"),
                    ai_suggested_tags=actions_data.get("suggestedTags", []),
                    ai_confidence=confidence,
                    is_processed=confidence >= threshold,
                )
                await inbox_repo.save(inbox_item)

                if confidence >= threshold and existing_project_id_str:
                    await project_repo.add_meeting_link(
                        meeting.id, uuid.UUID(existing_project_id_str)
                    )

                # 임베딩 (비치명적)
                try:
                    project_id = (
                        uuid.UUID(existing_project_id_str)
                        if (confidence >= threshold and existing_project_id_str)
                        else None
                    )
                    await embedding_service.embed_meeting(
                        meeting_id=meeting.id,
                        workspace_id=meeting.workspace_id,
                        project_id=project_id,
                        title=meeting.title,
                        segments=[{
                            "speaker": "텍스트",
                            "text": transcript_text,
                            "start_sec": 0.0,
                            "end_sec": 0.0,
                        }],
                    )
                    await embedding_service.invalidate_cache(meeting.workspace_id, project_id)
                except Exception as emb_err:
                    logger.warning(
                        "임베딩 생성 실패 (비치명적, meeting=%s): %s", meeting_id, emb_err
                    )

                await meeting_repo.update_status(meeting_id, "completed")
                await meeting_repo.commit()

            except Exception as e:
                logger.exception("capture_text 파이프라인 실패 (meeting=%s): %s", meeting_id, e)
                try:
                    await session.rollback()
                    await meeting_repo.update_status(
                        meeting_id, "failed", error_message=str(e)
                    )
                    await meeting_repo.commit()
                except Exception as rollback_err:
                    logger.exception(
                        "상태 failed 업데이트 실패 (meeting=%s): %s", meeting_id, rollback_err
                    )
