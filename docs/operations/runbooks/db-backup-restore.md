# 런북: DB 백업 · 복원 · 복원 리허설

> BL-OCI-1 · 체크리스트 0-11. 스크립트는 [`deploy/oci/backup/`](../../../deploy/oci/backup/) 에 있다.
> **2026-10-02 서버 cron 등록 완료** (`37 18 * * *` UTC = KST 03:37, 첫 실행 R2 업로드 확인). 등록 여부는 `crontab -l | grep pg-backup` 로 본다.

| 스크립트 | 하는 일 |
|---|---|
| `pg-backup.sh` | `kairos-db` 컨테이너에서 `pg_dump -Fc` → 목차 검증 → `~/kairos/backups/` 보관(14일) → R2 `backups/kairos/YYYY/MM/DD/` 업로드 |
| `pg-restore-check.sh` | 덤프를 **새 임시 컨테이너**에 복원 → 모든 public 테이블의 정확한 row count 를 원본과 비교 → 임시 컨테이너 제거 |

## 1. 설계 요약

- **호스트에서 `.env` 를 읽지 않는다.** 덤프는 db 컨테이너 안의 `POSTGRES_USER/POSTGRES_DB` 로,
  업로드는 `kairos-api` 컨테이너 안의 `R2_ACCOUNT_ID` · `R2_ACCESS_KEY_ID` · `R2_SECRET_ACCESS_KEY` ·
  `R2_BUCKET_NAME` 과 boto3 로 한다 (앱과 같은 변수·같은 라이브러리). 필요한 도구는 `docker` CLI 뿐이다.
- **R2 버킷은 Kairos 전용 `kairos-prod` 다** (ADR-033 — 회의·메모 원본 `uploads/`·`memory/` 와 같은 버킷).
  ★업로드는 api 컨테이너의 `R2_*` 를 따라간다. **서버 `.env` 의 R2 전환(`R2_BUCKET_NAME=kairos-prod`) 뒤에** 첫 실행·cron 등록을 한다 —
  전환 전에 돌리면 옛 공유 버킷 `nexus-core-storage` 로 올라간다 (전환은 2026-10-02 완료).
  키는 `backups/kairos/` 아래로만 쓰고 (업로드 코드가 다른 prefix 를 거부한다 — 원본 prefix 를 덮어쓰지 않게),
  스크립트는 R2 에서 **아무것도 지우지 않는다.**
- 임시 이름(`.partial`)으로 쓰고 `pg_restore --list` 검증을 통과해야 최종 이름을 갖는다. 목차에
  `alembic_version · users · auth_user · auth_account · workspaces · meetings` 데이터가 없으면 실패다.
- 실패하면 exit 1. 업로드가 실패해도 검증된 로컬 사본은 남는다. 보존 정리는 전부 성공했을 때만 돈다.
- 성공할 때마다 `~/kairos/backups/last-success` 를 갱신한다 (신선도 점검용).
- **백업에는 `.env` 가 없다.** `BETTER_AUTH_SECRET`(auth_jwks 개인키 암호화)·`INTEGRATIONS_ENCRYPTION_KEY`
  (Drive 토큰 암호화)가 백업 시점 값과 다르면 복원해도 로그인·Drive 연동이 깨진다.
  `.env` 는 비밀번호 관리자 등 **별도 위치**에 보관한다.
- 덤프에는 비밀번호 해시·세션 토큰·OAuth 토큰이 들어 있다. 로컬 파일은 `umask 077`(600), 디렉터리는 700 이다.

## 2. 설치 (사용자, 서버에서 1회 · 10분)

맥(레포 루트)에서 스크립트를 올린다.

```bash
scp -r deploy/oci/backup oci-tokyo:~/kairos/
```

서버에서:

```bash
ssh oci-tokyo
cd ~/kairos
chmod 700 backup/*.sh
mkdir -p -m 700 ~/kairos/backups       # cron 의 >> 리다이렉트가 스크립트보다 먼저 돈다

# 1) 점검만 (변경 0건) → 2) 실제 1회. 둘 다 exit 0 이어야 한다.
backup/pg-backup.sh --dry-run
backup/pg-backup.sh && cat ~/kairos/backups/last-success

# 서버 시간대 확인 — 아래 cron 줄은 UTC 기준이다
timedatectl | grep 'Time zone'
crontab -e
```

crontab 에 한 줄 추가한다 (UTC 18:37 = **KST 03:37**, 사용자 idle 시간대).
서버 시간대가 `Asia/Seoul` 이면 `37 3 * * *` 로 바꾼다. 같은 서버의 nexus-core 백업(04:17)과 겹치지 않는다.

```cron
37 18 * * * /bin/bash -lc '$HOME/kairos/backup/pg-backup.sh >> $HOME/kairos/backups/backup.log 2>&1'
```

`bash -lc` 로 감싸는 이유 — 비로그인 셸의 PATH 에 docker 가 없을 수 있다 (`deploy/oci/README.md` 함정).

다음 날 확인:

```bash
tail -n 20 ~/kairos/backups/backup.log          # "✅ R2 업로드 — key=backups/kairos/..." 줄
find ~/kairos/backups/last-success -mmin -1560   # 26시간 이내면 경로가 출력된다. 빈 출력 = 백업 멈춤
```

**R2 보존 기간 = 14일** (2026-09-27 사용자 결정, 로컬 보관과 같다) — 스크립트는 R2 를 지우지 않으므로
`kairos-prod` → Settings → Object lifecycle rules 의 `backups-14d` (prefix `backups/kairos/` 만, 14일 후 삭제) 가 지운다.
원본 prefix 에는 걸지 않는다.

## 3. 복원 리허설 (분기 1회 · 체크리스트 2-4)

백업 직후 조용한 시간에 서버에서 돌린다. 임시 컨테이너는 메모리 512m, 포트 publish 없음, 끝나면 자동 제거.

```bash
cd ~/kairos
LATEST=$(ls -1t ~/kairos/backups/kairos-*.dump | head -1)
(cd ~/kairos/backups && sha256sum -c "$(basename "$LATEST").sha256")
backup/pg-restore-check.sh "$LATEST" --compare kairos-db
```

통과 기준 = 마지막 줄 `✅ 테이블 N개 row count 전부 일치 · alembic_version 일치`.
백업 이후 운영 DB 에 쓰기가 있었으면 그 테이블(`auth_session`, `memory_events` 등)만 `MISMATCH` 가 날 수 있다
— 새로 백업을 뜬 직후 다시 돌려서 사라지면 정상이다.

비교 쿼리 (스크립트에 들어 있는 것과 같다 — 모든 public 테이블의 **정확한** count, 쓰기 없음):

```sql
SELECT table_name,
       (xpath('/row/c/text()',
              query_to_xml(format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name),
                           false, true, '')))[1]::text::bigint AS rows
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

주요 테이블: `users` · `auth_user` · `auth_account` · `auth_session` · `workspaces` · `workspace_members` ·
`projects` · `meetings` · `transcript_segments` · `notes` · `action_items` · `inbox_items` ·
`embedding_chunks` · `memory_items` (2026-09-27 기준 전체 32개 = `models.py` `__tablename__` 26 + Better Auth 5 + `alembic_version`.
스크립트는 목록을 하드코딩하지 않고 `information_schema` 에서 읽으므로 테이블이 늘어도 따라간다).

### 로컬 리허설 기록

2026-09-27 — 로컬 QA DB(`kairos-qa-db`, rev `b3d5f8a1c2e4`)를 `--local-only` 로 덤프(256,579 bytes · 목차 239개)
→ 임시 컨테이너 복원(확장 `vector 0.8.0` · `pg_trgm 1.6` 포함) → 32개 테이블 row count 전부 일치, alembic_version 일치.
음성 대조군도 확인했다: 없는 DB 컨테이너 → exit 1, 잘린 덤프 → `pg_restore` 실패(exit 1),
행 1개를 지운 사본과 비교 → `semantic_caches MISMATCH`(exit 1). 남은 임시 컨테이너·dangling 볼륨 0.
R2 업로드 단계는 R2 에 닿지 않도록 가짜 boto3 로만 검증했다(키 prefix 거부 · 크기 불일치 감지) —
**실제 업로드는 서버 첫 실행(§2)이 첫 검증이다.**

## 4. 실제 복원

### A. DB 는 살아 있고 데이터가 망가졌을 때 (잘못된 삭제·마이그레이션 사고)

새 DB 에 복원해 검증한 뒤 **이름을 바꿔 끼운다.** 망가진 DB 는 지우지 않고 남긴다 (되돌릴 수 있게).

```bash
cd ~/kairos
backup/pg-backup.sh --local-only                        # 0. 지금 상태도 보존
docker compose -f docker-compose.prod.yml stop web api  # 1. 쓰기 중단 (cloudflared 는 502 를 낸다)

DUMP=~/kairos/backups/kairos-YYYYMMDDTHHMMSSZ.dump     # 2. 복원할 덤프
docker exec kairos-db createdb -U kairos kairos_restored
docker exec -i kairos-db pg_restore -U kairos -d kairos_restored \
  --no-owner --no-privileges --exit-on-error < "$DUMP"

# 3. 검증 — 위 비교 쿼리를 kairos_restored 에 돌려 기대치와 맞는지 본다
docker exec kairos-db psql -U kairos -d kairos_restored -c "SELECT version_num FROM alembic_version"

# 4. 교체 (접속이 남아 있으면 실패한다 — web/api 가 멈췄는지 먼저 확인)
docker exec kairos-db psql -U kairos -d postgres -c "ALTER DATABASE kairos RENAME TO kairos_broken_YYYYMMDD"
docker exec kairos-db psql -U kairos -d postgres -c "ALTER DATABASE kairos_restored RENAME TO kairos"

# 5. 재기동 — migrate one-shot 이 먼저 돌아 백업 시점 리비전을 현재 이미지의 head 로 올린다
docker compose -f docker-compose.prod.yml up -d
curl -s https://kairos.woosung.dev/api/auth/jwks   # 키가 나와야 한다 (BETTER_AUTH_SECRET 일치 확인)
```

### B. 볼륨·VM 을 잃었을 때

1. `deploy/oci/README.md` "최초 부트스트랩" 대로 서버를 세운다. `.env` 는 별도 보관본에서 복구한다.
2. 덤프를 구한다 — 로컬 사본이 없으면 Cloudflare 대시보드 → R2 → `kairos-prod` →
   `backups/kairos/YYYY/MM/DD/` 에서 내려받아 `scp` 로 올린다.
3. `docker compose -f docker-compose.prod.yml up -d db` (db 만. initdb 가 확장을 만든다)
4. `docker exec -i kairos-db pg_restore -U kairos -d kairos --no-owner --no-privileges --exit-on-error < "$DUMP"`
5. `docker compose -f docker-compose.prod.yml up -d` → 위 `jwks` 확인 → 브라우저 로그인 후 데이터 화면까지.

## 5. 하지 말 것

- `docker compose down -v` — `db-data` 볼륨이 지워진다. 백업이 있어도 마지막 백업 이후 데이터는 사라진다.
- 백업 prefix 를 바꾸거나 `backups/` 밖으로 올리기 — 같은 버킷에 회의·메모 원본이 있고, lifecycle `backups-14d` 가 이 prefix 에만 걸려 있다.
- 복원 리허설을 운영 컨테이너(`kairos-db`) 안의 새 DB 로 하기 — 리허설은 항상 `pg-restore-check.sh` 의 임시 컨테이너로.
