# 실서명 JWT 하네스 — ADR-031
"""auth 테스트가 **진짜로 서명된 토큰**을 검증하게 하는 fixture 모음.

왜 필요한가: 전환 전 `tests/auth/` 는 `jwt.decode` 를 통째로 mock 해서, 서명 알고리즘을
바꿔도 전부 green 이었다. 그 상태에서 RS256 → EdDSA 로 갈아타면 깨져도 CI 가 못 잡는다.

여기서는 `jwt.decode` 를 mock 하지 않는다. 실제 키로 서명하고 실제 공개키로 검증한다.
알고리즘을 파라미터화해 두었으므로, 나중에 `AUTH_JWT_ALGORITHMS` 를 뒤집는 결정이
"테스트가 이미 증명한 선택지 중 하나 고르기" 가 된다.

`scripts/sprint24_wave2_perf_spike.py` 의 self-signed JWT 기법을 재사용 가능한 형태로 승격한 것이다.
"""
import time
import uuid
from typing import Any, Callable

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from jwt.algorithms import ECAlgorithm, OKPAlgorithm, RSAAlgorithm

# Better Auth jwt 플러그인의 기본값은 EdDSA(Ed25519)다. 나머지 둘은 `jwks.keyPairConfig.alg`
# 로 갈아탈 수 있는 선택지 — 폴백 경로도 살아 있음을 매 CI 에서 증명한다.
SUPPORTED_ALGORITHMS = ["EdDSA", "ES256", "RS256"]

TEST_ISSUER = "https://auth.test.kairos"
TEST_AUDIENCE = "https://auth.test.kairos"
TEST_JWKS_URL = "https://auth.test.kairos/api/auth/jwks"


def _generate_keypair(algorithm: str) -> tuple[Any, dict[str, Any]]:
    """(개인키, 공개키 JWK dict) 를 돌려준다.

    JWK 변환을 여기서 끝내는 이유 — 알고리즘별 키 타입과 `to_jwk` 오버로드는 런타임에는
    짝이 맞지만 호출부로 들고 나가면 union 이 되어 정적 타입이 어느 오버로드도 못 고른다.
    """
    if algorithm == "EdDSA":
        ed_key = ed25519.Ed25519PrivateKey.generate()
        return ed_key, OKPAlgorithm.to_jwk(ed_key.public_key(), as_dict=True)
    if algorithm == "ES256":
        ec_key = ec.generate_private_key(ec.SECP256R1())
        return ec_key, ECAlgorithm.to_jwk(ec_key.public_key(), as_dict=True)
    if algorithm == "RS256":
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        return rsa_key, RSAAlgorithm.to_jwk(rsa_key.public_key(), as_dict=True)
    raise AssertionError(f"지원하지 않는 알고리즘: {algorithm}")


class _LocalJWKClient:
    """PyJWKClient 대역 — 네트워크 대신 로컬 공개키를 돌려준다.

    `PyJWK` 를 그대로 반환하므로 호출부(`jwt.decode(token, signing_key.key, ...)`)의
    서명 검증 경로는 프로덕션과 동일하다. 바꿔치기하는 것은 "키를 어디서 가져오는가" 뿐이다.
    """

    def __init__(self, public_jwk: dict[str, Any]) -> None:
        self._jwk = jwt.PyJWK.from_dict(public_jwk)

    def get_signing_key_from_jwt(self, _token: str):
        # 키가 하나뿐인 대역이라 kid 조회 없이 그대로 돌려준다.
        return self._jwk


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Settings 부팅에 필요한 최소 env 를 채우는 헬퍼를 돌려준다."""

    def _apply(**overrides: str) -> None:
        base = {
            "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
            "R2_ACCOUNT_ID": "test",
            "R2_ACCESS_KEY_ID": "test",
            "R2_SECRET_ACCESS_KEY": "test",
            "R2_BUCKET_NAME": "test",
            "GEMINI_API_KEY": "test-gemini-key",
            "OPENAI_API_KEY": "sk-xxx",
            "APP_ENV": "test",
            "AUTH_JWT_ISSUER": TEST_ISSUER,
            "AUTH_JWKS_URL": TEST_JWKS_URL,
        }
        base.update(overrides)
        for key, value in base.items():
            monkeypatch.setenv(key, value)
        # 설정 싱글톤 + JWKS 싱글톤 + claims 캐시를 전부 버려야 새 env 가 반영된다.
        from src.auth import dependencies as deps
        from src.core import config as cfg_mod

        cfg_mod.get_settings.cache_clear()
        deps.reset_jwks_client()
        deps._JWT_CLAIMS_CACHE.clear()
        deps._USER_CACHE.clear()

    return _apply


@pytest.fixture(params=SUPPORTED_ALGORITHMS)
def signing(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """알고리즘별 실서명 도구. `signing.make_token(...)` 이 진짜 서명된 JWT 를 만든다.

    파라미터화라 EdDSA/ES256/RS256 3종이 매번 돌아간다 — 알고리즘 결정이 되돌릴 수 있는
    결정으로 유지된다.
    """
    algorithm: str = request.param
    private_key, public_jwk = _generate_keypair(algorithm)
    public_jwk.setdefault("kid", str(uuid.uuid4()))
    public_jwk.setdefault("alg", algorithm)

    client = _LocalJWKClient(public_jwk)

    def _install() -> None:
        """`_get_jwks_client()` 가 로컬 대역을 돌려주도록 갈아끼운다."""
        from src.auth import dependencies as deps

        monkeypatch.setattr(deps, "_get_jwks_client", lambda: client)

    def _make_token(
        *,
        sub: str = "ba_user_test",
        issuer: str = TEST_ISSUER,
        audience: str | None = TEST_AUDIENCE,
        expires_in: float = 900.0,
        **extra_claims: Any,
    ) -> str:
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": sub,
            "iss": issuer,
            "iat": now,
            "exp": int(now + expires_in),
        }
        if audience is not None:
            payload["aud"] = audience
        payload.update(extra_claims)
        return jwt.encode(
            payload,
            private_key,
            algorithm=algorithm,
            headers={"kid": public_jwk["kid"]},
        )

    class _Signing:
        alg = algorithm
        jwk = public_jwk
        install = staticmethod(_install)
        make_token = staticmethod(_make_token)

    return _Signing
