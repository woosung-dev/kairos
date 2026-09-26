#!/usr/bin/env bash
# Kairos DB 일일 백업 — pg_dump(custom format) → 로컬 보관 → R2 오프사이트 사본 (BL-OCI-1 · 체크리스트 0-11)
#
# 런북: docs/operations/runbooks/db-backup-restore.md (cron 등록 · 복원 · 검증 쿼리)
#
# 사용:
#   pg-backup.sh               # 덤프 + 검증 + R2 업로드 + 로컬 보존 정리 (cron 이 부르는 형태)
#   pg-backup.sh --local-only  # R2 업로드만 건너뛴다 (리허설 · R2 장애 시)
#   pg-backup.sh --dry-run     # 사전 점검 + 할 일 출력만. 덤프/업로드/삭제 0건
#
# 환경변수 (전부 선택 — 기본값이 서버 배치다):
#   DB_CONTAINER      덤프 대상 postgres 컨테이너   (기본 kairos-db)
#   UPLOAD_CONTAINER  R2 업로드를 실행할 컨테이너   (기본 kairos-api)
#   BACKUP_DIR        로컬 보관 디렉터리            (기본 $HOME/kairos/backups)
#   KEEP_DAYS         로컬 보존 일수                (기본 14)
#
# 종료 코드: 0 = 성공, 1 = 실패 (덤프·검증·업로드 중 하나라도 실패하면 1).
#
# ★설계 메모
#   - 호스트에서 .env 를 읽지 않는다. pg_dump 는 db 컨테이너 안의 POSTGRES_USER/POSTGRES_DB 를,
#     업로드는 api 컨테이너 안의 R2_* 를 쓴다 → 앱과 같은 자격증명·같은 boto3 로 올리고,
#     시크릿이 이 스크립트의 환경·로그·argv 어디에도 나타나지 않는다.
#   - 필요한 도구는 docker CLI 하나다 (compose 플러그인 · aws-cli · 호스트 psql 불필요).
#   - R2 버킷(nexus-core-storage)은 다른 프로젝트와 공유한다. 이 스크립트는 R2 에서
#     **아무것도 지우지 않는다.** 원격 보존 기간은 R2 lifecycle 규칙(prefix backups/kairos/)으로 건다.
#   - 맥(bash 3.2 · BSD 도구)에서도 로컬 리허설이 되도록 bash 4 전용 문법과 GNU 전용 옵션을 쓰지 않는다.
set -euo pipefail
umask 077
# cron 의 최소 PATH 보강 (docker 가 /usr/bin 밖에 있을 수 있다)
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin:${PATH:-}"

DB_CONTAINER="${DB_CONTAINER:-kairos-db}"
UPLOAD_CONTAINER="${UPLOAD_CONTAINER:-kairos-api}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/kairos/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
# 고정값 — 공유 버킷이라 환경변수로 바꿀 수 없게 둔다. 업로드 코드도 이 prefix 밖으로는 거부한다.
R2_PREFIX="backups/kairos"
# 덤프 목차에 반드시 있어야 하는 테이블 데이터 (없으면 잘못된 DB 이거나 잘린 덤프다)
REQUIRED_TABLES="alembic_version users auth_user auth_account workspaces meetings"

MODE="full"
case "${1:-}" in
  "") ;;
  --local-only) MODE="local-only" ;;
  --dry-run) MODE="dry-run" ;;
  -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
  *) echo "알 수 없는 인자: $1 (--local-only | --dry-run)" >&2; exit 1 ;;
esac

ts() { date "+%Y-%m-%dT%H:%M:%S%z"; }
log() { printf '[%s] %s\n' "$(ts)" "$*"; }
die() { log "⛔ $*"; exit 1; }

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

file_size() { wc -c < "$1" | tr -d ' '; }

container_running() {
  [ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null || true)" = "true" ]
}

case "$KEEP_DAYS" in ''|*[!0-9]*) die "KEEP_DAYS 는 양의 정수여야 한다: '$KEEP_DAYS'" ;; esac
[ "$KEEP_DAYS" -ge 1 ] || die "KEEP_DAYS 는 1 이상이어야 한다"

# ── 사전 점검 ──────────────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || die "docker CLI 가 PATH 에 없다 (PATH=$PATH)"
container_running "$DB_CONTAINER" || die "DB 컨테이너 '$DB_CONTAINER' 가 실행 중이 아니다"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DAY_PATH="$(date -u +%Y/%m/%d)"
NAME="kairos-$STAMP.dump"
FILE="$BACKUP_DIR/$NAME"
TMP="$FILE.partial"
KEY="$R2_PREFIX/$DAY_PATH/$NAME"

log "백업 시작 mode=$MODE db=$DB_CONTAINER → $FILE"

if [ "$MODE" = "dry-run" ]; then
  log "[dry-run] docker exec $DB_CONTAINER pg_dump -Fc → $TMP"
  log "[dry-run] pg_restore --list 로 목차 검증 (필수 테이블: $REQUIRED_TABLES)"
  if container_running "$UPLOAD_CONTAINER"; then
    log "[dry-run] R2 업로드 → key=$KEY (via $UPLOAD_CONTAINER)"
  else
    log "[dry-run] ⚠ 업로드 컨테이너 '$UPLOAD_CONTAINER' 가 실행 중이 아니다 — 실제 실행이면 업로드 단계에서 실패한다"
  fi
  if [ -d "$BACKUP_DIR" ]; then
    log "[dry-run] 보존 정리 대상 (${KEEP_DAYS}일 초과):"
    find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'kairos-*.dump' -o -name 'kairos-*.dump.sha256' \) \
      -mtime +"$KEEP_DAYS" -print
  fi
  log "[dry-run] 종료 — 변경 0건"
  exit 0
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
# ★임시 이름으로 쓰고 검증 후에 최종 이름으로 옮긴다. 실패하면 trap 이 지운다 —
#   잘린 파일이 정상 백업 이름으로 남는 것을 막는다.
trap 'rm -f "$TMP"' EXIT

# ── 1. 덤프 ────────────────────────────────────────────────────────────────
# -Fc = custom format (자체 압축 · pg_restore 로 선택 복원 가능). 컨테이너 안의 pg_dump 를
# 쓰므로 서버 버전과 도구 버전이 항상 같다. 로컬 소켓 접속이라 비밀번호가 필요 없다.
# shellcheck disable=SC2016  # $POSTGRES_* 는 컨테이너 안에서 전개돼야 한다
docker exec "$DB_CONTAINER" sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$TMP" \
  || die "pg_dump 실패 (exit $?)"
SIZE="$(file_size "$TMP")"
[ "$SIZE" -gt 0 ] || die "덤프 크기가 0 바이트다"

# ── 2. 검증 — 목차가 읽히고 필수 테이블 데이터가 들어 있어야 백업이다 ──────────
TOC="$(docker exec -i "$DB_CONTAINER" pg_restore --list < "$TMP")" || die "pg_restore --list 실패 — 덤프가 손상됐다"
# here-string 을 쓴다 — `printf | grep -q` 는 pipefail 아래에서 SIGPIPE 로 거짓 실패할 수 있다.
ENTRIES="$(grep -c '^[0-9]' <<<"$TOC" || true)"
for t in $REQUIRED_TABLES; do
  grep -Eq "TABLE DATA public $t " <<<"$TOC" || die "덤프 목차에 '$t' 테이블 데이터가 없다"
done
mv "$TMP" "$FILE"
trap - EXIT
DIGEST="$(sha256 "$FILE")"
printf '%s  %s\n' "$DIGEST" "$NAME" > "$FILE.sha256"
log "✅ 덤프 검증 통과 — ${SIZE} bytes · 목차 ${ENTRIES}개 · sha256=${DIGEST}"

# ── 3. R2 업로드 ───────────────────────────────────────────────────────────
if [ "$MODE" = "full" ]; then
  container_running "$UPLOAD_CONTAINER" \
    || die "업로드 컨테이너 '$UPLOAD_CONTAINER' 가 실행 중이 아니다 — 로컬 사본만 남았다: $FILE"
  # 앱 컨테이너의 venv(boto3 포함)와 env(R2_*)를 그대로 쓴다. 덤프는 stdin 으로 흘려보낸다.
  # checksum 옵션: botocore 1.36+ 의 기본 CRC 헤더를 R2 호환 모드로 낮춘다.
  UPLOAD_PY='
import os, sys
import boto3
from botocore.config import Config
key, expected = sys.argv[1], int(sys.argv[2])
if not key.startswith("backups/kairos/"):
    sys.exit("refuse: key outside backups/kairos/")
bucket = os.environ["R2_BUCKET_NAME"]
s3 = boto3.client(
    "s3",
    endpoint_url="https://%s.r2.cloudflarestorage.com" % os.environ["R2_ACCOUNT_ID"],
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    region_name="auto",
    config=Config(request_checksum_calculation="when_required", response_checksum_validation="when_required"),
)
s3.upload_fileobj(sys.stdin.buffer, bucket, key, ExtraArgs={"ContentType": "application/octet-stream"})
remote = s3.head_object(Bucket=bucket, Key=key)["ContentLength"]
if remote != expected:
    sys.exit("size mismatch: local=%d r2=%d" % (expected, remote))
print("uploaded %d bytes" % remote)
'
  OUT="$(docker exec -i "$UPLOAD_CONTAINER" python -c "$UPLOAD_PY" "$KEY" "$SIZE" < "$FILE" 2>&1)" \
    || die "R2 업로드 실패 — 로컬 사본만 남았다: $FILE / $(printf '%s' "$OUT" | tail -n 3)"
  log "✅ R2 업로드 — key=$KEY ($OUT)"
else
  log "ℹ R2 업로드 건너뜀 (--local-only)"
fi

# ── 4. 로컬 보존 정리 — 여기까지 성공한 경우에만 오래된 사본을 지운다 ──────────
# 이름 패턴을 이 스크립트가 만든 파일로 한정한다.
DELETED="$(find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'kairos-*.dump' -o -name 'kairos-*.dump.sha256' \) \
  -mtime +"$KEEP_DAYS" -print -delete | wc -l | tr -d ' ')"
KEPT="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'kairos-*.dump' | wc -l | tr -d ' ')"
log "보존 정리 — ${KEEP_DAYS}일 초과 ${DELETED}개 파일 삭제, 보관 중 덤프 ${KEPT}개"

# 모니터링용 마커 — 마지막 성공 시각. 런북의 신선도 점검이 이 파일의 mtime 을 본다.
printf 'at=%s file=%s mode=%s r2_key=%s\n' "$(ts)" "$NAME" "$MODE" \
  "$([ "$MODE" = "full" ] && printf '%s' "$KEY" || printf 'skipped')" > "$BACKUP_DIR/last-success"
log "완료"
