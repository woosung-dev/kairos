# apps/backend/src/auth/dependencies.py
"""Auth 의존성 — Depends() 조립의 유일한 위치."""
import hashlib
import logging
import time
import jwt
from fastapi import Depends, Header, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.auth.repository import UserRepository
from src.auth.service import AuthService
from src.common.database import get_async_session

# Sprint 28 BUG-S28-SEC-3 — JWT 검증 실패 forensic logging (stdout 이 유일한 관측 경로).
_auth_logger = logging.getLogger("src.auth.jwt_failure")

# Clerk JWKS 캐시
_jwks_client = None

# Sprint 24 Wave 2 T-BE-PERF Top 1 fix (BUG-MOBILE-005):
# verify_clerk_token 결과(claims) 을 token hash → (claims, expires_at) 으로 in-process 캐시.
# 동일 token 으로 dashboard 4 API 직렬 호출 시 PyJWKClient.get_signing_key_from_jwt +
# jwt.decode 가 매번 RSA 검증을 반복 → 첫 진입 latency 의 일부.
# 캐시 hit 시 dict lookup 만으로 종료 → JWT verify cost 0 화.
# TTL=60s (token 자체 exp 보다 짧게) + maxsize=1000 (LRU 방식 단순 dict + 만료 청소).
_JWT_CLAIMS_CACHE: dict[str, tuple[dict, float]] = {}
_JWT_CACHE_TTL_SEC = 60.0
_JWT_CACHE_MAX_SIZE = 1000


def _token_cache_key(token: str) -> str:
    """token 전체를 캐시 키로 쓰면 메모리 낭비 — sha256 hash 로 32 byte 고정."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# Sprint 28 BUG-S28-PERF-RT-1 fix — User in-process TTL cache (clerk_id → User).
# Round B dynamic verify 결과: find_by_clerk_id 가 매 호출 1.2-4.5s (Neon dev cold start + RTT).
# dashboard 5 endpoint fanout 시 5× SELECT users WHERE clerk_id = 4-22s hidden cost.
# JWT cache 와 동일 패턴 + 동일 TTL 60s. cache hit 시 SELECT 0 → 외부 사용자 매 클릭 sub-ms.
_USER_CACHE: dict[str, tuple[User, float]] = {}
_USER_CACHE_TTL_SEC = 60.0
_USER_CACHE_MAX_SIZE = 1000


def _is_expired_orm_instance(instance: object) -> bool:
    """live ORM 인스턴스가 expire 되어 `id` 속성 접근이 DetachedInstanceError 를 낼 상태인지.

    비 ORM 객체(테스트 mock 등)는 False. rbac 멤버 캐시와 공용.
    """
    from sqlalchemy import inspect as _sa_inspect
    from sqlalchemy.orm.state import InstanceState

    state = _sa_inspect(instance, raiseerr=False)
    if not isinstance(state, InstanceState):
        return False
    return bool(state.expired_attributes) or "id" not in instance.__dict__


def _user_cache_get(clerk_id: str) -> User | None:
    entry = _USER_CACHE.get(clerk_id)
    if entry is None:
        return None
    user, expires_at = entry
    if time.time() >= expires_at:
        _USER_CACHE.pop(clerk_id, None)
        return None
    if _is_expired_orm_instance(user):
        # BUG-CACHE-DETACHED-EXPIRED (2026-07-05): 캐시는 live ORM 인스턴스를 보관하는데,
        # 보관 후 원 세션 수명 이벤트(rollback 등)로 인스턴스가 expire+detach 되면 이후
        # 모든 요청의 속성 접근이 DetachedInstanceError → 500 연쇄. miss 처리로 자가치유.
        logging.getLogger(__name__).warning(
            "user cache 에 expired-detached 인스턴스 감지 — drop (clerk_id=%s)", clerk_id
        )
        _USER_CACHE.pop(clerk_id, None)
        return None
    return user


def _user_cache_set(clerk_id: str, user: User) -> None:
    now = time.time()
    if len(_USER_CACHE) >= _USER_CACHE_MAX_SIZE:
        expired = [k for k, (_, exp) in _USER_CACHE.items() if exp <= now]
        for k in expired:
            _USER_CACHE.pop(k, None)
        if len(_USER_CACHE) >= _USER_CACHE_MAX_SIZE:
            oldest = next(iter(_USER_CACHE))
            _USER_CACHE.pop(oldest, None)
    _USER_CACHE[clerk_id] = (user, now + _USER_CACHE_TTL_SEC)


def invalidate_user_cache(clerk_id: str) -> None:
    """User cache 강제 invalidate — onboarding step 증가 직후 호출 권고 (60s 지연 회피)."""
    _USER_CACHE.pop(clerk_id, None)


def _jwt_cache_get(key: str) -> dict | None:
    """캐시 lookup — 만료 시 evict."""
    entry = _JWT_CLAIMS_CACHE.get(key)
    if entry is None:
        return None
    claims, expires_at = entry
    if time.time() >= expires_at:
        _JWT_CLAIMS_CACHE.pop(key, None)
        return None
    return claims


def _jwt_cache_set(key: str, claims: dict, token_exp: float | None = None) -> None:
    """캐시 저장 — maxsize 초과 시 가장 오래된 만료 항목부터 정리.

    Codex F-1 fix (Sprint 24 Wave 2 P1): cache expiry 를 min(60s, token.exp - now) 로 제한.
    token 이 60s 안에 만료되면 그 exp 가 cache TTL 의 상한. expired 토큰이 cache hit 통과 위험 회피.
    token_exp 누락 시 보수적으로 60s 미만 (50s) 적용 (caller 가 exp 안 보낸 경우 fallback).
    """
    now = time.time()
    if len(_JWT_CLAIMS_CACHE) >= _JWT_CACHE_MAX_SIZE:
        # 단순 청소: 만료된 것 먼저 제거, 모두 살아있으면 가장 오래된 1개 evict
        expired = [k for k, (_, exp) in _JWT_CLAIMS_CACHE.items() if exp <= now]
        for k in expired:
            _JWT_CLAIMS_CACHE.pop(k, None)
        if len(_JWT_CLAIMS_CACHE) >= _JWT_CACHE_MAX_SIZE:
            # FIFO 1개 제거
            oldest = next(iter(_JWT_CLAIMS_CACHE))
            _JWT_CLAIMS_CACHE.pop(oldest, None)

    # Codex F-1: cache TTL ≤ token exp 보장
    cache_ttl = _JWT_CACHE_TTL_SEC
    if token_exp is not None:
        ttl_until_token_exp = token_exp - now
        if ttl_until_token_exp <= 0:
            # 이미 만료된 token — cache 저장 skip
            return
        cache_ttl = min(_JWT_CACHE_TTL_SEC, ttl_until_token_exp)
    _JWT_CLAIMS_CACHE[key] = (claims, now + cache_ttl)


def _get_jwks_client():
    """Clerk JWKS 클라이언트를 가져온다 (싱글톤).

    Sprint 27e BUG-S27e-SEC-3 — Clerk issuer URL 을 settings 기반으로 분리.
      이전: 하드코드 dev URL → ADR-024 Clerk Production cutover 시 swap 결손 risk.
      이후: settings.clerk_jwt_issuer + "/.well-known/jwks.json" — production env 로 override.

    cache_keys=True (Sprint 24 Wave 2 T-BE-PERF, low-risk 보강).
    """
    global _jwks_client
    if _jwks_client is None:
        from src.core.config import get_settings
        settings = get_settings()
        _jwks_client = jwt.PyJWKClient(
            f"{settings.clerk_jwt_issuer}/.well-known/jwks.json",
            cache_keys=True,
        )
    return _jwks_client


async def verify_clerk_token(authorization: str = Header(default="")) -> dict:
    """Clerk JWT 검증. Bearer 토큰에서 클레임 추출.

    T-BE-PERF Top 1 fix: in-process TTL cache (60s) 로 동일 token 재검증 cost 제거.
    캐시 hit 시 PyJWKClient + jwt.decode 우회 → dict lookup 만 (sub-ms).
    캐시 miss 시 원본 흐름 그대로 + 결과 저장.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증이 필요합니다")

    token = authorization.removeprefix("Bearer ")
    cache_key = _token_cache_key(token)

    # 캐시 hit — JWT 검증 우회 (TTL 안에서 동일 token 재사용)
    cached = _jwt_cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        from src.core.config import get_settings
        settings = get_settings()
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        # Sprint 27e BUG-S27e-SEC-3 — issuer 검증 명시 + audience 명시 (None 이면 PyJWT 가 skip).
        # 이전: options={"verify_aud": False} + issuer 미전달 → cross-account JWT 통과 risk.
        # 이후: 환경별 issuer 강제 + audience 일치 검증 (audience 미설정 시 PyJWT default).
        decode_kwargs: dict = {
            "algorithms": ["RS256"],
            "issuer": settings.clerk_jwt_issuer,
            # Sprint 27e Post-Merge BUG-QA-2 — Clerk dev JWT exp = 60s + FE Clerk SDK
            # 의 stale token cache 결합으로 페이지 전환 시 401 다발. 10s clock skew
            # 허용으로 short window 통과 — 정상 사용자 UX 회복.
            # production 에선 token exp 가 더 길어 leeway 영향 마이크로.
            "leeway": 10,
        }
        if settings.clerk_jwt_audience is not None:
            decode_kwargs["audience"] = settings.clerk_jwt_audience
        else:
            # Clerk JWT Template 미설정 환경 — audience claim 자체 검증은 skip
            decode_kwargs["options"] = {"verify_aud": False}
        claims = jwt.decode(token, signing_key.key, **decode_kwargs)
        # Clerk JWT의 sub 클레임 = Clerk 사용자 ID
        result = {"sub": claims["sub"]}
        # Sprint 29 R1 (auth-claim): name/email claim 보존. 이전엔 sub 만 남겨 lazy seed
        # (get_current_user)의 claims.get("name"/"email") 이 항상 fallback("사용자"/"")로
        # 동작 → 신규 user 이름/이메일 누락. JWT 에 해당 claim 이 있으면 사용, 없으면 caller
        # 의 fallback 유지(현 동작 보존). claim 노출은 Clerk JWT Template 설정에 의존(외부).
        for optional_key in ("name", "email"):
            if optional_key in claims:
                result[optional_key] = claims[optional_key]
        # Codex F-1 fix: token exp 를 cache TTL 상한으로 (만료된 token cache hit 차단)
        _jwt_cache_set(cache_key, result, token_exp=claims.get("exp"))
        return result
    except jwt.ExpiredSignatureError:
        _auth_logger.warning("jwt_expired", extra={"error_type": "ExpiredSignatureError"})
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다")
    except jwt.InvalidIssuerError:
        # Sprint 27e BUG-S27e-SEC-3 — issuer mismatch 명시 분리 (forensic).
        _auth_logger.warning("jwt_invalid_issuer", extra={"error_type": "InvalidIssuerError"})
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰 발급자입니다")
    except jwt.InvalidAudienceError:
        _auth_logger.warning("jwt_invalid_audience", extra={"error_type": "InvalidAudienceError"})
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰 대상입니다")
    except jwt.InvalidTokenError as _e:
        _auth_logger.warning("jwt_invalid_token", extra={"error_type": type(_e).__name__})
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    except Exception as _e:
        _auth_logger.warning("jwt_verify_unexpected_error", extra={"error_type": type(_e).__name__})
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
    from sqlmodel import text as _text

    # Sprint 28 BUG-S28-PERF-RT-1 fix — User in-process TTL cache (clerk_id → User, 60s).
    # JWT cache 와 동일 패턴 + 동일 TTL. Neon dev cold start + RTT 1.2-4.5s 의 hidden cost
    # 가 dashboard 5 endpoint fanout 시 5× = 6-22s 잠재 (실측 4286ms critical path).
    # cache hit 시 SELECT 1번도 SKIP → fast path 보다 더 빨라짐 (DB query 0).
    # 60s 안 onboarding_step 갱신은 cache TTL 만료 후 반영 (acceptable, hook 자체는 동기 DB write).
    clerk_id = claims["sub"]
    cached_user = _user_cache_get(clerk_id)
    if cached_user is not None:
        return cached_user

    repo = UserRepository(session)
    user = await repo.find_by_clerk_id(clerk_id)

    # Sprint 27e Post-Merge BUG-QA-1 fast path — 이미 onboarding_step >= 1 (lazy seed 완료)
    # 사용자는 매 request lazy seed SKIP (workspace + member + onboarding hook).
    # dashboard 첫 진입 5 endpoint fanout 시 BE call 5건 × ~1.5s = 7.5s 의 hidden cost 해소.
    # 신규 user / step=0 (lazy seed 미완료) 는 기존 경로로 fall-through.
    if user is not None and user.onboarding_step >= 1:
        # Sprint 28 — User cache 저장 (fast path 도달 시점에만 — onboarding 완료 user 한정).
        _user_cache_set(clerk_id, user)
        return user

    is_new_user = user is None
    if user is None:
        # 첫 로그인: race-safe lazy seed (ON CONFLICT, workspace INSERT 패턴 정합)
        # FE 가 dashboard 첫 진입 시 5+ API 동시 호출 → 각 transaction 의 User INSERT 동시 시도
        # → UniqueViolation `ix_users_clerk_id` race → 500. Sprint 27c audit P0-S27c-1 fix.
        await session.execute(
            _text(
                """
                INSERT INTO users (id, clerk_id, display_name, email, created_at, updated_at, onboarding_step)
                VALUES (gen_random_uuid(), :clerk_id, :name, :email, now(), now(), 0)
                ON CONFLICT (clerk_id) DO NOTHING
                """
            ),
            {
                "clerk_id": claims["sub"],
                "name": claims.get("name", "사용자"),
                "email": claims.get("email", ""),
            },
        )
        # Re-fetch after race-safe INSERT — one row guaranteed (this tx or concurrent winner)
        user = await repo.find_by_clerk_id(claims["sub"])
        if user is None:
            # 극단적 DB 일관성 issue — race 모두 fail. graceful 401 으로 사용자 재시도 유도
            raise HTTPException(status_code=500, detail="사용자 초기화에 실패했습니다")

    # Personal workspace lazy seed — 신규 user / 기존 user backfill 안전망
    # ON CONFLICT는 partial unique index `uq_workspaces_owner_personal` 사용
    # PostgreSQL 제약: partial unique index는 named constraint로 ON CONFLICT 참조 불가
    # -> index_predicate 형식 (column + WHERE) 으로 명시
    await session.execute(
        _text(
            """
            INSERT INTO workspaces (id, owner_id, name, type, inbox_threshold, created_at, updated_at)
            VALUES (gen_random_uuid(), :owner_id, :name, 'personal', 0.9, now(), now())
            ON CONFLICT (owner_id) WHERE type = 'personal' DO NOTHING
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
    # Sprint 22 OBN-02: personal workspace lazy seed 완료 시 onboarding step=1
    # is_new_user 여부 무관 — idempotent (step >= 1 이면 UPDATE no-op).
    # commit 이전 위치 — 같은 transaction 으로 atomicity 보장.
    # graceful: hook 실패 시도 lazy seed / auth 전체 흐름은 영향 받지 않음
    # (CI E2E fail 학습 — entire request fail 차단).
    try:
        from src.onboarding.service import OnboardingService
        onboarding = OnboardingService(session)
        await onboarding.increment_step(user.id, 1)
    except Exception as ob_err:
        import logging
        logging.getLogger(__name__).warning(
            "onboarding step=1 advance 실패 (비치명적, lazy seed 보존): %s", ob_err
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
