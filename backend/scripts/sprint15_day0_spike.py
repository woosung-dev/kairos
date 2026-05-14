# Sprint 15 Day 0 cost/latency spike — 10 sample 실측 + Gemini EOL deprecation probe
"""Sprint 15 Day 0 spike.

목적:
- Whisper (gpt-4o-mini-transcribe) + Gemini 2.5 Flash distill + OpenAI embedding 1-pass 실측
- 10 sample (audio 7 + text 3)
- per-step latency / cost / failure 측정
- patch §12 invalidate threshold 자동 평가
- Gemini response header에 deprecation/sunset 정보 dump (Q3 EOL probe)

실행:
  cd backend
  uv run python scripts/sprint15_day0_spike.py
  # 또는
  python scripts/sprint15_day0_spike.py

전제:
- backend/.env에 OPENAI_API_KEY + GEMINI_API_KEY 설정
- samples/ 디렉토리에 audio 7개 (manual 녹음 필요):
    samples/chrome_10s.webm
    samples/chrome_60s.webm
    samples/chrome_5min.webm
    samples/ios_10s.mp4
    samples/ios_60s.mp4
    samples/ko_filler_60s.webm
    samples/silent_10s.webm
- 없는 sample은 skip + log

결과:
- 표준출력: 요약 + 각 sample raw
- docs/dev-log/sprint-15-cost-spike.md에 manual paste용 JSON block
"""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# sys.path에 backend/src 추가 — Settings 재사용
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from src.core.config import get_settings  # noqa: E402

# ---- 모델 / 가격 (2026-05-14 기준) ----
WHISPER_MODEL = "gpt-4o-mini-transcribe"  # patch §13: $0.003/min
WHISPER_COST_PER_MIN = 0.003
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_INPUT_COST_PER_1M = 0.30
GEMINI_OUTPUT_COST_PER_1M = 2.50
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_COST_PER_1M = 0.020

DISTILL_PROMPT = """당신은 사용자의 voice/text 메모를 요약하는 AI. 입력을 다음 JSON 구조로 변환하세요.
{
  "title": "10자 이내 짧은 제목",
  "atomic_notes": ["핵심 1", "핵심 2"],
  "suggested_visibility": "personal | team"
}
JSON만 반환. 다른 텍스트 금지.

입력:
"""

# ---- Sample 정의 ----
SAMPLES_DIR = BACKEND_DIR / "scripts" / "samples"


@dataclass
class Sample:
    name: str
    kind: str  # 'audio' | 'text'
    path: Path | None = None
    text: str | None = None
    duration_sec: float = 0.0  # audio 길이 (수동 입력, 비용 계산용)


SAMPLES: list[Sample] = [
    Sample("chrome_webm_10s", "audio", SAMPLES_DIR / "chrome_10s.webm", duration_sec=10),
    Sample("chrome_webm_60s", "audio", SAMPLES_DIR / "chrome_60s.webm", duration_sec=60),
    Sample("chrome_webm_5min", "audio", SAMPLES_DIR / "chrome_5min.webm", duration_sec=300),
    Sample("ios_mp4_10s", "audio", SAMPLES_DIR / "ios_10s.mp4", duration_sec=10),
    Sample("ios_mp4_60s", "audio", SAMPLES_DIR / "ios_60s.mp4", duration_sec=60),
    Sample("ko_filler_60s", "audio", SAMPLES_DIR / "ko_filler_60s.webm", duration_sec=60),
    Sample("silent_10s", "audio", SAMPLES_DIR / "silent_10s.webm", duration_sec=10),
    Sample("text_500", "text", text="한국어 메모 예시 " * 50),
    Sample("text_3000", "text", text="한국어 메모 예시 " * 300),
    Sample("text_10000", "text", text="한국어 메모 예시 " * 1000),
]


@dataclass
class StepResult:
    elapsed_ms: int = 0
    cost_usd: float = 0.0
    success: bool = True
    error: str | None = None
    output: Any = None


@dataclass
class SampleResult:
    sample: str
    kind: str
    transcription: StepResult = field(default_factory=StepResult)
    distill: StepResult = field(default_factory=StepResult)
    embedding: StepResult = field(default_factory=StepResult)
    total_ms: int = 0
    total_cost: float = 0.0
    failure_step: str | None = None


async def transcribe(openai_client, sample: Sample) -> StepResult:
    """Whisper API 호출. audio sample만."""
    if sample.kind != "audio":
        return StepResult(elapsed_ms=0, cost_usd=0.0, success=True, output=sample.text)
    if sample.path is None or not sample.path.exists():
        return StepResult(success=False, error=f"sample file missing: {sample.path}")
    start = time.time()
    try:
        with sample.path.open("rb") as f:
            resp = await openai_client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=f,
                language="ko",
            )
        elapsed = int((time.time() - start) * 1000)
        cost = (sample.duration_sec / 60.0) * WHISPER_COST_PER_MIN
        return StepResult(elapsed_ms=elapsed, cost_usd=cost, success=True, output=resp.text)
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return StepResult(elapsed_ms=elapsed, success=False, error=str(e))


async def distill(gemini_client, transcript: str, probe_headers: list[Any]) -> StepResult:
    """Gemini distill. 첫 호출에서 response 객체 dump (EOL probe — Q3)."""
    start = time.time()
    try:
        resp = await gemini_client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=DISTILL_PROMPT + transcript,
        )
        elapsed = int((time.time() - start) * 1000)
        # ---- EOL probe (Q3 inline) ----
        if len(probe_headers) == 0:
            probe = {
                "note": "Gemini response object dump for EOL/sunset header probe",
                "model": GEMINI_MODEL,
                "usage_metadata": getattr(resp, "usage_metadata", None).__dict__
                if getattr(resp, "usage_metadata", None) else None,
                "response_attrs": [a for a in dir(resp) if not a.startswith("_")],
            }
            probe_headers.append(probe)
        # cost — usage_metadata 기반
        cost = 0.0
        usage = getattr(resp, "usage_metadata", None)
        in_tok = getattr(usage, "prompt_token_count", 0) or 0
        out_tok = getattr(usage, "candidates_token_count", 0) or 0
        cost = (in_tok / 1_000_000) * GEMINI_INPUT_COST_PER_1M + \
               (out_tok / 1_000_000) * GEMINI_OUTPUT_COST_PER_1M
        # JSON parse 시도
        text = resp.text or ""
        clean = text.replace("```json", "").replace("```", "").strip()
        parsed = None
        parse_ok = True
        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            parse_ok = False
        return StepResult(
            elapsed_ms=elapsed,
            cost_usd=cost,
            success=parse_ok,
            error=None if parse_ok else "json parse fail",
            output={"raw": text, "parsed": parsed, "input_tokens": in_tok, "output_tokens": out_tok},
        )
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return StepResult(elapsed_ms=elapsed, success=False, error=str(e))


async def embed(openai_client, text: str) -> StepResult:
    start = time.time()
    try:
        resp = await openai_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        elapsed = int((time.time() - start) * 1000)
        in_tok = resp.usage.total_tokens
        cost = (in_tok / 1_000_000) * EMBEDDING_COST_PER_1M
        return StepResult(elapsed_ms=elapsed, cost_usd=cost, success=True,
                          output={"dim": len(resp.data[0].embedding), "tokens": in_tok})
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return StepResult(elapsed_ms=elapsed, success=False, error=str(e))


async def run_sample(sample: Sample, openai_client, gemini_client, probe_headers: list) -> SampleResult:
    result = SampleResult(sample=sample.name, kind=sample.kind)
    # 1. Transcription
    result.transcription = await transcribe(openai_client, sample)
    if not result.transcription.success:
        result.failure_step = "transcription"
        return result
    transcript = result.transcription.output or sample.text or ""
    # 2. Distill
    result.distill = await distill(gemini_client, transcript, probe_headers)
    if not result.distill.success:
        result.failure_step = "distill"
    # 3. Embed (atomic_notes 또는 raw transcript)
    embed_input = transcript
    if result.distill.success and result.distill.output:
        parsed = result.distill.output.get("parsed")
        if parsed and parsed.get("atomic_notes"):
            embed_input = " ".join(parsed["atomic_notes"])
    result.embedding = await embed(openai_client, embed_input)
    if not result.embedding.success and result.failure_step is None:
        result.failure_step = "embedding"
    # aggregate
    result.total_ms = (
        result.transcription.elapsed_ms + result.distill.elapsed_ms + result.embedding.elapsed_ms
    )
    result.total_cost = (
        result.transcription.cost_usd + result.distill.cost_usd + result.embedding.cost_usd
    )
    return result


def aggregate(results: list[SampleResult]) -> dict:
    valid = [r for r in results if r.failure_step is None]
    failures = [r for r in results if r.failure_step is not None]
    e2e_ms = [r.total_ms for r in results if r.total_ms > 0]
    total_cost = sum(r.total_cost for r in results)
    # tester per week: 7일 × ~10 capture
    cost_per_tester = total_cost * 10 / len(results) if results else 0
    return {
        "total_samples": len(results),
        "successful": len(valid),
        "failed": len(failures),
        "failure_rate": len(failures) / len(results) if results else 0,
        "e2e_p50_ms": int(statistics.median(e2e_ms)) if e2e_ms else 0,
        "e2e_p95_ms": int(statistics.quantiles(e2e_ms, n=20)[18]) if len(e2e_ms) >= 20 else (max(e2e_ms) if e2e_ms else 0),
        "total_cost_usd": round(total_cost, 4),
        "cost_per_tester_week_estimate_usd": round(cost_per_tester, 4),
    }


def evaluate_thresholds(agg: dict) -> list[str]:
    """patch §12 invalidate thresholds — violation 시 plan revise 트리거."""
    violations = []
    if agg["failure_rate"] > 0.05:
        violations.append(f"transcription/distill failure rate {agg['failure_rate']:.1%} > 5% — Whisper 모델 재선택 또는 distill prompt revise")
    if agg["e2e_p95_ms"] > 60_000:
        violations.append(f"end-to-end p95 {agg['e2e_p95_ms']}ms > 60s — R1 BackgroundTask 확정 / R7 polling 최적")
    if agg["cost_per_tester_week_estimate_usd"] > 2.0:
        violations.append(f"cost per tester per week ${agg['cost_per_tester_week_estimate_usd']} > $2 — 모델 다운그레이드 / sample size 조정")
    return violations


async def main() -> None:
    settings = get_settings()
    from openai import AsyncOpenAI
    from google import genai

    openai_client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    gemini_client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
    probe_headers: list = []

    print("=" * 80)
    print(f"Sprint 15 Day 0 spike — {len(SAMPLES)} samples")
    print(f"Whisper: {WHISPER_MODEL} | Gemini: {GEMINI_MODEL} | Embedding: {EMBEDDING_MODEL}")
    print("=" * 80)

    results: list[SampleResult] = []
    for s in SAMPLES:
        print(f"\n[run] {s.name} ({s.kind})... ", end="", flush=True)
        r = await run_sample(s, openai_client, gemini_client, probe_headers)
        results.append(r)
        if r.failure_step:
            print(f"FAIL at {r.failure_step}: {getattr(r, r.failure_step).error}")
        else:
            print(f"OK total={r.total_ms}ms cost=${r.total_cost:.5f}")

    # raw results
    print("\n" + "=" * 80)
    print("RAW RESULTS (JSON):")
    print("=" * 80)
    raw_json = [
        {
            "sample": r.sample,
            "kind": r.kind,
            "transcription": {"elapsed_ms": r.transcription.elapsed_ms, "cost_usd": r.transcription.cost_usd, "success": r.transcription.success, "error": r.transcription.error},
            "distill": {"elapsed_ms": r.distill.elapsed_ms, "cost_usd": r.distill.cost_usd, "success": r.distill.success, "error": r.distill.error, "tokens": r.distill.output if isinstance(r.distill.output, dict) else None},
            "embedding": {"elapsed_ms": r.embedding.elapsed_ms, "cost_usd": r.embedding.cost_usd, "success": r.embedding.success, "error": r.embedding.error},
            "total_ms": r.total_ms,
            "total_cost": r.total_cost,
            "failure_step": r.failure_step,
        }
        for r in results
    ]
    print(json.dumps(raw_json, ensure_ascii=False, indent=2))

    # aggregate + thresholds
    agg = aggregate(results)
    violations = evaluate_thresholds(agg)
    print("\n" + "=" * 80)
    print("AGGREGATE:")
    print("=" * 80)
    print(json.dumps(agg, ensure_ascii=False, indent=2))
    print("\nTHRESHOLD VIOLATIONS:")
    if violations:
        for v in violations:
            print(f"  ❌ {v}")
    else:
        print("  ✅ 위반 없음 — R1 진입 OK")

    # EOL probe (Q3)
    print("\n" + "=" * 80)
    print("GEMINI EOL PROBE (Q3 inline):")
    print("=" * 80)
    if probe_headers:
        print(json.dumps(probe_headers[0], ensure_ascii=False, indent=2, default=str))
    else:
        print("(no probe data — distill 모두 실패)")
    print("\n>> 위 dump에서 deprecation / sunset / x-deprecation header 존재 시 별도 ADR 가속")


if __name__ == "__main__":
    asyncio.run(main())
