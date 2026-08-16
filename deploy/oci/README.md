# Kairos — Oracle Cloud 배포 운영 문서

ADR-028. Vercel(FE) + GCP Cloud Run(BE) + Neon(DB) → 오라클 단일 VM 셀프호스팅.

## 배치

서버 `truewords-oracle` (Ampere A1 aarch64, 2 OCPU / 12GB, 도쿄, Ubuntu 22.04)를
quantbridge · truewords 와 **공유**한다. 인바운드는 SSH 22 만 열려 있고, 공개 경로는
Cloudflare Tunnel 이다.

| 서비스 | 컨테이너 | 호스트 포트 | 공개 주소 |
|---|---|---|---|
| Next.js | `kairos-web` | 127.0.0.1:3100 | https://kairos.woosung.dev |
| FastAPI | `kairos-api` | 127.0.0.1:8200 | https://kairos-api.woosung.dev |
| PostgreSQL 17 + pgvector 0.8 | `kairos-db` | 127.0.0.1:5434 | (비공개) |
| Cloudflare Tunnel | `kairos-cloudflared` | `network_mode: host` | — |

이미 점유된 포트(건드리지 말 것): 3200 quantbridge-frontend · 5432 truewords postgres ·
5433 quantbridge-db · 6333 qdrant · 6380 quantbridge-redis · 8100 quantbridge-api.

## 최초 부트스트랩

```bash
ssh truewords-oracle
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
XHR 과 SSR 헤어핀이 그 리다이렉트를 따라가지 못한다. API 의 문은 Clerk JWT 다.

## 배포

맥에서 arm64 네이티브로 빌드해 SSH 파이프로 넘긴다. 레지스트리를 쓰지 않는다.
맥(darwin/arm64)과 서버(aarch64)가 같은 아키텍처라 에뮬레이션이 없다.

```bash
TAG=$(git rev-parse --short HEAD)

# BE
docker buildx build --platform linux/arm64 -t kairos-api:$TAG --load apps/api

# FE — NEXT_PUBLIC_* 는 빌드타임 인라인이다. 도메인이 바뀌면 반드시 재빌드.
docker buildx build --platform linux/arm64 -t kairos-web:$TAG --load \
  --build-arg NEXT_PUBLIC_API_URL=https://kairos-api.woosung.dev \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_... \
  --build-arg NEXT_PUBLIC_RECALL_ENABLED=true \
  --build-arg NEXT_PUBLIC_APP_ENV=production \
  --build-arg NEXT_PUBLIC_FOUNDER_CLERK_ID=user_... \
  apps/web

# 전송
docker save kairos-api:$TAG | gzip -1 | ssh truewords-oracle 'gunzip | docker load'
docker save kairos-web:$TAG | gzip -1 | ssh truewords-oracle 'gunzip | docker load'

# 태그 교체 후 기동
ssh truewords-oracle "bash -lc \"cd ~/kairos && \
  sed -i 's/^KAIROS_API_TAG=.*/KAIROS_API_TAG=$TAG/; s/^KAIROS_WEB_TAG=.*/KAIROS_WEB_TAG=$TAG/' .env && \
  docker compose -f docker-compose.prod.yml up -d\""
```

원격 명령은 항상 `bash -lc` 로 감싼다. 비로그인 ssh 셸은 PATH 에 docker compose 가 없다.

### 배포 전 확인

진행 중인 회의 처리가 있으면 배포하지 않는다. BackgroundTasks 는 재시도가 없어서
컨테이너가 교체되면 그 회의는 `transcribing` 상태로 영구 정지한다.

```sql
SELECT count(*) FROM meetings WHERE status IN ('transcribing','analyzing');
```

## 롤백

`.env` 의 태그 두 줄을 이전 값으로 되돌리고 `up -d`. 서버에 직전 2개 태그를 남겨 둔다.

```bash
ssh truewords-oracle "bash -lc 'cd ~/kairos && \
  sed -i \"s/^KAIROS_API_TAG=.*/KAIROS_API_TAG=<이전>/\" .env && \
  docker compose -f docker-compose.prod.yml up -d api'"
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
uptime && free -h
```

## 함정

- **`/health` 200 은 배포 검증이 아니다.** 플레이스홀더 Clerk 키로도 200 이 난다. 검증은
  반드시 브라우저 로그인 후 데이터 화면까지.
- **`.env` 인라인 주석 금지.** 값에 섞인 한글이 Clerk 헤더 ascii 인코딩에서 터져 500 을 만든다.
  `CORS_ORIGINS` 오염은 조용한 CORS 전면 차단으로 나타난다.
- **원격 실행은 `bash -lc`.** 비로그인 셸의 PATH 문제.
- **`docker compose down -v` 금지.** `-v` 는 `db-data` 볼륨을 지운다. 백업이 아직 없다.
- **Cloudflare 413 은 CORS 오류처럼 보인다.** 엣지가 반환하는 413 에는 CORS 헤더가 없다.
  업로드 실패 시 파일 크기부터 확인할 것 (`MAX_UPLOAD_BYTES` 90MB).

## 미착수 (BL 등재)

- DB 백업 자동화 — 운영 전환 시 착수. 현재는 개발 단계라 의도적으로 없다.
- presigned URL 업로드 전환 — 100MB 초과 파일이 실제로 필요해지면.
- GitHub Actions 자동 배포 — 수동 3회 성공 + 7일 무사고 후.
