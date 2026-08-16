# Sprint 15 dogfooding 자동화 — 5+1 시나리오 BE smoke test (founder 1h → ~10분 절감)
"""Sprint 15 dogfooding smoke test.

5 시나리오 BE 직접 호출 + 1 admin metric check:
1. /workspaces → personal + team 식별
2. POST /memory (text) → 202 + memory_id
3. Polling /memory/{id} → status=active + distilled_json
4. GET /memory/recall?q=keyword → memory_id 매치
5. POST /memory/{id}/promote → 202 + new_memory_id + audit_id
6. GET /memory/metrics → 5 metric 필드

실행:
  # 1. backend uvicorn 띄운 후
  cd apps/api && uv run uvicorn src.main:app --reload &

  # 2. Clerk JWT 토큰 추출 (브라우저 devtools / Clerk dashboard)
  export CLERK_JWT=eyJ...

  # 3. smoke 실행
  cd apps/api && uv run python scripts/dogfood_smoke.py --token $CLERK_JWT

옵션:
  --base-url   http://localhost:8000 (default)
  --token      Clerk JWT (env CLERK_JWT 도 OK, required)
  --keyword    capture 텍스트 + recall 키워드 (default "테스트메모카이로스")
  --personal-id  personal workspace UUID 명시 (생략 시 type=personal 자동)
  --team-id      team workspace UUID 명시 (생략 시 첫 type=team)
  --poll-timeout 60 (sec, distill 완료 대기)
  --skip-promote false (team 없을 때 promote step skip)

출력: 각 step PASS/FAIL + 누적 elapsed + 발견 bug log.
exit code: 0=all pass / 1=any fail / 2=usage error.

이 script는 read-write 다중 API 호출. R8 14일 demo 중 사용 시
demo 환경 분리 권장 (e2e_test_* prefix 등).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class StepLog:
    name: str
    success: bool
    elapsed_ms: int
    detail: str = ""
    data: Any = None


@dataclass
class SmokeContext:
    base_url: str
    token: str
    keyword: str
    poll_timeout_sec: int
    personal_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    memory_id: uuid.UUID | None = None
    promoted_memory_id: uuid.UUID | None = None
    skip_promote: bool = False
    steps: list[StepLog] = field(default_factory=list)


def log_step(ctx: SmokeContext, name: str, success: bool, elapsed_ms: int, detail: str = "", data: Any = None) -> None:
    s = StepLog(name=name, success=success, elapsed_ms=elapsed_ms, detail=detail, data=data)
    ctx.steps.append(s)
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status}  {name:<28}  {elapsed_ms:>5}ms  {detail}")


async def step_1_workspaces(client: httpx.AsyncClient, ctx: SmokeContext) -> bool:
    """1. /workspaces → personal + team 식별."""
    start = time.time()
    try:
        r = await client.get(f"{ctx.base_url}/api/v1/workspaces")
        elapsed = int((time.time() - start) * 1000)
        if r.status_code != 200:
            log_step(ctx, "1. list_workspaces", False, elapsed, f"status={r.status_code} body={r.text[:200]}")
            return False
        rows = r.json()
        # 사용자 override 우선
        if ctx.personal_id is None:
            personal = next((w for w in rows if w.get("type") == "personal"), None)
            if personal is None:
                log_step(ctx, "1. list_workspaces", False, elapsed, f"no personal workspace in {len(rows)} rows — Sprint 15 R5 seed 미작동 가능")
                return False
            ctx.personal_id = uuid.UUID(personal["id"])
        if ctx.team_id is None and not ctx.skip_promote:
            team = next((w for w in rows if w.get("type") == "team" and uuid.UUID(w["id"]) != ctx.personal_id), None)
            if team is None:
                log_step(ctx, "1. list_workspaces", True, elapsed,
                         f"personal={ctx.personal_id} (no team — promote step skipped)")
                ctx.skip_promote = True
                return True
            ctx.team_id = uuid.UUID(team["id"])
        log_step(ctx, "1. list_workspaces", True, elapsed,
                 f"personal={ctx.personal_id} team={ctx.team_id} (total={len(rows)})")
        return True
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        log_step(ctx, "1. list_workspaces", False, elapsed, f"exception: {e}")
        return False


async def step_2_capture(client: httpx.AsyncClient, ctx: SmokeContext) -> bool:
    """2. POST /memory text capture → 202 + memory_id."""
    assert ctx.personal_id is not None
    start = time.time()
    text = f"{ctx.keyword} — Sprint 15 dogfooding smoke {uuid.uuid4().hex[:8]}"
    try:
        r = await client.post(
            f"{ctx.base_url}/api/v1/workspaces/{ctx.personal_id}/memory",
            data={"text": text},
        )
        elapsed = int((time.time() - start) * 1000)
        if r.status_code != 202:
            log_step(ctx, "2. capture_text", False, elapsed, f"status={r.status_code} body={r.text[:200]}")
            return False
        body = r.json()
        ctx.memory_id = uuid.UUID(body["memory_id"])
        ok = body["status"] in {"processing", "active"}
        log_step(ctx, "2. capture_text", ok, elapsed,
                 f"memory_id={ctx.memory_id} status={body['status']}")
        return ok
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        log_step(ctx, "2. capture_text", False, elapsed, f"exception: {e}")
        return False


async def step_3_poll_distill(client: httpx.AsyncClient, ctx: SmokeContext) -> bool:
    """3. Polling /memory/{id} → status=active + distilled_json 채워짐."""
    assert ctx.personal_id is not None and ctx.memory_id is not None
    start = time.time()
    deadline = start + ctx.poll_timeout_sec
    last_status = "unknown"
    distilled: dict | None = None
    while time.time() < deadline:
        try:
            r = await client.get(
                f"{ctx.base_url}/api/v1/workspaces/{ctx.personal_id}/memory/{ctx.memory_id}"
            )
            if r.status_code != 200:
                await asyncio.sleep(1.0)
                continue
            body = r.json()
            last_status = body.get("status", "unknown")
            distilled = body.get("distilled_json")
            if last_status == "active" and distilled:
                elapsed = int((time.time() - start) * 1000)
                schema_ok = all(k in distilled for k in ("title", "atomic_notes", "suggested_visibility"))
                log_step(ctx, "3. poll_distill", schema_ok, elapsed,
                         f"status=active schema_ok={schema_ok} title='{distilled.get('title', '')[:20]}'")
                return schema_ok
            if last_status == "failed":
                elapsed = int((time.time() - start) * 1000)
                log_step(ctx, "3. poll_distill", False, elapsed, "status=failed (distill error)")
                return False
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            log_step(ctx, "3. poll_distill", False, elapsed, f"exception: {e}")
            return False
        await asyncio.sleep(1.0)
    elapsed = int((time.time() - start) * 1000)
    log_step(ctx, "3. poll_distill", False, elapsed,
             f"timeout {ctx.poll_timeout_sec}s last_status={last_status}")
    return False


async def step_4_recall(client: httpx.AsyncClient, ctx: SmokeContext) -> bool:
    """4. GET /memory/recall?q=keyword → memory_id 매치."""
    assert ctx.personal_id is not None and ctx.memory_id is not None
    start = time.time()
    try:
        r = await client.get(
            f"{ctx.base_url}/api/v1/workspaces/{ctx.personal_id}/memory/recall",
            params={"q": ctx.keyword},
        )
        elapsed = int((time.time() - start) * 1000)
        if r.status_code != 200:
            log_step(ctx, "4. recall", False, elapsed, f"status={r.status_code} body={r.text[:200]}")
            return False
        body = r.json()
        sources = body.get("sources", [])
        matched = any(uuid.UUID(s["memory_id"]) == ctx.memory_id for s in sources)
        match_types = [s.get("match_type") for s in sources]
        fallback = body.get("fallback_used", False)
        log_step(ctx, "4. recall", matched, elapsed,
                 f"matched={matched} top_k={len(sources)} types={match_types} fallback={fallback}")
        return matched
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        log_step(ctx, "4. recall", False, elapsed, f"exception: {e}")
        return False


async def step_5_promote(client: httpx.AsyncClient, ctx: SmokeContext) -> bool:
    """5. POST /memory/{id}/promote → 202 + new_memory_id + audit_id."""
    if ctx.skip_promote:
        log_step(ctx, "5. promote", True, 0, "skipped (no team workspace)")
        return True
    assert ctx.personal_id is not None and ctx.team_id is not None and ctx.memory_id is not None
    start = time.time()
    try:
        r = await client.post(
            f"{ctx.base_url}/api/v1/workspaces/{ctx.personal_id}/memory/{ctx.memory_id}/promote",
            json={"target_workspace_id": str(ctx.team_id)},
        )
        elapsed = int((time.time() - start) * 1000)
        if r.status_code != 202:
            log_step(ctx, "5. promote", False, elapsed, f"status={r.status_code} body={r.text[:200]}")
            return False
        body = r.json()
        ctx.promoted_memory_id = uuid.UUID(body["new_memory_id"])
        audit_id = body.get("audit_id")
        ok = body["status"] in {"processing", "active", "promoted"}
        log_step(ctx, "5. promote", ok, elapsed,
                 f"new_id={ctx.promoted_memory_id} audit_id={audit_id} status={body['status']}")
        return ok
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        log_step(ctx, "5. promote", False, elapsed, f"exception: {e}")
        return False


async def step_6_metrics(client: httpx.AsyncClient, ctx: SmokeContext) -> bool:
    """6. GET /memory/metrics → 5 metric 필드 (R7)."""
    assert ctx.personal_id is not None
    start = time.time()
    try:
        r = await client.get(
            f"{ctx.base_url}/api/v1/workspaces/{ctx.personal_id}/memory/metrics"
        )
        elapsed = int((time.time() - start) * 1000)
        if r.status_code != 200:
            log_step(ctx, "6. metrics", False, elapsed, f"status={r.status_code} body={r.text[:200]}")
            return False
        body = r.json()
        required = {"capture_count", "recall_count", "promote_count", "recall_p50_ms", "recall_p95_ms"}
        missing = required - set(body.keys())
        ok = not missing
        log_step(ctx, "6. metrics", ok, elapsed,
                 f"missing={missing or 'none'} cap={body.get('capture_count')} "
                 f"rec={body.get('recall_count')} prom={body.get('promote_count')} "
                 f"p50={body.get('recall_p50_ms')}ms p95={body.get('recall_p95_ms')}ms")
        return ok
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        log_step(ctx, "6. metrics", False, elapsed, f"exception: {e}")
        return False


async def run(ctx: SmokeContext) -> int:
    print("=" * 80)
    print(f"Sprint 15 Dogfooding Smoke — {ctx.base_url}")
    print("=" * 80)

    headers = {"Authorization": f"Bearer {ctx.token}"}
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        steps = [
            step_1_workspaces,
            step_2_capture,
            step_3_poll_distill,
            step_4_recall,
            step_5_promote,
            step_6_metrics,
        ]
        for step_fn in steps:
            ok = await step_fn(client, ctx)
            if not ok and step_fn in (step_1_workspaces, step_2_capture):
                # 첫 두 step은 후속 의존성 → fail-fast
                print("\n⚠️  의존 step 실패 — 후속 step 중단.")
                break

    total_ms = sum(s.elapsed_ms for s in ctx.steps)
    pass_count = sum(1 for s in ctx.steps if s.success)
    fail_count = len(ctx.steps) - pass_count

    print("\n" + "=" * 80)
    print(f"SUMMARY  {pass_count}/{len(ctx.steps)} pass  total={total_ms}ms")
    print("=" * 80)
    if fail_count:
        print("\n실패 step 상세:")
        for s in ctx.steps:
            if not s.success:
                print(f"  ❌ {s.name}: {s.detail}")
        return 1
    print("\n✅ 모든 step pass — Sprint 15 dogfooding 5+1 시나리오 OK")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sprint 15 dogfooding smoke test")
    p.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://localhost:8000"))
    p.add_argument("--token", default=os.environ.get("CLERK_JWT", ""))
    p.add_argument("--keyword", default="테스트메모카이로스")
    p.add_argument("--personal-id", default=None)
    p.add_argument("--team-id", default=None)
    p.add_argument("--poll-timeout", type=int, default=60)
    p.add_argument("--skip-promote", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.token:
        print("ERROR: Clerk JWT 필요. --token 또는 CLERK_JWT 환경변수 설정.", file=sys.stderr)
        return 2
    ctx = SmokeContext(
        base_url=args.base_url.rstrip("/"),
        token=args.token,
        keyword=args.keyword,
        poll_timeout_sec=args.poll_timeout,
        personal_id=uuid.UUID(args.personal_id) if args.personal_id else None,
        team_id=uuid.UUID(args.team_id) if args.team_id else None,
        skip_promote=args.skip_promote,
    )
    return asyncio.run(run(ctx))


if __name__ == "__main__":
    sys.exit(main())
