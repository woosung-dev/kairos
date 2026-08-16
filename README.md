# Kairos — 팀의 세컨드 브레인

> *καιρός — 흘러가는 시간(Chronos) 속 결정적 순간.*
> 회의, 노트, 자료를 넣으면 AI가 정리하고, 질문하면 인사이트가 나온다.

**프로덕션:** [kairos.woosung.dev](https://kairos.woosung.dev) · BE: `https://kairos-api.woosung.dev` (오라클 셀프호스팅, ADR-028)

**현재 상태:** Sprint 26 (glittery-tulip, 2026-05-23) — docs 거버넌스 경량화 진행. ~Sprint 25 (moonlit-sutton) 까지 Multi-Agent QA P0~P2 + 보안 3-layer + 회귀 가드 완료. 상세: `git log` + `docs/REFACTORING-BACKLOG.md` "다음 Sprint 진입점".

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Next.js 16 + React 19 + Tailwind v4 + shadcn/ui |
| Backend | FastAPI + SQLModel + asyncpg |
| Database | PostgreSQL 17 + pgvector 0.8 (오라클 셀프호스팅) |
| Auth | Clerk |
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

루트 `justfile` 이 단일 진입점 (`brew install just`, ADR-027):

```bash
just install          # BE uv sync --frozen + FE pnpm install
just be-test          # 백엔드 pytest — CI 와 동일 호출 (transcription/r2-cors 2개 제외)
just fe-build         # 프론트엔드 빌드 (타입 검사 포함)
just e2e              # Playwright — 로컬 .env.local에 E2E_USER_EMAIL/PASSWORD 필요
just contracts-check  # OpenAPI 계약 drift 게이트 (재생성 + git diff)
```

전체 recipe 는 `just --list`. `just` 없이는 각 recipe 안의 원 명령을 직접 실행해도 된다.

---

## 배포

자동 배포는 없다. 맥에서 arm64 네이티브로 빌드해 SSH 파이프로 서버에 넘긴다.

```bash
TAG=$(git rev-parse --short HEAD)
just deploy-preflight     # 진행 중 작업 0 확인 + .env 인코딩 게이트
just deploy-build $TAG
just deploy-ship $TAG
just deploy-status
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
| [`docs/TODO.md`](docs/TODO.md) | 현재 작업 상태 |
