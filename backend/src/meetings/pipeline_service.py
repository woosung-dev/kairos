# backend/src/meetings/pipeline_service.py
"""회의 처리 오케스트레이터. BackgroundTasks에서 실행.

도메인 간 직접 import 금지 원칙을 준수:
- 모든 Repository는 process_meeting / capture_text 실행 시 세션 팩토리로 직접 생성
- R2Service, TranscriptionService, AIProcessingService는 생성자 주입
- 헌법 I-9 (CONTEXT-MAP.md:208): pipeline 진입점 + 모든 내부 호출 workspace_id 필수 (Codex F-1 Critical)
"""
import logging
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.actions.models import ActionItem
from src.actions.repository import ActionItemRepository
from src.meetings.models import Meeting, TranscriptSegment
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

    async def _analyze_and_store(
        self,
        *,
        meeting: Meeting,
        workspace_id: uuid.UUID,
        transcript_text: str,
        auto_confirm_threshold: float,
        segments_data: list[dict],
        meeting_repo: MeetingRepository,
        project_repo: ProjectRepository,
        action_repo: ActionItemRepository,
        inbox_repo: InboxRepository,
        embedding_service: EmbeddingService,
    ) -> None:
        """요약 → 액션 추출 → Inbox 적재 → 자동 확정 → 임베딩 → 완료 공통 블록.

        헌법 I-9 (Codex F-1): meeting_repo 호출 시 workspace_id 동반 전달.
        """
        summary_data = await self.ai_service.summarize(transcript_text)
        await meeting_repo.save_summary(meeting.id, workspace_id, summary_data)
        await meeting_repo.set_has_summary(meeting.id, workspace_id, True)

        existing_projects = await project_repo.find_by_workspace(meeting.workspace_id)
        project_list = [
            {"id": str(p.id), "title": p.title, "status": p.status}
            for p in existing_projects
        ]
        actions_data = await self.ai_service.extract_actions_and_link(
            transcript_text, summary_data.get("summary", ""), project_list
        )

        # ActionItem 저장 (workspace_id 명시 — cross-domain orchestrator 안전)
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
                    logger.warning("dueDate 파싱 실패: %s (meeting=%s)", due_date_str, meeting.id)
            await action_repo.save(action_item)
            action_count += 1

        refreshed = await meeting_repo.find_by_id(meeting.id, workspace_id)
        if refreshed:
            refreshed.action_item_count = action_count
        logger.info("액션 아이템 %d개 추출 완료 (meeting=%s)", action_count, meeting.id)

        # InboxItem 생성 + 자동 확정
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
            is_processed=confidence >= auto_confirm_threshold,
        )
        await inbox_repo.save(inbox_item)

        if confidence >= auto_confirm_threshold and existing_project_id_str:
            # Sprint 19 PR #1 C9 (Codex F-1/F-3): workspace_id 명시 전달
            await project_repo.add_meeting_link(
                meeting.id,
                uuid.UUID(existing_project_id_str),
                meeting.workspace_id,
            )
            logger.info(
                "자동 확정: meeting=%s → project=%s (confidence=%.2f)",
                meeting.id, existing_project_id_str, confidence,
            )

        # 임베딩 (비치명적 — 실패해도 파이프라인은 완료)
        try:
            project_id = (
                uuid.UUID(existing_project_id_str)
                if (confidence >= auto_confirm_threshold and existing_project_id_str)
                else None
            )
            chunk_count = await embedding_service.embed_meeting(
                meeting_id=meeting.id,
                workspace_id=meeting.workspace_id,
                project_id=project_id,
                title=meeting.title,
                segments=segments_data,
            )
            await embedding_service.invalidate_cache(meeting.workspace_id, project_id)
            logger.info("임베딩 %d개 생성 (meeting=%s)", chunk_count, meeting.id)
        except Exception as emb_err:
            logger.warning("임베딩 생성 실패 (비치명적, meeting=%s): %s", meeting.id, emb_err)

        await meeting_repo.update_status(meeting.id, workspace_id, "completed")
        await meeting_repo.commit()

    async def process_meeting(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """회의 처리 전체 파이프라인. 실패 시 status: failed로 롤백.

        헌법 I-9 Critical (Codex F-1): 진입점 시그니처 workspace_id 필수.
        BackgroundTasks.add_task 시 router 에서 path workspace_id 동반 전달.
        """
        async with self._session_factory() as session:
            meeting_repo = MeetingRepository(session)
            project_repo = ProjectRepository(session)
            action_repo = ActionItemRepository(session)
            inbox_repo = InboxRepository(session)
            workspace_repo = WorkspaceRepository(session)
            embedding_service = EmbeddingService(EmbeddingRepository(session))

            try:
                meeting = await meeting_repo.find_by_id(meeting_id, workspace_id)
                if meeting is None:
                    return

                workspace = await workspace_repo.find_by_id(meeting.workspace_id)
                threshold = workspace.inbox_threshold if workspace else 0.9

                # [1] STT
                await meeting_repo.update_status(meeting_id, workspace_id, "transcribing")
                await meeting_repo.commit()

                audio_url = await self.r2_service.get_download_url(meeting.file_key)
                audio_bytes = await self.transcription_service.download_audio(audio_url)
                filename = meeting.file_key.split("/")[-1] if "/" in meeting.file_key else meeting.file_key
                segments, duration = await self.transcription_service.transcribe(audio_bytes, filename)

                await meeting_repo.save_segments(meeting_id, workspace_id, segments)
                await meeting_repo.set_has_transcript(meeting_id, workspace_id, True)

                meeting = await meeting_repo.find_by_id(meeting_id, workspace_id)
                if meeting:
                    meeting.duration_sec = int(duration)
                    await meeting_repo.commit()

                # [2] 분석
                await meeting_repo.update_status(meeting_id, workspace_id, "analyzing")
                await meeting_repo.commit()

                transcript_text = "\n".join(seg.text for seg in segments)
                segments_data = [
                    {"speaker": seg.speaker, "text": seg.text,
                     "start_sec": seg.start_sec, "end_sec": seg.end_sec}
                    for seg in segments
                ]
                await self._analyze_and_store(
                    meeting=meeting,
                    workspace_id=workspace_id,
                    transcript_text=transcript_text,
                    auto_confirm_threshold=threshold,
                    segments_data=segments_data,
                    meeting_repo=meeting_repo,
                    project_repo=project_repo,
                    action_repo=action_repo,
                    inbox_repo=inbox_repo,
                    embedding_service=embedding_service,
                )

            except Exception as e:
                logger.exception("파이프라인 실패 (meeting=%s): %s", meeting_id, e)
                try:
                    await session.rollback()
                    await meeting_repo.update_status(
                        meeting_id, workspace_id, "failed", error_message=str(e)
                    )
                    await meeting_repo.commit()
                except Exception as rollback_err:
                    logger.exception("상태 failed 업데이트 실패 (meeting=%s): %s", meeting_id, rollback_err)

    async def capture_text(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID, transcript_text: str
    ) -> None:
        """텍스트 캡처 파이프라인 — STT 건너뛰고 분석부터 시작.

        헌법 I-9 (Codex F-1): 진입점 시그니처 workspace_id 필수.
        """
        async with self._session_factory() as session:
            meeting_repo = MeetingRepository(session)
            project_repo = ProjectRepository(session)
            action_repo = ActionItemRepository(session)
            inbox_repo = InboxRepository(session)
            workspace_repo = WorkspaceRepository(session)
            embedding_service = EmbeddingService(EmbeddingRepository(session))

            try:
                meeting = await meeting_repo.find_by_id(meeting_id, workspace_id)
                if meeting is None:
                    return

                workspace = await workspace_repo.find_by_id(meeting.workspace_id)
                threshold = workspace.inbox_threshold if workspace else 0.9

                await meeting_repo.update_status(meeting_id, workspace_id, "analyzing")
                await meeting_repo.commit()

                segment = TranscriptSegment(
                    meeting_id=meeting_id, speaker="텍스트",
                    start_sec=0.0, end_sec=0.0, text=transcript_text,
                )
                await meeting_repo.save_segments(meeting_id, workspace_id, [segment])
                await meeting_repo.set_has_transcript(meeting_id, workspace_id, True)

                await self._analyze_and_store(
                    meeting=meeting,
                    workspace_id=workspace_id,
                    transcript_text=transcript_text,
                    auto_confirm_threshold=threshold,
                    segments_data=[{"speaker": "텍스트", "text": transcript_text,
                                    "start_sec": 0.0, "end_sec": 0.0}],
                    meeting_repo=meeting_repo,
                    project_repo=project_repo,
                    action_repo=action_repo,
                    inbox_repo=inbox_repo,
                    embedding_service=embedding_service,
                )

            except Exception as e:
                logger.exception("capture_text 파이프라인 실패 (meeting=%s): %s", meeting_id, e)
                try:
                    await session.rollback()
                    await meeting_repo.update_status(
                        meeting_id, workspace_id, "failed", error_message=str(e)
                    )
                    await meeting_repo.commit()
                except Exception as rollback_err:
                    logger.exception("상태 failed 업데이트 실패 (meeting=%s): %s", meeting_id, rollback_err)
