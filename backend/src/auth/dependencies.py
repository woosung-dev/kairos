# backend/src/auth/dependencies.py
"""Auth 의존성 — Depends() 조립의 유일한 위치."""
import jwt
import httpx
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.repository import UserRepository
from src.auth.service import AuthService
from src.common.database import get_async_session
from src.core.config import get_settings

# Clerk JWKS 캐시
_jwks_client = None


def _get_jwks_client():
    """Clerk JWKS 클라이언트를 가져온다 (싱글톤)."""
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        # Clerk publishable key에서 도메인 추출
        # pk_test_xxx → Clerk 대시보드의 JWKS URL 사용
        clerk_secret = settings.clerk_secret_key.get_secret_value()
        # Clerk의 JWKS URL: https://<clerk-domain>/.well-known/jwks.json
        # clerk_secret_key에서 도메인을 직접 가져올 수 없으므로
        # Clerk Frontend API에서 JWKS를 가져옴
        _jwks_client = jwt.PyJWKClient(
            "https://creative-boxer-79.clerk.accounts.dev/.well-known/jwks.json"
        )
    return _jwks_client


async def verify_clerk_token(authorization: str = Header(default="")) -> dict:
    """Clerk JWT 검증. Bearer 토큰에서 클레임 추출."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증이 필요합니다")

    token = authorization.removeprefix("Bearer ")

    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        # Clerk JWT의 sub 클레임 = Clerk 사용자 ID
        return {"sub": claims["sub"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    except Exception:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")


async def get_user_by_clerk_id(
    clerk_id: str,
    session: AsyncSession,
) -> User:
    """Clerk ID로 DB 사용자 조회."""
    repo = UserRepository(session)
    user = await repo.find_by_clerk_id(clerk_id)
    if user is None:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    return user


async def get_current_user(
    claims: dict = Depends(verify_clerk_token),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """현재 인증된 사용자를 반환. 없으면 자동 생성 (첫 로그인).

    Sprint 15 — 첫 로그인 시 personal workspace + WorkspaceMember(owner) lazy seed.
    동시 요청 race 대응: ON CONFLICT DO NOTHING (A9 fix, patch §8 P-R5).
    UNIQUE partial index `uq_workspaces_owner_personal` (postgresql_where=`type='personal'`)는
    R2 migration에서 사전 생성됨.
    """
    from sqlalchemy import text as _text

    repo = UserRepository(session)
    user = await repo.find_by_clerk_id(claims["sub"])
    is_new_user = user is None
    if user is None:
        # 첫 로그인: 자동 생성
        user = User(
            clerk_id=claims["sub"],
            display_name=claims.get("name", "사용자"),
            email=claims.get("email", ""),
        )
        user = await repo.save(user)
        await repo.commit()

    # Personal workspace lazy seed — 신규 user / 기존 user backfill 안전망
    # ON CONFLICT는 partial unique index `uq_workspaces_owner_personal` 사용
    await session.execute(
        _text(
            """
            INSERT INTO workspaces (id, owner_id, name, type, inbox_threshold, created_at, updated_at)
            VALUES (gen_random_uuid(), :owner_id, :name, 'personal', 0.9, now(), now())
            ON CONFLICT ON CONSTRAINT uq_workspaces_owner_personal DO NOTHING
            """
        ),
        {"owner_id": str(user.id), "name": f"{user.display_name}의 개인 Kairos"},
    )
    # WorkspaceMember(owner) seed — 동일 user 다중 personal-ws 방지된 상태에서 멤버십만 보장
    await session.execute(
        _text(
            """
            INSERT INTO workspace_members (id, workspace_id, user_id, role)
            SELECT gen_random_uuid(), w.id, w.owner_id, 'owner'
            FROM workspaces w
            WHERE w.owner_id = :owner_id AND w.type = 'personal'
              AND NOT EXISTS (
                SELECT 1 FROM workspace_members m
                WHERE m.workspace_id = w.id AND m.user_id = w.owner_id
              )
            """
        ),
        {"owner_id": str(user.id)},
    )
    if is_new_user:
        await session.commit()
    else:
        # 기존 user request 흐름에서는 commit을 짧게 — race 영향 최소화
        await session.commit()
    return user


async def get_auth_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    return UserRepository(session)


async def get_auth_service(
    repo: UserRepository = Depends(get_auth_repository),
) -> AuthService:
    return AuthService(repo)
