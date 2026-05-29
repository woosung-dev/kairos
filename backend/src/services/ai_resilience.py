# Sprint 28 PERF-4 — Gemini/Whisper API 안전망 (timeout + simple circuit breaker).
"""외부 AI vendor (Gemini, OpenAI Whisper) 호출 안전망.

Sprint 27e Round 2 PERF-4 P0 격상 — vendor incident 1주에 1회 발현 + retry 0건 +
timeout 0건 → 외부 5명 dogfooding 시 multi-user hang risk. 본 helper 가:

(a) `asyncio.wait_for(..., timeout=N)` — infinite hang 차단
(b) 간단한 in-process circuit breaker — 5 연속 실패 → 60s open → half-open trial

retry 는 사용자가 UI 에서 직접 클릭 (Kairos `Meeting.status='failed'` 후 retry 버튼,
RAG SSE error event 후 다시 질문). 자동 retry 는 cost 증폭 risk (Gemini API 호출당 비용)
+ 외부 incident 시 동일 결과 — 본 sprint 적용 X (BL-S28 carry).
"""
import asyncio
import logging
import time
from collections.abc import Awaitable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Gemini: distill / summary / RAG stream — 정상 5-15s. 30s 가 안전 한계.
GEMINI_TIMEOUT_SEC = 30.0
# RAG stream 은 토큰 단위 yield — 전체 stream timeout 별도 (60s).
GEMINI_STREAM_TIMEOUT_SEC = 60.0
# Whisper: 5min audio 정상 5-20s. 1hr chunk worst-case 60s. 90s 안전 한계.
WHISPER_TIMEOUT_SEC = 90.0


class CircuitBreakerOpen(Exception):
    """Circuit breaker open 상태. vendor outage 동안 fast fail.

    Kairos pipeline 은 BackgroundTask 패턴이라 worker 점유 회피 + Meeting.status='failed'
    빠른 전이로 사용자에게 알림. RAG 는 SSE error event 송출 → graceful degrade.
    """


class _CircuitBreaker:
    """단일 vendor circuit breaker.

    - closed: 정상 — 모든 호출 통과
    - open: 5 연속 실패 → 60s 동안 즉시 raise CircuitBreakerOpen
    - half-open: 60s 경과 후 1 trial 허용. 성공 시 closed, 실패 시 open
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_sec: float = 60.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_sec = recovery_sec
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    def check(self) -> None:
        """호출 직전 — open 시 즉시 raise."""
        if self._opened_at is None:
            return
        if time.time() - self._opened_at >= self.recovery_sec:
            # half-open: 다음 호출이 trial. _opened_at 유지 (on_success 가 reset).
            return
        raise CircuitBreakerOpen(
            f"{self.name} circuit open ({self._consecutive_failures} 연속 실패, "
            f"{self.recovery_sec - (time.time() - self._opened_at):.0f}s 후 회복)"
        )

    def on_success(self) -> None:
        if self._consecutive_failures > 0 or self._opened_at is not None:
            # extra dict 의 "name" 은 LogRecord reserved key — `breaker_name` 사용.
            logger.info(
                "circuit_breaker_recovered",
                extra={
                    "breaker_name": self.name,
                    "previous_failures": self._consecutive_failures,
                },
            )
        self._consecutive_failures = 0
        self._opened_at = None

    def on_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold and self._opened_at is None:
            self._opened_at = time.time()
            logger.warning(
                "circuit_breaker_opened",
                extra={
                    "breaker_name": self.name,
                    "failures": self._consecutive_failures,
                    "recovery_sec": self.recovery_sec,
                },
            )


# Module-level singleton — 각 process 의 모든 worker 가 공유.
gemini_breaker = _CircuitBreaker("gemini")
whisper_breaker = _CircuitBreaker("whisper")


async def with_gemini_timeout(
    coro: Awaitable[T],
    timeout_sec: float = GEMINI_TIMEOUT_SEC,
) -> T:
    """Gemini API 호출 안전망 — timeout + circuit breaker.

    Usage:
        response = await with_gemini_timeout(
            self.client.aio.models.generate_content(model=..., contents=...)
        )
    """
    gemini_breaker.check()
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_sec)
    except (asyncio.TimeoutError, Exception):
        gemini_breaker.on_failure()
        raise
    gemini_breaker.on_success()
    return result


async def with_whisper_timeout(
    coro: Awaitable[T],
    timeout_sec: float = WHISPER_TIMEOUT_SEC,
) -> T:
    """Whisper API 호출 안전망 — timeout + circuit breaker."""
    whisper_breaker.check()
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_sec)
    except (asyncio.TimeoutError, Exception):
        whisper_breaker.on_failure()
        raise
    whisper_breaker.on_success()
    return result


def reset_breakers_for_test() -> None:
    """test 격리용 — circuit breaker state 초기화."""
    gemini_breaker._consecutive_failures = 0
    gemini_breaker._opened_at = None
    whisper_breaker._consecutive_failures = 0
    whisper_breaker._opened_at = None
