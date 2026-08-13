#!/usr/bin/env python3
# RAG stage 타이밍 분포 측정 — PERF-r2-3 / BL-S27e-1 판정 근거 (Stage 2 재평가 2026-07-05)
"""RagService.ask 를 직접 조립·호출해 rag.timing 분포를 수집한다.

HTTP/SSE/auth 층은 생략 — 측정 대상(embed/vector/text/llm)이 전부 service 내부 구간.
`time_range="6m"` 고정으로 semantic cache read+write 둘 다 skip → 전 run cold path,
캐시 오염 0 (Codex F-2: time_range 필터 시 cache 미사용).

사용 예:
    cd apps/backend
    uv run python scripts/rag_timing_bench.py                       # team-fixtures 기본값
    uv run python scripts/rag_timing_bench.py --runs-per-question 4 \
        --workspace-id <uuid> --user-id <uuid> --json-out out.json

판정 기준 (승인된 plan):
    진행: p50(gain) >= 300ms 또는 p50(gain) >= p50(total) * 10%  (gain = min(vector, text))
    skip: llm 비중 p50 >= 90% 이고 p50(gain) < 150ms
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import statistics
import sys
import uuid
from pathlib import Path

# 스크립트 실행 시 apps/backend/src 모듈 import 가능하도록 sys.path 보정
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import text  # noqa: E402

from src.common.database import (  # noqa: E402
    dispose_engine,
    get_session_factory,
    init_engine,
)
from src.core.config import get_settings  # noqa: E402
from src.embeddings.repository import EmbeddingRepository  # noqa: E402
from src.embeddings.service import EmbeddingService  # noqa: E402
from src.rag.service import RagService  # noqa: E402
from src.services.ai_processing import AIProcessingService  # noqa: E402

_FIXTURES_PATH = _BACKEND_DIR.parent / "frontend" / "e2e" / ".auth" / "team-fixtures.json"

_QUESTIONS = [
    "최근 회의에서 결정된 사항들을 요약해줘",
    "진행 중인 프로젝트의 주요 액션 아이템은 뭐야?",
    "팀이 논의한 기술적 이슈에는 어떤 것들이 있어?",
    "노트에 기록된 아이디어 중 중요한 것을 알려줘",
    "지난 스프린트에서 완료된 작업은 무엇인가?",
]

_TIMING_RE = re.compile(
    r"rag\.timing embed=(?P<embed>\d+)ms search=(?P<search>\d+)ms "
    r"vector=(?P<vector>\d+)ms text=(?P<text>\d+)ms "
    r"enrich=(?P<enrich>\d+)ms commit=(?P<commit>\d+)ms "
    r"llm=(?P<llm>\d+)ms total=(?P<total>\d+)ms"
)


class _TimingCollector(logging.Handler):
    """src.rag.service 의 rag.timing 라인만 파싱해 축적."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.samples: list[dict[str, int]] = []

    def emit(self, record: logging.LogRecord) -> None:
        m = _TIMING_RE.search(record.getMessage())
        if m:
            self.samples.append({k: int(v) for k, v in m.groupdict().items()})


def _percentile(values: list[int], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = (len(ordered) - 1) * pct
    lo, hi = int(idx), min(int(idx) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (idx - lo)


def _load_fixture_defaults() -> tuple[str | None, str | None]:
    if not _FIXTURES_PATH.exists():
        return None, None
    data = json.loads(_FIXTURES_PATH.read_text())
    return data.get("teamWsId"), data.get("ownerUserId")


async def _precheck_chunks(session_factory, workspace_id: uuid.UUID) -> int:
    """6개월 내 L2 chunk 수 — 0 이면 fused 빈 결과로 timing 이 안 찍힘."""
    async with session_factory() as session:
        result = await session.execute(
            text(
                "SELECT count(*) FROM embedding_chunks "
                "WHERE workspace_id = :wid AND chunk_level = 2 "
                "AND created_at >= now() - interval '6 months'"
            ),
            {"wid": str(workspace_id)},
        )
        return int(result.scalar_one())


async def _run_bench(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    runs_per_question: int,
    json_out: str | None,
) -> int:
    settings = get_settings()
    init_engine(settings.database_url)
    session_factory = get_session_factory()

    chunk_count = await _precheck_chunks(session_factory, workspace_id)
    print(f"[precheck] workspace={workspace_id} 6개월 내 L2 chunks={chunk_count}")
    if chunk_count == 0:
        print(
            "[abort] chunk 0건 — timing 이 기록되지 않습니다. "
            "--workspace-id 로 데이터 있는 ws 지정 또는 scripts/seed_qa_fixtures.py 시드 후 재실행."
        )
        await dispose_engine()
        return 1

    collector = _TimingCollector()
    rag_logger = logging.getLogger("src.rag.service")
    rag_logger.setLevel(logging.INFO)
    rag_logger.addHandler(collector)

    total_runs = len(_QUESTIONS) * runs_per_question
    run_no = 0
    try:
        for round_idx in range(runs_per_question):
            for q in _QUESTIONS:
                run_no += 1
                # run 마다 fresh session — 요청 스코프 세션과 동일 수명 모델
                async with session_factory() as session:
                    repo = EmbeddingRepository(session)
                    service = RagService(
                        embedding_repo=repo,
                        embedding_service=EmbeddingService(repo),
                        ai_service=AIProcessingService(),
                    )
                    before = len(collector.samples)
                    events = 0
                    async for _event in service.ask(
                        f"{q} (측정 {round_idx + 1}회차)",
                        workspace_id,
                        requester_user_id=user_id,
                        requester_role="owner",
                        time_range="6m",  # cache read+write 둘 다 skip → 전 run cold
                    ):
                        events += 1
                    got = len(collector.samples) > before
                    print(
                        f"[run {run_no:02d}/{total_runs}] events={events} "
                        f"timing={'OK' if got else 'MISSING(빈 결과/AI 오류 경로)'}"
                    )
    finally:
        rag_logger.removeHandler(collector)
        await dispose_engine()

    samples = collector.samples
    if not samples:
        print("[abort] 수집된 rag.timing 0건 — 전 run 이 빈 결과/오류 경로.")
        return 1

    fields = ["embed", "search", "vector", "text", "enrich", "commit", "llm", "total"]
    gains = [min(s["vector"], s["text"]) for s in samples]
    llm_ratios = [s["llm"] / s["total"] * 100 for s in samples if s["total"] > 0]

    print(f"\n=== rag.timing 분포 (n={len(samples)}) ===")
    print(f"{'stage':<8}{'p50(ms)':>10}{'p95(ms)':>10}{'mean(ms)':>10}")
    summary: dict[str, dict[str, float]] = {}
    for f in fields:
        vals = [s[f] for s in samples]
        p50, p95 = _percentile(vals, 0.5), _percentile(vals, 0.95)
        summary[f] = {"p50": p50, "p95": p95, "mean": statistics.mean(vals)}
        print(f"{f:<8}{p50:>10.0f}{p95:>10.0f}{statistics.mean(vals):>10.0f}")

    gain_p50 = _percentile(gains, 0.5)
    total_p50 = summary["total"]["p50"]
    llm_ratio_p50 = _percentile([int(r) for r in llm_ratios], 0.5)
    go = gain_p50 >= 300 or (total_p50 > 0 and gain_p50 >= total_p50 * 0.10)
    skip = llm_ratio_p50 >= 90 and gain_p50 < 150
    print(f"\ngain(=min(vector,text)) p50={gain_p50:.0f}ms / llm 비중 p50={llm_ratio_p50:.0f}%")
    print(f"판정: 진행 조건 {'충족' if go else '미충족'} / skip 조건 {'충족' if skip else '미충족'}")

    if json_out:
        Path(json_out).write_text(
            json.dumps(
                {
                    "n": len(samples),
                    "workspace_id": str(workspace_id),
                    "summary": summary,
                    "gain_p50_ms": gain_p50,
                    "llm_ratio_p50_pct": llm_ratio_p50,
                    "go": go,
                    "skip": skip,
                    "samples": samples,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        print(f"[saved] {json_out}")
    return 0


def main() -> int:
    fixture_ws, fixture_user = _load_fixture_defaults()
    parser = argparse.ArgumentParser(description="RAG stage 타이밍 분포 측정")
    parser.add_argument("--workspace-id", default=fixture_ws, help="대상 workspace UUID")
    parser.add_argument("--user-id", default=fixture_user, help="requester user UUID (owner)")
    parser.add_argument("--runs-per-question", type=int, default=4)
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    if not args.workspace_id or not args.user_id:
        parser.error("team-fixtures.json 부재 — --workspace-id / --user-id 를 지정하세요.")

    return asyncio.run(
        _run_bench(
            uuid.UUID(args.workspace_id),
            uuid.UUID(args.user_id),
            args.runs_per_question,
            args.json_out,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
