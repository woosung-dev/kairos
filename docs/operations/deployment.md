# Kairos 배포 가이드

> 2026-08-14 ADR-028 로 **오라클 클라우드 셀프호스팅** 전환 완료.
> Vercel · GCP Cloud Run 은 같은 날 철거됐다. 이 문서는 그 이후의 절차만 담는다.

**운영 상세(명령어·트러블슈팅)는 [`deploy/oci/README.md`](../../deploy/oci/README.md) 가 정본이다.**
여기서는 전체 그림과 진입점만 다룬다.

---

## 아키텍처

```
브라우저
  └─ Cloudflare (엣지 TLS)
       └─ Cloudflare Tunnel  ── 인바운드 포트 0개
            └─ 오라클 A1 (truewords-oracle, aarch64, 도쿄)
                 ├─ kairos-web   127.0.0.1:3100   Next.js standalone
                 ├─ kairos-api   127.0.0.1:8200   FastAPI
                 └─ kairos-db    127.0.0.1:5434   PostgreSQL 17 + pgvector 0.8
```

| 항목 | 값 |
|---|---|
| FE | https://kairos.woosung.dev |
| API | https://kairos-api.woosung.dev |
| 서버 | `ssh truewords-oracle` (quantbridge · truewords 와 **공유**) |
| 배포 디렉토리 | `~/kairos` (compose · `.env` · initdb) |
| 오브젝트 스토리지 | Cloudflare R2 (유지) |
| 인증 | Better Auth 자체 호스팅 (web 컨테이너, ADR-031) |
| AI | Gemini · OpenAI (유지) |

**같은 호스트의 다른 프로젝트가 쓰는 포트**(건드리지 말 것): 3200 quantbridge-frontend ·
5432 truewords postgres · 5433 quantbridge-db · 6333 qdrant · 6380 quantbridge-redis ·
8100 quantbridge-api.

---

## 배포

```bash
TAG=$(git rev-parse --short HEAD)

mise run deploy-preflight      # 진행 중인 회의 처리가 0 인지 + .env 인코딩 게이트
mise run deploy-build $TAG     # 맥에서 arm64 네이티브 빌드 (BE + FE)
mise run deploy-ship $TAG      # docker save | ssh | docker load → 태그 교체 → up -d → GC
mise run deploy-status         # 컨테이너 상태 + /ready + 서버 자원 (디스크 포함)
```

`deploy-ship` 은 마지막에 `deploy-gc` 를 부른다 — 서버에 **운영중 태그 + 직전 태그**만 남기고
나머지 `kairos-api` / `kairos-web` 이미지를 지운다. 이 서버는 quantbridge·truewords 와
공유하므로 **`docker system prune` 계열을 쓰지 않는다** (남의 프로젝트 이미지가 지워진다).

레지스트리를 쓰지 않는다. 맥(darwin/arm64)과 서버(aarch64)가 같은 아키텍처라
`--platform linux/arm64` 가 에뮬레이션 없이 돈다.

**FE 빌드 인자**는 `deploy/oci/build.env` (gitignore) 에서 읽는다. `NEXT_PUBLIC_*` 은
빌드타임에 번들로 인라인되므로 **도메인이 바뀌면 반드시 재빌드**해야 한다.

### 배포 전 반드시 확인

`BackgroundTasks` 는 재시도가 없다. 처리 중인 회의가 있는 상태로 컨테이너를 교체하면
그 회의는 `transcribing` 으로 영구 정지한다. `mise run deploy-preflight` 가 이걸 검사한다.

---

## 롤백

`~/kairos/.env` 의 태그 두 줄을 이전 값으로 되돌리고 `up -d`.

```bash
mise run deploy-rollback <이전TAG>
```

서버에 **운영중 + 직전 1개** 태그를 남긴다 (`deploy-gc` 가 매 배포마다 강제한다 —
직전 태그는 `deploy-ship` 이 `.env` 를 덮어쓰기 전에 읽어 GC 에 넘긴다).
그보다 오래된 태그로 되돌리려면 이미지를 다시 빌드해 보내야 한다.

**마이그레이션은 자동 롤백되지 않으므로** 스키마 변경은 expand-then-contract 로만 한다.

---

## 환경변수

서버 `~/kairos/.env` (0600) 가 **프로덕션 SoT** 다. 템플릿은 `deploy/oci/.env.example`.
발급처와 전체 매트릭스는 [`secrets.md`](../development/secrets.md) 참조.

> ⚠️ **`.env` 에 인라인 주석을 절대 붙이지 마라.** docker compose 의 env_file 파서는
> `KEY=value  # 설명` 에서 주석을 값의 일부로 읽는다. 한글이 값에 섞이면 헤더
> ascii 인코딩에서 터져 401 이 아니라 **500** 이 나고, `CORS_ORIGINS` 오염은 조용한 CORS
> 전면 차단으로 나타난다.
>
> 게이트: `LC_ALL=C grep -n '[^[:print:][:space:]]' ~/kairos/.env` → 출력 0줄

---

## 데이터베이스

`pgvector/pgvector:0.8.0-pg17` 컨테이너. 확장(`vector`, `pg_trgm`)은 `deploy/oci/initdb/`
스크립트가 볼륨 최초 생성 시 자동으로 만든다.

마이그레이션은 compose 의 **one-shot `migrate` 서비스**가 담당하고, `api` 는
`service_completed_successfully` 로 게이트된다. 앱 기동에 묶지 않는 이유는
`restart: unless-stopped` 와 결합하면 마이그레이션 실패가 무한 재시작 루프가 되기 때문이다
(2026-06-23~30 prod 전면 다운이 그 형태였다).

**백업은 아직 없다.** 개발 단계라 의도적으로 제외했고 운영 전환 시 착수한다(BL-OCI-1).
그때까지 **`docker compose down -v` 는 절대 금지** — `-v` 가 `db-data` 볼륨을 지운다.

이전 원본인 Neon(`neondb`)은 당분간 남겨 두어 사실상의 백업 역할을 한다.

---

## 검증

```bash
# 로컬 게이트 (CI 와 동일 invocation)
mise run be-test && mise run fe-test && mise run fe-typecheck && mise run contracts-check

# 배포 후
mise run deploy-status
./scripts/verify-prod.sh https://kairos-api.woosung.dev
```

> **`/health` 200 은 배포 검증이 아니다.** 플레이스홀더 키로도 200 이 난다.
> 인증까지 살아 있는지는 `curl -s https://kairos.woosung.dev/api/auth/jwks` 가 키를 돌려주는지로 본다.
> 검증은 반드시 **브라우저 로그인 후 데이터 화면까지** 확인한다.

---

## 알려진 함정

- **Cloudflare 413 은 CORS 오류처럼 보인다.** Free/Pro 는 요청 바디를 100MB 에서 자르는데
  엣지가 반환하는 413 에는 CORS 헤더가 없다. 업로드 실패 시 파일 크기부터 확인할 것
  (`MAX_UPLOAD_BYTES` 90MB, FE 에도 동일 가드).
- **hostname 등록 전에 도메인을 조회하면 로컬 DNS 에 NXDOMAIN 이 캐시된다.** `dig` 는 되는데
  curl/브라우저만 실패하면 `sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder`.
- **원격 명령은 `ssh host 'bash -lc "..."'`** — 비로그인 셸의 PATH 에 docker compose 가 없다.
- **API 호스트명에 Cloudflare Access 를 걸지 마라.** XHR·SSR 이 Access 리다이렉트를 따라가지
  못한다. API 의 문은 Better Auth 가 발급한 JWT 다 (ADR-031).

---

## 부록 — 이전 배포 스택 (2026-08-14 철거)

| 레이어 | 위치 | 철거 사유 |
|---|---|---|
| FE | Vercel (Git 연동, `vercel.json` 없음) | 운영 단일화. 철거 시점에 Root Directory 가 `frontend` 로 남아 **배포가 이미 실패 중**이었다(ADR-027 이동 후 미갱신) |
| BE | GCP Cloud Run `kairos-api` @ asia-northeast3 | 동일. 철거 시점에 IAM 바인딩이 0개라 **외부에서 403** 이었다 |
| 자동배포 | `.github/workflows/deploy.yml` (WIF + Artifact Registry) | 파일 삭제. GitHub Actions 결제 실패로 실행되지 않던 상태였다 |

Artifact Registry `kairos-docker` · WIF provider `kairos` · SA `kairos-deployer` · 미사용
GitHub Secrets 7건은 2026-08-14 에 함께 삭제했다.

GCP 프로젝트 `gcp-project-504004` 와 WIF pool `github` 는 cookmark · nexus-core 가 공유하므로
남겨 둔다.

**남은 GitHub Secrets 15건은 전부 `test.yml` · `nightly-e2e.yml` · `r2-cleanup.yml` 이 실제로
참조하는 것들이다.** 정리 판단은 워크플로 grep 과 대조해서 한다:

```bash
comm -23 <(gh secret list --repo woosung-dev/kairos --json name --jq '.[].name' | sort) \
         <(grep -rhoE "secrets\.[A-Z_0-9]+" .github/workflows/ | sed 's/secrets\.//' | sort -u)
```
