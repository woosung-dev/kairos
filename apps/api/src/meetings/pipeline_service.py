# apps/api/src/meetings/pipeline_service.py
"""회의 처리 오케스트레이터. BackgroundTasks에서 실행.

도메인 간 직접 import 금지 원칙을 준수:
- 모든 Repository는 process_meeting / capture_text 실행 시 세션 팩토리로 직접 생성
- R2Service, TranscriptionService, AIProcessingService는 생성자 주입
- 헌법 I-9 (CONTEXT-MAP.md:208): pipeline 진입점 + 모든 내부 호출 workspace_id 필수 (Codex F-1 Critical)
"""
import logging
import uuid
from datetime import date
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    # 런타임 import 는 _notify_meeting_finished 안에서 지연 (온보딩 훅과 같은 패턴)
    from src.push.schemas import PushKind

logger = logging.getLogger(__name__)

# C-023 (2026-09-26 정검): 실패 원문(str(e))에는 R2 endpoint·버킷·access key id·서명 URL 이
# 들어 있었고 viewer 이상에게 그대로 반환됐다. DB 에는 분류명 + 일반 문구만 남기고,
# 원문은 logger.exception 으로만 남긴다 (docker logs).
PIPELINE_FAILURE_MESSAGE = "회의 처리 중 오류가 발생했습니다. 다시 시도하거나 관리자에게 문의하세요."


def _public_error_message(error: Exception) -> str:
    """사용자에게 보여도 되는 실패 사유 — 예외 클래스명만 덧붙인다 (원문·URL 제외)."""
    return f"{PIPELINE_FAILURE_MESSAGE} ({type(error).__name__})"


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
        # T-AI-DATE (BUG-CURIOUS-001): current_year 컨텍스트 명시 전달.
        # 기본값은 service 가 date.today().year 사용하지만 호출처에서 명시해 audit 추적 가능.
        actions_data = await self.ai_service.extract_actions_and_link(
            transcript_text,
            summary_data.get("summary", ""),
            project_list,
            current_year=date.today().year,
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
        is_auto_confirmed = bool(
            confidence >= auto_confirm_threshold and existing_project_id_str
        )

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
            # C-002 (2026-09-26 정검): 자동 확정은 "기존 프로젝트에 연결" 할 때만이다.
            # 새 프로젝트 제안은 링크가 안 생기므로, 신뢰도가 높아도 처리됨으로 두면
            # 인박스에서 사라지고 회의는 미연결로 남는다 → 사람이 판단하도록 미처리 유지.
            is_processed=is_auto_confirmed,
        )
        await inbox_repo.save(inbox_item)

        if is_auto_confirmed:
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
                uuid.UUID(existing_project_id_str) if is_auto_confirmed else None
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

        # Sprint 22 OBN-02: AI distillation 완료 시 onboarding step=3.
        # meeting.created_by_id = 실제 회의 업로드한 user (workspace owner 와 다를 수 있음).
        # graceful: hook 실패 시도 pipeline 완료 흐름 보존.
        if meeting.created_by_id is not None:
            try:
                from src.onboarding.service import OnboardingService
                onboarding = OnboardingService(meeting_repo.session)
                await onboarding.increment_step(meeting.created_by_id, 3)
            except Exception as ob_err:
                logger.warning("onboarding step=3 advance 실패 (비치명적, meeting=%s): %s", meeting.id, ob_err)

        await meeting_repo.update_status(meeting.id, workspace_id, "completed")
        await meeting_repo.commit()

    async def process_meeting(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """회의 처리 전체 파이프라인. 실패 시 status: failed로 롤백.

        헌법 I-9 Critical (Codex F-1): 진입점 시그니처 workspace_id 필수.
        BackgroundTasks.add_task 시 router 에서 path workspace_id 동반 전달.
        """
        # 웹 푸시 결과 플래그 (pwa.md §5.3) — 최종 commit 이 성공했을 때만 채운다
        outcome: "PushKind | None" = None
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
                # Sprint 24 Wave 2 T-N+4 (BL-T2-003): 4hr+ chunk 분할 진입점.
                # 1hr 이하는 기존 transcribe 와 동일 동작, 1hr+ 면 chunked 경로로 분기.
                segments, duration = await self.transcription_service.transcribe_with_chunking(
                    audio_bytes, filename
                )

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
                if meeting is None:
                    logger.error("Meeting %s not found after transcription, skipping analyze", meeting_id)
                    return
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
                outcome = "meeting.completed"

            except Exception as e:
                logger.exception("파이프라인 실패 (meeting=%s): %s", meeting_id, e)
                try:
                    await session.rollback()
                    await meeting_repo.update_status(
                        meeting_id, workspace_id, "failed",
                        error_message=_public_error_message(e),
                    )
                    await meeting_repo.commit()
                    outcome = "meeting.failed"
                except Exception as rollback_err:
                    logger.exception("상태 failed 업데이트 실패 (meeting=%s): %s", meeting_id, rollback_err)

        # 파이프라인 세션 close 이후에만 발송한다 (안쪽에서 부르면 발송 내내 세션이 열려 있다)
        if outcome is not None:
            await self._notify_meeting_finished(meeting_id, workspace_id, outcome)

    async def capture_text(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID, transcript_text: str
    ) -> None:
        """텍스트 캡처 파이프라인 — STT 건너뛰고 분석부터 시작.

        헌법 I-9 (Codex F-1): 진입점 시그니처 workspace_id 필수.
        """
        # 웹 푸시 결과 플래그 (pwa.md §5.3) — 최종 commit 이 성공했을 때만 채운다
        outcome: "PushKind | None" = None
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
                outcome = "meeting.completed"

            except Exception as e:
                logger.exception("capture_text 파이프라인 실패 (meeting=%s): %s", meeting_id, e)
                try:
                    await session.rollback()
                    await meeting_repo.update_status(
                        meeting_id, workspace_id, "failed",
                        error_message=_public_error_message(e),
                    )
                    await meeting_repo.commit()
                    outcome = "meeting.failed"
                except Exception as rollback_err:
                    logger.exception("상태 failed 업데이트 실패 (meeting=%s): %s", meeting_id, rollback_err)

        # 파이프라인 세션 close 이후에만 발송한다 (안쪽에서 부르면 발송 내내 세션이 열려 있다)
        if outcome is not None:
            await self._notify_meeting_finished(meeting_id, workspace_id, outcome)

    async def _notify_meeting_finished(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        kind: "PushKind",
    ) -> None:
        """회의 완료·실패를 업로더 본인에게 웹 푸시 (REQ-008, pwa.md §5.3) — best-effort.

        인자는 원시 값만 받는다 (rollback 뒤 만료된 ORM 객체를 건드리지 않는다).
        순서: 조회 세션 → 닫기 → 발송(열린 DB 세션 0개) → 404/410 이 있으면 정리용 새 세션.
        느린 푸시 서비스가 커넥션 풀을 붙잡지 않게 발송 구간에는 세션을 열지 않는다.
        어떤 실패도 회의 상태·파이프라인 흐름에 영향을 주지 않는다 (예외 타입명만 warning).
        """
        try:
            from src.push.repository import PushRepository
            from src.push.service import create_push_dispatcher

            dispatcher = create_push_dispatcher()
            if dispatcher is None:
                logger.info("push_dispatch_skipped reason=not_configured meeting=%s", meeting_id)
                return

            # 1. 조회 — 짧은 세션. 구독은 원시 값으로 복사해 세션 밖으로 가져간다
            async with self._session_factory() as session:
                meeting = await MeetingRepository(session).find_by_id(meeting_id, workspace_id)
                if meeting is None:
                    return
                recipient_id = meeting.created_by_id
                meeting_workspace_id = meeting.workspace_id
                member = await WorkspaceRepository(session).find_member(
                    meeting_workspace_id, recipient_id
                )
                if member is None:
                    logger.info(
                        "push_dispatch_skipped reason=not_member meeting=%s user=%s",
                        meeting_id, recipient_id,
                    )
                    return
                targets = await PushRepository(session).list_by_user(recipient_id)

            # 2. 조회 세션 반납 완료 — 이 아래 발송 구간에는 열린 세션이 없다
            if not targets:
                return

            # 3. 발송
            report = await dispatcher.dispatch_meeting_finished(
                targets,
                kind=kind,
                meeting_id=meeting_id,
                workspace_id=meeting_workspace_id,
            )

            # 4. 정리 — 404·410 이 있을 때만 새 짧은 세션 (회의 commit 과 별개 트랜잭션)
            pruned = 0
            if report.gone_ids:
                async with self._session_factory() as session:
                    push_repo = PushRepository(session)
                    pruned = await push_repo.delete_by_ids(report.gone_ids, recipient_id)
                    await push_repo.commit()

            logger.info(
                "push_dispatch_done meeting=%s user=%s sent=%d failed=%d pruned=%d",
                meeting_id, recipient_id, report.sent, report.failed, pruned,
            )
        except Exception as push_err:
            logger.warning(
                "push_dispatch_failed meeting=%s error=%s", meeting_id, type(push_err).__name__
            )
