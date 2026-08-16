# Sprint 29 R1 (auth-claim) 회귀 가드 — verify_bearer_token 이 name/email claim 보존.
"""이전엔 result={"sub": ...} 만 남겨 lazy seed 의 claims.get("name"/"email") 이 항상
fallback("사용자"/"")로 동작 → 신규 user 이름/이메일 누락. 이제 claim 이 있으면 보존한다.

ADR-031: 이 claim 들의 공급원은 `apps/web/src/lib/auth.ts` 의 `jwt.definePayload` 다.
FE 가 payload 에서 name/email 을 빼면 신규 가입자의 표시 이름이 조용히 "사용자" 가 된다 —
그래서 "있으면 보존" 과 "없어도 안 터짐" 양쪽을 다 가드한다.
"""
import pytest

from tests.auth.conftest import TEST_AUDIENCE


@pytest.mark.asyncio
async def test_preserves_name_and_email(auth_env, signing):
    """name/email claim 이 있으면 result 에 보존돼 lazy seed 가 사용한다."""
    auth_env(AUTH_JWT_AUDIENCE=TEST_AUDIENCE, AUTH_JWT_ALGORITHMS=signing.alg)
    signing.install()
    from src.auth import dependencies as deps

    token = signing.make_token(
        sub="ba_user_abc", name="홍길동", email="hong@example.com"
    )
    result = await deps.verify_bearer_token(authorization=f"Bearer {token}")

    assert result["sub"] == "ba_user_abc"
    assert result["name"] == "홍길동"
    assert result["email"] == "hong@example.com"


@pytest.mark.asyncio
async def test_omits_absent_name_and_email(auth_env, signing):
    """name/email claim 부재 시 result 에 키 없음 — KeyError 없이 caller fallback 유지."""
    auth_env(AUTH_JWT_AUDIENCE=TEST_AUDIENCE, AUTH_JWT_ALGORITHMS=signing.alg)
    signing.install()
    from src.auth import dependencies as deps

    token = signing.make_token(sub="ba_user_xyz")
    result = await deps.verify_bearer_token(authorization=f"Bearer {token}")

    assert result["sub"] == "ba_user_xyz"
    assert "name" not in result
    assert "email" not in result


@pytest.mark.asyncio
async def test_extra_claims_are_not_leaked(auth_env, signing):
    """토큰에 다른 클레임이 실려 있어도 sub/name/email 만 통과시킨다.

    Better Auth 의 기본 payload 는 session.user 전체(emailVerified/createdAt 등)라
    definePayload 를 되돌리는 실수가 나면 불필요한 필드가 백엔드로 흘러든다.
    """
    auth_env(AUTH_JWT_AUDIENCE=TEST_AUDIENCE, AUTH_JWT_ALGORITHMS=signing.alg)
    signing.install()
    from src.auth import dependencies as deps

    token = signing.make_token(
        sub="ba_user_extra",
        email="e@kairos.test",
        emailVerified=True,
        image="https://cdn.example.com/a.png",
        role="admin",
    )
    result = await deps.verify_bearer_token(authorization=f"Bearer {token}")

    assert set(result) == {"sub", "email"}
    assert "role" not in result, "role 클레임을 그대로 신뢰하면 권한 판정이 토큰에 넘어간다"
