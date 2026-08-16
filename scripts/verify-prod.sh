#!/usr/bin/env bash
# Sprint 18 — production smoke / verify
# BL-040 (RAG visibility) + BL-036 (perf indexes) + BL-034 (asyncpg pool) 효과 측정 entry.
#
# 사용:
#   ./scripts/verify-prod.sh [base-url]
#
# 기본 base-url: https://kairos-api.woosung.dev
# 환경변수 (optional):
#   KAIROS_JWT  — 인증 필요 endpoint 검증용 토큰. 미설정 시 health 만.
#   WORKSPACE_ID — workspace endpoints 검증용 UUID (KAIROS_JWT 와 같이).

set -euo pipefail

BASE_URL="${1:-https://kairos-api.woosung.dev}"
JWT="${KAIROS_JWT:-}"
WS_ID="${WORKSPACE_ID:-}"

GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
RESET="\033[0m"

ok() { printf "${GREEN}✅ %s${RESET}\n" "$1"; }
fail() { printf "${RED}❌ %s${RESET}\n" "$1"; }
info() { printf "${YELLOW}ℹ  %s${RESET}\n" "$1"; }

echo "=== Kairos production verify — ${BASE_URL} ==="

# ── 1. /health ────────────────────────────────────────────────────────
start=$(date +%s%N)
status=$(curl -s -o /tmp/verify-health.json -w "%{http_code}" --max-time 15 "${BASE_URL}/api/v1/health" || echo "000")
end=$(date +%s%N)
elapsed_ms=$(( (end - start) / 1000000 ))

if [ "$status" = "200" ]; then
  ok "GET /api/v1/health  (HTTP 200, ${elapsed_ms}ms)"
  if [ "$elapsed_ms" -gt 2000 ]; then
    info "  ⚠ 응답 ${elapsed_ms}ms — Cloud Run cold start 가능성 (warm 후 재측정)"
  fi
else
  fail "GET /api/v1/health  (HTTP $status, ${elapsed_ms}ms)"
  echo "  body: $(cat /tmp/verify-health.json 2>/dev/null | head -c 200)"
  exit 1
fi

# ── 2. asyncpg pool 효과 — 연속 호출 (BL-034) ────────────────────────
info "  → BL-034 pool_pre_ping: 연속 5회 health 호출 (intermittent 500 회귀 검출)"
fail_count=0
for i in $(seq 1 5); do
  s=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${BASE_URL}/api/v1/health" || echo "000")
  [ "$s" != "200" ] && fail_count=$((fail_count + 1))
  sleep 1
done
if [ "$fail_count" = "0" ]; then
  ok "  연속 5회 모두 200 — pool_pre_ping 효과 정상"
else
  fail "  ${fail_count}/5 실패 — BL-034 회귀 가능성, BE 로그 확인 필요"
fi

# ── 3. 인증 endpoint (JWT 있을 때만) ─────────────────────────────────
if [ -z "$JWT" ]; then
  info "KAIROS_JWT 미설정 — 인증 endpoint 검증 skip."
  info "  사용법: export KAIROS_JWT='eyJ...' && ./scripts/verify-prod.sh"
  exit 0
fi

start=$(date +%s%N)
status=$(curl -s -o /tmp/verify-ws.json -w "%{http_code}" --max-time 15 \
  -H "Authorization: Bearer $JWT" "${BASE_URL}/api/v1/workspaces" || echo "000")
end=$(date +%s%N)
elapsed_ms=$(( (end - start) / 1000000 ))

if [ "$status" = "200" ]; then
  ok "GET /api/v1/workspaces  (HTTP 200, ${elapsed_ms}ms)"
  count=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d) if isinstance(d, list) else 0)" < /tmp/verify-ws.json 2>/dev/null || echo "?")
  info "  workspaces count: $count"
else
  fail "GET /api/v1/workspaces  (HTTP $status, ${elapsed_ms}ms)"
  exit 1
fi

# ── 4. BL-036 hot path 측정 (projects + members) ──────────────────────
if [ -z "$WS_ID" ]; then
  info "WORKSPACE_ID 미설정 — BL-036 측정 skip."
  exit 0
fi

# 4-1. projects list (status=active) — BL-036 인덱스 효과
start=$(date +%s%N)
status=$(curl -s -o /tmp/verify-proj.json -w "%{http_code}" --max-time 15 \
  -H "Authorization: Bearer $JWT" "${BASE_URL}/api/v1/workspaces/${WS_ID}/projects?status=active" || echo "000")
end=$(date +%s%N)
elapsed_ms=$(( (end - start) / 1000000 ))

if [ "$status" = "200" ]; then
  ok "GET /workspaces/{ws_id}/projects  (HTTP 200, ${elapsed_ms}ms)"
  if [ "$elapsed_ms" -lt 500 ]; then
    ok "  BL-036 perf: ${elapsed_ms}ms < 500ms 목표 달성"
  else
    info "  BL-036 perf: ${elapsed_ms}ms — 목표 500ms 초과 (Neon network 변동 가능)"
  fi
else
  fail "projects list HTTP $status"
fi

# 4-2. members list — BL-036 workspace_members 인덱스 효과
start=$(date +%s%N)
status=$(curl -s -o /tmp/verify-mem.json -w "%{http_code}" --max-time 15 \
  -H "Authorization: Bearer $JWT" "${BASE_URL}/api/v1/workspaces/${WS_ID}/members" || echo "000")
end=$(date +%s%N)
elapsed_ms=$(( (end - start) / 1000000 ))

if [ "$status" = "200" ]; then
  ok "GET /workspaces/{ws_id}/members  (HTTP 200, ${elapsed_ms}ms)"
  if [ "$elapsed_ms" -lt 500 ]; then
    ok "  BL-036 perf: ${elapsed_ms}ms < 500ms 목표 달성"
  else
    info "  BL-036 perf: ${elapsed_ms}ms — 목표 500ms 초과"
  fi
else
  fail "members list HTTP $status"
fi

echo ""
echo "=== verify 완료 ==="
