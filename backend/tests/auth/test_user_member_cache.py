# Sprint 28 BUG-S28-PERF-RT-1 회귀 가드 — User + WorkspaceMember in-process cache.
"""Round B 측정: find_by_clerk_id 1.2-4.5s × 5 endpoint fanout = dogfooding-blocker.

User cache (clerk_id → User, TTL 60s) + Member cache ((workspace_id, user_id) → Member, TTL 60s)
도입으로 dashboard fanout critical path 4286ms → 1586ms 측정 (63% 감소).

본 test: cache hit / miss / TTL / invalidate 정확 동작 검증.
"""
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.auth import dependencies as auth_deps
from src.auth import rbac as auth_rbac


@pytest.fixture(autouse=True)
def _clear_caches():
    """각 test 시작 시 cache 비움."""
    auth_deps._USER_CACHE.clear()
    auth_rbac._MEMBER_CACHE.clear()
    yield
    auth_deps._USER_CACHE.clear()
    auth_rbac._MEMBER_CACHE.clear()


# ── User cache ────────────────────────────────────────────────────────


def test_user_cache_set_get_roundtrip():
    """단일 set → get cache hit."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.clerk_id = "user_abc"
    user.onboarding_step = 1

    auth_deps._user_cache_set("user_abc", user)
    cached = auth_deps._user_cache_get("user_abc")
    assert cached is user


def test_user_cache_miss_for_unknown_clerk_id():
    """미등록 clerk_id → None."""
    assert auth_deps._user_cache_get("user_unknown") is None


def test_user_cache_ttl_expiry(monkeypatch):
    """TTL 60s 경과 후 cache miss."""
    user = MagicMock()
    user.clerk_id = "user_ttl"

    # 시간 freeze
    fake_now = [1000.0]
    monkeypatch.setattr(auth_deps.time, "time", lambda: fake_now[0])

    auth_deps._user_cache_set("user_ttl", user)
    assert auth_deps._user_cache_get("user_ttl") is user

    # 59s 후 — 여전히 hit
    fake_now[0] += 59
    assert auth_deps._user_cache_get("user_ttl") is user

    # 61s 후 — expired
    fake_now[0] += 2
    assert auth_deps._user_cache_get("user_ttl") is None


def test_user_cache_invalidate():
    """invalidate_user_cache 강제 제거."""
    user = MagicMock()
    auth_deps._user_cache_set("user_inv", user)
    assert auth_deps._user_cache_get("user_inv") is user

    auth_deps.invalidate_user_cache("user_inv")
    assert auth_deps._user_cache_get("user_inv") is None


def test_user_cache_lru_eviction():
    """MAX_SIZE 도달 시 eviction (expired 우선)."""
    monkeypatch_size = 5
    original_max = auth_deps._USER_CACHE_MAX_SIZE
    try:
        auth_deps._USER_CACHE_MAX_SIZE = monkeypatch_size
        for i in range(monkeypatch_size + 2):
            u = MagicMock()
            u.clerk_id = f"user_{i}"
            auth_deps._user_cache_set(f"user_{i}", u)
        assert len(auth_deps._USER_CACHE) <= monkeypatch_size
    finally:
        auth_deps._USER_CACHE_MAX_SIZE = original_max


# ── Member cache ──────────────────────────────────────────────────────


def test_member_cache_set_get_roundtrip():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member = MagicMock()
    member.role = "owner"

    auth_rbac._member_cache_set(ws_id, user_id, member)
    cached = auth_rbac._member_cache_get(ws_id, user_id)
    assert cached is member


def test_member_cache_distinct_workspace_user_keys():
    """동일 user 라도 다른 workspace = 다른 cache key."""
    user_id = uuid.uuid4()
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()

    member_a = MagicMock()
    member_a.role = "owner"
    member_b = MagicMock()
    member_b.role = "viewer"

    auth_rbac._member_cache_set(ws_a, user_id, member_a)
    auth_rbac._member_cache_set(ws_b, user_id, member_b)

    assert auth_rbac._member_cache_get(ws_a, user_id) is member_a
    assert auth_rbac._member_cache_get(ws_b, user_id) is member_b


def test_member_cache_invalidate():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member = MagicMock()

    auth_rbac._member_cache_set(ws_id, user_id, member)
    auth_rbac.invalidate_member_cache(ws_id, user_id)
    assert auth_rbac._member_cache_get(ws_id, user_id) is None


def test_member_cache_ttl_expiry(monkeypatch):
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member = MagicMock()

    fake_now = [1000.0]
    monkeypatch.setattr(auth_rbac.time, "time", lambda: fake_now[0])

    auth_rbac._member_cache_set(ws_id, user_id, member)
    fake_now[0] += 61
    assert auth_rbac._member_cache_get(ws_id, user_id) is None


# ── Integration: get_current_user 의 cache hit fast path ─────────────


@pytest.mark.asyncio
async def test_get_current_user_uses_user_cache_when_present():
    """User cache hit 시 find_by_clerk_id 호출 0건 (Neon RTT SKIP)."""
    from src.auth.dependencies import get_current_user

    cached_user = MagicMock()
    cached_user.id = uuid.uuid4()
    cached_user.clerk_id = "user_cached"
    cached_user.onboarding_step = 1
    auth_deps._user_cache_set("user_cached", cached_user)

    mock_session = AsyncMock()
    claims = {"sub": "user_cached"}

    with patch("src.auth.dependencies.UserRepository") as MockRepo:
        repo = AsyncMock()
        repo.find_by_clerk_id = AsyncMock(return_value=None)  # should not be called
        MockRepo.return_value = repo

        result = await get_current_user(claims=claims, session=mock_session)

    # User cache hit → repo.find_by_clerk_id 호출 0건
    assert repo.find_by_clerk_id.call_count == 0
    assert result is cached_user


@pytest.mark.asyncio
async def test_get_current_user_fills_cache_on_fast_path():
    """fast path 도달 시 User cache 저장 (다음 호출 cache hit)."""
    from src.auth.dependencies import get_current_user

    user = MagicMock()
    user.id = uuid.uuid4()
    user.clerk_id = "user_fill"
    user.onboarding_step = 1

    mock_session = AsyncMock()
    claims = {"sub": "user_fill"}

    with patch("src.auth.dependencies.UserRepository") as MockRepo:
        repo = AsyncMock()
        repo.find_by_clerk_id = AsyncMock(return_value=user)
        MockRepo.return_value = repo

        result = await get_current_user(claims=claims, session=mock_session)

    assert result is user
    # cache 채워짐
    assert auth_deps._user_cache_get("user_fill") is user
