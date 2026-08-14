# ADR-028: 셀프호스팅 전환 — OCI 단일 VM + Cloudflare Tunnel

**Status**: Accepted
**Date**: 2026-08-14
**관련**: ADR-001 (기술 스택) · ADR-008 (BE 배포 자동화 — 본 ADR 이 대체) · ADR-020 (pgvector HNSW halfvec) · ADR-021 (Sentry) · ADR-024 (GA readiness / Clerk Production) · ADR-027 (apps 레이아웃) · `deploy/oci/README.md`

---

## 1. 배경

배포가 3곳에 흩어져 있었다.

| 레이어 | 위치 | 정의 |
|---|---|---|
| FE | Vercel (Git 연동) | **레포에 없음** — 대시보드 설정이 유일한 진실 |
| BE | GCP Cloud Run `kairos-api` @ asia-northeast3 | `.github/workflows/deploy.yml` 단 하나 (IaC 없음) |
| DB | Neon PostgreSQL 17.10 @ us-east-1 | — |

여기에 WIF pool / Artifact Registry / Cloud Scheduler 를 별도 관리해야 했다. 이미
quantbridge · truewords 를 돌리는 오라클 서버가 있으므로 **개인 프로젝트 운영 지점을 하나로 합친다.**

### 결정을 좌우한 실측 (2026-08-14)

- **오라클 A1 무료 한도가 2026-06-15 부로 4 OCPU/24GB → 2 OCPU/12GB 로 반감**됐다(무공지). 기존
  `truewords-oracle` 이 정확히 그만큼 쓰고 있어 **신규 인스턴스는 PAYG 과금 대상**이다.
- 그 서버 실측: `load average 0.19`(2코어), 메모리 available **7.7GB**, 디스크 여유 **63GB**,
  컨테이너 13개의 CPU 합계 2% 미만. → 공유 여력이 있다.
- 런타임에 로컬 ML 추론이 **0건**이다. STT=OpenAI Whisper API, LLM=Gemini API, 임베딩=OpenAI API.
  `uv.lock` 79 패키지가 전부 aarch64 또는 pure 휠(예외 `pywin32` 는 win32 마커 + dev 그룹).
  시스템 의존성은 ffmpeg 하나. → ARM 이전 리스크가 없다.
- Vercel 전용 기능 실사용이 거의 없다. middleware 1개(`apps/web/src/proxy.ts`) + `next/image` 1곳뿐이고
  **ISR·edge runtime·route handler·server actions·rewrites·cron 은 전부 0건**이다.
- 업로드 실태(운영 DB 전수, 회의 87건): **최장 5.1분**, p50 8초, p95 29초. 확장자 `.m4a` 71 /
  `.webm` 17 / `.mp3` 6 / `.mp4` 1 → 최대 파일 약 5MB.
- DB 규모: **전체 14MB**. → 이전 부담이 사실상 없다.

## 2. 결정

### D1. 기존 `truewords-oracle` 공유 (신규 인스턴스 아님)

무료 한도가 이미 소진돼 신규 A1 은 과금이다. 실측 여유(available 7.7GB / load 0.19)가 Kairos 상시
요구(~500MB)를 크게 웃돈다. 유일한 실질 리스크는 ffmpeg chunk 병렬이 2 OCPU 를 순간 점유해 같은
호스트의 quantbridge 소크를 굶기는 것 → `cpus: 1.5` 하드 캡으로 격리한다.

컨테이너가 격리해주지 **않는** 4가지만 맞추면 공존한다: 호스트 publish 포트 · 컨테이너 이름 ·
compose 프로젝트명 · 자원 총량.

| 서비스 | 컨테이너 | 호스트 포트 | 캡 |
|---|---|---|---|
| Next.js standalone | `kairos-web` | 127.0.0.1:3100 | 512m |
| FastAPI | `kairos-api` | 127.0.0.1:8200 | 1536m / cpus 1.5 |
| PostgreSQL 17 + pgvector 0.8 | `kairos-db` | 127.0.0.1:5434 | 1g |
| Cloudflare Tunnel | `kairos-cloudflared` | `network_mode: host` | 128m |

기존 점유(건드리지 않음): 3200 · 5432 · 5433 · 6333 · 6380 · 8100.

### D2. DB 를 Neon 에서 오라클 셀프호스팅으로 이전

`pgvector/pgvector:0.8.0-pg17` 이 Neon 원본(PG 17.10 / vector 0.8.0)과 정확히 일치한다.
`embeddings/repository.py` 의 `hnsw.iterative_scan='relaxed_order'` 가 요구하는 pgvector ≥ 0.8 을 만족한다.
14MB 라 이전 비용이 낮고, us-east-1 RTT(~150ms)가 사라져 RAG 지연이 개선된다.

Neon 이 기본 설치했던 `pg_session_jwt` 는 코드 사용처가 0건이라 재현하지 않는다.

**백업은 이번 범위에서 의도적으로 제외한다** — 아직 개발 단계이고, 운영 전환 시점에 착수한다(BL-OCI-1).
그때까지 `docker compose down -v` 는 금지다.

### D3. R2 · Clerk · Gemini · OpenAI · Sentry 는 유지

이전 범위는 **컴퓨트 + DB** 다. R2 는 egress 무료이고 presigned/cleanup/CORS 회귀 테스트가 이미
자산으로 존재한다. OCI Object Storage 로 옮기면 `r2.py`·`r2_cleanup`·회귀 테스트를 전부 재작성해야
하는데 얻는 게 없다.

### D4. 업로드는 현행 백엔드 프록시 유지 + 한도만 낮춤

Cloudflare Free/Pro 는 요청 바디를 100MB 에서 자른다(Tunnel 경유 동일). Kairos 서버 기본값은 500MB 다.
그러나 **운영 데이터 전수 실측 결과 최대 파일이 약 5MB** 로 상한의 1/20 이다. `.m4a`(아이폰 음성메모·
카카오톡) 기준 100MB 에 닿으려면 7시간 이상 녹음해야 한다.

→ presigned URL 전환(약 5시간)은 지금 필요 없는 보험이다. **BL-OCI-2 로 등재**하고, 대신
`MAX_UPLOAD_BYTES=90MB` env override(코드 변경 0) + FE 클라이언트 사전 안내만 넣는다.

이유: **Cloudflare 엣지가 반환하는 413 에는 CORS 헤더가 없어 브라우저 콘솔에 CORS 오류로 보인다.**
나중에 이 벽에 부딪히면 "R2 CORS 문제 재발"로 오진하기 딱 좋다. 서버가 먼저 한국어로 거절하게 한다.

memory 음성 캡처(`MAX_AUDIO_BYTES` 25MB, Whisper API 한도)는 100MB 에 구조적으로 도달할 수 없어
별도 가드를 두지 않는다.

### D5. 공개 경로는 Cloudflare Tunnel, 호스트명 2개

```
kairos.woosung.dev      → http://127.0.0.1:3100
kairos-api.woosung.dev  → http://127.0.0.1:8200
```

인바운드 포트 0개, 인증서 관리 0, origin IP 비노출. 이 계정에서 이미 검증된 패턴이다.
Tunnel 의 유일한 실질 비용이던 100MB 바디 한도는 D4 에서 무해함이 실측됐다.

- **두 호스트 모두 Cloudflare Access 를 걸지 않는다.** API 는 XHR·SSR 이 Access 리다이렉트를 따라가지
  못하고(quant-bridge 실측), FE 는 Access 가 Clerk 자체 로그인 플로우를 깬다. API 의 문은 Clerk JWT 다.
- 호스트명을 나누는 이유: 단일 호스트 + Next rewrites 는 CORS 를 없애주지만 모든 API 트래픽이 단일
  스레드 Node 서버를 한 번 더 거치고, `rag/router.py` 의 SSE 가 프록시 버퍼링 위험을 얻는다. CORS 는
  이미 구현·테스트돼 있다(`main.py:161-175`, `tests/test_cors.py`).
- `cloudflared` 는 `network_mode: host` — 이 호스트의 iptables 가 INPUT 에서 22 만 ACCEPT 하므로
  브리지에서 호스트 loopback 으로 가는 경로가 구조적으로 없다.

### D6. alembic 은 별도 one-shot 서비스 + advisory lock

기존 `Dockerfile` CMD 는 `alembic upgrade head && uvicorn ...` 이었다. `restart: unless-stopped` 와
결합하면 마이그레이션 실패가 **무한 재시작 루프**가 되고, "마이그레이션 실패"와 "앱 크래시"를 구분할
수 없다 — 2026-06-23~30 prod 전면 다운이 정확히 그 형태였다.

→ `docker-entrypoint.sh` 가 role(`migrate`/`api`)로 분기하고, compose 의 `migrate` 서비스가
`service_completed_successfully` 조건으로 `api` 를 게이트한다.

동시 실행 직렬화를 위해 `alembic/env.py` 에 `pg_advisory_lock` 을 넣되, **반드시 별도 커넥션에서
AUTOCOMMIT 으로** 잡는다. 2026-08-14 실측한 실패 2종:

1. 마이그레이션 커넥션에서 잡으면 `exec_driver_sql` 이 연 트랜잭션이 alembic 의
   `autocommit_block`(CONCURRENTLY DDL 용)과 충돌해 `assert self._transaction is not None` 로 죽는다.
2. 별도 커넥션이어도 트랜잭션을 열어두면(`idle in transaction`) 다음 마이그레이션의
   `CREATE INDEX CONCURRENTLY` 가 `virtualxid` 락을 기다리며 **영구 대기**한다.

### D7. 배포는 1차 수동, 자동화는 조건부

맥에서 arm64 네이티브 빌드 → `docker save | ssh | docker load` → 서버 `.env` 의 태그 교체 → `up -d`.
레지스트리(OCIR/GHCR)를 쓰지 않는다. 맥(darwin/arm64) ↔ 서버(aarch64) 가 같은 아키텍처라
에뮬레이션이 없다. GH 러너는 amd64 라 arm64 빌드에 QEMU 가 붙어 `uv sync` 가 5~10배 느려진다.

**GitHub Actions 자동화 진입 조건**: 수동 배포 3회 연속 성공 + 컷오버 후 7일 무사고 + 실제 장시간
오디오 1건 end-to-end 완주. (BL-OCI-3)

`deploy.yml` 은 컷오버 당일 push 트리거만 제거해 `workflow_dispatch` 로 남긴다. 병행 기간 중
`apps/backend/**` 머지가 Cloud Run 을 조용히 재배포하는 것을 막되, 롤백 경로는 유지한다.
D+7 무사고 후 삭제.

### D8. FE 이미지는 컨테이너 내부 빌드(멀티스테이지)

`next/image` 사용으로 런타임에 sharp 네이티브 바이너리가 필요하다. 맥에서 빌드한
`.next/standalone` 을 그대로 얹으면 darwin-arm64 바이너리가 들어가 리눅스에서 깨진다.
빌드를 컨테이너 안에서 하면 linuxmusl-arm64 가 설치된다.

`NEXT_PUBLIC_*` 6종은 `ARG` 로 받아 **빌드타임 인라인**된다(`src/lib/api-client.ts:2`).
도메인이 바뀌면 반드시 재빌드해야 하며 런타임 env 로는 바뀌지 않는다.

## 3. 기각한 대안

| 대안 | 기각 사유 |
|---|---|
| 신규 A1 인스턴스 | 무료 한도 소진으로 월 $25~30 과금. 실측상 기존 서버에 여유가 충분하고, 도쿄 A1 은 `Out of capacity` 도 잦다 |
| presigned URL 업로드 전환 | 운영 실측 최대 파일이 5MB. 지금 필요 없는 5시간 작업 → BL-OCI-2 |
| 업로드 한도를 100MB 로 두고 방치 | 엣지 413 이 CORS 오류로 보여 나중에 오진을 부른다 |
| 443 직접 개방 + Caddy/Let's Encrypt | 100MB 하나 피하려고 영구적인 2번째 인그레스 평면과 origin IP 노출을 도입 |
| Neon 유지 | 운영 단일화라는 1순위 목적에 반한다. DB 가 14MB 라 이전 비용도 낮다 |
| R2 → OCI Object Storage | 재작성 비용만 있고 얻는 게 없다 |
| 처음부터 GH Actions 자동 배포 | 검증 안 된 경로를 자동화하면 미지수가 곱해진다. 첫 배포를 손으로 완주한 뒤 자동화 |

## 4. 결과 / 후속

### 즉시 얻는 것
- Cloud Run 1Gi 메모리 한도와 `/tmp`=tmpfs(RAM) 제약 해소. 4시간 오디오 처리 시 피크 ~900MB 가
  1Gi 한도에 눌리던 구조가 사라진다.
- `CORS_ORIGINS` 다중 오리진 가능(Cloud Run 액션의 쉼표 파싱 제약 소멸).
- 배포 정의가 레포 안으로 들어온다(`deploy/oci/`). Vercel 대시보드에만 있던 설정이 사라진다.

### 롤백
prod FE 가 `kairos-zeta-ebon.vercel.app`(Vercel 소유 호스트명)이라 컷오버는 DNS 전환이 아니다.
컷오버 = "새 URL 을 쓰기 시작", 롤백 = "이전 URL 로 복귀". Vercel + Cloud Run 을 건드리지 않으므로
전파 지연 0 으로 즉시 되돌아간다.

단 **컷오버 이후 오라클 DB 에 쌓인 데이터는 Neon 에 없다.** 실사용 데이터가 쌓이기 전이 롤백
마지노선이다.

### 후속 (BL 등재)
- **BL-OCI-1** DB 백업 자동화 — 운영 전환 시
- **BL-OCI-2** presigned URL 업로드 전환 — 100MB 초과 파일이 실제로 필요해지면. BL-070(500MB RAM 적재)도 함께 해소
- **BL-OCI-3** GitHub Actions 자동 배포 — D7 조건 충족 시

### 이번 범위에서 제외한 기존 갭
- `CLERK_PROD_HARDENING=false` 는 ADR-024(Clerk Production 컷오버) 소관이다. `true` 로 재무장하려면
  `CLERK_JWT_ISSUER` 가 Clerk Production 인스턴스를 가리켜야 하고, 그건 커스텀 도메인·신규 키·
  사용자 마이그레이션 전체를 요구한다. **인프라 이전과 같은 창에서 하면 인증 실패와 인프라 실패를
  구분할 수 없다.**
- `SENTRY_DSN` / `CRON_SECRET_TOKEN` 은 Cloud Run 에 주입돼 있지 않았다(2026-08-14 확인). 새 `.env` 를
  쓰는 김에 채운다 — 관측 없이 새 인프라로 들어가는 리스크가 더 크다.

### 관측된 문서 드리프트 (별건)
- prod Cloud Run URL 이 `kairos-api-gnd4iunquq-du.a.run.app` 인데 README·`secrets.md`·
  `verify-prod.sh` 에 적힌 값이 서로 다른 3종이었다. `verify-prod.sh` 만 정정했다.
- **dev 와 prod 가 같은 Neon DB(`neondb`)를 쓰고 있다.** 로컬 개발이 운영 데이터를 직접 건드린다.
  이번 이전으로 오라클 DB 가 분리되지만, 로컬 개발 DB 분리는 별도 과제다.
