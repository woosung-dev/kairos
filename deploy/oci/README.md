# Kairos — Oracle Cloud 배포 운영 문서

ADR-028. Vercel(FE) + GCP Cloud Run(BE) + Neon(DB) → 오라클 단일 VM 셀프호스팅.

## 배치

서버 `oci-tokyo` (Ampere A1 aarch64, 2 OCPU / 12GB, 도쿄, Ubuntu 22.04)를
truewords · quantbridge · nexus-core 와 **공유**한다 (4개 프로젝트, `ubuntu` 계정 하나). 인바운드는 SSH 22 만 열려 있고,
공개 경로는 Cloudflare Tunnel 이다. 서버 전체 설정은 Kairos 가 소유하지 않는다 — 아래 "호스트 공통 설정".

`oci-tokyo` 는 맥 `~/.ssh/config` 의 별칭이다 (`mise.toml` 의 `oci_host`). 옛 별칭 `truewords-oracle` 을
같은 `Host` 줄에 남겨 둔다 — truewords · quant-bridge 레포의 스크립트가 아직 그 이름을 쓴다(2026-10-02 개명).

```
Host oci-tokyo truewords-oracle
  HostName <서버 공인 IP>
  User ubuntu
  IdentityFile <키 경로>
```

| 서비스 | 컨테이너 | 호스트 포트 | 공개 주소 |
|---|---|---|---|
| Next.js | `kairos-web` | 127.0.0.1:3100 | https://kairos.woosung.dev |
| FastAPI | `kairos-api` | 127.0.0.1:8200 | https://kairos-api.woosung.dev |
| PostgreSQL 17 + pgvector 0.8 | `kairos-db` | 127.0.0.1:5434 | (비공개) |
| Cloudflare Tunnel | `kairos-cloudflared` | `network_mode: host` | — |

이미 점유된 포트(건드리지 말 것): 3200 quantbridge-frontend · 5432 truewords postgres ·
5433 quantbridge-db · 6333 qdrant · 6380 quantbridge-redis · 8100 quantbridge-api ·
3300 · 3301 · 8300 · 5435 nexus-core (2026-10-02 실측 — 그전 목록에서 빠져 있었다).

## 최초 부트스트랩

```bash
ssh oci-tokyo
mkdir -p ~/kairos
```

`deploy/oci/` 의 `docker-compose.prod.yml`, `initdb/`, `.env.example` 을 서버 `~/kairos/` 로 복사한 뒤:

```bash
cd ~/kairos
cp .env.example .env && chmod 600 .env
vi .env    # 값 채우기

# 인코딩 게이트 — 반드시 통과해야 한다 (출력 0줄)
LC_ALL=C grep -n '[^[:print:][:space:]]' .env
```

Cloudflare Zero Trust → Networks → Tunnels 에서 `kairos` 터널을 만들고 public hostname 2건을 등록한다.

- `kairos.woosung.dev` → `http://localhost:3100`
- `kairos-api.woosung.dev` → `http://localhost:8200`

**API 호스트명에는 Cloudflare Access 를 걸지 말 것.** Access 는 브라우저 리다이렉트로 인증하는데
XHR 과 SSR 헤어핀이 그 리다이렉트를 따라가지 못한다. API 의 문은 Better Auth 가 발급한 JWT 다 (ADR-031).

## 배포

이미지는 CI 가 만든다. `main` 에 push 된 커밋이 Test 를 통과하면 `.github/workflows/release.yml` 이
`ubuntu-24.04-arm` 러너(서버와 같은 aarch64 — 에뮬레이션 없음)에서 빌드해 **GHCR 공개 패키지**에 올린다.
서버는 빌드하지 않고 pull 만 한다 (ADR-028 D7 Phase A, 2026-10-02).

| 이미지 | 태그 |
|---|---|
| `ghcr.io/woosung-dev/kairos-api` | `sha-<커밋 7자리>` — 불변. 같은 sha 는 다시 빌드하지 않는다 |
| `ghcr.io/woosung-dev/kairos-web` | 〃 |

배포는 서버 스크립트 하나가 한다 — `~/kairos/bin/kairos-deploy.sh` (정본 `bin/kairos-deploy.sh`, ADR-028 D7 Phase B).
부르는 곳은 둘이다. main 머지마다 자동으로 도는 것은 아직 꺼져 있다 (진입 조건 = 60분 오디오 1건 운영 완주).

```bash
gh run list --workflow release.yml --repo woosung-dev/kairos --limit 3   # 배포할 커밋의 런이 success 인지
TAG=sha-<커밋 7자리>

# A. 맥에서 — compose·스크립트 동기화 후 서버 스크립트 실행
mise run deploy-preflight             # 디스크 80% 미만 · 진행 중 회의 0 · .env 인코딩 (스크립트도 다시 확인한다)
mise run deploy-ship $TAG             # 스키마 변경이 있으면 rc 3 으로 멈춘다 → 확인 후 --migrate 를 붙여 다시
mise run deploy-status

# B. GitHub Actions — 빌드 후 배포. Actions 화면의 Review deployments 에서 승인한다
gh workflow run release.yml --repo woosung-dev/kairos -f sha=<40자 sha> -f deploy=true
```

스크립트 순서와 이유:

1. **compose·스크립트 해시 대조가 먼저.** 2026-08-17 Better Auth 컷오버에서 서버 compose 가 최초 부트스트랩 버전이라
   ADR-031 이 추가한 web.environment 5줄이 없었고 `BETTER_AUTH_SECRET` 이 빈 문자열로 주입돼 web 이 전면 500 이었다.
   `deploy-ship` 은 동기화한 뒤 부른다. Actions 는 파일을 보내지 않으므로 다르면 **rc 6** 으로 멈춘다 → 그 커밋은 A 로 배포.
2. **pull 이 `.env` 교체보다 먼저.** 없는 태그로 `.env` 를 바꾸면 `up` 만 실패하고 가짜 태그가 남아
   다음 배포의 GC 보존 대상이 된다. 서버에 이미 있는 태그는 pull 하지 않는다 (태그 불변) — 아래 비상 경로가 이 성질을 쓴다.
3. **스키마 관문.** 이미지의 `alembic heads` 와 DB 리비전이 다르면 아무것도 바꾸지 않고 **rc 3**.
   `--migrate`(A) 또는 `deploy-migrate` job 승인(B) 뒤에만 로컬 덤프를 뜨고 진행한다.
4. **처리 중 회의 대기.** 60초마다 최대 30분. 끝나지 않으면 **rc 4** (아무것도 바꾸지 않았다). 강제 옵션은 없다.
5. 기동 후 healthy → env 주입(이름만) → `/api/v1/ready` 를 확인한다. 실패하면 **rc 5** 와 롤백 명령을 출력한다.

종료 코드 전체와 결정 근거는 ADR-028 "D7 개정 — Phase B". 출력은 서버 `~/kairos/deploy.log` 에도 남는다.

**배포 전용 키** (Actions 용) — 서버 `~/.ssh/authorized_keys` 에 이 형식의 한 줄로 묶여 있다. 이 키로는 배포 하나만 할 수 있다.

```
restrict,command="/home/ubuntu/kairos/bin/kairos-deploy.sh --from-ssh" ssh-ed25519 AAAA... kairos-deploy@github-actions
```

키 교체: 맥에서 `ssh-keygen -t ed25519 -N "" -C kairos-deploy@github-actions -f <임시 경로>` → 서버의 그 줄 교체 →
`gh secret set DEPLOY_SSH_KEY --repo woosung-dev/kairos --env oci-production < <임시 경로>` (`oci-production-migrate` 도) → 임시 파일 삭제.

**FE 빌드 인자** `NEXT_PUBLIC_*` 는 repo **Variables** 에 있다 (secrets 가 아니다 — 브라우저 번들에 실리는 공개 값).
빌드타임 인라인이라 도메인이 바뀌면 변수를 고친 뒤 **새 커밋**으로 다시 빌드해야 한다 — 같은 sha 는 태그가 이미 있어 건너뛴다.
GHCR 이 공개이므로 이미지 레이어 히스토리도 공개다 — 빌드 인자에 비밀을 넣지 않는다 (`docs/development/secrets.md`).

```bash
gh variable list --repo woosung-dev/kairos
gh variable set NEXT_PUBLIC_API_URL --repo woosung-dev/kairos --body https://kairos-api.woosung.dev
```

### 비상 경로 — GitHub Actions · GHCR 장애 시

2026-08 에 Actions 결제 실패로 워크플로가 아예 돌지 않은 전례가 있다. 그때는 맥에서 빌드해 SSH 로 올린다.
이름은 GHCR 그대로 붙이므로 `deploy-ship` 이 서버에 있는 이미지를 보고 pull 을 건너뛴다.

```bash
TAG=sha-$(git rev-parse --short=7 HEAD)   # origin/main 과 같은 clean main 에서
mise run deploy-build $TAG                # 맥 arm64 빌드 — deploy/oci/build.env 필요 (gitignore)
docker save ghcr.io/woosung-dev/kairos-api:$TAG | gzip -1 | ssh oci-tokyo 'gunzip | docker load'
docker save ghcr.io/woosung-dev/kairos-web:$TAG | gzip -1 | ssh oci-tokyo 'gunzip | docker load'
mise run deploy-ship $TAG
```

나중에 CI 가 같은 sha 를 GHCR 에 올려도 서버는 맥 빌드본을 계속 쓴다 (같은 커밋이라 내용은 같다).

원격 명령은 항상 `bash -lc` (또는 `bash -ls`) 로 감싼다. 비로그인 ssh 셸은 PATH 에 docker compose 가 없다.

### 배포 전 확인

진행 중인 회의 처리가 있으면 배포하지 않는다. BackgroundTasks 는 재시도가 없어서
컨테이너가 교체되면 그 회의는 `transcribing` 상태로 영구 정지한다. 배포 스크립트가 이 SQL 로 기다린다.
최근 2시간 내 갱신분만 센다 — 최장 작업이 약 15분이라 더 오래된 것은 이미 죽은 좀비이고, 그걸로 막으면 배포가 영영 못 나간다.

```sql
SELECT count(*) FROM meetings WHERE status IN ('transcribing','analyzing') AND updated_at > now() - interval '2 hours';
```

## 롤백

`.env` 의 태그 두 줄을 이전 값으로 되돌리고 **api·web 만** 다시 띄운다 (`--no-deps` — migrate 를 돌리지 않는다).
구 이미지의 migrate 는 DB 의 새 리비전을 몰라 실패하고, 그러면 api·web 이 기동하지 않는다 (`docs/operations/deployment.md` 롤백 절).
롤백 상태에서는 `--no-deps` 없는 `up -d` 를 쓰지 않는다 (`up -d api` 도 — `.env` 를 바꾼 뒤면 api 가 멈춘다). 다음 정방향 배포는 `mise run deploy-ship`.
서버에 남는 것은 **운영중 + 직전 1개** 뿐이다 (`mise run deploy-gc` 가 매 배포마다 강제).
그보다 오래된 태그는 `deploy-rollback` 이 GHCR 에서 받아 온다 — 레지스트리가 이력을 보관한다.
Phase A 이전 태그(`sha-` 없는 맥 빌드)는 GHCR 에 없다.

```bash
mise run deploy-rollback sha-<이전>   # 서버에 없으면 pull → .env 태그 교체 → up -d --no-deps api web
```

마이그레이션은 자동 롤백되지 않는다. 스키마 변경은 expand-then-contract 로만 한다.

## 운영 명령

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml restart api

# 헬스
curl -sf 127.0.0.1:8200/api/v1/health        # liveness (DB 미검증)
curl -sf 127.0.0.1:8200/api/v1/ready         # readiness (SELECT 1)

# 같은 호스트의 다른 프로젝트 영향 확인
docker ps --format 'table {{.Names}}\t{{.Status}}'
uptime && free -h && df -h /

# 이미지 정리 (배포 시 자동 실행됨. 수동은 보존할 롤백 태그를 인자로)
mise run deploy-gc <롤백용_태그>
```

## DB 백업

`backup/pg-backup.sh` — 일 1회 `pg_dump -Fc` → `~/kairos/backups/` 14일 보관 → R2 `backups/kairos/YYYY/MM/DD/`.
`backup/pg-restore-check.sh` — 덤프를 임시 컨테이너에 복원해 테이블별 row count 를 원본과 대조한다.
설치·cron 줄·복원 절차는 [`docs/operations/runbooks/db-backup-restore.md`](../../docs/operations/runbooks/db-backup-restore.md).

```bash
scp -r deploy/oci/backup oci-tokyo:~/kairos/     # 맥에서. 이후 서버에서 런북 §2 대로 crontab 등록
```

## 호스트 공통 설정 — Kairos 는 소유하지 않는다

서버 전체에 하나뿐인 설정 5개가 있다. Kairos 도 기대고 있지만 만든 곳은 다른 레포이고,
**Kairos 레포는 이 중 어느 것도 쓰지 않는다** (2026-10-02 결정, ADR-028 D7 결정 5).

| 설정 | 값 (2026-10-02 실측) | 소유 |
|---|---|---|
| Docker 로그 회전 `/etc/docker/daemon.json` | json-file 10m × 3 | truewords `setup-vm.sh`(없을 때만 씀) · quant-bridge `host-bootstrap.sh`(덮어씀) |
| journald 상한 | 500M (`quantbridge.conf`) | quant-bridge |
| swap | 4GB | truewords |
| 디스크 경보 `dev.quantbridge.disk-guard` | 매시 :15, `/` 80% 이상이면 텔레그램 (회복 · 유닛 실패 알림 포함) | quant-bridge (user 타이머) |
| 빌더 캐시 정리 | 주 1회, 168h 초과분 | quant-bridge `docker-reclaim` · truewords |

Kairos 쪽 대응은 둘뿐이다.

- `mise run deploy-preflight` 가 `/` 사용률 80% 이상이면 배포를 멈춘다 — disk-guard 와 같은 기준.
- compose 의 `x-logging`(10m × 3)은 서비스 단위라 daemon.json 이 바뀌어도 Kairos 컨테이너 로그는 회전된다.

★**quant-bridge 가 이 서버에서 빠지면 디스크 경보와 빌더 캐시 정리가 함께 사라진다.** 그때 경보를 남는 프로젝트로 옮긴다.
지금 Kairos 에 따로 두지 않는 이유는 같은 경보가 두 개가 되기 때문이다.

## 함정

- **`/health` 200 은 배포 검증이 아니다.** 플레이스홀더 키로도 200 이 난다. 인증까지 살아 있는지는
  `curl -s https://kairos.woosung.dev/api/auth/jwks` 가 키를 돌려주는지로 본다. 검증은
  반드시 브라우저 로그인 후 데이터 화면까지.
- **`.env` 인라인 주석 금지.** 값에 섞인 한글이 헤더 ascii 인코딩에서 터져 500 을 만든다.
  `CORS_ORIGINS` 오염은 조용한 CORS 전면 차단으로 나타난다.
- **원격 실행은 `bash -lc`.** 비로그인 셸의 PATH 문제.
- **`docker compose down -v` 금지.** `-v` 는 `db-data` 볼륨을 지운다. 백업은 `backup/pg-backup.sh` 가
  cron 으로 돌 때만 존재한다 (`crontab -l | grep pg-backup`). 있어도 마지막 백업 이후 데이터는 잃는다.
- **`docker system prune` / `docker image prune -a` 금지.** 이 호스트는 truewords·quantbridge·nexus-core 와
  공유한다. 정리는 `mise run deploy-gc` 로만 — `kairos-api` / `kairos-web` 리포지토리(GHCR 이름 포함)로 한정한다.
- **`docker images` 는 생성일순이 아니다.** 이 서버는 Docker 29 + containerd 이미지 스토어라
  **태그 알파벳순**으로 나온다 (2026-08-30 실측). "최신 N개만 남긴다" 류의 `head`/`tail` 컷은
  운영중 태그를 삭제 대상에 넣는다 — 보존할 태그를 **명시**해야 한다.
- **Cloudflare 413 은 CORS 오류처럼 보인다.** 엣지가 반환하는 413 에는 CORS 헤더가 없다.
  업로드 실패 시 파일 크기부터 확인할 것 (`MAX_UPLOAD_BYTES` 90MB).

## 미착수 (BL 등재)

- presigned URL 업로드 전환 — 100MB 초과 파일이 실제로 필요해지면.
- main 머지마다 자동 배포 — 배포 job 은 있다(수동 실행). 남은 진입 조건 = 60분 오디오 1건 운영 완주 (ADR-028 D7 Phase B). 충족 후 `release.yml` `deploy` job 의 `if` 에 `|| github.event_name == 'workflow_run'` 한 줄.
- GHCR 보존 정책 (Phase C) — 태그가 쌓이기만 한다. GHCR 저장은 현재 무료라 급하지 않다.
