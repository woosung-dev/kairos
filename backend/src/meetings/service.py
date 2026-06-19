# backend/src/meetings/service.py
"""Meeting 서비스 — AsyncSession import 금지. 단일 도메인 CRUD만.

Sprint 23 D4 Task 2 Step 2.2: cross-workspace promote 추가 (4 도메인 중 meeting).
- I-18 (복제 + tombstone): 원본 보존 + target ws Meeting/Summary/Segments 복제 + ItemPromotionAudit.
- workspace_repo / session_factory 옵션 주입 — promote 호출 시 필수 (없으면 RuntimeError).
"""
import json
import logging
import uuid

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.actions.repository import ActionItemRepository
from src.common.promote_helpers import (
    PromoteValidationError,
    build_item_promotion_audit,
    clone_action_items_for_promote,
    validate_promote_target,
)
from src.embeddings.models import EmbeddingChunk
from src.meetings.exceptions import (
    CannotPromoteToPersonalError,
    CannotPromoteToSameWorkspaceError,
    MeetingNotFoundError,
    MeetingPromoteNonTerminalError,
    MeetingPromoteNotEmbeddedError,
    TargetWorkspaceInvalidError,
)
from src.meetings.models import Meeting, MeetingSummary, TranscriptSegment
from src.meetings.repository import MeetingRepository
from src.meetings.schemas import MeetingPromoteOut
from src.projects.repository import ProjectRepository
from src.workspaces.repository import WorkspaceRepository

logger = logging.getLogger(__name__)


class MeetingService:
    def __init__(
        self,
        repo: MeetingRepository,
        action_repo: ActionItemRepository | None = None,
        project_repo: ProjectRepository | None = None,
        workspace_repo: WorkspaceRepository | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.repo = repo
        self.action_repo = action_repo
        self.project_repo = project_repo
        # Sprint 23 D4 (Task 2 Step 2.2): promote 흐름 필수 의존성.
        # 일반 CRUD 흐름은 None 허용 — promote 호출 시점에 fail-closed 검증.
        self.workspace_repo = workspace_repo
        self._session_factory = session_factory

    async def create_meeting(
        self,
        workspace_id: uuid.UUID,
        title: str,
        file_key: str,
        created_by_id: uuid.UUID,
        recorded_at=None,
        source: str | None = None,
    ) -> dict:
        """회의 레코드 생성 (status: uploading). 파이프라인은 router에서 BackgroundTasks로."""
        meeting = Meeting(
            workspace_id=workspace_id,
            title=title,
            file_key=file_key,
            created_by_id=created_by_id,
            recorded_at=recorded_at,
            status="uploading",
            source=source,
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
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> dict:
        """워크스페이스 회의 목록 (페이지네이션, project_id 필터 옵션).

        CAND-A completeness: requester visibility 게이트 — private-linked 회의의
        metadata/존재성이 비-ProjectMember 에게 노출되지 않도록 제외.
        requester_role 미전달(None) = 내부/파이프라인 호출 → 게이트 skip (하위호환).
        """
        offset = (page - 1) * page_size
        meetings = await self.repo.find_by_workspace(
            workspace_id,
            offset,
            page_size,
            project_id,
            requester_user_id=requester_user_id,
            requester_role=requester_role,
        )
        total = await self.repo.count_by_workspace(
            workspace_id,
            project_id,
            requester_user_id=requester_user_id,
            requester_role=requester_role,
        )

        return {
            "items": [self._to_list_item(m) for m in meetings],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "hasNext": page * page_size < total,
        }

    async def _verify_meeting_visibility(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID | None,
        requester_role: str | None,
    ) -> None:
        """CAND-A: 회의에 연결된 project visibility 게이트 (get_project 정합).

        require_viewer 만으론 private/draft project 에 연결된 회의의 트랜스크립트/요약/
        export 가 비-ProjectMember 에게 노출된다 (visibility-residue IDOR).

        회의는 MeetingProjectLink 로 N개 project 와 연결될 수 있다. 규칙:
        - admin/owner: 우회
        - project 링크 0개: 워크스페이스 멤버 누구나 OK (프로젝트 미연결 = 미제한)
        - 링크된 project 중 접근 가능한 것이 1개라도 있으면 OK
        - 링크된 project 가 전부 접근 불가(private 비-멤버 / draft 비-작성자)면 404

        requester_role 미전달(None) = 내부/특권 호출 → 게이트 skip (하위호환).
        """
        if requester_role is None:
            return
        if requester_role in ("admin", "owner"):
            return
        if self.project_repo is None:
            raise RuntimeError("project_repo 필수 (CAND-A visibility 검증)")
        linked = await self.project_repo.find_projects_by_meeting(
            meeting_id, workspace_id
        )
        if not linked:
            # 프로젝트 미연결 = 워크스페이스 레벨 (미제한)
            return
        for project in linked:
            if project.visibility == "public":
                return
            if project.visibility == "draft":
                if project.created_by_id == requester_user_id:
                    return
            elif project.visibility == "private":
                if requester_user_id is not None and await self.project_repo.is_member(
                    project.id, requester_user_id, workspace_id
                ):
                    return
        # 접근 가능한 연결 project 없음 → fail-closed 404
        raise MeetingNotFoundError()

    async def get_meeting_detail(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> dict:
        """회의 상세 (요약 + 트랜스크립트 포함). 헌법 I-9 workspace_id 필수 (Codex F-1).

        CAND-A: 연결된 project visibility 게이트 (비-ProjectMember 누출 차단).
        """
        meeting = await self.repo.find_by_id(meeting_id, workspace_id)
        if meeting is None:
            raise MeetingNotFoundError()
        await self._verify_meeting_visibility(
            meeting_id, workspace_id, requester_user_id, requester_role
        )

        segments = await self.repo.get_segments(meeting_id, workspace_id)
        summary = await self.repo.get_summary(meeting_id, workspace_id)

        result = self._to_list_item(meeting)
        # S28b BUG-MEETING-FAILED-UI: 실패 사유를 상세 응답에 노출 (이전엔 status
        # 엔드포인트에만 errorMessage 가 있어 detail 뷰가 실패 원인을 못 보여줬다).
        result["errorMessage"] = meeting.error_message
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
        # Sprint 14 T-8: 연결된 프로젝트 (MeetingProjectLink) 동기화 (BUG-H04)
        # Sprint 19 PR #1 C9 (Codex F-1): workspace_id 명시 전달
        if self.project_repo is not None:
            linked = await self.project_repo.find_projects_by_meeting(meeting_id, workspace_id)
            result["projects"] = [
                {
                    "id": str(p.id),
                    "title": p.title,
                    "status": p.status,
                    "visibility": p.visibility,
                }
                for p in linked
            ]
        else:
            result["projects"] = []
        return result

    async def get_meeting_status(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> dict:
        """회의 처리 상태. 헌법 I-9 workspace_id 필수 (Codex F-1).

        CAND-A completeness: 연결된 project visibility 게이트 — 비-ProjectMember 가
        private-linked 회의의 처리상태(존재성/실패사유)를 polling 으로 캐내는 status leak 차단.
        """
        meeting = await self.repo.find_by_id(meeting_id, workspace_id)
        if meeting is None:
            raise MeetingNotFoundError()
        await self._verify_meeting_visibility(
            meeting_id, workspace_id, requester_user_id, requester_role
        )
        return {
            "status": meeting.status,
            "errorMessage": meeting.error_message,
        }

    async def export_meeting(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        fmt: str,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> tuple[str, str, str]:
        """회의 내보내기 (content, filename, media_type). 헌법 I-9 workspace_id 필수 (Codex F-1).

        CAND-A: 연결된 project visibility 게이트 (비-ProjectMember 누출 차단).
        """
        meeting = await self.repo.find_by_id(meeting_id, workspace_id)
        if meeting is None:
            raise MeetingNotFoundError()
        await self._verify_meeting_visibility(
            meeting_id, workspace_id, requester_user_id, requester_role
        )

        segments = await self.repo.get_segments(meeting_id, workspace_id)
        summary = await self.repo.get_summary(meeting_id, workspace_id)

        # 액션 아이템 조회 (actions 도메인 workspace 격리는 Phase 5 commit C4 에서 강제)
        actions = []
        if self.action_repo:
            actions = await self.action_repo.find_by_meeting(meeting_id)

        if fmt == "md":
            content = self._to_markdown(meeting, summary, segments, actions)
            return content, f"{meeting.title}.md", "text/markdown; charset=utf-8"
        else:
            detail = await self.get_meeting_detail(
                meeting_id,
                workspace_id,
                requester_user_id=requester_user_id,
                requester_role=requester_role,
            )
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

    # ── Sprint 23 D4 Task 2 Step 2.2: promote 1-button ──

    async def promote(
        self,
        *,
        meeting_id: uuid.UUID,
        source_workspace_id: uuid.UUID,
        target_workspace_id: uuid.UUID,
        promoted_by_user_id: uuid.UUID,
        background_tasks: BackgroundTasks,
        requester_role: str | None = None,
    ) -> MeetingPromoteOut:
        """1-button promote: 원본 보존 + target ws 복제 (Meeting/Summary/Segments) + audit + bg embedding 복제.

        I-18 (Promotion = 복제 + tombstone, 이동 금지): source Meeting.status 변경 없음.
        검증: source != target / target type='team' / promoter 가 target ws 멤버.
        helper: common/promote_helpers.validate_promote_target + build_item_promotion_audit.
        """
        # Sprint 23 D4 (Task 2 Step 2.2): promote 흐름 의존성 fail-closed 검증.
        if self._session_factory is None:
            raise RuntimeError(
                "session_factory 필수 (I-18 promote BG embedding 복제, fail-closed)"
            )

        # 1. promote target 검증 (헬퍼 — 4 도메인 공통 패턴)
        try:
            await validate_promote_target(
                source_workspace_id=source_workspace_id,
                target_workspace_id=target_workspace_id,
                promoted_by_user_id=promoted_by_user_id,
                workspace_repo=self.workspace_repo,
            )
        except PromoteValidationError as exc:
            # PromoteValidationError.code → meetings 도메인 HTTPException 매핑.
            if exc.code == "same_workspace":
                raise CannotPromoteToSameWorkspaceError() from exc
            if exc.code == "target_personal":
                raise CannotPromoteToPersonalError() from exc
            # target_invalid / not_member → 403 (memory 패턴 정렬)
            raise TargetWorkspaceInvalidError() from exc

        # 2. 원본 Meeting + Summary + Segments fetch (I-9 workspace_id 강제)
        source = await self.repo.find_by_id(meeting_id, source_workspace_id)
        if source is None:
            raise MeetingNotFoundError()

        # CAND-A completeness: SOURCE 회의의 연결 project visibility 게이트 — 비-멤버가
        # private/draft 프로젝트의 회의를 team ws 로 promote(=복제 노출)하는 IDOR 차단.
        # promoter 는 source ws 멤버지만 ProjectMember 가 아닐 수 있음 → 비-멤버 → 404.
        await self._verify_meeting_visibility(
            meeting_id, source_workspace_id, promoted_by_user_id, requester_role
        )

        # Sprint 23 Codex 4차 P2-1 fix: terminal status (completed / failed) 만 promote 허용.
        # uploading / transcribing / analyzing 같은 transient 는 target ws 에서 영원히 stuck
        # (pipeline 미실행, 동기화 없음) → 거부 + 사용자 안내.
        if source.status not in ("completed", "failed"):
            raise MeetingPromoteNonTerminalError()

        # Sprint 23 Codex 8차 P2 fix: status='completed' 라도 embedding step 실패 → chunk 0 인
        # 경우 BG task 가 audit 'n/a' silent success → target 영원히 unsearchable. notes 의
        # NotePromoteNotEmbeddedError 패턴 (Codex 6차 P2) 와 동일. preflight 거부.
        # failed status 는 임베딩 자체 의미 없음 (예외 — chunk 검증 skip).
        if source.status == "completed":
            existing_chunks = await self.repo.find_meeting_chunks(
                source.id, source_workspace_id
            )
            if not existing_chunks:
                raise MeetingPromoteNotEmbeddedError()

        source_summary = await self.repo.get_summary(
            meeting_id, source_workspace_id
        )
        source_segments = await self.repo.get_segments(
            meeting_id, source_workspace_id
        )

        # 3. 복제 Meeting (id 새로 발급, workspace_id=target, status=processing).
        # I-18: 원본 보존 — source.status 미변경.
        new_meeting = Meeting(
            workspace_id=target_workspace_id,
            title=source.title,
            file_key=source.file_key,
            source=source.source,
            recorded_at=source.recorded_at,
            duration_sec=source.duration_sec,
            # Sprint 23 Codex 2차 P2 fix: source.status 보존 (이전: 'completed' 하드코드).
            # 사유: uploading/transcribing/analyzing/failed source 를 promote 시 target ws 에
            # misleadingly 'completed' 표시 → 사용자 인지 오류. STT/Gemini 재실행 안 함이므로
            # source 상태 그대로 복제 = source 진행상황 정직하게 반영.
            # Sprint 23 Codex 4차 P2-1 fix: source.status 가 terminal (completed/failed) 인 경우만
            # 통과 (검증은 위에서 raise 로 처리). 본 row 는 source.status 그대로 복제 = 정직 반영.
            status=source.status,
            has_transcript=source.has_transcript,
            has_summary=source.has_summary,
            # Sprint 23 Codex 5차 P3 fix: failed meeting 의 error_message 보존.
            # status='failed' 도 terminal 로 허용 (4차 P2-1) — 그러면 target 의 error_message 가 None
            # 이면 사용자가 실패 이유 알 수 없음. source.error_message 그대로 복제.
            error_message=source.error_message,
            # Sprint 23 Codex 3차 P3 (임시 fix): action_item_count=0 reset.
            # Sprint 24 BL-063: 아래 clone_action_items_for_promote 호출 후 실 count 로 갱신
            # (helper 가 target meeting_id 로 ActionItem rows 자동 복제 → 인지 불일치 해소).
            action_item_count=0,
            created_by_id=promoted_by_user_id,
        )
        new_meeting = await self.repo.save_promoted_meeting(new_meeting)

        # 4. MeetingSummary 복제 (있으면)
        if source_summary is not None:
            new_summary = MeetingSummary(
                meeting_id=new_meeting.id,
                summary=source_summary.summary,
                key_decisions=list(source_summary.key_decisions or []),
                topics=list(source_summary.topics or []),
            )
            await self.repo.save_promoted_summary(new_summary)

        # 5. TranscriptSegment[] 복제
        if source_segments:
            new_segments = [
                TranscriptSegment(
                    meeting_id=new_meeting.id,
                    speaker=seg.speaker,
                    start_sec=seg.start_sec,
                    end_sec=seg.end_sec,
                    text=seg.text,
                )
                for seg in source_segments
            ]
            await self.repo.save_promoted_segments(new_segments)

        # 5.5. Sprint 24 BL-063: source ActionItem rows 자동 복제 (assignee_id target ws verify).
        # parent SAVEPOINT 활용 — 부분 실패 시 entire promote rollback (transactional 보장).
        # target_project_id=None — cross-ws project 제약 (사용자가 추후 수동 연결).
        cloned_action_count = await clone_action_items_for_promote(
            source_meeting_id=source.id,
            target_meeting_id=new_meeting.id,
            target_workspace_id=target_workspace_id,
            target_project_id=None,
            session=self.repo.session,
        )
        if cloned_action_count > 0:
            new_meeting.action_item_count = cloned_action_count
            self.repo.session.add(new_meeting)
            await self.repo.session.flush()

        # 6. ItemPromotionAudit row (helper)
        audit = build_item_promotion_audit(
            item_type="meeting",
            source_item_id=source.id,
            new_item_id=new_meeting.id,
            source_workspace_id=source_workspace_id,
            target_workspace_id=target_workspace_id,
            promoted_by_user_id=promoted_by_user_id,
            embedding_status="pending",
        )
        await self.repo.save_item_promotion_audit(audit)

        await self.repo.commit()

        # 7. background: target ws 에 EmbeddingChunk 복제 + audit status 갱신.
        # session 종료 시 source.id 등 객체 expire 가능성 — 원시 UUID 로 전달.
        background_tasks.add_task(
            _bg_promote_embed_meeting,
            source_meeting_id=source.id,
            source_workspace_id=source_workspace_id,
            new_meeting_id=new_meeting.id,
            target_workspace_id=target_workspace_id,
            audit_id=audit.id,
            session_factory=self._session_factory,
        )

        return MeetingPromoteOut(
            new_meeting_id=new_meeting.id,
            audit_id=audit.id,
            status="embedding_pending",
        )


# ── Sprint 23 D4 Task 2 Step 2.2: promote BG embedding 복제 헬퍼 ──


async def _bg_promote_embed_meeting(
    source_meeting_id: uuid.UUID,
    source_workspace_id: uuid.UUID,
    new_meeting_id: uuid.UUID,
    target_workspace_id: uuid.UUID,
    audit_id: uuid.UUID,
    session_factory: "async_sessionmaker[AsyncSession]",
) -> None:
    """meeting promote BG: source ws 의 EmbeddingChunk 들을 target ws 로 복제 + audit status 갱신.

    pending → processing → completed/failed 흐름. session_factory 로 별도 session.
    임베딩 vector 자체는 그대로 복사 (재계산 불필요 — Gemini cost 절감).
    """
    from sqlmodel import update as _update

    from src.common.promote_models import ItemPromotionAudit

    async with session_factory() as session:
        repo = MeetingRepository(session)
        # processing 마크
        await session.exec(
            _update(ItemPromotionAudit)
            .where(ItemPromotionAudit.id == audit_id)
            .values(embedding_status="processing")
        )
        await session.commit()

        try:
            source_chunks = await repo.find_meeting_chunks(
                source_meeting_id, source_workspace_id
            )
            # chunk 0개 → audit n/a. embed_meeting 이 호출되지 않은 (text-only short) 회의 케이스.
            if not source_chunks:
                await session.exec(
                    _update(ItemPromotionAudit)
                    .where(ItemPromotionAudit.id == audit_id)
                    .values(embedding_status="n/a")
                )
                await session.commit()
                return

            # parent_chunk_id (L1) 매핑 유지: old_id → new_id.
            id_map: dict[uuid.UUID, uuid.UUID] = {}
            # 1차: L1 chunk 먼저 (parent_chunk_id 없음) 복제
            for src_chunk in source_chunks:
                if src_chunk.parent_chunk_id is None:
                    new_id = uuid.uuid4()
                    id_map[src_chunk.id] = new_id
                    dup = EmbeddingChunk(
                        id=new_id,
                        workspace_id=target_workspace_id,
                        project_id=None,  # promote 시 target ws 의 project 미연결 (사용자가 별도 연결)
                        source_id=new_meeting_id,
                        source_type="meeting",
                        chunk_text=src_chunk.chunk_text,
                        chunk_index=src_chunk.chunk_index,
                        chunk_level=src_chunk.chunk_level,
                        parent_chunk_id=None,
                        embedding=src_chunk.embedding,
                        metadata_json=dict(src_chunk.metadata_json or {}),
                    )
                    session.add(dup)
            # 2차: L2 chunk (parent_chunk_id 가 1차에서 매핑된 새 UUID 로 변환)
            for src_chunk in source_chunks:
                if src_chunk.parent_chunk_id is not None:
                    parent_new_id = id_map.get(src_chunk.parent_chunk_id)
                    # parent 가 source set 에 없으면 (이론상 발생 X) None 으로 fallback
                    dup = EmbeddingChunk(
                        workspace_id=target_workspace_id,
                        project_id=None,
                        source_id=new_meeting_id,
                        source_type="meeting",
                        chunk_text=src_chunk.chunk_text,
                        chunk_index=src_chunk.chunk_index,
                        chunk_level=src_chunk.chunk_level,
                        parent_chunk_id=parent_new_id,
                        embedding=src_chunk.embedding,
                        metadata_json=dict(src_chunk.metadata_json or {}),
                    )
                    session.add(dup)
            await session.flush()

            # Sprint 23 Codex 5차 P2-2 fix: target ws 의 SemanticCache 무효화 — 새 chunk 가
            # 추가됐으니 stale RAG 답변 (TTL 7d) 이 우회되도록.
            # 기존 meeting embedding pipeline 도 chunk 변경 후 invalidate_cache 호출 (pattern 정합).
            from src.embeddings.repository import EmbeddingRepository as _EmbeddingRepository

            embed_repo = _EmbeddingRepository(session)
            await embed_repo.delete_caches(target_workspace_id, None)

            await session.exec(
                _update(ItemPromotionAudit)
                .where(ItemPromotionAudit.id == audit_id)
                .values(embedding_status="completed")
            )
            await session.commit()
        except Exception as exc:
            logger.warning(
                "meeting promote embedding 복제 실패 (audit=%s): %s",
                audit_id, exc,
            )
            # Sprint 23 Codex 4차 P2-2 fix: rollback 먼저 — session.flush() 실패 시 transaction
            # state failed → 후속 update 도 fail → audit 가 'processing' stuck. rollback 으로
            # session 재사용 가능 상태로 복구 후 failed mark.
            await session.rollback()
            await session.exec(
                _update(ItemPromotionAudit)
                .where(ItemPromotionAudit.id == audit_id)
                .values(embedding_status="failed")
            )
            await session.commit()
