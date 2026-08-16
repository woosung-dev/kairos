# Sprint 24 Wave 2 T-2 Post-Swap Delta 측정 — gemini-2.5-flash vs gemini-3.1-flash-lite
"""Phase B Gemini swap (003908a) 품질 회귀 검증용 5 시나리오 직접 측정 script.

worktree 한쪽에서 실행 → 결과 JSON dump.
baseline = `003908a~1` checkout 한 별도 worktree, post-swap = main worktree.

Usage:
  cd apps/api
  uv run python -m scripts.sprint24_wave2_delta --output /tmp/post-swap.json

Codex F-2 fix: AIProcessingService 는 class. 인스턴스 method 호출.
Codex F-3 fix: baseline 측정은 worktree 분리 + .env 복사 + 동일 fixture 사용.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# sys.path 에 backend root 추가 (스크립트 단독 실행 대비)
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from src.services.ai_processing import AIProcessingService, GEMINI_MODEL  # noqa: E402  # pyright: ignore[reportMissingImports]
from tests.llm.fixtures.sample_transcripts import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    DELTA_1_RAG_QUESTIONS,
    DELTA_2_MEETING_TRANSCRIPT,
    DELTA_3_ACTION_SAMPLES,
    DELTA_4_KOREAN_SAMPLES,
    DELTA_5_EXISTING_PROJECTS,
    DELTA_5_INBOX_CLASSIFY,
)


# ── DELTA-1: RAG 답변 품질 ──
async def measure_delta_1_rag(svc: AIProcessingService, sources_text: str) -> list[dict]:
    """5 질문 → stream_rag_answer 로 응답 수집. 길이 + raw text 캡쳐."""
    results = []
    for q in DELTA_1_RAG_QUESTIONS:
        start = time.monotonic()
        try:
            chunks: list[str] = []
            async for chunk in svc.stream_rag_answer(question=q, sources_text=sources_text):
                chunks.append(chunk)
            answer = "".join(chunks)
            elapsed = time.monotonic() - start
            results.append({
                "question": q,
                "answer": answer,
                "length_chars": len(answer),
                "elapsed_sec": round(elapsed, 2),
                "error": None,
            })
        except Exception as e:
            results.append({
                "question": q,
                "answer": "",
                "length_chars": 0,
                "elapsed_sec": round(time.monotonic() - start, 2),
                "error": f"{type(e).__name__}: {e}",
            })
    return results


# ── DELTA-2: 회의 요약 ──
async def measure_delta_2_summary(svc: AIProcessingService) -> dict:
    start = time.monotonic()
    try:
        raw = await svc.summarize(DELTA_2_MEETING_TRANSCRIPT)
        elapsed = time.monotonic() - start
        return {
            "transcript_chars": len(DELTA_2_MEETING_TRANSCRIPT),
            "result": raw,
            "summary_chars": len(raw.get("summary", "")),
            "key_decisions_count": len(raw.get("key_decisions", [])),
            "risks_count": len(raw.get("risks_and_issues", [])),
            "participants_count": len(raw.get("participants", [])),
            "topics_count": len(raw.get("topics", [])),
            "next_agenda_count": len(raw.get("next_meeting_agenda", [])),
            "elapsed_sec": round(elapsed, 2),
            "error": None,
        }
    except Exception as e:
        return {
            "transcript_chars": len(DELTA_2_MEETING_TRANSCRIPT),
            "result": {},
            "elapsed_sec": round(time.monotonic() - start, 2),
            "error": f"{type(e).__name__}: {e}",
        }


# ── DELTA-3: 액션 아이템 추출 precision/recall ──
def _has_assignee(text: str, assignee: str) -> bool:
    """assignee 가 text 어딘가에 등장하는지 (`님` 접미사 제거 허용)."""
    if not assignee:
        return True
    return assignee in text or assignee.replace("님", "") in text


def _title_hint_match(text: str, title_hint: str) -> bool:
    """title_hint 토큰의 최소 50% 가 text 에 등장하면 매치 (token-level overlap).

    엄격한 substring 비교는 `랜딩 카피` vs `랜딩 페이지 카피` 같은 어휘 변주에 약함.
    """
    if not title_hint:
        return True
    tokens = [t for t in title_hint.split() if len(t) >= 2]
    if not tokens:
        return title_hint in text
    hits = sum(1 for t in tokens if t in text)
    return hits / len(tokens) >= 0.5


def _compute_action_pr(actions: list[dict], ground_truth: list[dict]) -> dict:
    """Precision/recall — assignee 등장 + title_hint 토큰 50% overlap → TP."""
    if not actions and not ground_truth:
        return {"tp": 0, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0}
    tp = 0
    matched_gt_indices: set[int] = set()
    for a in actions:
        title = (a.get("title") or "")
        desc = (a.get("description") or "")
        text_haystack = title + " " + desc
        for i, gt in enumerate(ground_truth):
            if i in matched_gt_indices:
                continue
            if _has_assignee(text_haystack, gt.get("assignee", "")) and _title_hint_match(text_haystack, gt.get("title_hint", "")):
                matched_gt_indices.add(i)
                tp += 1
                break
    fp = max(0, len(actions) - tp)
    fn = max(0, len(ground_truth) - tp)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
    }


async def measure_delta_3_actions(svc: AIProcessingService) -> dict:
    samples_result = []
    agg_tp = agg_fp = agg_fn = 0
    for sample in DELTA_3_ACTION_SAMPLES:
        start = time.monotonic()
        try:
            raw = await svc.extract_actions_and_link(
                transcript=sample["transcript"],
                summary=sample.get("summary", ""),
                existing_projects=DELTA_5_EXISTING_PROJECTS,
            )
            elapsed = time.monotonic() - start
            actions = raw.get("actionItems", [])
            pr = _compute_action_pr(actions, sample["ground_truth"])
            agg_tp += pr["tp"]
            agg_fp += pr["fp"]
            agg_fn += pr["fn"]
            samples_result.append({
                "transcript_preview": sample["transcript"][:80],
                "ground_truth": sample["ground_truth"],
                "actions": actions,
                "pr": pr,
                "elapsed_sec": round(elapsed, 2),
                "error": None,
            })
        except Exception as e:
            samples_result.append({
                "transcript_preview": sample["transcript"][:80],
                "ground_truth": sample["ground_truth"],
                "actions": [],
                "pr": {"tp": 0, "fp": 0, "fn": len(sample["ground_truth"]), "precision": 0.0, "recall": 0.0},
                "elapsed_sec": round(time.monotonic() - start, 2),
                "error": f"{type(e).__name__}: {e}",
            })
            agg_fn += len(sample["ground_truth"])
    agg_precision = agg_tp / (agg_tp + agg_fp) if (agg_tp + agg_fp) > 0 else 0.0
    agg_recall = agg_tp / (agg_tp + agg_fn) if (agg_tp + agg_fn) > 0 else 0.0
    return {
        "samples": samples_result,
        "aggregate": {
            "tp": agg_tp,
            "fp": agg_fp,
            "fn": agg_fn,
            "precision": round(agg_precision, 3),
            "recall": round(agg_recall, 3),
        },
    }


# ── DELTA-4: 한국어 처리 ──
async def measure_delta_4_korean(svc: AIProcessingService) -> list[dict]:
    """3 sample → summarize. 출력의 summary text 보존 + 정상 파싱 여부 + 길이."""
    results = []
    for sample in DELTA_4_KOREAN_SAMPLES:
        start = time.monotonic()
        try:
            raw = await svc.summarize(sample["content"])
            elapsed = time.monotonic() - start
            summary_text = raw.get("summary", "")
            results.append({
                "label": sample["label"],
                "input": sample["content"],
                "summary": summary_text,
                "summary_chars": len(summary_text),
                "parsed_ok": True,
                "participants": raw.get("participants", []),
                "elapsed_sec": round(elapsed, 2),
                "error": None,
            })
        except Exception as e:
            results.append({
                "label": sample["label"],
                "input": sample["content"],
                "summary": "",
                "summary_chars": 0,
                "parsed_ok": False,
                "participants": [],
                "elapsed_sec": round(time.monotonic() - start, 2),
                "error": f"{type(e).__name__}: {e}",
            })
    return results


# ── DELTA-5: Inbox 자동 분류 confidence ──
async def measure_delta_5_inbox(svc: AIProcessingService) -> dict:
    """10 sample (5 회의 + 5 노트) 를 extract_actions_and_link 로 분류 → suggestedProject 추출."""
    samples_result = []
    confidences: list[float] = []
    auto_confirm_count = 0  # confidence >= 0.7 임계
    correct_match_count = 0
    for sample in DELTA_5_INBOX_CLASSIFY:
        start = time.monotonic()
        try:
            raw = await svc.extract_actions_and_link(
                transcript=sample["content"],
                summary=sample["content"][:80],
                existing_projects=DELTA_5_EXISTING_PROJECTS,
            )
            elapsed = time.monotonic() - start
            suggested = raw.get("suggestedProject", {}) or {}
            confidence = float(suggested.get("confidence") or 0.0)
            confidences.append(confidence)
            if confidence >= 0.7:
                auto_confirm_count += 1
            # 매칭 검증 — existingProjectId 가 expected_project_hint 와 일치하는 project 인지
            existing_id = suggested.get("existingProjectId")
            project_title_match = ""
            for p in DELTA_5_EXISTING_PROJECTS:
                if p["id"] == existing_id:
                    project_title_match = p["title"]
                    break
            is_correct = project_title_match == sample["expected_project_hint"]
            if is_correct:
                correct_match_count += 1
            samples_result.append({
                "kind": sample["kind"],
                "content_preview": sample["content"][:80],
                "expected_project_hint": sample["expected_project_hint"],
                "suggested": suggested,
                "matched_project_title": project_title_match,
                "is_correct": is_correct,
                "confidence": confidence,
                "elapsed_sec": round(elapsed, 2),
                "error": None,
            })
        except Exception as e:
            samples_result.append({
                "kind": sample["kind"],
                "content_preview": sample["content"][:80],
                "expected_project_hint": sample["expected_project_hint"],
                "suggested": {},
                "matched_project_title": "",
                "is_correct": False,
                "confidence": 0.0,
                "elapsed_sec": round(time.monotonic() - start, 2),
                "error": f"{type(e).__name__}: {e}",
            })
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return {
        "samples": samples_result,
        "aggregate": {
            "avg_confidence": round(avg_conf, 3),
            "auto_confirm_ratio": round(auto_confirm_count / len(DELTA_5_INBOX_CLASSIFY), 3),
            "correct_match_ratio": round(correct_match_count / len(DELTA_5_INBOX_CLASSIFY), 3),
            "n": len(DELTA_5_INBOX_CLASSIFY),
        },
    }


# ── 통합 측정 ──
async def measure_all() -> dict[str, Any]:
    svc = AIProcessingService()
    print(f"[measure_all] model={GEMINI_MODEL}", flush=True)
    # DELTA-1 sources 는 DELTA-2 회의 transcript 를 그대로 사용.
    sources_text = (
        "📎 Q3 로드맵 회의 (2026-05-20)\n\n" + DELTA_2_MEETING_TRANSCRIPT
    )
    print("[measure_all] DELTA-1 RAG ...", flush=True)
    d1 = await measure_delta_1_rag(svc, sources_text)
    print("[measure_all] DELTA-2 summary ...", flush=True)
    d2 = await measure_delta_2_summary(svc)
    print("[measure_all] DELTA-3 actions ...", flush=True)
    d3 = await measure_delta_3_actions(svc)
    print("[measure_all] DELTA-4 korean ...", flush=True)
    d4 = await measure_delta_4_korean(svc)
    print("[measure_all] DELTA-5 inbox ...", flush=True)
    d5 = await measure_delta_5_inbox(svc)
    return {
        "model": GEMINI_MODEL,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "delta_1_rag": d1,
        "delta_2_summary": d2,
        "delta_3_actions": d3,
        "delta_4_korean": d4,
        "delta_5_inbox": d5,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sprint 24 Wave 2 Post-Swap Delta 측정")
    parser.add_argument(
        "--output",
        default="/tmp/sprint24-wave2-delta.json",
        help="결과 JSON 출력 경로",
    )
    args = parser.parse_args()
    result = asyncio.run(measure_all())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"[main] Delta result written to {output}")
    # 요약 출력
    d3_agg = result["delta_3_actions"]["aggregate"]
    d5_agg = result["delta_5_inbox"]["aggregate"]
    print(f"[main] DELTA-3 precision={d3_agg['precision']} recall={d3_agg['recall']}")
    print(f"[main] DELTA-5 avg_confidence={d5_agg['avg_confidence']} correct_match_ratio={d5_agg['correct_match_ratio']}")


if __name__ == "__main__":
    main()
