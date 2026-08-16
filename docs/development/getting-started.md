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
| `apps/api/.env` | `CLERK_SECRET_KEY` | Clerk 대시보드 → API Keys |
| `apps/api/.env` | `GEMINI_API_KEY` · `OPENAI_API_KEY` | AI 파이프라인·임베딩 |
| `apps/api/.env` | `R2_*` 4종 | Cloudflare R2 (업로드) |
| `apps/api/.env` | `CORS_ORIGINS` | 기본 `http://localhost:3000`. Playwright 는 `:3003` 도 필요 |
| `apps/web/.env.local` | `NEXT_PUBLIC_API_URL` | **`http://localhost:8000`** — 경로(`/api/v1`)를 붙이지 않는다 |
| `apps/web/.env.local` | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` · `CLERK_SECRET_KEY` | 같은 Clerk 앱 |

> `core/config.py` 는 `.env.example` 에 없는 변수를 참조하지 않는다. 반대로
> **`.env.example` 에 있는 키는 빠지면 부팅 단계에서 `ValidationError` 로 죽는다** (Pydantic settings).

### Clerk 키 발급

1. [Clerk 대시보드](https://dashboard.clerk.com/) → "Create application" → Google OAuth 활성화
2. "API Keys" 탭에서 `pk_test_...` / `sk_test_...` 복사
3. Clerk 대시보드 "Allowed origins" 에 `http://localhost:3000` 추가

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

### Clerk 로그인 실패
`apps/web/.env.local` 의 키 2개 확인 + Clerk 대시보드 "Allowed origins" 에 `http://localhost:3000`.

### 타입 에러
`node_modules/next/dist/docs/` 로 Next.js 16 API 변경사항 확인. `params` 는 반드시 `Promise<>` 타입.
