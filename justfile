# Kairos 단일 명령 진입점 (ADR-027 D3).
# ⚠️ 테스트/빌드 recipe 는 CI(.github/workflows/test.yml)와 invocation 을
#    문자 그대로 동일하게 유지한다 — 여기를 바꾸면 test.yml 도 같이 바꾼다.

set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

install:
    cd apps/backend && uv sync --frozen
    cd apps/web && pnpm install --frozen-lockfile

be-dev:
    cd apps/backend && uv run uvicorn src.main:app --reload --port 8000

# CI 와 동일 (README 의 `uv run pytest -v` 아님 — transcription/r2-cors 2개 제외가 정본)
be-test:
    cd apps/backend && uv run pytest --ignore=tests/services/test_transcription.py --ignore=tests/test_r2_cors_regression.py -v

be-migrate:
    cd apps/backend && uv run alembic upgrade head

fe-dev:
    cd apps/web && pnpm dev

fe-test:
    cd apps/web && pnpm test

fe-typecheck:
    cd apps/web && pnpm typecheck

fe-lint:
    cd apps/web && pnpm lint

fe-build:
    cd apps/web && pnpm build

e2e:
    cd apps/web && pnpm e2e

# ── API 계약 (ADR-027 D2) ─────────────────────────────────────────────
openapi-export:
    cd apps/backend && uv run python -m scripts.export_openapi

types-gen:
    cd apps/web && pnpm gen:api

contracts: openapi-export types-gen

# CI contract-check job 과 동일한 drift 게이트
contracts-check: contracts
    git diff --exit-code -- contracts/ apps/web/src/types/api.gen.ts

verify-prod *args:
    ./scripts/verify-prod.sh {{args}}
