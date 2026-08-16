# Kairos 단일 명령 진입점 (ADR-027 D3).
# ⚠️ 테스트/빌드 recipe 는 CI(.github/workflows/test.yml)와 invocation 을
#    문자 그대로 동일하게 유지한다 — 여기를 바꾸면 test.yml 도 같이 바꾼다.

set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

install:
    cd apps/api && uv sync --frozen
    cd apps/web && pnpm install --frozen-lockfile

be-dev:
    cd apps/api && uv run uvicorn src.main:app --reload --port 8000

# CI 와 동일 (README 의 `uv run pytest -v` 아님 — transcription/r2-cors 2개 제외가 정본)
be-test:
    cd apps/api && uv run pytest --ignore=tests/services/test_transcription.py --ignore=tests/test_r2_cors_regression.py -v

be-migrate:
    cd apps/api && uv run alembic upgrade head

fe-dev:
    cd apps/web && pnpm dev

fe-test:
    cd apps/web && pnpm test

fe-typecheck:
    cd apps/web && pnpm typecheck

fe-lint:
    cd apps/web && pnpm lint

fe-build:
    # ADR-031: `next build` 의 page data 수집이 auth.ts 를 평가한다. secret 이 없으면
    # BetterAuthError 로그가 찍힌다(빌드는 통과). CI frontend-build 스텝의 env 와
    # **문자 그대로 같은 값**을 기본값으로 둬서 로컬과 CI 출력이 갈라지지 않게 한다.
    cd apps/web && BETTER_AUTH_SECRET="${BETTER_AUTH_SECRET:-ci-fake-secret-at-least-32-bytes-long}" pnpm build

e2e:
    cd apps/web && pnpm e2e

# ── API 계약 (ADR-027 D2) ─────────────────────────────────────────────
openapi-export:
    cd apps/api && uv run python -m scripts.export_openapi

types-gen:
    cd apps/web && pnpm gen:api

contracts: openapi-export types-gen

# CI contract-check job 과 동일한 drift 게이트
contracts-check: contracts
    git diff --exit-code -- contracts/ apps/web/src/types/api.gen.ts

# ── 로컬 머지 게이트 (ADR-027 D3 연장) ────────────────────────────────
# ★반드시 **빌드 산출물**(`pnpm start`)을 검증한다. `playwright.config.ts` 의 webServer 는
#   비-CI 에서 `pnpm dev` 를 띄우는데 CI 는 `pnpm start` 를 검증한다 — 그대로 두면
#   프로덕션에서만 나는 헤더/기동 회귀가 이 게이트를 통과해 버린다 (2026-08-16 codex 리뷰 P2).
#   여기서 서버를 직접 띄우면 webServer 의 `reuseExistingServer: true` 가 그것을 재사용한다.
# ★포트는 3005 고정 — dev(:3000)/playwright 기본(:3003)과 겹치지 않게. 이미 점유돼 있으면
#   남의 서버를 검증하게 되므로 **중단**한다. 헤더 단언은 포트에 의존하지 않아 CI(:3000)와 동치다.
#   `.next` 가 최신이어야 한다 — `ci-local` 이 `fe-build` 를 먼저 돌려 그 순서를 보장한다.
# ★CI 도 이 recipe 를 호출한다 (`test.yml` frontend-build, PORT="3000"). 사본을 두지 않는다 —
#   사본이 갈라지는 게 정확히 이 게이트가 잡으려는 버그 클래스다 (2026-08-16 코드리뷰 지적).
# CI frontend-build 의 보안 헤더 스텝 (public route, secrets·BE 불요)
fe-security-headers PORT="3005":
    #!/usr/bin/env bash
    set -euo pipefail
    # ★인자는 **값만** 넘긴다: `just fe-security-headers 3000`.
    #   `PORT=3000` 형태로 주면 just 가 그 문자열을 값으로 넘겨 `next start -p PORT=3000` 이 된다
    #   (2026-08-16 CI 실측 — 내가 test.yml 에 그렇게 써서 frontend-build 가 깨졌다).
    #   기본값 경로만 로컬 테스트하고 인자 경로를 안 돌려본 게 원인이라 여기서 즉시 거른다.
    case "{{PORT}}" in ''|*[!0-9]*)
      echo "PORT 는 숫자만 받는다 (받은 값: '{{PORT}}'). 사용법: just fe-security-headers 3000" >&2
      exit 1 ;;
    esac
    cd apps/web
    if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:{{PORT}} -sTCP:LISTEN >/dev/null 2>&1; then
      echo "포트 {{PORT}} 가 이미 사용 중이다. 그 서버를 검증하게 되므로 중단한다." >&2
      echo "  정리: lsof -ti:{{PORT}} | xargs kill" >&2
      exit 1
    fi
    BETTER_AUTH_SECRET="${BETTER_AUTH_SECRET:-ci-fake-secret-at-least-32-bytes-long}" pnpm start -p {{PORT}} -H 0.0.0.0 > /tmp/kairos-next-headers.log 2>&1 &
    _pid=$!
    # pnpm 이 SIGTERM 을 자식(next start)에 전달하지 못하는 경우가 있어 프로세스 그룹까지 정리한다.
    trap 'pkill -P "$_pid" 2>/dev/null || true; kill "$_pid" 2>/dev/null || true' EXIT
    pnpm exec wait-on http://127.0.0.1:{{PORT}}/sign-in -t 180000 -v || { echo "--- next start 로그 ---"; cat /tmp/kairos-next-headers.log; exit 1; }
    E2E_PORT={{PORT}} E2E_BASE_URL=http://localhost:{{PORT}} pnpm exec playwright test --project=public-only

# ★새 명령을 정의하지 않고 기존 recipe 를 조합만 한다 — "로컬 = CI 문자 동일" 불변 보존.
# 푸쉬 전 사전 확인용이다. 최종 판정은 CI 의 `ci-required` 가 한다 (docs/development/testing.md).
#   - 실패가 환경 문제로 의심되면 `just install` 을 먼저 돌린다.
#   - ★clean tree 에서 실행한다. contracts-check 는 `git diff --exit-code` 라
#     작업 트리가 더러우면 계약과 무관한 변경까지 drift 로 잡는다(오탐).
# ★contracts-check 를 fe-test/fe-build **앞**에 둔다. 이게 api.gen.ts 를 재생성하므로,
#   뒤에 두면 fe-build(=타입 검사)가 **낡은 생성 타입**으로 통과한 뒤에야 drift 가 잡힌다 —
#   그때 PR 에 붙일 빌드 결과는 새 계약을 검증한 적이 없다 (2026-08-16 코드리뷰 지적).
# 머지 게이트 — CI 의 backend-test + frontend-build + contract-check 로컬 미러
ci-local: be-test contracts-check fe-test fe-build fe-security-headers

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
    docker buildx build --platform linux/arm64 -t kairos-api:{{TAG}} --load apps/api
    set -a && source deploy/oci/build.env && set +a && \
      docker buildx build --platform linux/arm64 -t kairos-web:{{TAG}} --load \
        --build-arg NEXT_PUBLIC_API_URL="$NEXT_PUBLIC_API_URL" \
        --build-arg NEXT_PUBLIC_RECALL_ENABLED="$NEXT_PUBLIC_RECALL_ENABLED" \
        --build-arg NEXT_PUBLIC_FOUNDER_USER_ID="$NEXT_PUBLIC_FOUNDER_USER_ID" \
        --build-arg NEXT_PUBLIC_APP_ENV="$NEXT_PUBLIC_APP_ENV" \
        apps/web

# 서버의 compose 파일을 레포 정본으로 동기화한다.
#
# ★2026-08-17 Better Auth 컷오버 사고의 재발 방지 레시피다.
#   그날까지 배포는 이미지와 .env 태그만 옮겼고 compose 파일은 "최초 부트스트랩" 때 한 번
#   복사한 게 전부였다(서버 파일 mtime 8/14). ADR-031 이 web 서비스에 새로 추가한
#   environment 5줄(BETTER_AUTH_*, GOOGLE_CLIENT_*)이 서버에 도달하지 못했고,
#   그 결과 BETTER_AUTH_SECRET 이 빈 값으로 주입돼 web 이 전면 500 이었다
#   (BetterAuthError: You are using the default secret).
#
#   교훈: 배포 단위는 "이미지"가 아니라 "이미지 + 그 이미지를 띄우는 방법"이다.
#   compose 파일이 레포에 있는데 서버로 갈 경로가 없으면 그건 배포가 아니라 반쪽이다.
deploy-sync-config:
    ssh {{oci_host}} 'bash -lc "cd {{oci_dir}} && cp docker-compose.prod.yml docker-compose.prod.yml.bak"'
    scp deploy/oci/docker-compose.prod.yml {{oci_host}}:{{oci_dir}}/docker-compose.prod.yml
    # 문법 검증 — .env 참조가 깨졌으면 여기서 죽는다 (up -d 이후가 아니라)
    ssh {{oci_host}} 'bash -lc "cd {{oci_dir}} && {{oci_compose}} config -q && echo \"compose 문법 OK\""'

# 레지스트리 없이 SSH 파이프로 전송 후 태그 교체 + 기동.
# ★compose 동기화가 선행 의존이다 — 순서를 바꾸면 위 사고가 그대로 재현된다.
deploy-ship TAG: deploy-sync-config
    docker save kairos-api:{{TAG}} | gzip -1 | ssh {{oci_host}} 'gunzip | docker load'
    docker save kairos-web:{{TAG}} | gzip -1 | ssh {{oci_host}} 'gunzip | docker load'
    ssh {{oci_host}} 'bash -lc "cd {{oci_dir}} && \
      sed -i \"s/^KAIROS_API_TAG=.*/KAIROS_API_TAG={{TAG}}/; s/^KAIROS_WEB_TAG=.*/KAIROS_WEB_TAG={{TAG}}/\" .env && \
      {{oci_compose}} up -d"'
    @just deploy-verify-env

# 컨테이너에 런타임 env 가 실제로 주입됐는지 확인한다.
# compose 의 `environment:` 치환은 변수가 없어도 빈 문자열로 조용히 통과하므로
# (env_file 과 달리 에러가 안 난다) 이 게이트가 없으면 첫 로그인에서야 드러난다.
deploy-verify-env:
    ssh {{oci_host}} 'bash -lc "docker exec kairos-web env | grep -q \"^BETTER_AUTH_SECRET=.\" && echo \"web: BETTER_AUTH_SECRET 주입 OK\""'
    ssh {{oci_host}} 'bash -lc "docker exec kairos-web env | grep -q \"^GOOGLE_CLIENT_SECRET=.\" && echo \"web: GOOGLE_CLIENT_SECRET 주입 OK\""'
    ssh {{oci_host}} 'bash -lc "docker exec kairos-api env | grep -q \"^AUTH_JWKS_URL=.\" && echo \"api: AUTH_JWKS_URL 주입 OK\""'

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
