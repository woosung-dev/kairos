# Sprint 28 BUG-S28-PERF-RT-1 회귀 가드 — User + WorkspaceMember in-process cache.
"""Round B 측정: find_by_auth_user_id 1.2-4.5s × 5 endpoint fanout = dogfooding-blocker.

User cache (auth_user_id → User, TTL 60s) + Member cache ((workspace_id, user_id) → Member, TTL 15s)
도입으로 dashboard fanout critical path 4286ms → 1586ms 측정 (63% 감소).
Member cache 는 Stage 2 #6 (2026-07-05) 하드닝: TTL 60→15s + admin/owner 게이트 bypass.

본 test: cache hit / miss / TTL / invalidate / admin-owner bypass 정확 동작 검증.
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
    user.auth_user_id = "user_abc"
    user.onboarding_step = 1

    auth_deps._user_cache_set("user_abc", user)
    cached = auth_deps._user_cache_get("user_abc")
    assert cached is user


def test_user_cache_miss_for_unknown_auth_user_id():
    """미등록 auth_user_id → None."""
    assert auth_deps._user_cache_get("user_unknown") is None


def test_user_cache_ttl_expiry(monkeypatch):
    """TTL 60s 경과 후 cache miss."""
    user = MagicMock()
    user.auth_user_id = "user_ttl"

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
            u.auth_user_id = f"user_{i}"
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
    """TTL 15s 경계 — 14s hit / 16s miss (Stage 2 #6 하드닝)."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member = MagicMock()

    fake_now = [1000.0]
    monkeypatch.setattr(auth_rbac.time, "time", lambda: fake_now[0])

    auth_rbac._member_cache_set(ws_id, user_id, member)
    fake_now[0] += 14
    assert auth_rbac._member_cache_get(ws_id, user_id) is member
    fake_now[0] += 2
    assert auth_rbac._member_cache_get(ws_id, user_id) is None


# ── Member cache — admin/owner 게이트 bypass (Stage 2 #6, 2026-07-05) ──


def _make_member(role: str) -> MagicMock:
    member = MagicMock()
    member.role = role
    return member


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    return user


async def _call_checker(min_role: str, ws_id, user, db_member):
    """RoleChecker 를 mock repo 로 호출, (결과 or HTTPException, find_member mock) 반환."""
    from fastapi import HTTPException

    with patch("src.auth.rbac.WorkspaceRepository") as MockRepo:
        repo = AsyncMock()
        repo.find_member = AsyncMock(return_value=db_member)
        MockRepo.return_value = repo
        try:
            result = await auth_rbac.RoleChecker(min_role)(
                workspace_id=ws_id, current_user=user, session=AsyncMock()
            )
        except HTTPException as exc:
            result = exc
    return result, repo.find_member


@pytest.mark.asyncio
async def test_admin_gate_bypasses_stale_elevated_cache():
    """캐시에 stale 'admin' 이 남아도 admin 게이트는 DB fresh 'member' 로 403.

    핵심 보안 속성 — cross-instance 강등 즉시 반영 (Stage 2 #6).
    """
    from fastapi import HTTPException

    ws_id = uuid.uuid4()
    user = _make_user()
    auth_rbac._member_cache_set(ws_id, user.id, _make_member("admin"))

    result, find_member = await _call_checker("admin", ws_id, user, _make_member("member"))

    assert isinstance(result, HTTPException)
    assert result.status_code == 403
    assert find_member.call_count == 1


@pytest.mark.asyncio
async def test_admin_gate_reads_fresh_promotion():
    """캐시에 구 'member' 가 남아도 admin 게이트는 DB fresh 'admin' 으로 통과."""
    ws_id = uuid.uuid4()
    user = _make_user()
    auth_rbac._member_cache_set(ws_id, user.id, _make_member("member"))

    fresh_admin = _make_member("admin")
    result, find_member = await _call_checker("admin", ws_id, user, fresh_admin)

    assert result is fresh_admin
    assert find_member.call_count == 1


@pytest.mark.asyncio
async def test_owner_gate_always_hits_db():
    """owner 게이트는 캐시가 채워져 있어도 항상 DB 조회."""
    ws_id = uuid.uuid4()
    user = _make_user()
    auth_rbac._member_cache_set(ws_id, user.id, _make_member("owner"))

    fresh_owner = _make_member("owner")
    result, find_member = await _call_checker("owner", ws_id, user, fresh_owner)

    assert find_member.call_count == 1
    assert result is fresh_owner


@pytest.mark.asyncio
async def test_member_gate_still_uses_cache():
    """viewer/member 게이트는 캐시 유지 — dashboard fanout 성능 회귀 가드."""
    ws_id = uuid.uuid4()
    user = _make_user()
    cached = _make_member("member")
    auth_rbac._member_cache_set(ws_id, user.id, cached)

    result, find_member = await _call_checker("member", ws_id, user, _make_member("viewer"))

    assert result is cached
    assert find_member.call_count == 0


@pytest.mark.asyncio
async def test_viewer_gate_still_uses_cache():
    """viewer 게이트도 캐시 유지."""
    ws_id = uuid.uuid4()
    user = _make_user()
    cached = _make_member("viewer")
    auth_rbac._member_cache_set(ws_id, user.id, cached)

    result, find_member = await _call_checker("viewer", ws_id, user, _make_member("member"))

    assert result is cached
    assert find_member.call_count == 0


# ── BUG-CACHE-DETACHED-EXPIRED (2026-07-05) — expire+detach 인스턴스 자가치유 ──


def _expired_detached(instance):
    """live ORM 인스턴스가 rollback 등으로 expire+detach 된 상태 시뮬레이션.

    속성이 __dict__ 에서 제거된 detached 인스턴스는 접근 시 DetachedInstanceError.
    """
    instance.__dict__.pop("id", None)
    return instance


def test_user_cache_drops_expired_detached_instance():
    """expired-detached User 는 cache miss 처리 (500 연쇄 자가치유)."""
    from src.auth.models import User

    user = User(auth_user_id="user_det", email="d@e.com", display_name="d")
    auth_deps._user_cache_set("user_det", user)
    _expired_detached(user)

    assert auth_deps._user_cache_get("user_det") is None
    assert "user_det" not in auth_deps._USER_CACHE


def test_member_cache_drops_expired_detached_instance():
    """expired-detached WorkspaceMember 는 cache miss 처리."""
    from src.workspaces.models import WorkspaceMember

    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member = WorkspaceMember(workspace_id=ws_id, user_id=user_id, role="member")
    auth_rbac._member_cache_set(ws_id, user_id, member)
    _expired_detached(member)

    assert auth_rbac._member_cache_get(ws_id, user_id) is None
    assert (ws_id, user_id) not in auth_rbac._MEMBER_CACHE


@pytest.mark.asyncio
async def test_admin_gate_write_through_refreshes_cache():
    """bypass 조회 결과가 캐시에 write-through — 이후 member 게이트가 fresh role 을 봄."""
    ws_id = uuid.uuid4()
    user = _make_user()
    auth_rbac._member_cache_set(ws_id, user.id, _make_member("admin"))

    fresh = _make_member("owner")
    await _call_checker("admin", ws_id, user, fresh)

    assert auth_rbac._member_cache_get(ws_id, user.id) is fresh


# ── Integration: get_current_user 의 cache hit fast path ─────────────


@pytest.mark.asyncio
async def test_get_current_user_uses_user_cache_when_present():
    """User cache hit 시 find_by_auth_user_id 호출 0건 (Neon RTT SKIP)."""
    from src.auth.dependencies import get_current_user

    cached_user = MagicMock()
    cached_user.id = uuid.uuid4()
    cached_user.auth_user_id = "user_cached"
    cached_user.onboarding_step = 1
    auth_deps._user_cache_set("user_cached", cached_user)

    mock_session = AsyncMock()
    claims = {"sub": "user_cached"}

    with patch("src.auth.dependencies.UserRepository") as MockRepo:
        repo = AsyncMock()
        repo.find_by_auth_user_id = AsyncMock(return_value=None)  # should not be called
        MockRepo.return_value = repo

        result = await get_current_user(claims=claims, session=mock_session)

    # User cache hit → repo.find_by_auth_user_id 호출 0건
    assert repo.find_by_auth_user_id.call_count == 0
    assert result is cached_user


@pytest.mark.asyncio
async def test_get_current_user_fills_cache_on_fast_path():
    """fast path 도달 시 User cache 저장 (다음 호출 cache hit)."""
    from src.auth.dependencies import get_current_user

    user = MagicMock()
    user.id = uuid.uuid4()
    user.auth_user_id = "user_fill"
    user.onboarding_step = 1

    mock_session = AsyncMock()
    claims = {"sub": "user_fill"}

    with patch("src.auth.dependencies.UserRepository") as MockRepo:
        repo = AsyncMock()
        repo.find_by_auth_user_id = AsyncMock(return_value=user)
        MockRepo.return_value = repo

        result = await get_current_user(claims=claims, session=mock_session)

    assert result is user
    # cache 채워짐
    assert auth_deps._user_cache_get("user_fill") is user
