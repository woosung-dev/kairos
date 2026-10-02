#!/usr/bin/env bash
# Kairos 운영 배포 — 서버에 하나뿐인 배포 경로 (ADR-028 D7 Phase B).
#
# 부르는 곳은 둘이고 코드는 이것 하나다 (수동 배포가 성공할 때마다 자동 경로도 같이 검증된다):
#   수동  맥 `mise run deploy-ship <tag> [--migrate]` → 평소 ssh 로
#         `kairos-deploy.sh deploy <tag> --files <sha256> [--migrate]`
#   자동  release.yml `deploy` job → 배포 전용 키 → authorized_keys 의 forced command
#         `kairos-deploy.sh --from-ssh` 가 SSH_ORIGINAL_COMMAND(`<tag> --files <sha256> [--migrate]`)를 읽는다
#   <sha256> = 레포의 compose + 이 스크립트를 이어 붙인 해시 (서버 두 파일이 정본과 같은지 대조)
#   정리  `kairos-deploy.sh gc <보존 태그|__none__>` (맥 `mise run deploy-gc`)
#
# 순서: 인자 검증 → 잠금 → 디스크 80% 관문 → .env 인코딩 관문 → compose·스크립트 해시 대조 → 이미지 pull
#       → 스키마 관문 → 처리 중 회의 대기(60초 × 30) → 태그 교체 + up -d → env 주입·health·/ready 확인 → GC
#
# 종료 코드 (release.yml 이 읽는다):
#   0 성공 · 1 실패(아무것도 안 바뀌었거나 원인 출력) · 2 인자 오류
#   3 스키마 변경 있음 — 승인 필요. 아무것도 바꾸지 않았다 (--migrate 로 다시)
#   4 처리 중 회의가 30분 동안 끝나지 않음. 아무것도 바꾸지 않았다
#   5 기동 후 확인 실패 — .env 태그는 이미 바뀌었다. 출력된 롤백 명령을 본다
#   6 서버 compose·이 스크립트가 레포 정본과 다르다 — 맥에서 `mise run deploy-ship` (동기화 포함) 으로
#
# ★compose 와 이 스크립트는 러너가 보내지 않는다. 서버에 있는 파일을 쓰고, 레포 정본과 해시만 대조한다.
#   compose 는 볼륨·권한을 정한다 — 러너가 바꿀 수 있으면 이 키 하나로 공유 호스트(4 프로젝트) 전체가 열린다.
#   그래서 compose 나 이 스크립트가 바뀐 커밋은 맥에서 한 번 수동 배포한다 (deploy-sync-config 가 둘 다 올린다).
# ★비로그인 셸(forced command)에서도 돌도록 PATH 를 직접 잡는다 (pg-backup.sh 와 같은 이유).
set -euo pipefail
umask 077
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin:${PATH:-}"

DIR="$HOME/kairos"
ENV_FILE="$DIR/.env"
COMPOSE_FILE="$DIR/docker-compose.prod.yml"
GHCR="ghcr.io/woosung-dev"
LOG="$DIR/deploy.log"
WAIT_INTERVAL=60   # 처리 중 회의 재확인 간격(초) — ADR-028 D7 결정 4
WAIT_ROUNDS=30     # 최대 30분. 자동 경로에는 강제 옵션을 두지 않는다
HEALTH_TIMEOUT=180 # 기동 후 healthy 대기(초)

ts() { date -u "+%Y-%m-%dT%H:%M:%SZ"; }
log() { printf '[%s] %s\n' "$(ts)" "$*"; }
die() { local rc="$1"; shift; log "✗ $*"; exit "$rc"; }
compose() { docker compose -f "$COMPOSE_FILE" "$@"; }
psql_db() { docker exec -i kairos-db psql -U kairos -d kairos -tA; }

usage() {
  sed -n '4,9p' "$0" >&2
  exit 2
}

# ── 이미지 정리: .env 현재 태그 + 인자 태그만 남긴다 ─────────────────────────────
# ★공유 호스트 — prune 계열은 남의 프로젝트 이미지를 지운다. kairos 저장소 2개로만 한정한다.
# ★정렬에 기대지 않는다 (Docker 29 + containerd 는 태그 알파벳순). 보존할 태그를 명시한다.
gc_images() {
  local keep_extra="${1:-__none__}" rc=0 repo var cur ref
  for repo in "$GHCR/kairos-api" "$GHCR/kairos-web"; do
    case "$repo" in
      *kairos-api) var=KAIROS_API_TAG ;;
      *kairos-web) var=KAIROS_WEB_TAG ;;
    esac
    cur=$(grep -m1 "^$var=" "$ENV_FILE" | cut -d= -f2)
    # 빈 값이면 아래 필터가 무력화돼 운영 중 태그까지 지운다 — 멈추는 쪽이 옳다
    [ -n "$cur" ] || { log "✗ .env 에서 $var 를 읽지 못했다 — 이미지 정리 중단"; return 1; }
    log "$repo 보존: $cur (운영중), $keep_extra (롤백용)"
    while read -r ref; do
      docker rmi "$ref" >/dev/null || rc=1
    done < <(docker images "$repo" --format '{{.Repository}}:{{.Tag}}' \
               | grep -vx -e "$repo:$cur" -e "$repo:$keep_extra" -e "$repo:<none>" || true)
  done
  log "디스크 $(df -h / | awk 'NR==2{print $3"/"$2" ("$5")"}')"
  return $rc
}

deploy() {
  local tag="$1" want_sha="$2" migrate="$3"
  local api_img="$GHCR/kairos-api:$tag" web_img="$GHCR/kairos-web:$tag"

  # 수동·자동이 겹치지 않게 한다. 대기(최대 30분) 중에도 잠금을 쥔다
  exec 9>"$DIR/.deploy.lock"
  flock -n 9 || die 1 "다른 배포가 진행 중이다 ($DIR/.deploy.lock)"

  log "배포 시작 tag=$tag migrate=$migrate"

  # 1) 디스크 — 80 = 같은 서버 disk-guard(quant-bridge 소유) 경보 기준 (ADR-028 D7 결정 5)
  local pct
  pct=$(df --output=pcent / | tail -1 | tr -dc '0-9')
  [ -n "$pct" ] || die 1 "디스크 사용률을 읽지 못했다"
  [ "$pct" -lt 80 ] || die 1 "디스크 ${pct}% — 80% 이상이면 배포하지 않는다. 직전 태그로 gc 후 다시"
  log "디스크 ${pct}%"

  # 2) .env 인코딩 — 값에 섞인 비ASCII 가 헤더를 깨 500 이 난 적이 있다. 줄 번호만 찍는다 (값은 비밀)
  local bad
  bad=$(LC_ALL=C grep -n '[^[:print:][:space:]]' "$ENV_FILE" | cut -d: -f1 | paste -sd, - || true)
  [ -z "$bad" ] || die 1 ".env 의 ${bad} 번째 줄에 출력 불가 문자가 있다"

  # 3) compose + 이 스크립트 — 레포 정본(배포하는 커밋의 두 파일)과 같아야 한다. 하나라도 다르면 옛 방식으로 조용히 배포하게 된다
  local have_sha
  have_sha=$(cat "$COMPOSE_FILE" "$DIR/bin/kairos-deploy.sh" | sha256sum | cut -d' ' -f1)
  [ "$have_sha" = "$want_sha" ] || die 6 "서버 compose·배포 스크립트가 이 커밋의 정본과 다르다 — 맥에서 mise run deploy-ship $tag 로 동기화하며 배포"
  compose config -q || die 1 "compose 문법·.env 참조 오류"

  # 4) 이미지 — 없으면 받는다. sha 태그는 불변이라 이미 있으면 그대로 쓴다 (맥 비상 경로의 docker load 도 이 단계를 지난다)
  local img
  for img in "$api_img" "$web_img"; do
    if docker image inspect "$img" >/dev/null 2>&1; then
      log "$img 서버에 있음"
    else
      docker pull -q "$img" >/dev/null || die 1 "pull 실패: $img — release.yml 런 성공 여부 확인"
      log "$img 받음"
    fi
  done

  # 5) 스키마 관문 — 이미지의 alembic head 와 DB 리비전이 다르면 승인(--migrate) 없이는 멈춘다 (ADR-028 D7 결정 2)
  local heads current
  heads=$(docker run --rm --network none --entrypoint "" "$api_img" alembic heads | awk '{print $1}' | sort | paste -sd' ' -)
  current=$(printf 'SELECT version_num FROM alembic_version;' | psql_db | sort | paste -sd' ' -)
  [ -n "$heads" ] || die 1 "이미지에서 alembic head 를 읽지 못했다"
  if [ "$heads" = "$current" ]; then
    log "스키마 변경 없음 ($current)"
  elif [ "$migrate" = "yes" ]; then
    log "스키마 변경 승인됨: DB ${current:-<없음>} → 이미지 $heads — 먼저 로컬 덤프"
    "$DIR/backup/pg-backup.sh" --local-only || die 1 "마이그레이션 전 백업 실패 — 배포 중단"
  else
    die 3 "스키마 변경 있음: DB ${current:-<없음>} → 이미지 $heads. 승인 후 --migrate 로 다시 (아무것도 바꾸지 않았다)"
  fi

  # 6) 처리 중 회의 — 재기동이 전사·분석을 끊는다. 최근 2시간 내 갱신된 것만 센다
  #    (최장 작업 ~15분. 더 오래된 것은 이미 죽은 좀비라 그걸로 막으면 관문이 무의미해진다 — deploy-preflight 와 같은 SQL)
  local n round=0
  while :; do
    n=$(printf "SELECT count(*) FROM meetings WHERE status IN ('transcribing','analyzing') AND updated_at > now() - interval '2 hours';" | psql_db)
    [ "$n" = "0" ] && break
    round=$((round + 1))
    [ "$round" -le "$WAIT_ROUNDS" ] || die 4 "처리 중 회의 ${n}건이 $((WAIT_ROUNDS * WAIT_INTERVAL / 60))분 동안 끝나지 않았다 (아무것도 바꾸지 않았다)"
    log "처리 중 회의 ${n}건 — ${WAIT_INTERVAL}초 뒤 다시 (${round}/${WAIT_ROUNDS})"
    sleep "$WAIT_INTERVAL"
  done
  log "처리 중 회의 0"

  # 7) 교체 + 기동. 직전 태그는 덮어쓰기 **전에** 읽는다 (GC 보존·롤백 대상)
  local prev
  prev=$(grep -m1 '^KAIROS_API_TAG=' "$ENV_FILE" | cut -d= -f2)
  sed -i "s/^KAIROS_API_TAG=.*/KAIROS_API_TAG=$tag/; s/^KAIROS_WEB_TAG=.*/KAIROS_WEB_TAG=$tag/" "$ENV_FILE"
  log "태그 교체 ${prev:-<없음>} → $tag"
  local rollback="롤백: 맥에서 mise run deploy-rollback ${prev:-<직전 태그>}"
  [ "$heads" = "$current" ] || rollback="$rollback (★스키마가 이미 올라갔다 — 옛 이미지가 새 스키마에서 도는지 먼저 확인)"
  compose up -d || die 5 "up -d 실패. $rollback"

  # 8) 확인 — healthy → env 주입 → /ready 순
  local c s waited=0
  for c in kairos-api kairos-web; do
    until s=$(docker inspect -f '{{.State.Health.Status}}' "$c" 2>/dev/null) && [ "$s" = healthy ]; do
      [ "$waited" -lt "$HEALTH_TIMEOUT" ] || die 5 "$c 가 ${HEALTH_TIMEOUT}초 안에 healthy 가 아니다 (지금 ${s:-없음}). $rollback"
      sleep 5; waited=$((waited + 5))
    done
  done
  # compose 의 environment: 치환은 변수가 없어도 빈 값으로 조용히 통과한다 → 이름만 대조한다.
  # ★`docker exec env | grep -q` 는 pipefail 에서 SIGPIPE 로 거짓 실패한다 — 이름 목록을 먼저 받는다
  local web_env api_env
  web_env=$(docker exec kairos-web env | grep -oE '^(BETTER_AUTH_SECRET|GOOGLE_CLIENT_SECRET)=.' || true)
  api_env=$(docker exec kairos-api env | grep -oE '^AUTH_JWKS_URL=.' || true)
  grep -q '^BETTER_AUTH_SECRET=' <<<"$web_env" || die 5 "web 에 BETTER_AUTH_SECRET 미주입. $rollback"
  grep -q '^GOOGLE_CLIENT_SECRET=' <<<"$web_env" || die 5 "web 에 GOOGLE_CLIENT_SECRET 미주입. $rollback"
  grep -q '^AUTH_JWKS_URL=' <<<"$api_env" || die 5 "api 에 AUTH_JWKS_URL 미주입. $rollback"
  curl -sf -o /dev/null http://127.0.0.1:8200/api/v1/ready || die 5 "/api/v1/ready 실패. $rollback"
  log "✅ 배포 완료 tag=$tag — api/web healthy · /ready 200 (healthy 까지 ${waited}초)"

  # 9) GC — 같은 태그 재실행이면 직전 태그를 모르는 상태라 건너뛴다. 실패해도 배포는 끝났다
  if [ "$prev" = "$tag" ]; then
    log "⚠ 직전 태그가 이번 태그와 같다(재실행) — 이미지 정리를 건너뛴다"
  else
    gc_images "${prev:-__none__}" || log "⚠ 이미지 정리 일부 실패 — 배포는 완료"
  fi
}

# ── 인자 해석 ────────────────────────────────────────────────────────────────
TAG_RE='sha-[0-9a-f]{7}'
SHA256_RE='[0-9a-f]{64}'

if [ "${1:-}" = "--from-ssh" ]; then
  # 배포 전용 키는 이것만 할 수 있다. 문법이 정확히 맞지 않으면 아무것도 하지 않는다
  cmd="${SSH_ORIGINAL_COMMAND:-}"
  [[ "$cmd" =~ ^($TAG_RE)\ --files\ ($SHA256_RE)(\ --migrate)?$ ]] || { echo "✗ 허용되지 않는 명령" >&2; exit 2; }
  set -- deploy "${BASH_REMATCH[1]}" --files "${BASH_REMATCH[2]}" ${BASH_REMATCH[3]:+--migrate}
fi

exec > >(tee -a "$LOG") 2>&1

case "${1:-}" in
  deploy)
    tag="${2:-}"; [[ "$tag" =~ ^$TAG_RE$ ]] || usage
    [ "${3:-}" = "--files" ] && [[ "${4:-}" =~ ^$SHA256_RE$ ]] || usage
    case "${5:-}" in
      "") migrate=no ;;
      --migrate) migrate=yes ;;
      *) usage ;;
    esac
    deploy "$tag" "$4" "$migrate"
    ;;
  gc)
    keep="${2:-}"; [[ "$keep" =~ ^($TAG_RE|__none__)$ ]] || usage
    gc_images "$keep"
    ;;
  *) usage ;;
esac
