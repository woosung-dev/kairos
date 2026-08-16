# 로컬 개발 환경 셋업

> 환경변수 **전체 매트릭스**(로컬/CI/프로덕션, 발급처 포함)는 [`secrets.md`](secrets.md) 가 정본이다.
> 본 문서는 "처음 클론해서 화면이 뜰 때까지" 만 다룬다.

## 사전 요구사항

| 도구 | 최소 버전 | 확인 명령어 |
|------|----------|------------|
| Node.js | 20+ | `node -v` |
| pnpm | 9+ | `pnpm -v` |
| uv | latest | `uv --version` |
| just | latest | `just --version` (`brew install just`, ADR-027) |
| Git | 2.30+ | `git --version` |

## 1. 클론 + 의존성 설치

```bash
git clone <repository-url> kairos
cd kairos
just install   # = apps/api uv sync --frozen + apps/web pnpm install --frozen-lockfile
```

## 2. 환경 변수 — **앱마다 파일이 다르다**

루트에는 `.env.example` 이 없다. 앱별로 복사한다.

```bash
cp apps/api/.env.example apps/api/.env        # FastAPI 는 .env 가 표준
cp apps/web/.env.example apps/web/.env.local  # Next.js 는 .env.local 이 표준
```

최소로 채워야 부팅되는 값:

| 파일 | 키 | 비고 |
|---|---|---|
| `apps/api/.env` | `DATABASE_URL` | PostgreSQL 17 + pgvector 0.8 (HNSW/halfvec 필요, ADR-020) |
| `apps/api/.env` | `AUTH_JWT_ISSUER` · `AUTH_JWKS_URL` | 로컬은 기본값(`http://localhost:3000`)으로 충분 |
| `apps/api/.env` | `GEMINI_API_KEY` · `OPENAI_API_KEY` | AI 파이프라인·임베딩 |
| `apps/api/.env` | `R2_*` 4종 | Cloudflare R2 (업로드) |
| `apps/api/.env` | `CORS_ORIGINS` | 기본 `http://localhost:3000`. Playwright 는 `:3003` 도 필요 |
| `apps/web/.env.local` | `NEXT_PUBLIC_API_URL` | **`http://localhost:8000`** — 경로(`/api/v1`)를 붙이지 않는다 |
| `apps/web/.env.local` | `BETTER_AUTH_SECRET` · `BETTER_AUTH_DATABASE_URL` · `GOOGLE_CLIENT_*` | 아래 "Google OAuth 클라이언트 발급" 참조 |

> **없으면 부팅이 죽는 키는 9개뿐이다** — `Settings`(`src/core/config.py`)에서 기본값이 없는 필드다:
> `DATABASE_URL` · `R2_ACCOUNT_ID` ·
> `R2_ACCESS_KEY_ID` · `R2_SECRET_ACCESS_KEY` · `R2_BUCKET_NAME` · `GEMINI_API_KEY` · `OPENAI_API_KEY`.
> 나머지(`APP_ENV` `LOG_LEVEL` `CORS_ORIGINS` `FRONTEND_URL` `GOOGLE_OAUTH_*` 등)는 기본값이 있어
> 비워도 부팅한다 — Google Drive 키는 `.env.example` 자신이 "비워두면 기존 부팅에 영향 없음" 이라고 적어 뒀다.
>
> 반대 방향도 성립하지 않는다. `Settings` 에는 있는데 `.env.example` 에 없는 필드가 8개다
> (`db_pool_size` `db_max_overflow` `max_upload_bytes` `allowed_upload_mimes` `auth_jwt_issuer`
> `auth_jwks_url` `auth_jwt_audience` `auth_jwt_algorithms` `auth_prod_hardening` `slack_feedback_webhook_url`) — 전부 기본값이 있어
> 평소엔 안 보이지만, 튜닝하려면 `config.py` 를 봐야 한다. **`.env.example` 은 필수 키 목록이지 전체 목록이 아니다.**

### Google OAuth 클라이언트 발급 (ADR-031)

1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → "OAuth 클라이언트 ID 만들기" (웹 애플리케이션)
   ★Drive 연동(ADR-026)의 클라이언트와 **다른 것을 새로 만든다** — 이유는 `docs/development/secrets.md` 참조
2. "API Keys" 탭에서 `pk_test_...` / `sk_test_...` 복사
3. 승인된 리디렉션 URI 에 `http://localhost:3000/api/auth/callback/google` 추가
4. `BETTER_AUTH_SECRET` 생성: `openssl rand -base64 32`

## 3. DB 마이그레이션 + 서버 실행

터미널 2개가 필요하다.

```bash
just be-migrate     # alembic upgrade head — 최초 1회 + 모델 변경 시마다
just be-dev         # FastAPI :8000
```

```bash
just fe-dev         # Next.js :3000
```

브라우저에서 `http://localhost:3000`.

> **Mock 모드는 존재하지 않는다.** `NEXT_PUBLIC_API_MOCK` 변수도 `src/mocks/` 디렉터리도
> 코드에 없다 — FE 는 항상 실제 BE 를 호출한다(`src/lib/api-client.ts`).
> BE 없이 FE 만 띄우면 데이터 화면이 전부 실패한다.

## 4. 자주 쓰는 명령

전체 목록은 `just --list`. 루트 `justfile` 이 단일 진입점이다 (ADR-027 D3).

```bash
just ci-local         # 머지 전 게이트 전체 — 아래 testing.md 참조
just be-test          # pytest (CI 와 문자 동일 호출)
just fe-build         # Next 빌드 (타입 검사 포함)
just contracts        # OpenAPI 계약 + FE 타입 재생성
just e2e              # Playwright
```

테스트 게이트 상세는 [`testing.md`](testing.md), 마이그레이션은 [`migrations.md`](migrations.md).

## 5. shadcn/ui 컴포넌트 추가

```bash
pnpm --dir apps/web dlx shadcn@latest add [component-name]
```

> `components/ui/` 내 파일은 직접 수정하지 않는다 (F-1). 커스텀은 래핑 컴포넌트로.

## 6. 트러블슈팅

### `pnpm install` 실패
```bash
rm -rf apps/web/node_modules && pnpm --dir apps/web install
```

### `uv run` 이 `No such file or directory` 로 죽을 때
venv 가 절대 경로를 굽기 때문에 디렉터리를 옮기면 깨진다(ADR-030 rename 때 실제 발생).
```bash
rm -rf apps/api/.venv && (cd apps/api && uv sync)
```

### 로그인 실패
`apps/web/.env.local` 의 `BETTER_AUTH_SECRET`(32자 이상) · `BETTER_AUTH_DATABASE_URL` 확인.
Google 로그인이면 리디렉션 URI 등록 여부도 본다.
백엔드가 401 이면 `curl localhost:3000/api/auth/jwks` 가 키를 돌려주는지, `AUTH_JWT_ISSUER` 가
`BETTER_AUTH_URL` 과 문자 그대로 같은지 확인 (issuer 불일치는 전 요청 401 로 나타난다).

### 타입 에러
`node_modules/next/dist/docs/` 로 Next.js 16 API 변경사항 확인. `params` 는 반드시 `Promise<>` 타입.
