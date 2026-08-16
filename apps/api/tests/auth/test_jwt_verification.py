# JWT 검증 회귀 가드 — ADR-031 (Better Auth JWKS)
"""`auth/dependencies.py:verify_bearer_token` 을 **실서명 토큰**으로 관통 검증한다.

전환 전 이 파일은 `jwt.decode` 를 mock 해서 "decode 에 어떤 인자가 넘어갔는가" 만 봤다.
그건 서명이 실제로 검증되는지, 알고리즘이 맞는지를 증명하지 못한다. 지금은
`tests/auth/conftest.py` 의 실서명 하네스로 EdDSA/ES256/RS256 3종을 매번 관통시킨다.

승계한 가드 (Sprint 27e BUG-S27e-SEC-3):
  - issuer 는 항상 강제 검증된다 (cross-issuer 토큰 통과 차단)
  - audience 는 설정 시 강제, 미설정 시에만 skip
"""
import time

import pytest
from fastapi import HTTPException

from tests.auth.conftest import TEST_AUDIENCE, TEST_ISSUER


@pytest.mark.asyncio
async def test_valid_token_passes(auth_env, signing):
    """정상 서명 + issuer/audience 일치 → 클레임 반환."""
    auth_env(AUTH_JWT_AUDIENCE=TEST_AUDIENCE, AUTH_JWT_ALGORITHMS=signing.alg)
    signing.install()
    from src.auth import dependencies as deps

    token = signing.make_token(sub="ba_user_ok", name="테스터", email="ok@kairos.test")
    claims = await deps.verify_bearer_token(authorization=f"Bearer {token}")

    assert claims["sub"] == "ba_user_ok"
    assert claims["name"] == "테스터"
    assert claims["email"] == "ok@kairos.test"


@pytest.mark.asyncio
async def test_algorithm_must_be_allowlisted(auth_env, signing):
    """설정된 허용 목록에 없는 알고리즘으로 서명된 토큰은 거부된다.

    헤더의 `alg` 를 신뢰하면 alg confusion 공격의 진입점이 된다. 허용 목록을 실제로
    강제하는지 — 즉 `algorithms=` 인자가 살아 있는지 — 를 서명 자체로 확인한다.
    """
    other_alg = "ES256" if signing.alg != "ES256" else "RS256"
    auth_env(AUTH_JWT_AUDIENCE=TEST_AUDIENCE, AUTH_JWT_ALGORITHMS=other_alg)
    signing.install()
    from src.auth import dependencies as deps

    token = signing.make_token()
    with pytest.raises(HTTPException) as exc:
        await deps.verify_bearer_token(authorization=f"Bearer {token}")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_wrong_issuer_rejected(auth_env, signing):
    """다른 발급자가 서명한 토큰은 401 + '발급자' 메시지."""
    auth_env(AUTH_JWT_AUDIENCE=TEST_AUDIENCE, AUTH_JWT_ALGORITHMS=signing.alg)
    signing.install()
    from src.auth import dependencies as deps

    token = signing.make_token(issuer="https://evil.example.com")
    with pytest.raises(HTTPException) as exc:
        await deps.verify_bearer_token(authorization=f"Bearer {token}")
    assert exc.value.status_code == 401
    assert "발급자" in exc.value.detail


@pytest.mark.asyncio
async def test_wrong_audience_rejected(auth_env, signing):
    """audience 가 설정돼 있으면 불일치 토큰은 401 + '대상' 메시지."""
    auth_env(AUTH_JWT_AUDIENCE=TEST_AUDIENCE, AUTH_JWT_ALGORITHMS=signing.alg)
    signing.install()
    from src.auth import dependencies as deps

    token = signing.make_token(audience="https://other-app.example.com")
    with pytest.raises(HTTPException) as exc:
        await deps.verify_bearer_token(authorization=f"Bearer {token}")
    assert exc.value.status_code == 401
    assert "대상" in exc.value.detail


@pytest.mark.asyncio
async def test_audience_skipped_when_unset(auth_env, signing):
    """audience 미설정(dev) 이면 aud 검증을 skip 한다 — non-dev 는 config validator 가 막는다."""
    auth_env(AUTH_JWT_ALGORITHMS=signing.alg)
    signing.install()
    from src.auth import dependencies as deps

    token = signing.make_token(sub="ba_user_no_aud", audience="anything-at-all")
    claims = await deps.verify_bearer_token(authorization=f"Bearer {token}")
    assert claims["sub"] == "ba_user_no_aud"


@pytest.mark.asyncio
async def test_expired_token_rejected(auth_env, signing):
    """만료된 토큰은 401 + '만료' 메시지. leeway 5s 보다 확실히 크게 만든다."""
    auth_env(AUTH_JWT_AUDIENCE=TEST_AUDIENCE, AUTH_JWT_ALGORITHMS=signing.alg)
    signing.install()
    from src.auth import dependencies as deps

    token = signing.make_token(expires_in=-60)
    with pytest.raises(HTTPException) as exc:
        await deps.verify_bearer_token(authorization=f"Bearer {token}")
    assert exc.value.status_code == 401
    assert "만료" in exc.value.detail


@pytest.mark.asyncio
async def test_tampered_signature_rejected(auth_env, signing):
    """페이로드를 바꿔치기한 토큰은 서명 불일치로 401.

    ★이 테스트가 mock 기반 구성에서는 **원리적으로 불가능**했다.
      서명을 실제로 검증한다는 사실 자체의 유일한 증거다.
    """
    auth_env(AUTH_JWT_AUDIENCE=TEST_AUDIENCE, AUTH_JWT_ALGORITHMS=signing.alg)
    signing.install()
    from src.auth import dependencies as deps

    victim = signing.make_token(sub="ba_user_victim")
    attacker = signing.make_token(sub="ba_user_attacker")
    # victim 의 서명에 attacker 의 페이로드를 붙인다.
    forged = f"{attacker.split('.')[0]}.{attacker.split('.')[1]}.{victim.split('.')[2]}"

    with pytest.raises(HTTPException) as exc:
        await deps.verify_bearer_token(authorization=f"Bearer {forged}")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_issuer_and_jwks_url_are_independent(auth_env, signing):
    """JWKS URL 이 issuer 와 다른 호스트여도 검증이 성립한다.

    prod 구성(issuer=공개 URL, JWKS=compose 내부망)의 회귀 가드다. 예전처럼
    `issuer + "/.well-known/jwks.json"` 으로 조립하면 이 구성이 성립하지 않는다.
    """
    auth_env(
        AUTH_JWT_AUDIENCE=TEST_AUDIENCE,
        AUTH_JWT_ALGORITHMS=signing.alg,
        AUTH_JWKS_URL="http://web:3000/api/auth/jwks",
    )
    signing.install()
    from src.auth import dependencies as deps
    from src.core.config import get_settings

    settings = get_settings()
    assert settings.auth_jwt_issuer == TEST_ISSUER
    assert settings.auth_jwks_url == "http://web:3000/api/auth/jwks"

    token = signing.make_token(sub="ba_user_split_host")
    claims = await deps.verify_bearer_token(authorization=f"Bearer {token}")
    assert claims["sub"] == "ba_user_split_host"


@pytest.mark.asyncio
async def test_missing_bearer_prefix_rejected(auth_env, signing):
    """Authorization 헤더가 없거나 Bearer 가 아니면 서명 검증 전에 401."""
    auth_env(AUTH_JWT_ALGORITHMS=signing.alg)
    signing.install()
    from src.auth import dependencies as deps

    for header in ("", "Basic abc", signing.make_token()):
        with pytest.raises(HTTPException) as exc:
            await deps.verify_bearer_token(authorization=header)
        assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_claims_cached_within_ttl(auth_env, signing):
    """동일 토큰 재검증은 캐시에서 나온다 — JWKS 조회가 다시 일어나지 않는다."""
    auth_env(AUTH_JWT_AUDIENCE=TEST_AUDIENCE, AUTH_JWT_ALGORITHMS=signing.alg)
    signing.install()
    from src.auth import dependencies as deps

    token = signing.make_token(sub="ba_user_cached")
    first = await deps.verify_bearer_token(authorization=f"Bearer {token}")

    # JWKS 대역을 끊어도 캐시 hit 이면 통과해야 한다.
    def _boom():
        raise AssertionError("캐시 hit 이어야 하는데 JWKS 를 다시 조회했다")

    deps._get_jwks_client = _boom  # type: ignore[assignment]
    second = await deps.verify_bearer_token(authorization=f"Bearer {token}")
    assert first == second

    # 캐시 TTL 은 token exp 를 넘지 못한다 (Codex F-1 가드).
    cached_entry = deps._JWT_CLAIMS_CACHE[deps._token_cache_key(token)]
    assert cached_entry[1] <= time.time() + deps._JWT_CACHE_TTL_SEC + 1
