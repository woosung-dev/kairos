# 환경변수 & 시크릿 관리 가이드

> **한 줄 원칙 (2026-08-14 ADR-028 갱신):** 로컬은 파일로 관리(BE: `.env` / FE: `.env.local`),
> **프로덕션 SoT 는 오라클 서버의 `~/kairos/.env` (0600)**, GitHub Secrets 는 **CI 전용**이다.
> 이미지는 레지스트리를 거치지 않고 `docker save | ssh | docker load` 로 전달한다.
> 코드에 값을 하드코딩하거나 env 파일을 커밋하는 것은 절대 금지.

---

## 빠른 시작 (로컬 셋업)

```bash
# 1. 템플릿 복사
cp apps/api/.env.example apps/api/.env        # FastAPI: .env 표준
cp apps/web/.env.example apps/web/.env.local  # Next.js: .env.local 표준

# 2. 각 파일을 열어 실제 값 입력 (아래 발급처 참고)
```

---

## 전체 환경변수 매트릭스

### 범례

| 기호 | 의미 |
|---|---|
| ✅ | 해당 환경에서 필요 |
| ➖ | 불필요 (fake 값으로 대체) |
| 🔒 | 민감 정보 — 직접 노출 금지 |

---

> **프로덕션 컬럼 = 오라클 서버 `~/kairos/.env`** (아래 SoT 절). 2026-08-14 ADR-028 이전의
> "Cloud Run env" / "GitHub Secret" / "Vercel 환경변수" 표기는 2026-08-16 에 정정했다.
> `NEXT_PUBLIC_*` 는 **빌드타임 인라인**이라 서버 `.env` 가 아니라 `deploy/oci/build.env` 에 있고,
> 값을 바꾸면 **FE 이미지를 재빌드해야 한다**.

### 백엔드 (`apps/api/.env`)

| 변수명 | 로컬 | CI (test) | 프로덕션 | 발급처 |
|---|:---:|:---:|:---:|---|
| `APP_ENV` | ✅ `development` | ➖ | 서버 `.env` | 직접 입력 |
| `LOG_LEVEL` | ✅ `INFO` | ➖ | 서버 `.env` | 직접 입력 |
| `CORS_ORIGINS` | ✅ `http://localhost:3000` | ➖ | 서버 `.env` | `https://kairos.woosung.dev` |
| `FRONTEND_URL` | ✅ `http://localhost:3000` | ➖ | 서버 `.env` | `https://kairos.woosung.dev` |
| `DATABASE_URL` 🔒 | ✅ | ➖ fake | 서버 `.env` | 프로덕션은 오라클 VM 의 `kairos-db` 컨테이너 (ADR-028). 로컬/백업은 [Neon](https://console.neon.tech) |
| `AUTH_JWT_ISSUER` | ✅ | ➖ 기본값 | 서버 `.env` | FE 공개 URL. 토큰 `iss`/`aud` 와 대조 (ADR-031) |
| `AUTH_JWKS_URL` | ✅ | ➖ 기본값 | 서버 `.env` | 공개키 fetch 주소. prod 는 compose 내부망 `http://web:3000/api/auth/jwks` |
| `AUTH_JWT_AUDIENCE` | ✅ | ➖ 기본값 | 서버 `.env` | non-dev 에서 명시 필수 (validator 가 None 거부) |
| `AUTH_JWT_ALGORITHMS` | ➖ 기본 `EdDSA` | ➖ | 서버 `.env` | 허용 목록. 헤더의 `alg` 를 신뢰하지 않기 위함 |
| `R2_ACCOUNT_ID` 🔒 | ✅ | ➖ fake | 서버 `.env` | Cloudflare 대시보드 → 우측 상단 Account ID |
| `R2_ACCESS_KEY_ID` 🔒 | ✅ | ➖ fake | 서버 `.env` | Cloudflare R2 → Manage R2 API tokens |
| `R2_SECRET_ACCESS_KEY` 🔒 | ✅ | ➖ fake | 서버 `.env` | 위와 동일 (토큰 생성 시 1회만 표시) |
| `R2_BUCKET_NAME` | ✅ | ➖ fake | 서버 `.env` | Cloudflare R2 버킷 이름 |
| `GEMINI_API_KEY` 🔒 | ✅ | ➖ fake | 서버 `.env` | [Google AI Studio](https://aistudio.google.com) → Get API key |
| `OPENAI_API_KEY` 🔒 | ✅ | ➖ fake | 서버 `.env` | [OpenAI Platform](https://platform.openai.com/api-keys) |

---

### 프론트엔드 (`apps/web/.env.local`)

| 변수명 | 로컬 | CI (build) | 프로덕션 | 발급처 |
|---|:---:|:---:|:---:|---|
| `NEXT_PUBLIC_API_URL` | ✅ `http://localhost:8000` | ➖ fake | `build.env` | `https://kairos-api.woosung.dev` |
| `BETTER_AUTH_SECRET` 🔒 | ✅ | ➖ fake | 서버 `.env` (web 컨테이너 런타임) | `openssl rand -base64 32`. **세션 서명 + `auth_jwks.privateKey` 암호화 겸용 — 유출 = JWT 위조 가능** |
| `BETTER_AUTH_URL` | ✅ | ➖ | 서버 `.env` (web) | 공개 origin. Better Auth 의 기본 issuer/audience 가 이 값이다 |
| `BETTER_AUTH_DATABASE_URL` 🔒 | ✅ | ➖ | 서버 `.env` (web) | **node-postgres 형식**. BE 의 `postgresql+asyncpg://` 와 다르다 |
| `GOOGLE_CLIENT_ID` | ✅ | ➖ | 서버 `.env` (web) | ★Drive 연동의 `GOOGLE_OAUTH_CLIENT_ID` 와 **다른 클라이언트** (아래 주의 참조) |
| `GOOGLE_CLIENT_SECRET` 🔒 | ✅ | ➖ | 서버 `.env` (web) | 위와 같은 클라이언트의 시크릿 |

---

### 프로덕션 — 오라클 서버 `~/kairos/.env` (SoT)

> 템플릿: `deploy/oci/.env.example` · 권한 `chmod 600` 필수
> 배포 자동화가 없으므로 GitHub Secrets 에 프로덕션 값을 둘 이유가 없다.

| 분류 | 키 |
|---|---|
| 배포 단위 | `KAIROS_API_TAG`, `KAIROS_WEB_TAG` (git short SHA — 롤백은 이 둘을 되돌린다) |
| Tunnel | `KAIROS_TUNNEL_TOKEN` 🔒 (Cloudflare Zero Trust → Tunnels) |
| DB (컨테이너) | `POSTGRES_USER`, `POSTGRES_PASSWORD` 🔒, `POSTGRES_DB`, `DATABASE_URL` 🔒 |
| 앱 | `APP_ENV`, `ENVIRONMENT`, `LOG_LEVEL`, `AUTH_PROD_HARDENING`, `FRONTEND_URL`, `CORS_ORIGINS`, `MAX_UPLOAD_BYTES` |
| 인증 (api) | `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE`, `AUTH_JWKS_URL`, `AUTH_JWT_ALGORITHMS` |
| 인증 (web) | `BETTER_AUTH_SECRET` 🔒, `BETTER_AUTH_URL`, `BETTER_AUTH_DATABASE_URL` 🔒, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` 🔒 |
| R2 | `R2_ACCOUNT_ID` 🔒, `R2_ACCESS_KEY_ID` 🔒, `R2_SECRET_ACCESS_KEY` 🔒, `R2_BUCKET_NAME` |
| AI | `GEMINI_API_KEY` 🔒, `OPENAI_API_KEY` 🔒 |
| 운영 | `CRON_SECRET_TOKEN` 🔒 (`openssl rand -hex 32`) |

**FE 빌드 인자**는 별도 파일 `deploy/oci/build.env` (gitignore, 템플릿 `build.env.example`).
전부 `NEXT_PUBLIC_*` 이라 브라우저 번들에 인라인되므로 시크릿이 아니지만,
**도메인이 바뀌면 반드시 고치고 재빌드**해야 한다.

> ⚠️ **인라인 주석 금지.** `KEY=value  # 설명` 에서 주석이 값에 섞이면 헤더 ascii
> 인코딩에서 터져 500 이 나고, `CORS_ORIGINS` 오염은 조용한 CORS 전면 차단이 된다.
> 게이트: `LC_ALL=C grep -n '[^[:print:][:space:]]' ~/kairos/.env` → 출력 0줄

---

### CI 전용 — GitHub Secrets (E2E 테스트)

> E2E 잡은 `E2E_ENABLED = true` Variable이 설정된 경우에만 실행됨

| 이름 | 탭 | 값 |
|---|---|---|
| `E2E_API_URL` | Secrets | `https://kairos-api.woosung.dev` |
| `E2E_USER_EMAIL` | Secrets | 테스트 계정 이메일 |
| `E2E_USER_PASSWORD` | Secrets | 테스트 계정 비밀번호 |
| `E2E_ENABLED` | **Variables** | `true` |

---

## 자주 하는 실수

| 실수 | 결과 | 방지 |
|---|---|---|
| `.env.local`을 git add | 시크릿 유출 | `.gitignore`에 `.env.local` 확인 |
| 프로덕션 키를 로컬에서 사용 | 실수로 프로덕 DB 조작 | 로컬은 항상 dev/test 키 사용 |
| `.env`에 인라인 주석(`KEY=값  # 설명`) | 값에 섞인 한글이 헤더 인코딩을 깨서 500 / CORS 전면 차단 | 설명은 별도 줄 주석으로만. 배포 전 비ASCII 게이트 |
| 도메인 변경 후 FE 재빌드 누락 | `NEXT_PUBLIC_*`은 빌드타임 인라인이라 런타임 env로 안 바뀜 | `build.env` 수정 → `mise run deploy-build` |
| R2 Secret Access Key 재발급 없이 분실 | 재발급 필요 | 발급 직후 즉시 GitHub Secret에 저장 |

---

## ⚠️ Google OAuth 클라이언트는 **두 개**다 (ADR-031)

이름이 비슷해서 반드시 섞인다. 섞으면 로그인이 Drive 의 앱 검증 절차에 딸려 들어간다.

| 용도 | 컨테이너 | env | redirect URI |
|---|---|---|---|
| **로그인** | web | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | `{BETTER_AUTH_URL}/api/auth/callback/google` |
| **Drive 연동** (ADR-026) | api | `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | `/api/v1/integrations/google-drive/callback` |

같은 GCP 프로젝트 안에 클라이언트를 **따로** 만든다. Drive 스코프는 Google 의 restricted scope 라
앱 검증 대상이고, 로그인을 같은 클라이언트에 얹으면 ① 로그인이 그 검증 반경에 들어가고
② 시크릿 로테이션이 로그인과 Drive 를 동시에 끊으며 ③ 로그인 동의 화면이 Drive 권한까지 요구하게 된다.

## ⚠️ `BETTER_AUTH_SECRET` 의 블라스트 반경

이 값 하나가 세 가지를 겸한다 — 세션 쿠키 서명 / `auth_jwks.privateKey` 의 AES256-GCM 복호화 키 /
그로부터 파생되는 JWT 서명 능력. 유출 + DB read 권한이면 **임의 사용자의 JWT 위조 → API 전권 탈취**다.
백엔드는 서명만 믿는 순수 리소스 서버라 다른 방어선이 없다.

- 절대 `NEXT_PUBLIC_*` 로 만들지 않는다 (브라우저 번들에 박힌다).
- 절대 `deploy/oci/build.env` 에 넣지 않는다 — `mise run deploy-build` 가 `--build-arg` 로 넘겨 **이미지 레이어 히스토리에 평문으로 남는다**.
- 오직 서버 `~/kairos/.env` (0600) 의 런타임 env.
- 로테이션 절차: 새 시크릿 설정 → `DELETE FROM auth_jwks` (기존 키가 복호화 불가가 되므로 필수) → `web` 재기동 → `curl /api/auth/jwks` 1회 → 전 세션 무효 + 미만료 JWT 는 최대 15분 유효. 급박한 침해면 `api` 도 재기동해 claims 캐시(60초)를 비운다.
