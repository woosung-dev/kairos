# Sprint 15 Day 0 cost/latency spike — 10 sample 실측 + Gemini EOL probe + 2-model 비교 (ADR-019)
"""Sprint 15 Day 0 spike (ADR-019 확장판).

목적:
- Whisper (gpt-4o-mini-transcribe) + Gemini distill + OpenAI embedding 1-pass 실측
- **2개 Gemini 모델 dual-record** (baseline `gemini-2.5-flash` vs candidate `gemini-3.1-flash-lite`)
- 10 sample (audio 7 + text 3)
- per-step latency / cost / failure 측정
- patch §12 invalidate threshold 자동 평가
- Gemini response header에 deprecation/sunset 정보 dump (Q3 EOL probe)
- 모델별 비교 (latency_delta_ms / cost_delta_usd / output_equivalence)

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
- 표준출력: 요약 + 각 sample raw + 모델 비교 섹션
- docs/dev-log/sprints/sprint-15-cost-spike.md에 manual paste용 JSON block (§3.5 ADR-019 비교)
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

# Gemini 후보 2종 — ADR-019 비교
GEMINI_MODELS: list[dict[str, Any]] = [
    {
        "id": "gemini-2.5-flash",
        "label": "baseline",
        "input_cost_per_1m": 0.30,
        "output_cost_per_1m": 2.50,
    },
    {
        "id": "gemini-3.1-flash-lite",
        "label": "candidate",
        "input_cost_per_1m": 0.25,
        "output_cost_per_1m": 1.50,
    },
]

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
    # 모델 ID -> StepResult (ADR-019: 2개 모델 dual-record)
    distills: dict[str, StepResult] = field(default_factory=dict)
    embedding: StepResult = field(default_factory=StepResult)
    # 모델별 e2e 합계 (transcription + distill[model] + embedding)
    total_ms_per_model: dict[str, int] = field(default_factory=dict)
    total_cost_per_model: dict[str, float] = field(default_factory=dict)
    failure_step: str | None = None  # 'transcription' / 'distill:<model>' / 'embedding'


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


async def distill(
    gemini_client,
    transcript: str,
    model_spec: dict[str, Any],
    probe_headers: list[Any],
) -> StepResult:
    """Gemini distill. 첫 호출에서 response 객체 dump (EOL probe — Q3).

    Args:
        model_spec: GEMINI_MODELS 중 하나 ({id, label, input_cost_per_1m, output_cost_per_1m})
    """
    model_id = model_spec["id"]
    in_price = model_spec["input_cost_per_1m"]
    out_price = model_spec["output_cost_per_1m"]
    start = time.time()
    try:
        resp = await gemini_client.aio.models.generate_content(
            model=model_id,
            contents=DISTILL_PROMPT + transcript,
        )
        elapsed = int((time.time() - start) * 1000)
        # ---- EOL probe (Q3 inline) — 모델별 1회만 dump ----
        existing_models = {p.get("model") for p in probe_headers}
        if model_id not in existing_models:
            probe = {
                "note": f"Gemini response object dump for EOL/sunset header probe ({model_spec['label']})",
                "model": model_id,
                "usage_metadata": getattr(resp, "usage_metadata", None).__dict__
                if getattr(resp, "usage_metadata", None) else None,
                "response_attrs": [a for a in dir(resp) if not a.startswith("_")],
            }
            probe_headers.append(probe)
        # cost — usage_metadata 기반
        usage = getattr(resp, "usage_metadata", None)
        in_tok = getattr(usage, "prompt_token_count", 0) or 0
        out_tok = getattr(usage, "candidates_token_count", 0) or 0
        cost = (in_tok / 1_000_000) * in_price + (out_tok / 1_000_000) * out_price
        # JSON parse 시도
        text = resp.text or ""
        clean = text.replace("```json", "").replace("```", "").strip()
        parsed = None
        parse_ok = True
        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            parse_ok = False
        # schema 동등성 — atomic_notes/title/suggested_visibility 3개 필드 존재
        schema_ok = (
            parse_ok
            and isinstance(parsed, dict)
            and all(k in parsed for k in ("title", "atomic_notes", "suggested_visibility"))
        )
        return StepResult(
            elapsed_ms=elapsed,
            cost_usd=cost,
            success=parse_ok,
            error=None if parse_ok else "json parse fail",
            output={
                "raw": text,
                "parsed": parsed,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "schema_ok": schema_ok,
            },
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


async def run_sample(
    sample: Sample, openai_client, gemini_client, probe_headers: list,
) -> SampleResult:
    result = SampleResult(sample=sample.name, kind=sample.kind)
    # 1. Transcription
    result.transcription = await transcribe(openai_client, sample)
    if not result.transcription.success:
        result.failure_step = "transcription"
        return result
    transcript = result.transcription.output or sample.text or ""
    # 2. Distill — 모델별 dual-record
    primary_distill_success = True
    primary_parsed: dict[str, Any] | None = None
    for model_spec in GEMINI_MODELS:
        dr = await distill(gemini_client, transcript, model_spec, probe_headers)
        result.distills[model_spec["id"]] = dr
        # baseline (첫 모델) 기준으로 후속 embed 입력 결정
        if model_spec["label"] == "baseline":
            if not dr.success:
                primary_distill_success = False
                result.failure_step = f"distill:{model_spec['id']}"
            elif dr.output:
                primary_parsed = dr.output.get("parsed")
    # 3. Embed — baseline distill 기반 atomic_notes 또는 raw transcript
    embed_input = transcript
    if primary_distill_success and primary_parsed and primary_parsed.get("atomic_notes"):
        embed_input = " ".join(primary_parsed["atomic_notes"])
    result.embedding = await embed(openai_client, embed_input)
    if not result.embedding.success and result.failure_step is None:
        result.failure_step = "embedding"
    # 모델별 e2e aggregate
    for model_spec in GEMINI_MODELS:
        mid = model_spec["id"]
        dr = result.distills.get(mid)
        if dr is None:
            continue
        result.total_ms_per_model[mid] = (
            result.transcription.elapsed_ms + dr.elapsed_ms + result.embedding.elapsed_ms
        )
        result.total_cost_per_model[mid] = (
            result.transcription.cost_usd + dr.cost_usd + result.embedding.cost_usd
        )
    return result


def aggregate_per_model(results: list[SampleResult], model_id: str) -> dict[str, Any]:
    valid = [r for r in results if r.failure_step is None and model_id in r.distills and r.distills[model_id].success]
    failures = [r for r in results if r.failure_step is not None or (model_id in r.distills and not r.distills[model_id].success)]
    e2e_ms = [r.total_ms_per_model[model_id] for r in results if model_id in r.total_ms_per_model and r.total_ms_per_model[model_id] > 0]
    total_cost = sum(r.total_cost_per_model.get(model_id, 0.0) for r in results)
    cost_per_tester = total_cost * 10 / len(results) if results else 0
    distill_ms = [r.distills[model_id].elapsed_ms for r in results if model_id in r.distills and r.distills[model_id].elapsed_ms > 0]
    return {
        "model": model_id,
        "total_samples": len(results),
        "successful": len(valid),
        "failed": len(failures),
        "failure_rate": len(failures) / len(results) if results else 0,
        "e2e_p50_ms": int(statistics.median(e2e_ms)) if e2e_ms else 0,
        "e2e_p95_ms": int(statistics.quantiles(e2e_ms, n=20)[18]) if len(e2e_ms) >= 20 else (max(e2e_ms) if e2e_ms else 0),
        "distill_p50_ms": int(statistics.median(distill_ms)) if distill_ms else 0,
        "distill_p95_ms": int(statistics.quantiles(distill_ms, n=20)[18]) if len(distill_ms) >= 20 else (max(distill_ms) if distill_ms else 0),
        "total_cost_usd": round(total_cost, 4),
        "cost_per_tester_week_estimate_usd": round(cost_per_tester, 4),
    }


def compute_model_comparison(results: list[SampleResult]) -> dict[str, Any]:
    """baseline vs candidate 비교 (ADR-019 spike)."""
    if len(GEMINI_MODELS) < 2:
        return {"note": "single model — no comparison"}
    baseline = next((m for m in GEMINI_MODELS if m["label"] == "baseline"), GEMINI_MODELS[0])
    candidate = next((m for m in GEMINI_MODELS if m["label"] == "candidate"), GEMINI_MODELS[1])
    b_agg = aggregate_per_model(results, baseline["id"])
    c_agg = aggregate_per_model(results, candidate["id"])

    # output_equivalence: 두 모델 모두 distill 성공 + schema_ok인 sample 비율
    both_ok = 0
    schema_match = 0
    for r in results:
        b_dr = r.distills.get(baseline["id"])
        c_dr = r.distills.get(candidate["id"])
        if b_dr and c_dr and b_dr.success and c_dr.success:
            both_ok += 1
            b_schema = (b_dr.output or {}).get("schema_ok", False) if isinstance(b_dr.output, dict) else False
            c_schema = (c_dr.output or {}).get("schema_ok", False) if isinstance(c_dr.output, dict) else False
            if b_schema and c_schema:
                schema_match += 1

    return {
        "baseline": baseline["id"],
        "candidate": candidate["id"],
        "distill_latency_delta_ms_p50": c_agg["distill_p50_ms"] - b_agg["distill_p50_ms"],
        "distill_latency_delta_ms_p95": c_agg["distill_p95_ms"] - b_agg["distill_p95_ms"],
        "distill_speedup_ratio_p50": round(b_agg["distill_p50_ms"] / c_agg["distill_p50_ms"], 2) if c_agg["distill_p50_ms"] > 0 else None,
        "cost_per_tester_week_delta_usd": round(c_agg["cost_per_tester_week_estimate_usd"] - b_agg["cost_per_tester_week_estimate_usd"], 4),
        "cost_reduction_pct": round(
            (b_agg["cost_per_tester_week_estimate_usd"] - c_agg["cost_per_tester_week_estimate_usd"]) / b_agg["cost_per_tester_week_estimate_usd"] * 100, 1
        ) if b_agg["cost_per_tester_week_estimate_usd"] > 0 else None,
        "output_equivalence": {
            "both_distill_success": both_ok,
            "both_schema_ok": schema_match,
            "schema_match_rate": round(schema_match / both_ok, 2) if both_ok > 0 else None,
        },
    }


def evaluate_thresholds(agg: dict, model_id: str) -> list[str]:
    """patch §12 invalidate thresholds — violation 시 plan revise 트리거."""
    violations = []
    if agg["failure_rate"] > 0.05:
        violations.append(f"[{model_id}] failure rate {agg['failure_rate']:.1%} > 5% — 모델 또는 prompt revise")
    if agg["e2e_p95_ms"] > 60_000:
        violations.append(f"[{model_id}] e2e p95 {agg['e2e_p95_ms']}ms > 60s — R1 BackgroundTask 확정 / R7 polling 최적")
    if agg["cost_per_tester_week_estimate_usd"] > 2.0:
        violations.append(f"[{model_id}] cost per tester per week ${agg['cost_per_tester_week_estimate_usd']} > $2 — 다운그레이드")
    return violations


async def main() -> None:
    settings = get_settings()
    from openai import AsyncOpenAI
    from google import genai

    openai_client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    gemini_client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
    probe_headers: list = []

    print("=" * 80)
    print(f"Sprint 15 Day 0 spike (ADR-019) — {len(SAMPLES)} samples × {len(GEMINI_MODELS)} models")
    print(f"Whisper: {WHISPER_MODEL} | Embedding: {EMBEDDING_MODEL}")
    print(f"Gemini models:")
    for m in GEMINI_MODELS:
        print(f"  - {m['id']} ({m['label']}) — ${m['input_cost_per_1m']}/${m['output_cost_per_1m']} per 1M in/out")
    print("=" * 80)

    results: list[SampleResult] = []
    for s in SAMPLES:
        print(f"\n[run] {s.name} ({s.kind})... ", end="", flush=True)
        r = await run_sample(s, openai_client, gemini_client, probe_headers)
        results.append(r)
        if r.failure_step:
            err_step = r.failure_step.split(":")[0]
            err_msg: str
            if err_step == "distill":
                model_id = r.failure_step.split(":", 1)[1] if ":" in r.failure_step else ""
                dr = r.distills.get(model_id)
                err_msg = dr.error or "(none)" if dr else "(missing)"
            elif err_step in {"transcription", "embedding"}:
                step_obj = getattr(r, err_step)
                err_msg = step_obj.error or "(none)"
            else:
                err_msg = r.failure_step
            print(f"FAIL at {r.failure_step}: {err_msg}")
        else:
            ms_list = " / ".join(f"{mid.split('-')[-1]}={ms}ms" for mid, ms in r.total_ms_per_model.items())
            print(f"OK {ms_list}")

    # raw results — 모델별 distill 모두 포함
    print("\n" + "=" * 80)
    print("RAW RESULTS (JSON):")
    print("=" * 80)
    raw_json = [
        {
            "sample": r.sample,
            "kind": r.kind,
            "transcription": {
                "elapsed_ms": r.transcription.elapsed_ms,
                "cost_usd": r.transcription.cost_usd,
                "success": r.transcription.success,
                "error": r.transcription.error,
            },
            "distills": {
                mid: {
                    "elapsed_ms": d.elapsed_ms,
                    "cost_usd": d.cost_usd,
                    "success": d.success,
                    "error": d.error,
                    "tokens": d.output if isinstance(d.output, dict) else None,
                }
                for mid, d in r.distills.items()
            },
            "embedding": {
                "elapsed_ms": r.embedding.elapsed_ms,
                "cost_usd": r.embedding.cost_usd,
                "success": r.embedding.success,
                "error": r.embedding.error,
            },
            "total_ms_per_model": r.total_ms_per_model,
            "total_cost_per_model": r.total_cost_per_model,
            "failure_step": r.failure_step,
        }
        for r in results
    ]
    print(json.dumps(raw_json, ensure_ascii=False, indent=2))

    # aggregate per model + thresholds
    print("\n" + "=" * 80)
    print("PER-MODEL AGGREGATE:")
    print("=" * 80)
    all_violations: list[str] = []
    for m in GEMINI_MODELS:
        agg = aggregate_per_model(results, m["id"])
        print(f"\n{m['id']} ({m['label']}):")
        print(json.dumps(agg, ensure_ascii=False, indent=2))
        all_violations.extend(evaluate_thresholds(agg, m["id"]))

    # ADR-019: 모델 비교
    print("\n" + "=" * 80)
    print("MODEL COMPARISON (ADR-019):")
    print("=" * 80)
    comparison = compute_model_comparison(results)
    print(json.dumps(comparison, ensure_ascii=False, indent=2))

    print("\nTHRESHOLD VIOLATIONS:")
    if all_violations:
        for v in all_violations:
            print(f"  ❌ {v}")
    else:
        print("  ✅ 두 모델 모두 위반 없음 — ADR-019 swap OK")

    # EOL probe (Q3) — 모델별
    print("\n" + "=" * 80)
    print("GEMINI EOL PROBE (Q3 inline):")
    print("=" * 80)
    if probe_headers:
        for p in probe_headers:
            print(json.dumps(p, ensure_ascii=False, indent=2, default=str))
            print()
    else:
        print("(no probe data — distill 모두 실패)")
    print(">> 위 dump에서 deprecation / sunset / x-deprecation header 존재 시 별도 ADR 가속")


if __name__ == "__main__":
    asyncio.run(main())
