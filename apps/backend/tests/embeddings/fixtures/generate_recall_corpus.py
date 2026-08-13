#!/usr/bin/env python3
# Sprint 16 ADR-020 recall@10 ground truth corpus 생성 (옵션 B 합성)
"""합성 recall corpus 생성 — 결정론적 + 1536d + cosine ground truth.

당근 DB 밋업 §4 — recall 회귀 검증용 fixture. 실제 production export (옵션 A)가
이상적이나 환경 의존이라 본 스크립트로 옵션 B (합성) 폴백 제공.

사용:
    cd apps/backend
    uv run python tests/embeddings/fixtures/generate_recall_corpus.py
    # 출력: apps/backend/tests/embeddings/fixtures/recall_corpus.json

옵션:
    --chunks N    (default 200)
    --queries N   (default 30)
    --seed N      (default 42)
    --dim N       (default 1536)

설계:
- chunk: 정규분포 + L2 정규화 (OpenAI text-embedding-3-small 분포 모사)
- query: chunk 일부를 노이즈 추가하여 변형. ground truth = cosine top-10
- fp16 정밀도 손실 검증용으로 cosine 미세 차이가 나는 query 포함

ADR-020 §"Verification" 합격선: recall@10 >= baseline * 0.95.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import uuid
from pathlib import Path

WORKSPACE_ID = "00000000-0000-0000-0000-000000000aaa"
OUTPUT = Path(__file__).parent / "recall_corpus.json"


def _l2_normalize(vec: list[float]) -> list[float]:
    """L2 정규화 — OpenAI text-embedding-3-small과 동일 norm 분포."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def _gaussian_vec(rng: random.Random, dim: int) -> list[float]:
    """정규분포 (μ=0, σ=1) 벡터 + L2 정규화."""
    return _l2_normalize([rng.gauss(0.0, 1.0) for _ in range(dim)])


def _add_noise(rng: random.Random, vec: list[float], noise_std: float) -> list[float]:
    """원본 vector에 가우시안 노이즈 추가 후 재정규화."""
    noisy = [v + rng.gauss(0.0, noise_std) for v in vec]
    return _l2_normalize(noisy)


def _cosine(a: list[float], b: list[float]) -> float:
    """L2 정규화된 벡터 가정 — dot product = cosine similarity."""
    return sum(x * y for x, y in zip(a, b))


def _top_k_ids(query: list[float], chunks: list[dict], k: int) -> list[str]:
    """cosine 기준 top-K chunk id."""
    scored = [(c["id"], _cosine(query, c["embedding"])) for c in chunks]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [cid for cid, _ in scored[:k]]


def generate(
    n_chunks: int, n_queries: int, dim: int, seed: int
) -> dict:
    rng = random.Random(seed)
    chunks = []
    for _ in range(n_chunks):
        chunks.append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "embedding": _gaussian_vec(rng, dim),
                "workspace_id": WORKSPACE_ID,
            }
        )

    queries = []
    for qi in range(n_queries):
        # 30% — 기존 chunk 그대로 (recall 1.0 예상)
        # 40% — 기존 chunk + 소량 노이즈 (recall 0.9+ 예상)
        # 30% — 새 random vector (낮은 recall, ranking 검증)
        bucket = qi % 10
        if bucket < 3:
            anchor = rng.choice(chunks)
            qvec = list(anchor["embedding"])
        elif bucket < 7:
            anchor = rng.choice(chunks)
            qvec = _add_noise(rng, anchor["embedding"], noise_std=0.05)
        else:
            qvec = _gaussian_vec(rng, dim)

        queries.append(
            {
                "id": f"q{qi:03d}",
                "embedding": qvec,
                "workspace_id": WORKSPACE_ID,
                "expected_top10": _top_k_ids(qvec, chunks, 10),
            }
        )

    return {
        "version": "2026-05-15-sprint16-adr-020",
        "seed": seed,
        "dim": dim,
        "n_chunks": n_chunks,
        "n_queries": n_queries,
        "chunks": chunks,
        "queries": queries,
    }


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="recall corpus 합성 생성")
    p.add_argument("--chunks", type=int, default=200)
    p.add_argument("--queries", type=int, default=30)
    p.add_argument("--dim", type=int, default=1536)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=OUTPUT)
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    corpus = generate(
        n_chunks=args.chunks,
        n_queries=args.queries,
        dim=args.dim,
        seed=args.seed,
    )
    args.out.write_text(json.dumps(corpus))
    print(f"[done] {args.out} (chunks={args.chunks}, queries={args.queries}, dim={args.dim})")
    print(f"size: {args.out.stat().st_size / 1024 / 1024:.2f} MB")
