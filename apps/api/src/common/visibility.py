# Project visibility 정책 단일 진실 원천 (SSOT) — 규칙 정의는 이 파일에만 존재한다
"""Project visibility 규칙: public 통과 / draft = creator 만 / private = ProjectMember
∧ 현 WorkspaceMember (orphan ProjectMember 잔재 차단, CAND-B).

이 모듈은 100% stateless — AsyncSession/DB/서비스 호출 없음 (헌법 I-1 무충돌,
ADR-014 무충돌). 모델 import 는 함수 스코프 lazy import 로 한정한다.

admin/owner·내부호출(role=None) 우회는 **사이트 소유** — 사이트마다 fail 방향이
다르며(D1: projects 는 user=None → public-only 보수, notes/actions/meetings 는
role=None → 게이트 skip) 통일하면 파이프라인 침묵 실패 또는 목록 누수가 난다.
이 모듈은 코어 규칙(3-값 분기)만 제공하고 우회 분기는 어댑터/caller 에 남긴다.

인코딩 2계보 주의 (D3):
- ORM: WorkspaceMember 를 *같은* exists() 안에 펼친 flatten 단일 EXISTS —
  중첩 exists() 는 correlation 이 끊겨 LIST 누출 (codex P2 회귀). 변경 금지.
- raw SQL(embeddings): 중첩 EXISTS 인코딩. 두 상수(검색 필터 · 캐시 anti-join)는
  같은 `_PROJECT_RULE_SQL` 조각을 공유한다 (2026-09-26 정검에서 규칙이 바뀌며 통합).
  생성 SQL 은 tests/architecture/test_visibility_characterization.py 스냅샷이 고정한다.
"""
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

ADMIN_BYPASS_ROLES: tuple[str, ...] = ("admin", "owner")


@dataclass(frozen=True)
class RequesterContext:
    """요청자 컨텍스트 — (requester_user_id, requester_role) 쌍의 value object."""

    user_id: uuid.UUID | None
    role: str | None

    @property
    def is_admin(self) -> bool:
        return self.role in ADMIN_BYPASS_ROLES

    @property
    def is_internal(self) -> bool:
        """role 미전달 = 내부/파이프라인 호출 (notes/actions/meetings 게이트 skip 모드)."""
        return self.role is None


class Access(Enum):
    ALLOW = "allow"
    DENY = "deny"
    # private — caller 가 ProjectRepository.is_member() 로 해소 (is_member 가
    # ProjectMember ∧ WorkspaceMember 동시 검증을 이미 수행, CAND-B)
    NEED_MEMBERSHIP = "need_membership"


class ProjectLike(Protocol):
    visibility: str
    created_by_id: uuid.UUID | None


def decide_project_access(project: ProjectLike, user_id: uuid.UUID | None) -> Access:
    """단일 project 객체에 대한 코어 visibility 판정 (admin/internal 우회는 caller 몫).

    unknown visibility 값은 fail-closed DENY (D7 — visibility 는 스키마상 3값 고정이라
    유효 데이터에선 관찰 가능한 동작 변화 없음).
    """
    if project.visibility == "public":
        return Access.ALLOW
    if project.visibility == "draft":
        return (
            Access.ALLOW
            if user_id is not None and project.created_by_id == user_id
            else Access.DENY
        )
    if project.visibility == "private":
        return Access.DENY if user_id is None else Access.NEED_MEMBERSHIP
    return Access.DENY


def project_access_clause(user_id: uuid.UUID | None):
    """ORM 코어 술어 — 외부(또는 상관 서브쿼리 FROM 의) Project 행에 적용되는
    or_(public, draft∧creator, private∧member) 표현식.

    user_id=None 허용 — SQL 비교가 NULL 로 평가돼 draft/private 분기가 항상 거짓
    (기존 FK-상관 사이트와 byte 동일 동작).

    member 분기는 ProjectMember + WorkspaceMember 를 *같은* exists() 안에 펼친
    flatten 인코딩 (codex P2 correlation fix 보존 — 중첩 exists() 금지).
    """
    from sqlmodel import and_, exists, or_

    from src.projects.models import Project, ProjectMember
    from src.workspaces.models import WorkspaceMember

    member_exists = exists().where(
        and_(
            ProjectMember.project_id == Project.id,
            ProjectMember.user_id == user_id,
            WorkspaceMember.workspace_id == Project.workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    return or_(
        Project.visibility == "public",
        and_(
            Project.visibility == "draft",
            Project.created_by_id == user_id,
        ),
        and_(
            Project.visibility == "private",
            member_exists,
        ),
    )


def meeting_access_clause(meeting_id_col, user_id: uuid.UUID | None):
    """회의 접근 코어 술어 — N:M 링크 shape (2026-09-26 정검 C-014/C-015/C-016).

    회의는 MeetingProjectLink 로 N개 project 와 연결된다. 규칙:
    - 링크 0개 : 통과 (프로젝트 미연결 = 워크스페이스 레벨)
    - 링크된 project 중 접근 가능한 것이 1개라도 있으면 통과
    - 링크가 전부 접근 불가면 제외

    meeting_id_col 은 외부 쿼리의 회의 id 컬럼 (Meeting.id / ActionItem.meeting_id /
    InboxItem.source_id). 외부 쿼리가 MeetingProjectLink 를 join 할 수 있으므로
    상관 EXISTS 안에서는 별도 alias 를 쓴다. admin/internal 우회는 caller 몫.
    회의에서 파생된 데이터(청크·인박스·액션)는 전부 이 규칙과 결과가 같아야 한다.
    """
    from sqlalchemy.orm import aliased
    from sqlmodel import and_, exists, or_

    from src.projects.models import MeetingProjectLink, Project

    mpl_exists = aliased(MeetingProjectLink)
    mpl_link = aliased(MeetingProjectLink)

    no_links = ~exists().where(mpl_exists.meeting_id == meeting_id_col)
    has_accessible_link = exists().where(
        and_(
            mpl_link.meeting_id == meeting_id_col,
            mpl_link.project_id == Project.id,
            project_access_clause(user_id),
        )
    )
    return or_(no_links, has_accessible_link)


def apply_project_visibility(stmt, ctx: RequesterContext):
    """projects 전용 어댑터 (D1: user 부재 → public-only 보수 모드, role=None skip 없음)."""
    from src.projects.models import Project

    if ctx.is_admin:
        return stmt
    if ctx.user_id is None:
        return stmt.where(Project.visibility == "public")
    return stmt.where(project_access_clause(ctx.user_id))


def apply_fk_project_visibility(stmt, project_id_col, ctx: RequesterContext):
    """FK-상관 어댑터 (notes/actions — D1: 내부호출 skip / D2: project_id IS NULL 통과)."""
    from sqlmodel import and_, exists, or_

    from src.projects.models import Project

    if ctx.is_internal or ctx.is_admin:
        return stmt
    accessible_project = exists().where(
        and_(
            Project.id == project_id_col,
            project_access_clause(ctx.user_id),
        )
    )
    return stmt.where(
        or_(
            project_id_col.is_(None),
            accessible_project,
        )
    )


def apply_fk_meeting_visibility(stmt, meeting_id_col, ctx: RequesterContext):
    """회의 FK-상관 어댑터 (actions — 내부호출 skip / admin 우회 / meeting_id IS NULL 통과).

    C-016: 회의에서 추출된 액션은 project_id 가 NULL 이라 project 게이트를 통과했다.
    원본 회의가 보이지 않으면 그 액션도 보이지 않아야 한다.
    """
    from sqlmodel import or_

    if ctx.is_internal or ctx.is_admin:
        return stmt
    return stmt.where(
        or_(
            meeting_id_col.is_(None),
            meeting_access_clause(meeting_id_col, ctx.user_id),
        )
    )


# ── raw SQL 계보 (embeddings — 중첩 EXISTS 인코딩) ──────────────────────────────
# 바인딩 파라미터: :req_uid (requester user id), :req_role (requester role).
#
# 2026-09-26 정검 C-014/C-020 로 청크 규칙을 source_type 별로 나눴다.
# - meeting 청크 : 회의 규칙 (meeting_access_clause 와 같은 결과). chunk.project_id 는
#   파이프라인 자동 확정 때만 채워지고 수동 연결·인박스 확정·링크 해제를 따라가지
#   않으므로 판정에 쓰지 않는다 (N:M 링크가 진실 원천).
# - memory 청크  : 작성자 본인 또는 팀으로 올린(is_shared) 메모만. **admin/owner 도 우회하지
#   않는다** — 메모는 개인 레이어 (C-020 결정 (a), 2026-09-27).
# - 그 외        : 기존 project 규칙 (project_id IS NULL 통과).

# 코어 project 규칙 — 별칭 p 에 적용. 두 상수가 같은 문자열을 공유한다.
_PROJECT_RULE_SQL = """(
                        p.visibility = 'public'
                        OR (p.visibility = 'draft' AND p.created_by_id = :req_uid)
                        OR (p.visibility = 'private' AND EXISTS (
                            SELECT 1 FROM project_members pm
                            WHERE pm.project_id = p.id AND pm.user_id = :req_uid
                              AND EXISTS (
                                SELECT 1 FROM workspace_members wm
                                WHERE wm.workspace_id = p.workspace_id
                                  AND wm.user_id = :req_uid
                              )
                        ))
                      )"""

# EmbeddingRepository.vector_search / text_search 용 WHERE 절 조각.
PROJECT_VISIBILITY_FILTER_SQL = f"""
            AND (
                embedding_chunks.source_type <> 'memory'
                OR EXISTS (
                    SELECT 1 FROM memory_items mi
                    WHERE mi.id = embedding_chunks.source_id
                      AND (mi.user_id = :req_uid OR mi.is_shared)
                )
            )
            AND (
                :req_role IN ('admin', 'owner')
                OR (
                    embedding_chunks.source_type = 'meeting'
                    AND (
                        NOT EXISTS (
                            SELECT 1 FROM meeting_project_links ml
                            WHERE ml.meeting_id = embedding_chunks.source_id
                        )
                        OR EXISTS (
                            SELECT 1 FROM meeting_project_links ml
                            JOIN projects p ON p.id = ml.project_id
                            WHERE ml.meeting_id = embedding_chunks.source_id
                              AND {_PROJECT_RULE_SQL}
                        )
                    )
                )
                OR (
                    embedding_chunks.source_type <> 'meeting'
                    AND (
                        embedding_chunks.project_id IS NULL
                        OR EXISTS (
                            SELECT 1 FROM projects p
                            WHERE p.id = embedding_chunks.project_id
                              AND {_PROJECT_RULE_SQL}
                        )
                    )
                )
            )
        """

# EmbeddingRepository._all_chunks_visible 용 anti-join 쿼리 (캐시 hit 검증).
# 2026-08-01 BL-EXT-CACHE-1: 행 부재 = 위반(fail-closed) — 삭제된 source chunk 를
# 참조하는 캐시행의 서빙을 차단한다.
# 위반 정의 (하나라도 해당하면 캐시 miss):
# - 요청한 chunk 행이 없음 — admin/owner 제외 (N4: admin 은 삭제된 source 캐시도 HIT 정책)
# - memory chunk 인데 작성자 본인도 아니고 공유 메모도 아님 (admin 포함 전원 적용)
# - admin/owner 가 아니고, 위 검색 필터의 meeting/project 규칙을 통과하지 못함
# :req_role 이 NULL 이면 비-admin 으로 본다 (COALESCE — NOT IN 이 NULL 에서 fail-open 되는 것 차단)
ALL_CHUNKS_VISIBLE_SQL = f"""
            SELECT 1 FROM unnest(CAST(:chunk_ids AS uuid[])) AS req(id)
            LEFT JOIN embedding_chunks ec ON ec.id = req.id
            WHERE (ec.id IS NULL AND COALESCE(:req_role, '') NOT IN ('admin', 'owner'))
               OR (
                 ec.source_type = 'memory'
                 AND NOT EXISTS (
                   SELECT 1 FROM memory_items mi
                   WHERE mi.id = ec.source_id
                     AND (mi.user_id = :req_uid OR mi.is_shared)
                 )
               )
               OR (
                 COALESCE(:req_role, '') NOT IN ('admin', 'owner')
                 AND (
                   (
                     ec.source_type = 'meeting'
                     AND EXISTS (
                       SELECT 1 FROM meeting_project_links ml
                       WHERE ml.meeting_id = ec.source_id
                     )
                     AND NOT EXISTS (
                       SELECT 1 FROM meeting_project_links ml
                       JOIN projects p ON p.id = ml.project_id
                       WHERE ml.meeting_id = ec.source_id
                         AND {_PROJECT_RULE_SQL}
                     )
                   )
                   OR (
                     ec.source_type <> 'meeting'
                     AND ec.project_id IS NOT NULL
                     AND NOT EXISTS (
                       SELECT 1 FROM projects p
                       WHERE p.id = ec.project_id
                         AND {_PROJECT_RULE_SQL}
                     )
                   )
                 )
               )
            LIMIT 1
        """
