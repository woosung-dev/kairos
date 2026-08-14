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

# ── OCI 배포 (ADR-028) ────────────────────────────────────────────────
# 원격 명령은 전부 `bash -lc` 로 감싼다 — 비로그인 ssh 셸의 PATH 에 docker compose 가 없다.
oci_host := "truewords-oracle"
oci_dir := "~/kairos"
oci_compose := "docker compose -f docker-compose.prod.yml"

# 배포 전 필수 확인. BackgroundTasks 는 재시도가 없어서 처리 중인 회의가 있는 상태로
# 컨테이너를 교체하면 그 회의는 transcribing 상태로 영구 정지한다.
deploy-preflight:
    @echo "── 진행 중인 회의 처리 (0 이어야 배포 가능) ──"
    # SQL 은 stdin 으로 넘긴다. 인라인 -c 는 just/shell/ssh 3중 이스케이프를 타면서
    # 작은따옴표가 깨지고 `$$` 는 shell PID 로 치환된다 (2026-08-14 실측).
    # 최근 2시간 내 갱신된 것만 센다. 최장 작업이 ~15분이므로 그보다 오래된 것은
    # 이미 죽은 좀비이고(2026-05 에 멈춘 6건 실재), 그걸로 배포를 막으면 게이트가 무의미해진다.
    printf "SELECT count(*) FROM meetings WHERE status IN ('transcribing','analyzing') AND updated_at > now() - interval '2 hours';" | ssh {{oci_host}} 'bash -lc "docker exec -i kairos-db psql -U kairos -d kairos -tA"'
    @echo "── .env 인코딩 게이트 (출력 0줄이어야 정상) ──"
    ssh {{oci_host}} 'bash -lc "LC_ALL=C grep -n \"[^[:print:][:space:]]\" {{oci_dir}}/.env || true"'

# 이미지 2종 arm64 빌드. FE 는 NEXT_PUBLIC_* 이 빌드타임 인라인이라 build.env 가 필요하다.
deploy-build TAG:
    docker buildx build --platform linux/arm64 -t kairos-api:{{TAG}} --load apps/backend
    set -a && source deploy/oci/build.env && set +a && \
      docker buildx build --platform linux/arm64 -t kairos-web:{{TAG}} --load \
        --build-arg NEXT_PUBLIC_API_URL="$NEXT_PUBLIC_API_URL" \
        --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" \
        --build-arg NEXT_PUBLIC_RECALL_ENABLED="$NEXT_PUBLIC_RECALL_ENABLED" \
        --build-arg NEXT_PUBLIC_FOUNDER_CLERK_ID="$NEXT_PUBLIC_FOUNDER_CLERK_ID" \
        --build-arg NEXT_PUBLIC_APP_ENV="$NEXT_PUBLIC_APP_ENV" \
        apps/web

# 레지스트리 없이 SSH 파이프로 전송 후 태그 교체 + 기동
deploy-ship TAG:
    docker save kairos-api:{{TAG}} | gzip -1 | ssh {{oci_host}} 'gunzip | docker load'
    docker save kairos-web:{{TAG}} | gzip -1 | ssh {{oci_host}} 'gunzip | docker load'
    ssh {{oci_host}} 'bash -lc "cd {{oci_dir}} && \
      sed -i \"s/^KAIROS_API_TAG=.*/KAIROS_API_TAG={{TAG}}/; s/^KAIROS_WEB_TAG=.*/KAIROS_WEB_TAG={{TAG}}/\" .env && \
      {{oci_compose}} up -d"'

deploy-status:
    ssh {{oci_host}} 'bash -lc "cd {{oci_dir}} && {{oci_compose}} ps"'
    ssh {{oci_host}} 'bash -lc "curl -sf 127.0.0.1:8200/api/v1/ready; echo; uptime; free -h"'

deploy-logs SERVICE="api":
    ssh {{oci_host}} 'bash -lc "cd {{oci_dir}} && {{oci_compose}} logs --tail=100 -f {{SERVICE}}"'

# 롤백 — 이전 태그로 되돌린다. 마이그레이션은 자동 롤백되지 않는다.
deploy-rollback TAG:
    ssh {{oci_host}} 'bash -lc "cd {{oci_dir}} && \
      sed -i \"s/^KAIROS_API_TAG=.*/KAIROS_API_TAG={{TAG}}/; s/^KAIROS_WEB_TAG=.*/KAIROS_WEB_TAG={{TAG}}/\" .env && \
      {{oci_compose}} up -d"'
