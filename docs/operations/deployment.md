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
            └─ 오라클 A1 (oci-tokyo, aarch64, 도쿄)
                 ├─ kairos-web   127.0.0.1:3100   Next.js standalone
                 ├─ kairos-api   127.0.0.1:8200   FastAPI
                 └─ kairos-db    127.0.0.1:5434   PostgreSQL 17 + pgvector 0.8
```

| 항목 | 값 |
|---|---|
| FE | https://kairos.woosung.dev |
| API | https://kairos-api.woosung.dev |
| 서버 | `ssh oci-tokyo` (truewords · quantbridge · nexus-core 와 **공유**) |
| 배포 디렉토리 | `~/kairos` (compose · `.env` · initdb) |
| 오브젝트 스토리지 | Cloudflare R2 — 운영 `kairos-prod` · CI·로컬 `kairos-dev` (ADR-033, 버킷 한정 토큰). CI 는 전환 완료(#198). ⏳ 운영·로컬은 이전 진행 중 — `.env` 전환 전까지 옛 공유 버킷 `nexus-core-storage` (`docs/TODO.md` Blocked "Gate 0 잔여") |
| 인증 | Better Auth 자체 호스팅 (web 컨테이너, ADR-031) |
| AI | Gemini · OpenAI (유지) |

**같은 호스트의 다른 프로젝트가 쓰는 포트**(건드리지 말 것): 3200 quantbridge-frontend ·
5432 truewords postgres · 5433 quantbridge-db · 6333 qdrant · 6380 quantbridge-redis ·
8100 quantbridge-api · 3300 · 3301 · 8300 · 5435 nexus-core.
서버 전체 설정(로그 회전 · journald · swap · 디스크 경보 · 빌더 캐시 정리)은 Kairos 가 소유하지 않는다 —
[`deploy/oci/README.md`](../../deploy/oci/README.md) "호스트 공통 설정".

---

## 배포

```
main push → Test 통과 → release.yml (ubuntu-24.04-arm) → GHCR ghcr.io/woosung-dev/kairos-{api,web}:sha-<7>
                                                              ↓ docker pull (서버)
맥: mise run deploy-preflight → mise run deploy-ship sha-<7> → deploy-status
```

```bash
gh run list --workflow release.yml --repo woosung-dev/kairos --limit 3   # 배포할 커밋의 런이 success 인지

mise run deploy-preflight          # 디스크 80% 미만 + 진행 중 회의 0 + .env 인코딩 게이트
mise run deploy-ship sha-<7자리>   # compose 동기화 → 서버 pull → 태그 교체 → up -d → env 확인 → GC
mise run deploy-status             # 컨테이너 상태 + /ready + 서버 자원 (디스크 포함)
```

이미지는 CI 가 만든다 (ADR-028 D7 Phase A, 2026-10-02). 그전에는 맥에서 빌드해 `docker save | ssh | docker load` 로
옮겼다. 그 경로는 GitHub Actions · GHCR 장애 때의 **비상 경로**로만 남는다 — `deploy/oci/README.md` "비상 경로".
배포 실행(트리거)은 아직 수동이다. 자동 배포(Phase B)는 D7 진입 조건을 확인한 뒤 붙인다.

`deploy-ship` 은 마지막에 `deploy-gc` 를 부른다 — 서버에 **운영중 태그 + 직전 태그**만 남기고
나머지 `ghcr.io/woosung-dev/kairos-{api,web}` 이미지를 지운다. 이 서버는 다른 프로젝트와
공유하므로 **`docker system prune` 계열을 쓰지 않는다** (남의 프로젝트 이미지가 지워진다).
GC 가 이미지를 지우지 못하면 `deploy-ship` 은 `⚠ 이미지 정리 실패` 경고를 남기고 성공으로 끝난다 —
배포 자체는 이미 끝난 상태다. 경고가 보이면 `docker rmi` 오류를 읽고 `mise run deploy-gc <직전 태그>` 를 다시 돌린다.

**FE 빌드 인자** `NEXT_PUBLIC_*` 는 repo Variables 에서 읽는다 (맥 비상 경로는 `deploy/oci/build.env`, gitignore).
빌드타임에 번들로 인라인되므로 **도메인이 바뀌면 반드시 재빌드**해야 한다 — 태그가 sha 라 같은 커밋은 다시 빌드하지 않으므로
변수를 고친 뒤 새 커밋을 올린다.

### 배포 전 반드시 확인

`BackgroundTasks` 는 재시도가 없다. 처리 중인 회의가 있는 상태로 컨테이너를 교체하면
그 회의는 `transcribing` 으로 영구 정지한다. `mise run deploy-preflight` 가 이걸 검사한다.

Heavy e2e(실제 Whisper·Gemini + 회의 업로드 + 팀 spine)는 PR CI 에 없다. `nightly-e2e.yml` 은
주 1회만 돌기 때문에, 배포할 커밋에서 한 번 수동으로 돌려 success 를 확인한다:

```bash
gh workflow run nightly-e2e.yml --ref main --repo woosung-dev/kairos
```

이미지는 `main` 의 커밋에서만 만들어지므로(release.yml) dispatch 는 배포할 sha 가 `main` 에 있을 때 의미가 있다.
결과는 기다려서 본다:
`gh run list --workflow nightly-e2e.yml --repo woosung-dev/kairos --limit 1`.

---

## 롤백

`~/kairos/.env` 의 태그 두 줄을 이전 값으로 되돌리고 **api·web 만** 다시 띄운다 (`up -d --no-deps api web`).

```bash
mise run deploy-rollback sha-<이전>   # 서버에 없으면 GHCR 에서 pull
```

**migrate 를 다시 돌리지 않는 이유.** migrate 는 api 와 같은 이미지(`ghcr.io/woosung-dev/kairos-api:${KAIROS_API_TAG}`)를 쓴다.
전체 `up -d` 로 되돌리면 migrate 가 구 이미지로 재생성되는데, 구 이미지의 alembic 은 DB 에 이미 올라간
새 리비전을 몰라 `Can't locate revision` 으로 실패한다. api·web 은 `service_completed_successfully` 를
기다리므로 **기동하지 않는다 — 롤백이 장애를 만든다** (2026-09-27 토이 compose 재현, BL-LR-16).
`--no-deps` 는 migrate 가 exit 0 · exit 1(정방향 배포 실패 직후) · 컨테이너 없음 어느 상태여도 api·web 을 띄운다.
그래서 예전의 긴급 우회(`alembic stamp` 로 리비전을 내렸다가 다음 배포 전에 다시 올리기)는 필요 없다.

★**롤백 상태에서는 `--no-deps` 없는 `up -d` 를 쓰지 않는다 — 서비스를 지정해도(`up -d api`) 마찬가지다.**
`.env` 가 migrate 도 구 태그로 고정하므로 migrate 가 다시 실패하고 명령이 exit 1 로 끝난다.
api 설정이 그대로면 api 는 재생성되지 않고 계속 돌지만, `.env` 의 다른 값을 바꾼 뒤라면 api 가 재생성 대기에 걸려
**멈춘다** (`Created` 상태로 남음 — 2026-09-27 토이 compose 실측). 롤백 중 `.env` 를 고쳤으면 `up -d --no-deps api` 로 띄운다.
다음 정방향 배포는 `deploy-ship` 으로 한다. 새 마이그레이션이 있는 태그로 올릴 때 `deploy-rollback` 을 쓰면
마이그레이션이 빠진다.

RTO 는 약 2분이다. 진행 중인 BackgroundTasks 가 있으면 api 의 `stop_grace_period: 900s` 만큼 최대 15분 걸린다.

롤백 뒤에는 `mise run deploy-status` 로 `/ready` 200 을 확인한다. `--no-deps` 는 db healthy 도 기다리지 않으므로
명령이 exit 0 이어도 복구됐다는 뜻이 아니다.

★**롤백 대상이 보안 수정 이전 태그면 그 결함이 되살아난다.** 구 이미지는 새 컬럼이 있어도 쓰지 않는다
(예: `is_shared` 가 있어도 작성자 전용 메모 필터가 없다). 2026-09-27 기준 서버의 직전 태그 `884a145` 는
Gate 0(#196 — 작성자 전용 메모 · 파생 데이터 visibility) 이전이다. 다음 배포부터 직전 태그가 `2694847` 이 되어 해소된다.
그런 태그로 롤백했다면 그 사이 쓰인 데이터도 확인한다 — 구 이미지는 회의 실패 사유를 원문(`str(e)`)으로 저장하고,
정제 마이그레이션 `b3d5f8a1c2e4` 는 이미 적용된 리비전이라 롤포워드해도 다시 돌지 않는다.

**되돌리는 커밋(`git revert`)으로 롤포워드할 때 alembic 리비전 파일은 지우지 않는다.** DB 에 적용된 리비전을 새 이미지가
모르면 migrate 가 `Can't locate revision` 으로 실패하고, 이번에는 정방향 `up -d` 에서 같은 장애가 난다.

서버에 **운영중 + 직전 1개** 태그를 남긴다 (`deploy-gc` 가 매 배포마다 강제한다 —
직전 태그는 `deploy-ship` 이 `.env` 를 덮어쓰기 전에 읽어 GC 에 넘긴다).
그보다 오래된 태그는 `deploy-rollback` 이 GHCR 에서 받아 온다. Phase A 이전 태그(`sha-` 없는 맥 빌드)는 GHCR 에 없다.

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

**백업** — `deploy/oci/backup/pg-backup.sh` 가 일 1회 `pg_dump -Fc` → 로컬 14일 보관 → R2 `backups/kairos/`
사본을 만든다. 복원 리허설은 `pg-restore-check.sh` (새 임시 컨테이너 + 테이블별 row count 대조).
**서버 crontab 등록 전까지는 실제 백업이 없다** — 절차는 [`runbooks/db-backup-restore.md`](runbooks/db-backup-restore.md).
어느 경우든 **`docker compose down -v` 는 절대 금지** — `-v` 가 `db-data` 볼륨을 지운다.

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
참조하는 것들이다** (2026-09-27 재확인 — `E2E_R2_*` 3건 추가, 미참조 Clerk 3건 삭제). repo-level `R2_*` 는 `kairos-prod`
**읽기 전용** 토큰으로 바꾼다 (`r2-cleanup.yml` 인벤토리 몫, ADR-033 — 교체 전까지는 옛 공유 토큰, `docs/TODO.md` "Gate 0 잔여" R4). 정리 판단은 워크플로 grep 과 대조해서 한다:

```bash
comm -23 <(gh secret list --repo woosung-dev/kairos --json name --jq '.[].name' | sort) \
         <(grep -rhoE "secrets\.[A-Z_0-9]+" .github/workflows/ | sed 's/secrets\.//' | sort -u)
```
