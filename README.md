# Kairos — 팀의 세컨드 브레인

> *καιρός — 흘러가는 시간(Chronos) 속 결정적 순간.*
> 회의, 노트, 자료를 넣으면 AI가 정리하고, 질문하면 인사이트가 나온다.

**프로덕션:** [kairos.woosung.dev](https://kairos.woosung.dev) · BE: `https://kairos-api.woosung.dev` (오라클 셀프호스팅, ADR-028)

**현재 상태 (2026-08-16):** 오라클 셀프호스팅 컷오버 완료 (ADR-028) · AI 규칙을 `apps/*/AGENTS.md` 로 이전 (ADR-029) · `apps/backend` → `apps/api` 개명 + docs 재구성 (ADR-030).
진행 상세는 `git log` + [`docs/REFACTORING-BACKLOG.md`](docs/REFACTORING-BACKLOG.md) "다음 Sprint 진입점".

> 머지 판정은 CI(`ci-required`)가 한다. `mise run ci-local` 은 **푸쉬 전 사전 확인**용으로 같은 게이트를 로컬에서 돌린다 ([`docs/development/testing.md`](docs/development/testing.md)).

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Next.js 16 + React 19 + Tailwind v4 + shadcn/ui |
| Backend | FastAPI + SQLModel + asyncpg |
| Database | PostgreSQL 17 + pgvector 0.8 (오라클 셀프호스팅) |
| Auth | Better Auth (자체 호스팅, ADR-031) |
| Storage | Cloudflare R2 |
| AI | Gemini `gemini-3.1-flash-lite` + Whisper STT |
| Deploy | Oracle Cloud A1 단일 VM + Cloudflare Tunnel (ADR-028) |

---

## 로컬 개발 환경 셋업

### 1. 환경변수 설정

```bash
cp apps/api/.env.example apps/api/.env        # FastAPI: .env 표준
cp apps/web/.env.example apps/web/.env.local  # Next.js: .env.local 표준
```

각 파일을 열어 실제 값을 입력합니다.
**발급처 및 CI/프로덕션 설정 방법** → [`docs/development/secrets.md`](docs/development/secrets.md)

### 2. 백엔드 실행

```bash
cd apps/api
uv sync
uv run alembic upgrade head   # DB 마이그레이션
uv run uvicorn src.main:app --reload --port 8000
```

### 3. 프론트엔드 실행

```bash
cd apps/web
pnpm install
pnpm dev -p 3000
```

브라우저에서 `http://localhost:3000` 접속.

---

## 테스트

루트 `mise.toml` 이 단일 진입점 (`brew install mise`, ADR-032):

```bash
mise run ci-local         # ★ 머지 게이트 전체 (toolchain + be-test + contracts + fe-test/build + 보안헤더)
mise run install          # BE uv sync --frozen + FE pnpm install
mise run be-test          # 백엔드 pytest — CI 와 동일 호출 (transcription/r2-cors 2개 제외)
mise run fe-build         # 프론트엔드 빌드 (타입 검사 포함)
mise run e2e              # Playwright — 로컬 .env.local에 E2E_USER_EMAIL/PASSWORD 필요
mise run contracts-check  # OpenAPI 계약 drift 게이트 (재생성 + git diff)
```

전체 task 는 `mise tasks`. `mise` 없이는 각 task 안의 원 명령을 직접 실행해도 된다.
`mise install` 이 Node 22 / pnpm 8.15.9 / uv 0.10.4 를 프로덕션과 같은 버전으로 깔아준다.

---

## 배포

자동 배포는 없다. 맥에서 arm64 네이티브로 빌드해 SSH 파이프로 서버에 넘긴다.

```bash
TAG=$(git rev-parse --short HEAD)
mise run deploy-preflight     # 진행 중 작업 0 확인 + .env 인코딩 게이트
mise run deploy-build $TAG
mise run deploy-ship $TAG
mise run deploy-status
```

배포 상세 절차 → [`docs/operations/deployment.md`](docs/operations/deployment.md)
서버 운영 런북 → [`deploy/oci/README.md`](deploy/oci/README.md)

---

## 문서

| 문서 | 내용 |
|---|---|
| [`docs/requirements/prd.md`](docs/requirements/prd.md) | PRD + Phase 로드맵 |
| [`docs/development/secrets.md`](docs/development/secrets.md) | **환경변수 전체 매트릭스** (로컬/CI/프로덕션) |
| [`docs/operations/deployment.md`](docs/operations/deployment.md) | 배포 절차 (오라클 셀프호스팅) |
| [`deploy/oci/README.md`](deploy/oci/README.md) | 서버 운영 런북 (배포·롤백·함정) |
| [`docs/architecture/ai-pipeline.md`](docs/architecture/ai-pipeline.md) | AI 파이프라인 설계 |
| [`docs/architecture/rag-pipeline.md`](docs/architecture/rag-pipeline.md) | RAG 6-Layer 설계 |
| [`CONTEXT-MAP.md`](CONTEXT-MAP.md) | 도메인 헌법 (엔티티 + 불변식) |
| [`docs/TODO.md`](docs/TODO.md) | 열린 작업 (Blocked / Questions / Next Actions) |
| [`docs/README.md`](docs/README.md) | **문서 전체 색인** — active doc 의 유일한 entry point |
| [`docs/development/testing.md`](docs/development/testing.md) | 테스트 게이트 ↔ CI job 대응표 |
| [`docs/development/migrations.md`](docs/development/migrations.md) | alembic 규약 + 2단계 배포와 그 예외 |
| [`docs/product/glossary.md`](docs/product/glossary.md) | 도메인 용어 색인 (정의 SSOT 는 헌법) |
