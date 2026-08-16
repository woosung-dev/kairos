# apps/api/src/auth/dependencies.py
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

# JWKS 클라이언트 싱글톤 (Better Auth `/api/auth/jwks`)
_jwks_client = None

# Sprint 24 Wave 2 T-BE-PERF Top 1 fix (BUG-MOBILE-005):
# verify_bearer_token 결과(claims) 을 token hash → (claims, expires_at) 으로 in-process 캐시.
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


# Sprint 28 BUG-S28-PERF-RT-1 fix — User in-process TTL cache (auth_user_id → User).
# Round B dynamic verify 결과: 조회가 매 호출 1.2-4.5s (당시 Neon cold start + RTT).
# dashboard 5 endpoint fanout 시 5× SELECT users = 4-22s hidden cost.
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


def _user_cache_get(auth_user_id: str) -> User | None:
    entry = _USER_CACHE.get(auth_user_id)
    if entry is None:
        return None
    user, expires_at = entry
    if time.time() >= expires_at:
        _USER_CACHE.pop(auth_user_id, None)
        return None
    if _is_expired_orm_instance(user):
        # BUG-CACHE-DETACHED-EXPIRED (2026-07-05): 캐시는 live ORM 인스턴스를 보관하는데,
        # 보관 후 원 세션 수명 이벤트(rollback 등)로 인스턴스가 expire+detach 되면 이후
        # 모든 요청의 속성 접근이 DetachedInstanceError → 500 연쇄. miss 처리로 자가치유.
        logging.getLogger(__name__).warning(
            "user cache 에 expired-detached 인스턴스 감지 — drop (auth_user_id=%s)",
            auth_user_id,
        )
        _USER_CACHE.pop(auth_user_id, None)
        return None
    return user


def _user_cache_set(auth_user_id: str, user: User) -> None:
    now = time.time()
    if len(_USER_CACHE) >= _USER_CACHE_MAX_SIZE:
        expired = [k for k, (_, exp) in _USER_CACHE.items() if exp <= now]
        for k in expired:
            _USER_CACHE.pop(k, None)
        if len(_USER_CACHE) >= _USER_CACHE_MAX_SIZE:
            oldest = next(iter(_USER_CACHE))
            _USER_CACHE.pop(oldest, None)
    _USER_CACHE[auth_user_id] = (user, now + _USER_CACHE_TTL_SEC)


def invalidate_user_cache(auth_user_id: str) -> None:
    """User cache 강제 invalidate — onboarding step 증가 직후 호출 권고 (60s 지연 회피)."""
    _USER_CACHE.pop(auth_user_id, None)


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
    """JWKS 클라이언트를 가져온다 (싱글톤).

    ADR-031 — Better Auth jwt 플러그인이 `{baseURL}/api/auth/jwks` 로 공개키를 노출한다.

    ★URL 을 issuer 에서 조립하지 않는다. 이전에는 `issuer + "/.well-known/jwks.json"` 으로
      합성해 둘이 하드 결합돼 있었다. 분리하면 prod 에서 issuer 는 공개 URL 로 두고 JWKS 만
      compose 내부망(`http://web:3000/api/auth/jwks`)에서 가져올 수 있다 — 인증 경로에서
      Cloudflare Tunnel 왕복이 빠진다.

    cache_keys=True (Sprint 24 Wave 2 T-BE-PERF, low-risk 보강).
    """
    global _jwks_client
    if _jwks_client is None:
        from src.core.config import get_settings
        settings = get_settings()
        _jwks_client = jwt.PyJWKClient(settings.auth_jwks_url, cache_keys=True)
    return _jwks_client


def reset_jwks_client() -> None:
    """싱글톤 JWKS 클라이언트를 버린다.

    settings 를 갈아끼우는 테스트에서만 쓴다 — 런타임 코드는 호출하지 않는다.
    (`_jwks_client` 는 프로세스 수명 동안 유지되는 것이 정상 동작이다.)
    """
    global _jwks_client
    _jwks_client = None


async def verify_bearer_token(authorization: str = Header(default="")) -> dict:
    """Better Auth 가 발급한 JWT 검증. Bearer 토큰에서 클레임 추출.

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
        # issuer 검증 명시 + audience 명시 (None 이면 PyJWT 가 skip) — 27e SEC-3 가드 승계.
        # ★algorithms 는 반드시 허용 목록이어야 한다. 토큰 헤더의 alg 를 신뢰하면
        #   alg confusion 공격의 정석 진입점이 된다.
        decode_kwargs: dict = {
            "algorithms": [
                item.strip()
                for item in settings.auth_jwt_algorithms.split(",")
                if item.strip()
            ],
            "issuer": settings.auth_jwt_issuer,
            # clock skew 만 허용한다. 이전의 leeway=10 은 Clerk dev JWT 의 exp=60s 와 FE SDK
            # stale cache 가 겹쳐 나던 401 다발을 막으려던 것이고, Better Auth 기본 exp 는
            # 15분이라 그 압력이 사라졌다. 그래도 서버 간 시계 오차는 남으므로 0 은 아니다.
            "leeway": 5,
        }
        if settings.auth_jwt_audience is not None:
            decode_kwargs["audience"] = settings.auth_jwt_audience
        else:
            # dev 편의 — non-dev 에서는 config validator 가 None 을 거부한다.
            decode_kwargs["options"] = {"verify_aud": False}
        claims = jwt.decode(token, signing_key.key, **decode_kwargs)
        # sub = Better Auth 의 auth_user.id (users.auth_user_id 와 조인되는 키)
        result = {"sub": claims["sub"]}
        # name/email claim 보존 (Sprint 29 R1). lazy seed 가 신규 User 의 이름·이메일을
        # 여기서 받는다 — 없으면 caller 의 fallback("사용자"/"")이 그대로 쓰인다.
        # Better Auth 쪽 노출은 `apps/web/src/lib/auth.ts` 의 jwt.definePayload 소관이다.
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


async def get_user_by_auth_user_id(
    auth_user_id: str,
    session: AsyncSession,
) -> User:
    """외부 인증 ID(Better Auth auth_user.id)로 DB 사용자 조회."""
    repo = UserRepository(session)
    user = await repo.find_by_auth_user_id(auth_user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    return user


async def get_current_user(
    claims: dict = Depends(verify_bearer_token),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """현재 인증된 사용자를 반환. 없으면 자동 생성 (첫 로그인).

    Sprint 15 — 첫 로그인 시 personal workspace + WorkspaceMember(owner) lazy seed.
    동시 요청 race 대응: ON CONFLICT DO NOTHING (A9 fix, patch §8 P-R5).
    UNIQUE partial index `uq_workspaces_owner_personal` (postgresql_where=`type='personal'`)는
    R2 migration에서 사전 생성됨.
    """
    from sqlmodel import text as _text

    # Sprint 28 BUG-S28-PERF-RT-1 fix — User in-process TTL cache (auth_user_id → User, 60s).
    # JWT cache 와 동일 패턴 + 동일 TTL. Neon dev cold start + RTT 1.2-4.5s 의 hidden cost
    # 가 dashboard 5 endpoint fanout 시 5× = 6-22s 잠재 (실측 4286ms critical path).
    # cache hit 시 SELECT 1번도 SKIP → fast path 보다 더 빨라짐 (DB query 0).
    # 60s 안 onboarding_step 갱신은 cache TTL 만료 후 반영 (acceptable, hook 자체는 동기 DB write).
    auth_user_id = claims["sub"]
    cached_user = _user_cache_get(auth_user_id)
    if cached_user is not None:
        return cached_user

    repo = UserRepository(session)
    user = await repo.find_by_auth_user_id(auth_user_id)

    # Sprint 27e Post-Merge BUG-QA-1 fast path — 이미 onboarding_step >= 1 (lazy seed 완료)
    # 사용자는 매 request lazy seed SKIP (workspace + member + onboarding hook).
    # dashboard 첫 진입 5 endpoint fanout 시 BE call 5건 × ~1.5s = 7.5s 의 hidden cost 해소.
    # 신규 user / step=0 (lazy seed 미완료) 는 기존 경로로 fall-through.
    if user is not None and user.onboarding_step >= 1:
        # Sprint 28 — User cache 저장 (fast path 도달 시점에만 — onboarding 완료 user 한정).
        _user_cache_set(auth_user_id, user)
        return user

    is_new_user = user is None
    if user is None:
        # 첫 로그인: race-safe lazy seed (ON CONFLICT, workspace INSERT 패턴 정합)
        # FE 가 dashboard 첫 진입 시 5+ API 동시 호출 → 각 transaction 의 User INSERT 동시 시도
        # → UniqueViolation `ix_users_auth_user_id` race → 500. Sprint 27c audit P0-S27c-1 fix.
        # ★ON CONFLICT 는 index inference 로 `ix_users_auth_user_id` 를 찾는다 —
        #   alembic 리비전 c1a7e0b5d3f2 의 인덱스 이름/컬럼과 한 쌍이다.
        await session.execute(
            _text(
                """
                INSERT INTO users (id, auth_user_id, display_name, email, created_at, updated_at, onboarding_step)
                VALUES (gen_random_uuid(), :auth_user_id, :name, :email, now(), now(), 0)
                ON CONFLICT (auth_user_id) DO NOTHING
                """
            ),
            {
                "auth_user_id": auth_user_id,
                "name": claims.get("name", "사용자"),
                "email": claims.get("email", ""),
            },
        )
        # Re-fetch after race-safe INSERT — one row guaranteed (this tx or concurrent winner)
        user = await repo.find_by_auth_user_id(auth_user_id)
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
