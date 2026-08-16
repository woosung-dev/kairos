# Better Auth 전환 — 다음 세션 인계

> 그대로 복사해 새 세션에 붙여넣으면 된다.
> 상세 결정은 `docs/adr/031-better-auth-migration.md` 가 정본이다.

---

## 붙여넣을 프롬프트

```
Kairos 의 Clerk → Better Auth 전환을 이어서 진행한다.
정본은 docs/adr/031-better-auth-migration.md, 인계 문서는
docs/plans/active/2026-08-17-better-auth-cutover-handoff.md 다. 둘 다 먼저 읽어라.

코드 전환은 끝났고, 2026-08-17 에 배포 사전 준비(§1)까지 전부 완료했다 —
GCP 프로젝트 Kairos + OAuth 클라이언트 발급, 서버 ~/kairos/.env 10줄 반영,
로컬 build.env 갱신. 남은 것은 (2) PR #177 머지 (3) D-1/D-0 2단계 배포
(4) 컷오버 +7일 정리 다.

먼저 PR #177 상태와 main 이 움직였는지 확인하고, 서버 ~/kairos/.env 의
게이트(키 10개 / 인코딩 0줄)가 아직 유효한지 검증한 다음 진행 방향을 제안해줘.
```

---

## 지난 세션에 한 것 (PR #177, 8커밋 / 158파일)

**결정** — ADR-031 D1~D11. 핵심만:

- Better Auth 를 Next.js `/api/auth/[...all]` 에 마운트, `jwt` 플러그인 JWKS 로 FastAPI 가 검증 (Bearer 유지)
- 기각: BFF 전량 프록시(RAG SSE 프록시 재작성 필요) · 세션 쿠키 직접 조회(공식 계약 없음 + `.woosung.dev` 광역 쿠키가 형제 서비스로 샘)
- 서명 = EdDSA/Ed25519 기본값, exp 15분
- **컬럼은 rename 이 아니라 가산** — `auth_user_id` 추가, `clerk_id` 는 nullable 로 완화만. 롤백이 이미지 태그만으로 끝나고, 창업자 레거시 행 식별이 가능해진다
- `AUTH_PROD_HARDENING` 기본 True 로 **재무장** (migrate one-shot 이 config 게이트라 crash-loop 경로가 구조적으로 막힘)
- JWKS URL 을 issuer 에서 분리 → prod 는 내부망 `http://web:3000/api/auth/jwks`
- members 응답에서 외부 인증 ID 제거, FE 권한 판정은 내부 UUID 축으로

**검증 (전부 실측)**

- CI 전부 green: `changes · backend-test · contract-check · frontend-build · e2e · CI Required`
- e2e **32 passed, 11 skipped** — 로그인 폼 → 세션 → JWT → 백엔드 관통이 CI 에서 실제로 돈다
- 로컬: BE 919 passed / FE 164 passed / 계약 drift 0
- alembic 25 리비전을 일회용 pgvector 컨테이너에 실제 적용 + downgrade/재upgrade 멱등 확인
- 프로덕션 standalone 이미지를 띄워 compose 내부망 DB 에 붙여 `/api/auth/jwks` 200 + Ed25519 키 확인
- 창업자 재연결 SQL 을 실제로 실행해 검증 (아래 함정 참조)

**덤으로 고친 것** — `seed_qa_fixtures.py` 의 `owner_clerk_id`(존재한 적 없는 컬럼) · `find_by_email` dead code(비-UNIQUE email + `.one_or_none()`) · 랜딩 카피의 철거된 스택 4종

---

## 남은 것

### 1. 배포 사전 준비 — ✅ 2026-08-17 완료

- [x] **Google OAuth 클라이언트 신규 발급** — GCP 프로젝트 `Kairos` 신규 생성 후 클라이언트 `Kairos Login`.
  - ★Drive 연동(ADR-026)의 `GOOGLE_OAUTH_CLIENT_ID` 와 **반드시 다른 클라이언트**. 같이 쓰면 로그인이 Drive 의 restricted scope 앱 검증에 딸려 들어가고 시크릿 로테이션이 둘을 동시에 끊는다.
  - ★**실측 정정**: Drive 클라이언트는 **어느 프로젝트에도 존재하지 않았다.** Clerk dev 인스턴스가 Clerk 소유의 공용 Google 클라이언트를 쓰고 있었기 때문이다. 따라서 ADR-031 D1 의 "같은 GCP 프로젝트 안에" 는 기존 프로젝트가 아니라 **새 `Kairos` 프로젝트가 그 기준점이 된다** — 나중에 Drive 를 붙일 때 이 프로젝트 안에 별도 클라이언트로 만든다.
  - redirect URI: `https://kairos.woosung.dev/api/auth/callback/google`, `http://localhost:3000/api/auth/callback/google`
  - 동의 화면은 **`테스트 중`** 유지 (스코프가 `openid`/`email`/`profile` 뿐이라 게시해도 검증은 안 붙지만, 컷오버 창의 변수를 줄인다). 테스트 사용자 2계정 등록 완료. **Google 로그인은 등록된 계정만 가능하고, 미등록자는 이메일/비밀번호로 가입한다.**
- [x] **`BETTER_AUTH_SECRET` 생성** — `openssl rand -base64 32`. 서버 `~/kairos/.env` 에만. **`deploy/oci/build.env` 금지** (`--build-arg` 로 이미지 레이어에 평문으로 박힌다)
- [x] 서버 `~/kairos/.env` 갱신 — `AUTH_*` 5개 + `BETTER_AUTH_*` 3개 + `GOOGLE_CLIENT_*` 2개 **추가** (템플릿: `deploy/oci/.env.example`). 게이트 4종 통과: 키 10개 / `GOOGLE_CLIENT_SECRET` 비어있지 않음 / DSN 형태 정상 / `LC_ALL=C` 인코딩 0줄
- [x] 로컬 `deploy/oci/build.env` 갱신 — `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` 줄 삭제, `NEXT_PUBLIC_FOUNDER_CLERK_ID` → `NEXT_PUBLIC_FOUNDER_USER_ID=f0ae95bc-23aa-4681-ba40-e0084255138f`
  - ★**값은 컷오버 전에 확정된다.** D2 의 재연결 SQL 이 레거시 `users` 행을 `UPDATE` 하지 `INSERT` 하지 않으므로 창업자의 `users.id` 는 컷오버로 바뀌지 않는다. 따라서 D-1 에 빌드한 이미지를 컷오버 창 안에서 재빌드할 이유가 없다.

> #### ⚠️ `CLERK_*` 는 지금 지우지 않는다 (2026-08-17 정정)
>
> 이 절의 이전 판은 "`CLERK_*` 5줄 삭제" 를 사전 준비에 넣었는데, **그러면 1층 롤백이 죽는다.**
> 삭제는 §4(컷오버 +7일)가 맞고 두 절이 서로 모순이었다.
>
> - 서버 실측: `KAIROS_API_TAG=KAIROS_WEB_TAG=d761615` — 롤백 목적지가 이 태그다
> - `git show origin/main:apps/api/src/core/config.py:49-50` — 구 이미지의 `Settings` 가
>   `clerk_secret_key` / `clerk_webhook_secret` 을 **기본값 없이** 요구한다
> - 지우면 구 이미지의 `get_settings()` 가 터지고 → `migrate` one-shot 이 죽고 →
>   `just deploy-rollback d761615` 이 실패한다. ADR-031 D7 의 "롤백이 이미지 태그만으로 완결" 이 무너진다
>
> 신규 이미지는 `config.py` 의 `extra="ignore"` 로 `CLERK_*` 를 무시하므로 남아 있어도 무해하다.

### 2. PR #177 머지

머지해도 자동 배포는 없다 (`deploy.yml` 은 ADR-028 로 제거됨). 배포는 전부 수동 `just` 레시피다.

### 3. 2단계 배포

> 런북 정본은 이 절이다. ADR-031 에는 배포 절이 없다 (결정만 담는다).

**D-1 · dormant 준비** — 사용자 영향 0, Clerk 로그인 그대로 유지. 목적은 컷오버 당일에 처음 시도하는 것을 없애는 것 (ADR-028 이 스스로 남긴 교훈: 인증 실패와 인프라 실패를 같은 창에서 구분할 수 없다).

> #### ⚠️ `just deploy-ship` 을 D-1 에 쓰면 안 된다 (2026-08-17 정정)
>
> 이 절의 이전 판은 `deploy-ship <TAG-A>` 를 D-1 명령으로 적었는데, 그 레시피는
> **이미지 전송 + `.env` 태그 교체 + `up -d` 를 한 덩어리로** 수행한다(`justfile:137-142`).
> 실행하는 순간 web/api 가 교체돼 Better Auth 가 서비스에 뜨고 Clerk 로그인이 끝난다 —
> "Clerk 는 살아 있고 사용자 영향 0" 이 성립하지 않는다. TAG-A 와 TAG-B 를 나눈 것도
> 같은 코드에서 나온 두 태그라 의미가 없었다.
>
> 아래는 **태그를 교체하지 않고** 오래 걸리는 두 가지(이미지 적재 · 스키마 적용)만 미리
> 끝내는 형태다. 스키마 리비전이 100% 가산/완화형이라 **구 api 이미지가 새 스키마 위에서
> 그대로 동작**하기 때문에 성립한다 (ADR-031 D7).

> #### ⚠️ `pg_dump` 는 D-0 이 아니라 여기(D-1 ⓪)다
>
> 스키마가 실제로 바뀌는 시점이 D-1 ④ 로 앞당겨졌으므로 백업도 같이 앞당긴다.
> D-0 체크리스트에 남겨두면 **스키마 변경 뒤에 백업하는 순서**가 되어 2층 롤백이 무의미해진다.
> 검증까지가 백업이다 — 파일 크기만 보고 넘어가면 손상된 덤프를 안전망으로 착각한다.

```bash
TAG=$(git rev-parse --short HEAD)

# ⓪ 프로덕션 DB 백업 + 무결성 검증 (스키마 변경 전 유일한 안전망)
ssh truewords-oracle 'docker exec -i kairos-db pg_dump -U kairos -d kairos -Fc' > ~/kairos-backup-$(date +%Y%m%d).dump
cat ~/kairos-backup-$(date +%Y%m%d).dump | ssh truewords-oracle 'docker exec -i kairos-db pg_restore --list' | grep -cE '^[0-9]+;'
#   → 0 이면 덤프 손상. 로컬에 pg_restore 가 없어도 서버 컨테이너 것을 빌려 쓰면 검증된다

# ① 사전 게이트 + arm64 네이티브 빌드 (맥)
just deploy-preflight
just deploy-build $TAG

# ② 이미지만 전송 — .env 태그는 건드리지 않는다
docker save kairos-api:$TAG | gzip -1 | ssh truewords-oracle 'gunzip | docker load'
docker save kairos-web:$TAG | gzip -1 | ssh truewords-oracle 'gunzip | docker load'

# ③ migrate one-shot 만 선행 (auth_* 5테이블 + users.auth_user_id 추가, 전부 가산형)
ssh truewords-oracle "bash -lc 'cd ~/kairos && KAIROS_API_TAG=$TAG docker compose -f docker-compose.prod.yml run --rm migrate'"

# ④ 임시 web 컨테이너로 스모크 — 운영 web(3100)은 그대로 두고 3101 에 띄운다
ssh truewords-oracle "bash -lc 'cd ~/kairos && docker run -d --rm --name web-smoke --network kairos_default --env-file .env -p 127.0.0.1:3101:3000 kairos-web:$TAG'"
```

D-1 스모크 4항목 (전부 `ssh truewords-oracle` 안에서):

| # | 명령 | 통과 기준 |
|---|---|---|
| 1 | `curl -s 127.0.0.1:3101/api/auth/jwks` | `"kty":"OKP"`, `"crv":"Ed25519"` |
| 2 | `docker exec kairos-api python -c "import urllib.request;print(urllib.request.urlopen('http://web-smoke:3000/api/auth/jwks').status)"` | `200` (내부망 도달) |
| 3 | `docker stats --no-stream web-smoke` | mem 실측 → `mem_limit: 768m` 적정성 판단 |
| 4 | `docker logs web-smoke` | DB 연결 오류 0건 |

끝나면 `docker stop web-smoke`.

★**부수 효과**: 1번이 `auth_jwks` 에 Ed25519 키를 실제로 생성한다 (Better Auth 는 lazy 생성).
`BETTER_AUTH_SECRET` 이 같으므로 그 키가 D-0 에도 그대로 쓰인다 — 즉 D-0 의 "lazy 생성 트리거"
단계가 사실상 선해결된다. 확인용으로 D-0 체크리스트에는 남긴다.

★**D-1 에서 못 하는 것 2가지** (D-0 으로 이월):
- **Google 로그인 완주** — redirect URI 가 `kairos.woosung.dev` 라 공개 도메인이 붙어야 한다
- **`web` DNS 이름 검증** — 임시 컨테이너 이름이 `web-smoke` 라 `AUTH_JWKS_URL=http://web:3000/...`
  의 호스트명 자체는 D-0 에서 처음 쓰인다 (네트워크 도달성은 2번이 증명)

#### ✅ D-1 실행 결과 (2026-08-17, TAG `9e7dcf8`)

| 단계 | 결과 |
|---|---|
| ⓪ 백업 | `~/kairos-backup-20260817.dump` 1.2MB · `pg_restore --list` 261 오브젝트 |
| ① preflight | 진행 중 회의 `0` · 인코딩 게이트 0줄 |
| ② 빌드 | `kairos-api:9e7dcf8` 963MB / `kairos-web:9e7dcf8` 236MB (맥 기준) |
| ② 번들 검증 | founder UUID 2파일 · API URL 2파일 · better-auth 32파일 · **`.next/static` 의 clerk 0파일** |
| ③ 전송 | 서버 적재 완료. `.env` 태그는 `d761615` 유지 |
| ④ migrate | `7f6b8c9d0e1f -> c1a7e0b5d3f2`. `auth_*` 5테이블 · `users.auth_user_id` · `clerk_id` nullable=YES · `users` 16행 / `meetings` 98행 무손상 |
| ⑤ 스모크 1 | `{"alg":"EdDSA","crv":"Ed25519","kty":"OKP","kid":...}` |
| ⑤ 스모크 2 | api → `web-smoke:3000` **200** |
| ⑤ 스모크 3 | mem **56.5MiB** / 11.65GiB (idle). `mem_limit: 768m` 은 충분 — 단 scrypt 부하 시 측정이 아니다 |
| ⑤ 스모크 4 | 로그 에러 0건 |
| 정리 | `web-smoke` 제거. `auth_jwks` 1행 잔존 (D-0 에 그대로 쓰인다) |

★**ADR-031 D7 이 실측으로 증명됐다.** 스키마 변경 후에도 구 이미지 컨테이너가
**재생성 없이**(`api`/`web` 둘 다 `Up 4 hours (healthy)`) `ready=200` / `web=200` 을 유지했다.
"롤백은 이미지 태그만으로 완결" 이 추정이 아니라 관측이다.

★서버에 `kairos-api:d761615` / `kairos-web:d761615` 이미지가 실재함을 확인했다 —
`just deploy-rollback d761615` 가 이미지 pull 없이 즉시 성립한다.

**D-0 · 컷오버** — ⏱ **다운타임 2~4분 + 전원 재가입.**

D-1 을 마쳤다면 이미지와 스키마는 이미 서버에 있다. 남은 것은 **태그 2줄 교체**뿐이라
다운타임이 이미지 전송 시간과 무관해진다.

1. ☐ **백업은 D-1 ⓪ 에서 이미 받았다** — D-1 이후 새 회의가 들어왔다면 다시 받는다 (DB 백업 자동화 BL-OCI-1 미완)
2. ☐ `just deploy-preflight` (진행 중 회의 0 — BackgroundTasks 는 재시도가 없다)
3. ☐ `docker compose -f docker-compose.prod.yml stop web api` → 다운타임 시작
4. ☐ **`.env` 태그 2줄 교체 + `up -d`** — 이미지는 D-1 에 적재됐으므로 재전송하지 않는다:
   ```bash
   ssh truewords-oracle "bash -lc 'cd ~/kairos && \
     sed -i \"s/^KAIROS_API_TAG=.*/KAIROS_API_TAG=$TAG/; s/^KAIROS_WEB_TAG=.*/KAIROS_WEB_TAG=$TAG/\" .env && \
     docker compose -f docker-compose.prod.yml up -d\""
   ```
   `just deploy-ship $TAG` 를 써도 결과는 같지만 이미지를 다시 전송하느라 다운타임이 길어진다
5. ☐ **`curl https://kairos.woosung.dev/api/auth/jwks` 1회** — 2026-08-17 D-1 ⑤에서 키가 이미 생성됐다(`auth_jwks` 1행, `BETTER_AUTH_SECRET` 동일하므로 그대로 유효). 따라서 여기서는 lazy 생성 트리거가 아니라 **`web` DNS 이름 + Cloudflare 공개 경로 확인**이 목적이다
6. ☐ **Google 로그인 1회 완주** → `SELECT * FROM auth_account WHERE "providerId"='google'` 1행 (D-1 에서 못 한 항목)
7. ☐ 창업자 재가입 → **재연결 SQL** (아래 함정)
8. ☐ `just deploy-status` + `/dashboard` 로그인 관통 → 다운타임 종료
9. ☐ **Clerk dev 인스턴스는 삭제하지 않는다** — 롤백 창 7일 유지

#### ✅ D-0 실행 결과 (2026-08-17, 다운타임 약 5분 17:35~17:40)

| 항목 | 결과 |
|---|---|
| 태그 교체 | `d761615` → `9e7dcf8` (api·web) |
| 공개 경로 | `web=200` · `api_ready=200` · JWKS `kid=SW0G97Og...` (D-1 키 그대로) |
| Google 로그인 | 완주. `auth_account(providerId='google')` 1행 · `auth_session` 1행 |
| 재연결 SQL | `DELETE 1 / DELETE 1 / DELETE 1 / UPDATE 1 / COMMIT` |
| 창업자 행 | `users.id` `f0ae95bc-...` **유지** · `email` 채워짐 · 워크스페이스 6 / 회의 58 복귀 |
| 데이터 | `total_users=16` · `total_meetings=98` 무손상 |
| 메모리 | web 66.96MiB / 768MiB · api 135.1MiB / 1.5GiB → `mem_limit` 상향 적정 |

> #### 🔥 컷오버 중 실제로 터진 것 — `deploy-ship` 이 compose 파일을 동기화하지 않는다
>
> 태그 교체 직후 **web 이 전면 500** 이었다. 로그: `BetterAuthError: You are using the default secret`.
>
> **원인**: 서버의 `docker-compose.prod.yml` 이 최초 부트스트랩(2026-08-14) 버전이었다.
> 배포 레시피는 이미지와 `.env` 태그만 옮기고 compose 파일은 옮긴 적이 없다. ADR-031 이
> `web` 서비스에 새로 넣은 `environment:` 5줄이 서버에 도달하지 못해 `BETTER_AUTH_SECRET` 이
> **빈 문자열로 주입**됐다. `environment:` 치환은 변수가 없어도 에러 없이 통과한다 —
> `env_file` 과 달리 조용히 실패하는 경로다.
>
> **복구**: `scp` 로 compose 파일 교체 → `up -d`. 약 3분.
>
> **재발 방지**: `just deploy-sync-config`(신규, `deploy-ship` 의 선행 의존) +
> `just deploy-verify-env`(신규, `up -d` 직후 자동 실행). 둘 다 프로덕션에서 실동작 검증했다.
>
> **진단이 오래 걸린 이유 — `docker compose config` 를 오독했다.** `config` 는 `env_file` 을
> `environment` 로 확장해 출력하므로 `api`/`migrate` 의 값이 마치 `web` 것처럼 보였다.
> 다음엔 **`docker inspect kairos-web --format '{{len .Config.Env}}'` 로 주입 개수를 먼저 봐라** —
> 정상 12개 vs 사고 당시 8개로 1분이면 갈렸다.
>
> **D-1 스모크가 못 잡은 이유**: 임시 컨테이너를 `docker run --env-file .env` 로 띄워
> **compose 경로를 통째로 우회**했다. 스모크는 실제 배포 경로와 같은 경로여야 한다.

> #### ⚠️ 재연결 SQL 함정 2가지 (지난 세션에 실제로 깨뜨려 확인함)
>
> **① 순서가 계약이다.** UPDATE 를 먼저 하면 `ix_users_auth_user_id` UNIQUE 위반으로 통째로 실패한다.
> ```sql
> BEGIN;
>   DELETE FROM workspace_members WHERE user_id = :new_row_id;
>   DELETE FROM workspaces        WHERE owner_id = :new_row_id AND type = 'personal';
>   DELETE FROM users             WHERE id = :new_row_id;
>   UPDATE users SET auth_user_id = :new_auth_id, email = :new_email
>    WHERE clerk_id = :founder_clerk_id;
> COMMIT;
> ```
> **② 실행 직후 `api` 재기동.** `_USER_CACHE`(60초)가 삭제된 행을 들고 있어 그동안 창업자에게 워크스페이스가 비어 보인다 — 마이그레이션 실패로 오인하기 딱 좋다.

**롤백**

- **1층 (기본)**: `just deploy-rollback d761615` 만으로 완결. 스키마 가산 전용, RTO 약 2분, 데이터 손실 0.
  - ★**`d761615` 는 추정이 아니라 서버 실측값이다** — 2026-08-17 기준 `~/kairos/.env` 의
    `KAIROS_API_TAG` / `KAIROS_WEB_TAG` 가 둘 다 이 값이고, 이는 `origin/main` HEAD
    (`fix(security): bump next 16.2.6 -> 16.2.11`, PR #175) 와 일치한다
  - ★전제: `.env` 에 `CLERK_*` 가 살아 있어야 한다 (§1 의 정정 박스 참조). 구 이미지가
    `clerk_secret_key` / `clerk_webhook_secret` 을 필수로 요구한다
- **2층**: `pg_dump` 복원. ⚠️ `alembic downgrade` 는 운영에서 실행 금지.

### 4. 컷오버 +7일 (롤백 창 종료)

- [ ] alembic 신규 리비전 — `DROP INDEX ix_users_clerk_id` + `DROP COLUMN users.clerk_id`
- [ ] `apps/api/src/auth/models.py` 에서 `clerk_id` 필드 삭제 + `auth/CONTEXT.md` §3 레거시 주석 정리
- [ ] 서버 `~/kairos/.env` 의 `CLERK_*` 잔여 삭제 ← **여기가 유일한 삭제 시점이다.** 이걸 하는 순간 `just deploy-rollback d761615` 가 불가능해지므로, 위의 `clerk_id` DROP 리비전과 **같은 작업 창에서** 실행한다 (둘 다 롤백 창을 닫는 행위라 시점이 갈리면 안 된다)
- [ ] **Clerk dev 인스턴스 삭제** ← **ADR-031 종료 조건.** 레포가 public 이고 히스토리 675 커밋에 dev secret 이 있다. 키가 무의미해지는 것과 실제로 무효화되는 것은 다르다
- [ ] `docs/TODO.md` 의 T-SEC-CLERK-ROTATE / T-CLEANUP-1 종결, ADR-031 Status 갱신

### 5. 후속 백로그 (별건 · 컷오버와 같은 창에서 하지 말 것)

| 항목 | 메모 |
|---|---|
| **비밀번호 재설정 경로 부재** | 레포에 이메일 발송 인프라 0건. 현재는 사인인 화면에 "Google 로그인 또는 운영자 문의" 안내만. 외부 사용자 확대 전 필수 |
| team e2e 실행 | `E2E_RUN_TEAM=true` — 이번 run 의 11 skipped 에 포함 |
| FE 스크린샷 증거 | `console.error` 0건은 e2e 가 집계해 통과, 스크린샷은 별도 |
| 계약이 raw dict 표면을 못 덮음 | `/users/me`·members 가 `response_model` 없이 dict 반환 → wire 키 변경이 OpenAPI 에 안 잡힌다. BL 등재 |
| CSP `strict-dynamic` (BL-S27e-3) | Clerk·Sentry 도메인이 사라져 진입 장벽이 크게 낮아졌다 |
| `users.email` UNIQUE | 컷오버 후 레거시+재가입 행이 같은 이메일을 가질 수 있다 |
| `auth_user` 삭제가 `users` 로 전파 안 됨 | FK 없음(설계상 소유자 분리). 탈퇴 기능 생기면 2단계 삭제 필요 |
| main dependabot 취약점 104건 | 이번 작업과 무관, 별건 |
