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
- raw SQL(embeddings): 중첩 EXISTS 인코딩. 아래 두 상수는 기존 사이트의 문자열을
  byte 그대로 옮긴 것 — 쿼리 플랜 입력 불변 증명은
  tests/architecture/test_visibility_characterization.py 스냅샷이,
  두 상수의 논리 일치는 tests/common/test_visibility.py 정규화 비교가 강제한다.
  # ponytail: 상수 2개 병존 — 공용 템플릿화하려면 한쪽 whitespace 정규화(스냅샷
  # 갱신) 필요. 규칙 변경이 실제로 발생하는 시점에 통합.
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


# ── raw SQL 계보 (embeddings — 중첩 EXISTS 인코딩, 기존 문자열 byte 보존) ──────────
# 바인딩 파라미터: :req_uid (requester user id), :req_role (role — 필터 쪽만).

# EmbeddingRepository.vector_search / text_search 용 WHERE 절 조각.
# chunk.project_id IS NULL 통과 / admin·owner 통과 / 그 외 코어 규칙.
PROJECT_VISIBILITY_FILTER_SQL = """
            AND (
                project_id IS NULL
                OR :req_role IN ('admin', 'owner')
                OR EXISTS (
                    SELECT 1 FROM projects p
                    WHERE p.id = embedding_chunks.project_id
                      AND (
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
                      )
                )
            )
        """

# EmbeddingRepository._all_chunks_visible 용 anti-join 쿼리 (admin 우회는 caller).
# 2026-08-01 BL-EXT-CACHE-1: 행 부재 = 위반(fail-closed) — 삭제된 source chunk 를
# 참조하는 캐시행의 비-admin 서빙을 차단한다.
# 위반 정의: 요청한 chunk 행이 없거나, project_id 있고 코어 규칙 통과 못 하는 chunk 가 1개라도 존재.
ALL_CHUNKS_VISIBLE_SQL = """
            SELECT 1 FROM unnest(CAST(:chunk_ids AS uuid[])) AS req(id)
            LEFT JOIN embedding_chunks ec ON ec.id = req.id
            WHERE ec.id IS NULL
               OR (
                 ec.project_id IS NOT NULL
                 AND NOT EXISTS (
                   SELECT 1 FROM projects p
                   WHERE p.id = ec.project_id
                     AND (
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
                     )
                 )
               )
            LIMIT 1
        """
