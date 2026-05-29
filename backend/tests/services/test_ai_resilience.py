# Sprint 28 PERF-4 회귀 가드 — AI vendor timeout + circuit breaker.
"""Gemini / Whisper API 호출 안전망 (BUG-S27e-PERF-4 fix).

본 test: timeout / circuit breaker open / half-open recovery / state isolation 정확 검증.
"""
import asyncio
import time

import pytest

from src.services.ai_resilience import (
    CircuitBreakerOpen,
    GEMINI_TIMEOUT_SEC,
    WHISPER_TIMEOUT_SEC,
    gemini_breaker,
    reset_breakers_for_test,
    whisper_breaker,
    with_gemini_timeout,
    with_whisper_timeout,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_breakers_for_test()
    yield
    reset_breakers_for_test()


# ── timeout ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_with_gemini_timeout_passes_through_fast_call():
    """정상 fast call → 결과 그대로 통과."""
    async def fast():
        return "ok"

    result = await with_gemini_timeout(fast(), timeout_sec=1.0)
    assert result == "ok"


@pytest.mark.asyncio
async def test_with_gemini_timeout_raises_on_hang():
    """hang call → TimeoutError raise + circuit breaker failure 1 증가."""
    async def hang():
        await asyncio.sleep(10)
        return "never"

    assert gemini_breaker._consecutive_failures == 0
    with pytest.raises(asyncio.TimeoutError):
        await with_gemini_timeout(hang(), timeout_sec=0.1)
    assert gemini_breaker._consecutive_failures == 1


@pytest.mark.asyncio
async def test_with_whisper_timeout_uses_default():
    """WHISPER_TIMEOUT_SEC default = 90s — 1hr chunk worst-case cover."""
    assert WHISPER_TIMEOUT_SEC >= 60
    assert GEMINI_TIMEOUT_SEC >= 30


# ── circuit breaker ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_5_failures():
    """5 연속 실패 → open + 다음 호출 CircuitBreakerOpen 즉시 raise."""
    async def fail():
        raise RuntimeError("vendor down")

    for _ in range(5):
        with pytest.raises(RuntimeError):
            await with_gemini_timeout(fail(), timeout_sec=1.0)

    # 6번째 — circuit open → 즉시 CircuitBreakerOpen
    async def call():
        return "ok"

    with pytest.raises(CircuitBreakerOpen):
        await with_gemini_timeout(call(), timeout_sec=1.0)


@pytest.mark.asyncio
async def test_circuit_breaker_resets_on_success():
    """failure 1-4 후 success → counter 0 reset."""
    async def fail():
        raise RuntimeError("transient")

    async def ok():
        return "ok"

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await with_gemini_timeout(fail(), timeout_sec=1.0)
    assert gemini_breaker._consecutive_failures == 3

    result = await with_gemini_timeout(ok(), timeout_sec=1.0)
    assert result == "ok"
    assert gemini_breaker._consecutive_failures == 0


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_recovery(monkeypatch):
    """60s 경과 후 half-open — 다음 호출 trial 허용."""
    async def fail():
        raise RuntimeError("vendor down")

    async def ok():
        return "ok"

    fake_now = [1000.0]
    monkeypatch.setattr(
        "src.services.ai_resilience.time.time",
        lambda: fake_now[0],
    )

    # 5 연속 실패 → open
    for _ in range(5):
        with pytest.raises(RuntimeError):
            await with_gemini_timeout(fail(), timeout_sec=1.0)

    # open 상태에서 호출 → CircuitBreakerOpen
    with pytest.raises(CircuitBreakerOpen):
        await with_gemini_timeout(ok(), timeout_sec=1.0)

    # 61s 경과 — half-open
    fake_now[0] += 61
    result = await with_gemini_timeout(ok(), timeout_sec=1.0)
    assert result == "ok"
    # 성공 시 reset
    assert gemini_breaker._consecutive_failures == 0
    assert gemini_breaker._opened_at is None


@pytest.mark.asyncio
async def test_gemini_and_whisper_breakers_isolated():
    """Gemini breaker open ≠ Whisper breaker open."""
    async def fail():
        raise RuntimeError("gemini down")

    for _ in range(5):
        with pytest.raises(RuntimeError):
            await with_gemini_timeout(fail(), timeout_sec=1.0)

    # Whisper 는 영향 0 — 정상 호출 통과
    async def ok():
        return "ok"

    result = await with_whisper_timeout(ok(), timeout_sec=1.0)
    assert result == "ok"
    assert whisper_breaker._consecutive_failures == 0
