#!/usr/bin/env python3
# Multi-Agent QA fixture seed (Sprint 18 → 19, 2026-05-17). 계정 생성은 사용자 사전 수동.
"""Sprint 18 → 19 Multi-Agent QA fixture seed.

자격증명(Clerk 계정 + JWT)은 본 스크립트가 만들지 않는다.
사용자가 https://dashboard.clerk.com 에서 5계정 + sign-in token 발급 후
`seed-credentials.env` 채워 전달. 본 스크립트는 fixture (User row + Workspace +
Project + Note + EmbeddingChunk) 만 담당.

사용:
    # 1. 사용자가 Clerk dev에서 5계정 만들고 JWT 발급
    # 2. seed-credentials.env 채움
    # 3. backend 디렉터리에서:
    cd backend
    uv run python scripts/seed_qa_fixtures.py \
        --env ~/.kairos-qa-secrets/seed-credentials.env \
        --out /tmp/seed-fixtures.json

옵션:
    --env PATH              seed-credentials.env 경로 (required)
    --out PATH              seed-fixtures.json 출력 경로 (default: ./seed-fixtures.json)
    --dry-run-cleanup       삭제 대상 row 카운트만 출력 (--cleanup 안전 검증용)
    --cleanup               qa_run_id 기반 cascade delete (위험. --dry-run-cleanup 먼저)
    --skip-embeddings       임베딩 생성 스킵 (OpenAI 호출 회피, 빠른 dry-run)

종속:
    backend/src/* 모듈 import (uv run 안에서만 동작).
    OpenAI API 키 (settings.openai_api_key) — 임베딩 4건 생성 ~$0.001.

산출:
    seed-fixtures.json — workspace_id / project_id / note_id / chunk_id 매핑.
    Sentinel sub-agent 가 IDOR + RAG visibility 검증 시 expected source IDs 로 사용.

idempotent: 같은 clerk_id User, 같은 [QA-2026-05-17] prefix Workspace 가 이미 있으면 재사용.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.common.database import dispose_engine, get_session_factory, init_engine
from src.core.config import get_settings
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.notes.models import Note
from src.projects.models import Project, ProjectMember
from src.workspaces.models import Workspace, WorkspaceMember

QA_RUN_ID = "2026-05-17-multi-agent"
WS_PREFIX = "[QA-2026-05-17]"  # Workspace.name / Project.description / Note.title prefix
PERSONAS = ("SENTINEL_A", "SENTINEL_B", "CASUAL", "MOBILE", "POWER")

# RAG visibility 케이스 검증을 위한 fixture 텍스트 (sub-agent 가 expected source IDs 로 사용)
RAG_FIXTURE_NOTES = {
    "public": {
        "title": "공개 프로젝트 회의 요약",
        "content": "이번 분기 OKR 발표를 마쳤습니다. 전사 공유 가능한 내용입니다. 카이로스 검색 키워드: alpha-public-fixture-2026.",
    },
    "draft": {
        "title": "초안 프로젝트 아이디어 메모",
        "content": "아직 정리 중인 기획 초안입니다. 작성자와 ProjectMember만 봐야 합니다. 카이로스 검색 키워드: beta-draft-fixture-2026.",
    },
    "private": {
        "title": "비공개 프로젝트 민감 정보",
        "content": "외부 노출 절대 금지. ProjectMember 만 접근. 카이로스 검색 키워드: gamma-private-fixture-2026.",
    },
    "cross_tenant_private": {
        "title": "Sentinel B 전용 비공개 노트",
        "content": "Sentinel B 워크스페이스 전용. A 토큰으로 접근 시 leak되면 IDOR 버그. 카이로스 검색 키워드: delta-cross-tenant-fixture-2026.",
    },
}

POWER_NOTES = [
    {"title": "Power 노트 1 — 단축키 검증용", "content": "단축키 ⌘K로 검색 가능한 노트."},
    {"title": "Power 노트 2 — 벌크 export 검증용", "content": "여러 노트를 한 번에 export 시도."},
    {"title": "Power 노트 3 — 검색 고급 옵션 검증용", "content": "type:note 필터 검증."},
    {"title": "Power 노트 4 — Quick Capture 검증용", "content": "Quick Capture 모달로 즉시 저장."},
    {"title": "Power 노트 5 — API 직접 호출 검증용", "content": "/api/v1/notes API 호출 결과."},
]

POWER_PROJECTS = [
    {"title": "Power 프로젝트 A", "visibility": "public"},
    {"title": "Power 프로젝트 B", "visibility": "public"},
    {"title": "Power 프로젝트 C", "visibility": "draft"},
    {"title": "Power 프로젝트 D", "visibility": "private"},
]


@dataclass
class Credentials:
    """seed-credentials.env 파싱 결과 — 페르소나당 5필드."""
    persona: str  # SENTINEL_A / SENTINEL_B / CASUAL / MOBILE / POWER
    email: str
    clerk_user_id: str
    jwt: str
    jwt_expires_at: str
    display_name: str


@dataclass
class SeedResult:
    """seed 산출물 — seed-fixtures.json 으로 직렬화."""
    qa_run_id: str = QA_RUN_ID
    seeded_at: str = ""
    personas: dict[str, dict[str, Any]] = field(default_factory=dict)
    rag_visibility_fixtures: dict[str, Any] = field(default_factory=dict)
    cross_tenant_fixture: dict[str, Any] = field(default_factory=dict)
    power_fixtures: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def parse_env_file(env_path: Path) -> dict[str, Credentials]:
    """seed-credentials.env 파싱 → persona → Credentials."""
    if not env_path.exists():
        raise FileNotFoundError(f"env 파일 없음: {env_path}. 템플릿: seed-credentials.env.template")
    raw: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        raw[key.strip()] = val.strip()
    creds: dict[str, Credentials] = {}
    for p in PERSONAS:
        prefix = f"QA_{p}_"
        email = raw.get(f"{prefix}EMAIL", "")
        clerk_id = raw.get(f"{prefix}CLERK_USER_ID", "")
        jwt = raw.get(f"{prefix}JWT", "")
        if not email or not clerk_id or not jwt:
            raise ValueError(f"{prefix}EMAIL/CLERK_USER_ID/JWT 누락. seed-credentials.env 채워주세요.")
        if "xxxxx" in clerk_id or "eyJ..." in jwt[:10] or len(jwt) < 30:
            raise ValueError(f"{prefix} 값이 템플릿 그대로 (xxxxx / eyJ...). 실제 값으로 교체 필요.")
        creds[p] = Credentials(
            persona=p,
            email=email,
            clerk_user_id=clerk_id,
            jwt=jwt,
            jwt_expires_at=raw.get(f"{prefix}JWT_EXPIRES_AT", "unknown"),
            display_name=raw.get(f"{prefix}DISPLAY_NAME", p),
        )
    return creds


async def get_or_create_user(session: AsyncSession, cred: Credentials) -> User:
    """clerk_id로 User 조회, 없으면 생성 (idempotent)."""
    r = await session.execute(
        select(User).where(User.clerk_id == cred.clerk_user_id)  # type: ignore[arg-type]
    )
    user = r.scalar_one_or_none()
    if user is not None:
        return user
    user = User(
        clerk_id=cred.clerk_user_id,
        email=cred.email,
        display_name=cred.display_name,
    )
    session.add(user)
    await session.flush()
    return user


async def get_or_create_workspace(session: AsyncSession, owner: User, persona: str) -> Workspace:
    """[QA-2026-05-17] WS-QA-<persona>-2026-05-17 워크스페이스 생성/재사용."""
    ws_name = f"{WS_PREFIX} WS-QA-{persona}-2026-05-17"
    r = await session.execute(
        select(Workspace).where(
            Workspace.name == ws_name,  # type: ignore[arg-type]
            Workspace.owner_id == owner.id,  # type: ignore[arg-type]
        )
    )
    ws = r.scalar_one_or_none()
    if ws is not None:
        return ws
    ws = Workspace(name=ws_name, owner_id=owner.id, type="team")
    session.add(ws)
    await session.flush()
    # owner WorkspaceMember
    member = WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner")
    session.add(member)
    await session.flush()
    return ws


async def create_project_with_note_and_chunk(
    session: AsyncSession,
    embed_service: EmbeddingService | None,
    embed_repo: EmbeddingRepository,
    workspace: Workspace,
    owner: User,
    title: str,
    visibility: str,
    fixture_key: str,
    note_data: dict[str, str],
    skip_embeddings: bool = False,
) -> dict[str, Any]:
    """Project + Note + EmbeddingChunk 세트 생성. fixture metadata 반환."""
    description = f"{WS_PREFIX} {fixture_key} — RAG visibility test fixture"
    project = Project(
        workspace_id=workspace.id,
        title=f"{WS_PREFIX} {title}",
        description=description,
        visibility=visibility,
        created_by_id=owner.id,
    )
    session.add(project)
    await session.flush()

    note = Note(
        workspace_id=workspace.id,
        project_id=project.id,
        title=note_data["title"],
        content={"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": note_data["content"]}]}]},
        plain_text=note_data["content"],
        created_by_id=owner.id,
    )
    session.add(note)
    await session.flush()

    chunk_id: str | None = None
    if not skip_embeddings and embed_service is not None:
        embeddings = await embed_service.generate_embeddings([note_data["content"]])
        chunk = await embed_repo.save_chunk(
            workspace_id=workspace.id,
            source_workspace_id=workspace.id,
            source_type="note",
            source_id=note.id,
            chunk_text=note_data["content"],
            embedding=embeddings[0],
            project_id=project.id,
            metadata_json={"qa_run_id": QA_RUN_ID, "fixture_key": fixture_key},
        )
        chunk_id = str(chunk.id)

    return {
        "project_id": str(project.id),
        "note_id": str(note.id),
        "chunk_id": chunk_id,
        "title": project.title,
        "visibility": visibility,
        "expected_keyword": note_data["content"].split("키워드:")[-1].strip() if "키워드:" in note_data["content"] else "",
    }


async def seed_all(env_path: Path, out_path: Path, skip_embeddings: bool) -> int:
    """전체 시드 실행. 성공 시 0, 실패 시 1."""
    print(f"[seed] env={env_path} out={out_path} skip_embeddings={skip_embeddings}")
    creds = parse_env_file(env_path)
    print(f"[seed] 5 persona credentials 파싱 OK: {list(creds.keys())}")

    # DB 엔진 초기화 (lifespan 우회 — 단독 스크립트용)
    settings = get_settings()
    init_engine(settings.database_url)

    result = SeedResult(
        seeded_at=datetime.now(timezone.utc).isoformat(),
    )

    async with get_session_factory()() as session:
        embed_repo = EmbeddingRepository(session)
        embed_service: EmbeddingService | None = (
            EmbeddingService(embed_repo) if not skip_embeddings else None
        )

        # 1. 5 User + Workspace + WorkspaceMember(owner)
        users: dict[str, User] = {}
        workspaces: dict[str, Workspace] = {}
        for persona, cred in creds.items():
            user = await get_or_create_user(session, cred)
            users[persona] = user
            ws = await get_or_create_workspace(session, user, persona)
            workspaces[persona] = ws
            result.personas[persona] = {
                "user_id": str(user.id),
                "clerk_user_id": cred.clerk_user_id,
                "email": cred.email,
                "workspace_id": str(ws.id),
                "workspace_name": ws.name,
                "jwt_expires_at": cred.jwt_expires_at,
            }
            print(f"  ✅ {persona}: user={user.id} ws={ws.id}")

        await session.commit()

        # 2. Sentinel A workspace: 3 projects (public/draft/private) + ProjectMember(creator on private)
        ws_a = workspaces["SENTINEL_A"]
        user_a = users["SENTINEL_A"]
        rag_fixtures: dict[str, Any] = {}
        for visibility in ("public", "draft", "private"):
            fx = await create_project_with_note_and_chunk(
                session, embed_service, embed_repo, ws_a, user_a,
                title=f"{visibility}-project",
                visibility=visibility,
                fixture_key=visibility,
                note_data=RAG_FIXTURE_NOTES[visibility],
                skip_embeddings=skip_embeddings,
            )
            rag_fixtures[visibility] = fx
            print(f"  ✅ Sentinel A {visibility}: project={fx['project_id']} chunk={fx['chunk_id']}")

            # private 프로젝트에 Sentinel A 가 ProjectMember 등록 (creator 자체이지만 명시)
            if visibility == "private":
                pm = ProjectMember(
                    project_id=uuid.UUID(fx["project_id"]),
                    user_id=user_a.id,
                    workspace_id=ws_a.id,
                    role="member",
                )
                session.add(pm)
                await session.flush()
        result.rag_visibility_fixtures = rag_fixtures

        # 3. Sentinel B workspace: cross-tenant-private (Sentinel A 가 접근 시 차단되어야)
        ws_b = workspaces["SENTINEL_B"]
        user_b = users["SENTINEL_B"]
        ct_fx = await create_project_with_note_and_chunk(
            session, embed_service, embed_repo, ws_b, user_b,
            title="cross-tenant-private",
            visibility="private",
            fixture_key="cross_tenant_private",
            note_data=RAG_FIXTURE_NOTES["cross_tenant_private"],
            skip_embeddings=skip_embeddings,
        )
        ct_pm = ProjectMember(
            project_id=uuid.UUID(ct_fx["project_id"]),
            user_id=user_b.id,
            workspace_id=ws_b.id,
            role="member",
        )
        session.add(ct_pm)
        await session.flush()
        result.cross_tenant_fixture = ct_fx
        print(f"  ✅ Sentinel B cross-tenant-private: project={ct_fx['project_id']} chunk={ct_fx['chunk_id']}")

        # 4. Power workspace: 4 projects + 5 notes (bulk export / 단축키 검증)
        ws_power = workspaces["POWER"]
        user_power = users["POWER"]
        power_projects: list[dict[str, Any]] = []
        for pp in POWER_PROJECTS:
            p = Project(
                workspace_id=ws_power.id,
                title=f"{WS_PREFIX} {pp['title']}",
                description=f"{WS_PREFIX} power persona bulk fixture",
                visibility=pp["visibility"],
                created_by_id=user_power.id,
            )
            session.add(p)
            await session.flush()
            power_projects.append({"project_id": str(p.id), "title": p.title, "visibility": pp["visibility"]})
        power_notes: list[dict[str, Any]] = []
        for pn in POWER_NOTES:
            n = Note(
                workspace_id=ws_power.id,
                project_id=None,
                title=f"{WS_PREFIX} {pn['title']}",
                content={"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": pn["content"]}]}]},
                plain_text=pn["content"],
                created_by_id=user_power.id,
            )
            session.add(n)
            await session.flush()
            power_notes.append({"note_id": str(n.id), "title": n.title})
        result.power_fixtures = {"projects": power_projects, "notes": power_notes}
        print(f"  ✅ Power: {len(power_projects)} projects + {len(power_notes)} notes")

        await session.commit()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(
        {
            "qa_run_id": result.qa_run_id,
            "seeded_at": result.seeded_at,
            "personas": result.personas,
            "rag_visibility_fixtures": result.rag_visibility_fixtures,
            "cross_tenant_fixture": result.cross_tenant_fixture,
            "power_fixtures": result.power_fixtures,
        },
        ensure_ascii=False,
        indent=2,
    ))
    print(f"[seed] DONE — fixtures 저장: {out_path}")
    return 0


async def dry_run_cleanup() -> int:
    """삭제 대상 row 카운트만 출력. --cleanup 안전 검증."""
    settings = get_settings()
    init_engine(settings.database_url)
    async with get_session_factory()() as session:
        # Workspace prefix 매칭
        r = await session.execute(
            text("SELECT id, name FROM workspaces WHERE name LIKE :pat"),
            {"pat": f"{WS_PREFIX}%"},
        )
        ws_rows = r.all()
        if not ws_rows:
            print(f"[dry-run-cleanup] 삭제 대상 워크스페이스 0건. 정리할 것 없음.")
            return 0
        ws_ids = [row[0] for row in ws_rows]
        print(f"[dry-run-cleanup] 대상 워크스페이스 {len(ws_rows)}건:")
        for wid, name in ws_rows:
            print(f"  - {wid}  {name}")
        # 관련 row 카운트
        async def count(stmt: str, params: dict) -> int:
            cr = await session.execute(text(stmt), params)
            return cr.scalar_one()
        cnt_chunks = await count("SELECT COUNT(*) FROM embedding_chunks WHERE workspace_id = ANY(:wids)", {"wids": ws_ids})
        cnt_cache = await count("SELECT COUNT(*) FROM semantic_caches WHERE workspace_id = ANY(:wids)", {"wids": ws_ids})
        cnt_pm = await count("SELECT COUNT(*) FROM project_members WHERE workspace_id = ANY(:wids)", {"wids": ws_ids})
        cnt_proj = await count("SELECT COUNT(*) FROM projects WHERE workspace_id = ANY(:wids)", {"wids": ws_ids})
        cnt_notes = await count("SELECT COUNT(*) FROM notes WHERE workspace_id = ANY(:wids)", {"wids": ws_ids})
        cnt_ws_members = await count("SELECT COUNT(*) FROM workspace_members WHERE workspace_id = ANY(:wids)", {"wids": ws_ids})
        print(f"  embedding_chunks: {cnt_chunks}")
        print(f"  semantic_caches: {cnt_cache}")
        print(f"  project_members: {cnt_pm}")
        print(f"  projects: {cnt_proj}")
        print(f"  notes: {cnt_notes}")
        print(f"  workspace_members: {cnt_ws_members}")
        print(f"[dry-run-cleanup] R2 cleanup 별도 — meeting 업로드 시 발생한 R2 object 는 본 스크립트가 추적 못 함")
        return 0


async def cleanup() -> int:
    """qa_run_id 기반 cascade delete (수동 cascade — FK ondelete 미설정).

    안전망 (Codex P0-1 + 12항목 #7):
        1. WS_PREFIX 매칭만 (`WS-QA-...`)
        2. KAIROS_FOUNDER_CLERK_ID 환경변수 설정 시 founder 워크스페이스 매칭 차단
    """
    import os

    founder_clerk_id = os.environ.get("KAIROS_FOUNDER_CLERK_ID", "").strip()
    settings = get_settings()
    init_engine(settings.database_url)
    async with get_session_factory()() as session:
        r = await session.execute(
            text("SELECT id, name, owner_clerk_id FROM workspaces WHERE name LIKE :pat"),
            {"pat": f"{WS_PREFIX}%"},
        )
        ws_rows = r.all()
        if not ws_rows:
            print(f"[cleanup] 삭제 대상 워크스페이스 0건.")
            return 0
        # Founder guard
        if founder_clerk_id:
            overlap = [(wid, name, owner) for wid, name, owner in ws_rows if owner == founder_clerk_id]
            if overlap:
                print(
                    f"[cleanup] ABORT — founder({founder_clerk_id}) 소유 워크스페이스가 매칭됨:",
                    file=sys.stderr,
                )
                for wid, name, owner in overlap:
                    print(f"  - {wid}  {name}  owner={owner}", file=sys.stderr)
                print(
                    "[cleanup] WS_PREFIX 정책 위반 또는 founder 가 QA 시드 실행한 경우. 수동 검토 필요.",
                    file=sys.stderr,
                )
                return 2
        else:
            print("[cleanup] WARN — KAIROS_FOUNDER_CLERK_ID 미설정. founder guard 미적용.")
        ws_ids = [row[0] for row in ws_rows]
        print(f"[cleanup] {len(ws_ids)} 워크스페이스 + 자식 row 삭제 진행...")
        # 자식부터 삭제 (FK 제약)
        for stmt, label in [
            ("DELETE FROM embedding_chunks WHERE workspace_id = ANY(:wids)", "embedding_chunks"),
            ("DELETE FROM semantic_caches WHERE workspace_id = ANY(:wids)", "semantic_caches"),
            ("DELETE FROM project_members WHERE workspace_id = ANY(:wids)", "project_members"),
            ("DELETE FROM notes WHERE workspace_id = ANY(:wids)", "notes"),
            ("DELETE FROM projects WHERE workspace_id = ANY(:wids)", "projects"),
            ("DELETE FROM workspace_members WHERE workspace_id = ANY(:wids)", "workspace_members"),
            ("DELETE FROM workspace_invites WHERE workspace_id = ANY(:wids)", "workspace_invites"),
            ("DELETE FROM workspaces WHERE id = ANY(:wids)", "workspaces"),
        ]:
            res = await session.execute(text(stmt), {"wids": ws_ids})
            print(f"  ✅ {label}: {res.rowcount} row 삭제")
        await session.commit()
        print(f"[cleanup] DONE — User row 는 보존 (Clerk dashboard 에서 직접 삭제 필요)")
        print(f"[cleanup] R2 object 정리는 별도 (meeting 업로드 시 발생한 object 가 있다면 R2 dashboard 수동)")
        return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Multi-Agent QA fixture seed (Sprint 18 → 19)")
    p.add_argument("--env", type=Path, help="seed-credentials.env 경로")
    p.add_argument("--out", type=Path, default=Path("seed-fixtures.json"), help="seed-fixtures.json 출력")
    p.add_argument("--dry-run-cleanup", action="store_true", help="삭제 대상 카운트만")
    p.add_argument("--cleanup", action="store_true", help="qa_run_id 기반 cascade delete")
    p.add_argument("--skip-embeddings", action="store_true", help="OpenAI 호출 회피 (chunk 없이 fixture 만)")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    if args.dry_run_cleanup:
        return asyncio.run(dry_run_cleanup())
    if args.cleanup:
        return asyncio.run(cleanup())
    if args.env is None:
        print("ERROR: --env <seed-credentials.env> 필수 (또는 --dry-run-cleanup / --cleanup)", file=sys.stderr)
        return 2
    return asyncio.run(seed_all(args.env, args.out, args.skip_embeddings))


if __name__ == "__main__":
    raise SystemExit(main())
