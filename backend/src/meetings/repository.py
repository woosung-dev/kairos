# backend/src/meetings/repository.py
"""Meeting Repository — AsyncSession 유일 보유자. 헌법 I-9 workspace_id 필수 (Sprint 19 PR #1)."""
import uuid

from sqlalchemy.orm import aliased
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import and_, exists, func, or_, select

from src.common.promote_models import ItemPromotionAudit
from src.common.visibility import ADMIN_BYPASS_ROLES, project_access_clause
from src.embeddings.models import EmbeddingChunk
from src.meetings.models import Meeting, MeetingSummary, TranscriptSegment
from src.projects.models import MeetingProjectLink, Project


def _meeting_visibility_filter(
    stmt,
    requester_user_id: uuid.UUID | None,
    requester_role: str | None,
):
    """CAND-A completeness: meeting LIST 에 project visibility 게이트 적용.

    회의는 MeetingProjectLink 로 N개 project 와 연결될 수 있다. 규칙
    (_verify_meeting_visibility 와 동일):
    - admin/owner : 모든 visibility 우회 (필터 없음)
    - 링크 0개 : 통과 (프로젝트 미연결 = 미제한, 워크스페이스 레벨)
    - 링크된 project 중 접근 가능한 것이 1개라도 있으면 통과
    - 링크가 전부 접근 불가(private 비-멤버 / draft 비-작성자)면 제외

    requester_role 미전달(None) = 내부/파이프라인 호출 → 게이트 skip (하위호환).

    project_id 필터 시 외부 쿼리가 MeetingProjectLink 를 join 하므로, 상관 EXISTS
    안에서는 별도 alias 를 사용해 외부 join 과의 충돌을 피한다.
    """
    if requester_role is None:
        return stmt
    if requester_role in ADMIN_BYPASS_ROLES:
        return stmt

    mpl_exists = aliased(MeetingProjectLink)
    mpl_link = aliased(MeetingProjectLink)

    # 회의에 링크가 하나도 없으면 통과 (워크스페이스 레벨).
    no_links = ~exists().where(mpl_exists.meeting_id == Meeting.id)

    # 링크된 project 중 접근 가능한 것이 하나라도 있으면 통과.
    # 코어 규칙은 common/visibility.py SSOT (CAND-B flatten EXISTS 포함) —
    # N:M 링크 shape(aliased MPL + no_links)만 meetings 도메인 소유.
    has_accessible_link = exists().where(
        and_(
            mpl_link.meeting_id == Meeting.id,
            mpl_link.project_id == Project.id,
            project_access_clause(requester_user_id),
        )
    )
    return stmt.where(or_(no_links, has_accessible_link))


class MeetingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, meeting: Meeting) -> Meeting:
        self.session.add(meeting)
        await self.session.flush()
        return meeting

    async def find_by_id(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> Meeting | None:
        """헌법 I-9 (Codex F-1): meeting_id + workspace_id 동시 필터."""
        return (await self.session.exec(
            select(Meeting).where(
                Meeting.id == meeting_id,
                Meeting.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
        project_id: uuid.UUID | None = None,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> list[Meeting]:
        stmt = select(Meeting).where(Meeting.workspace_id == workspace_id)
        if project_id is not None:
            stmt = stmt.join(
                MeetingProjectLink,
                MeetingProjectLink.meeting_id == Meeting.id,
            ).where(MeetingProjectLink.project_id == project_id)
        # CAND-A completeness: project visibility 게이트 (비-멤버 private-linked 회의 metadata/존재성 누출 차단).
        stmt = _meeting_visibility_filter(stmt, requester_user_id, requester_role)
        stmt = stmt.order_by(Meeting.created_at.desc()).offset(offset).limit(limit)
        return list((await self.session.exec(stmt)).all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Meeting)
            .where(Meeting.workspace_id == workspace_id)
        )
        if project_id is not None:
            stmt = stmt.join(
                MeetingProjectLink,
                MeetingProjectLink.meeting_id == Meeting.id,
            ).where(MeetingProjectLink.project_id == project_id)
        # CAND-A completeness: total 도 필터된 집합 기준 (pagination 정합).
        stmt = _meeting_visibility_filter(stmt, requester_user_id, requester_role)
        return (await self.session.exec(stmt)).one()

    async def update_status(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """헌법 I-9 (Codex F-1): mutating 호출도 workspace_id 검증."""
        meeting = await self.find_by_id(meeting_id, workspace_id)
        if meeting:
            meeting.status = status
            meeting.error_message = error_message
            self.session.add(meeting)
            await self.session.flush()

    async def set_has_transcript(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID, value: bool
    ) -> None:
        meeting = await self.find_by_id(meeting_id, workspace_id)
        if meeting:
            meeting.has_transcript = value
            self.session.add(meeting)
            await self.session.flush()

    async def set_has_summary(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID, value: bool
    ) -> None:
        meeting = await self.find_by_id(meeting_id, workspace_id)
        if meeting:
            meeting.has_summary = value
            self.session.add(meeting)
            await self.session.flush()

    async def save_segments(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        segments: list[TranscriptSegment],
    ) -> None:
        """헌법 I-9 (Codex F-1): meeting workspace 사전 검증 후 INSERT."""
        meeting = await self.find_by_id(meeting_id, workspace_id)
        if meeting is None:
            return
        for seg in segments:
            seg.meeting_id = meeting_id
            self.session.add(seg)
        await self.session.flush()

    async def save_summary(
        self,
        meeting_id: uuid.UUID,
        workspace_id: uuid.UUID,
        summary_data: dict,
    ) -> MeetingSummary | None:
        """헌법 I-9 (Codex F-1): meeting workspace 사전 검증 후 INSERT."""
        meeting = await self.find_by_id(meeting_id, workspace_id)
        if meeting is None:
            return None
        summary = MeetingSummary(
            meeting_id=meeting_id,
            summary=summary_data.get("summary", ""),
            key_decisions=summary_data.get("key_decisions", []),
            topics=summary_data.get("topics", []),
        )
        self.session.add(summary)
        await self.session.flush()
        return summary

    async def get_segments(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> list[TranscriptSegment]:
        """헌법 I-9: Meeting join 으로 workspace 격리 검증."""
        return list((await self.session.exec(
            select(TranscriptSegment)
            .join(Meeting, TranscriptSegment.meeting_id == Meeting.id)
            .where(
                TranscriptSegment.meeting_id == meeting_id,
                Meeting.workspace_id == workspace_id,
            )
            .order_by(TranscriptSegment.start_sec)
        )).all())

    async def get_summary(
        self, meeting_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> MeetingSummary | None:
        """헌법 I-9: Meeting join 으로 workspace 격리 검증."""
        return (await self.session.exec(
            select(MeetingSummary)
            .join(Meeting, MeetingSummary.meeting_id == Meeting.id)
            .where(
                MeetingSummary.meeting_id == meeting_id,
                Meeting.workspace_id == workspace_id,
            )
        )).one_or_none()

    # ── Sprint 23 D4 Task 2 Step 2.2: promote 지원 메서드 ──

    async def save_promoted_meeting(self, meeting: Meeting) -> Meeting:
        """promote 복제본 Meeting INSERT — workspace_id 는 호출자가 target 으로 설정.

        save() 와 시그니처 동일하지만, promote 흐름에서 명시적으로 호출 출처 분리.
        I-9 검증은 호출자 (service.promote) 가 사전에 target workspace 멤버십을 확인.
        """
        self.session.add(meeting)
        await self.session.flush()
        return meeting

    async def save_promoted_summary(
        self, summary: MeetingSummary
    ) -> MeetingSummary:
        """promote 복제본 MeetingSummary INSERT — meeting_id 는 호출자가 새 meeting.id 로 설정."""
        self.session.add(summary)
        await self.session.flush()
        return summary

    async def save_promoted_segments(
        self, segments: list[TranscriptSegment]
    ) -> None:
        """promote 복제본 TranscriptSegment[] INSERT — meeting_id 는 호출자가 새 meeting.id 로 설정."""
        for seg in segments:
            self.session.add(seg)
        await self.session.flush()

    async def save_item_promotion_audit(
        self, audit: ItemPromotionAudit
    ) -> ItemPromotionAudit:
        """4 도메인 공통 ItemPromotionAudit INSERT — commit 은 호출자."""
        self.session.add(audit)
        await self.session.flush()
        return audit

    async def find_meeting_chunks(
        self, meeting_id: uuid.UUID, source_workspace_id: uuid.UUID
    ) -> list[EmbeddingChunk]:
        """promote BG 흐름용: source meeting 의 모든 EmbeddingChunk 조회 (target ws 복제용).

        I-9 4-C: source_workspace_id WHERE 필터 강제 — cross-workspace 격리.
        """
        return list((await self.session.exec(
            select(EmbeddingChunk).where(
                EmbeddingChunk.source_type == "meeting",
                EmbeddingChunk.source_id == meeting_id,
                EmbeddingChunk.workspace_id == source_workspace_id,
            )
        )).all())

    async def commit(self) -> None:
        await self.session.commit()
