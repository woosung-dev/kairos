#!/usr/bin/env bash
# 백업 복원 리허설 — 덤프를 **새 임시 컨테이너**에 복원하고 테이블별 row count 를 원본과 비교한다.
#
# 런북: docs/operations/runbooks/db-backup-restore.md
#
# 사용:
#   pg-restore-check.sh DUMP_FILE                      # 복원만 검증 (row count 출력)
#   pg-restore-check.sh DUMP_FILE --compare kairos-db  # 원본 컨테이너와 row count 비교 (불일치 시 exit 1)
#   pg-restore-check.sh DUMP_FILE --keep               # 끝나도 임시 컨테이너를 남긴다 (수동 조사용)
#
# 환경변수 (선택):
#   RESTORE_CONTAINER  임시 컨테이너 이름  (기본 kairos-restore-test — 이미 있으면 거부한다)
#   PG_IMAGE           임시 컨테이너 이미지 (기본 pgvector/pgvector:0.8.0-pg17 = 운영과 동일)
#   RESTORE_MEM        메모리 상한          (기본 512m — 공유 서버의 다른 프로젝트를 굶기지 않게)
#
# 안전 규칙:
#   - 기존 컨테이너·볼륨은 건드리지 않는다. 자기가 만든 이름 하나만 만들고 지운다.
#   - 포트를 publish 하지 않는다 (공유 서버 포트 충돌 방지). 조사는 docker exec 로 한다.
#   - --compare 대상에는 SELECT 만 보낸다 (information_schema 조회 + count(*)).
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin:${PATH:-}"

RESTORE_CONTAINER="${RESTORE_CONTAINER:-kairos-restore-test}"
PG_IMAGE="${PG_IMAGE:-pgvector/pgvector:0.8.0-pg17}"
RESTORE_MEM="${RESTORE_MEM:-512m}"
RESTORE_USER="kairos"
RESTORE_DB="kairos_restore"

DUMP=""
COMPARE=""
KEEP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --compare) COMPARE="${2:-}"; [ -n "$COMPARE" ] || { echo "--compare 에 컨테이너 이름이 필요하다" >&2; exit 1; }; shift 2 ;;
    --keep) KEEP=1; shift ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    -*) echo "알 수 없는 옵션: $1" >&2; exit 1 ;;
    *) [ -z "$DUMP" ] || { echo "덤프 파일은 하나만 받는다" >&2; exit 1; }; DUMP="$1"; shift ;;
  esac
done

ts() { date "+%Y-%m-%dT%H:%M:%S%z"; }
log() { printf '[%s] %s\n' "$(ts)" "$*"; }
die() { log "⛔ $*"; exit 1; }

[ -n "$DUMP" ] || die "사용법: pg-restore-check.sh DUMP_FILE [--compare CONTAINER] [--keep]"
[ -s "$DUMP" ] || die "덤프 파일이 없거나 비어 있다: $DUMP"
command -v docker >/dev/null 2>&1 || die "docker CLI 가 PATH 에 없다"
if docker inspect "$RESTORE_CONTAINER" >/dev/null 2>&1; then
  die "컨테이너 '$RESTORE_CONTAINER' 가 이미 있다. 남의 컨테이너일 수 있으니 지우지 않는다 — RESTORE_CONTAINER 로 다른 이름을 주거나 직접 확인 후 제거할 것"
fi
if [ -n "$COMPARE" ]; then
  [ "$(docker inspect -f '{{.State.Running}}' "$COMPARE" 2>/dev/null || true)" = "true" ] \
    || die "비교 대상 컨테이너 '$COMPARE' 가 실행 중이 아니다"
fi

# 모든 public 테이블의 **정확한** row count (통계 추정치 pg_class.reltuples 가 아니다).
# query_to_xml 로 동적 count 를 돌린다 — 함수를 만들지 않으므로 대상 DB 에 쓰기가 없다.
# 출력 형식: table|rows
ROW_COUNT_SQL="SELECT table_name,
       (xpath('/row/c/text()',
              query_to_xml(format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name),
                           false, true, '')))[1]::text::bigint
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;"

cleanup() {
  if [ "$KEEP" -eq 1 ]; then
    log "ℹ --keep — 임시 컨테이너를 남긴다: docker exec -it $RESTORE_CONTAINER psql -U $RESTORE_USER -d $RESTORE_DB"
    log "ℹ 조사 후 제거: docker rm -f -v $RESTORE_CONTAINER"
  else
    # -v: 이 컨테이너의 **익명** 볼륨(이미지의 VOLUME 선언)만 함께 지운다. 이름 있는 볼륨은 건드리지 않는다.
    #     빠뜨리면 리허설마다 dangling 볼륨이 하나씩 쌓인다 (2026-09-27 로컬 리허설에서 확인).
    docker rm -f -v "$RESTORE_CONTAINER" >/dev/null 2>&1 && log "임시 컨테이너 제거: $RESTORE_CONTAINER (익명 볼륨 포함)"
  fi
}

# ── 1. 임시 컨테이너 기동 ──────────────────────────────────────────────────
# 비밀번호는 쓰지 않는다(docker exec = 로컬 소켓 trust). 그래도 이미지가 요구하므로 난수로 채운다.
PW="$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32 || true)"
log "임시 컨테이너 기동 — $RESTORE_CONTAINER ($PG_IMAGE, mem $RESTORE_MEM, 포트 publish 없음)"
docker run -d --name "$RESTORE_CONTAINER" --memory "$RESTORE_MEM" \
  --label kairos.purpose=restore-test \
  -e POSTGRES_USER="$RESTORE_USER" -e POSTGRES_PASSWORD="$PW" -e POSTGRES_DB="$RESTORE_DB" \
  "$PG_IMAGE" >/dev/null
unset PW
trap cleanup EXIT

# ★-h 127.0.0.1 로 TCP 준비를 본다. 이미지의 초기화 단계는 소켓 전용 임시 서버를 띄웠다가
#   재시작하므로, 소켓 pg_isready 는 그 임시 서버에 "준비됨" 을 받고 곧 끊긴다.
READY=0
for _ in $(seq 1 60); do
  if docker exec "$RESTORE_CONTAINER" pg_isready -h 127.0.0.1 -U "$RESTORE_USER" -d "$RESTORE_DB" >/dev/null 2>&1; then
    READY=1; break
  fi
  sleep 1
done
[ "$READY" -eq 1 ] || die "임시 컨테이너가 60초 안에 준비되지 않았다 (docker logs $RESTORE_CONTAINER)"

# ── 2. 복원 ────────────────────────────────────────────────────────────────
# --no-owner/--no-privileges: 원본 롤 구성과 무관하게 복원한다. --exit-on-error: 한 건이라도 실패하면 중단.
# 확장(vector, pg_trgm)은 덤프에 CREATE EXTENSION 으로 들어 있다 → 이미지가 pgvector 여야 한다.
START="$(date +%s)"
docker exec -i "$RESTORE_CONTAINER" pg_restore -U "$RESTORE_USER" -d "$RESTORE_DB" \
  --no-owner --no-privileges --exit-on-error < "$DUMP" || die "pg_restore 실패"
log "✅ 복원 완료 ($(( $(date +%s) - START ))초)"

EXT="$(docker exec "$RESTORE_CONTAINER" psql -U "$RESTORE_USER" -d "$RESTORE_DB" -AtX -v ON_ERROR_STOP=1 \
  -c "SELECT string_agg(extname || ' ' || extversion, ', ' ORDER BY extname) FROM pg_extension")"
ALEMBIC="$(docker exec "$RESTORE_CONTAINER" psql -U "$RESTORE_USER" -d "$RESTORE_DB" -AtX -v ON_ERROR_STOP=1 \
  -c "SELECT string_agg(version_num, ',') FROM alembic_version")"
log "확장: $EXT"
log "alembic_version: $ALEMBIC"

# ── 3. row count ───────────────────────────────────────────────────────────
WORK="$(mktemp -d)"
RESTORED_TSV="$WORK/restored.txt"
SOURCE_TSV="$WORK/source.txt"
docker exec -i "$RESTORE_CONTAINER" psql -U "$RESTORE_USER" -d "$RESTORE_DB" -AtX -v ON_ERROR_STOP=1 \
  <<<"$ROW_COUNT_SQL" > "$RESTORED_TSV"

if [ -z "$COMPARE" ]; then
  printf '%-32s %12s\n' "table" "restored"
  awk -F'|' '{ printf "%-32s %12s\n", $1, $2 }' "$RESTORED_TSV"
  log "ℹ --compare 없이 실행 — 원본과의 대조는 생략했다"
  rm -rf "$WORK"
  exit 0
fi

# shellcheck disable=SC2016  # $POSTGRES_* 는 비교 대상 컨테이너 안에서 전개돼야 한다
docker exec -i "$COMPARE" sh -c 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -AtX -v ON_ERROR_STOP=1' \
  <<<"$ROW_COUNT_SQL" > "$SOURCE_TSV"
SRC_ALEMBIC="$(docker exec -i "$COMPARE" sh -c 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -AtX -v ON_ERROR_STOP=1' \
  <<<"SELECT string_agg(version_num, ',') FROM alembic_version")"

printf '%-32s %12s %12s  %s\n' "table" "source" "restored" "result"
set +e
awk -F'|' '
  FNR == NR { src[$1] = $2; seen[$1] = 1; next }
            { dst[$1] = $2; seen[$1] = 1 }
  END {
    bad = 0
    for (t in seen) {
      s = (t in src) ? src[t] : "-"
      d = (t in dst) ? dst[t] : "-"
      r = (s == d) ? "OK" : "MISMATCH"
      if (r != "OK") bad++
      printf "%-32s %12s %12s  %s\n", t, s, d, r
    }
    exit (bad > 0) ? 1 : 0
  }' "$SOURCE_TSV" "$RESTORED_TSV" | sort
AWK_STATUS="${PIPESTATUS[0]}"
set -e
TABLES="$(wc -l < "$RESTORED_TSV" | tr -d ' ')"
rm -rf "$WORK"

[ "$SRC_ALEMBIC" = "$ALEMBIC" ] || die "alembic_version 불일치 — source=$SRC_ALEMBIC restored=$ALEMBIC"
[ "$AWK_STATUS" -eq 0 ] || die "row count 불일치 — 위 MISMATCH 행 확인. 원본에 백업 이후 쓰기가 있었다면 그 테이블만 다를 수 있다"
log "✅ 테이블 ${TABLES}개 row count 전부 일치 · alembic_version 일치 ($ALEMBIC)"
