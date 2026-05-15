# Sprint 4: 배포 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sprint 1~3 기능을 GCP Cloud Run + Vercel에 배포하여 내부 5명이 사용 가능하게 함

**Architecture:** Backend-First 배포. Config 확장 → Dockerfile → Cloud Run → Neon prod → Vercel → GitHub Actions → QA 순서. RBAC은 Sprint 5로 분리.

**Tech Stack:** Docker + GCP Cloud Run + Vercel + Neon PostgreSQL + GitHub Actions

**설계 문서:** `docs/superpowers/specs/2026-04-02-sprint4-deploy-design.md`

---

## Slice 1: 백엔드 프로덕션 설정

### Task 1: Config 확장 + CORS 동적 설정

**Files:**
- Modify: `backend/src/core/config.py`
- Modify: `backend/src/main.py`

- [ ] **Step 1: config.py에 프로덕션 설정 추가**

```python
# backend/src/core/config.py
"""앱 설정. 모든 환경변수를 여기서 관리."""
from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Kairos 백엔드 설정. .env 파일 또는 환경변수에서 로드."""

    # 앱
    app_env: str = "development"
    log_level: str = "INFO"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # DB
    database_url: str

    # Clerk
    clerk_secret_key: SecretStr
    clerk_webhook_secret: SecretStr

    # Cloudflare R2
    r2_account_id: SecretStr
    r2_access_key_id: SecretStr
    r2_secret_access_key: SecretStr
    r2_bucket_name: str

    # AI
    gemini_api_key: SecretStr
    openai_api_key: SecretStr

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


def get_settings() -> Settings:
    """Settings 인스턴스를 반환한다. 모듈 레벨 싱글톤 대신 사용."""
    return Settings()
```

- [ ] **Step 2: main.py CORS를 동적 설정으로 변경**

`backend/src/main.py`에서 CORS 미들웨어를 수정:

```python
# 기존:
# allow_origins=["http://localhost:3000"],

# 변경:
from src.core.config import get_settings

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 3: 로깅 설정 추가**

`backend/src/main.py` 상단에:

```python
import logging

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
```

- [ ] **Step 4: 테스트 실행**

```bash
cd backend && uv run pytest --ignore=tests/services/test_transcription.py -v
```

Expected: 42 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/core/config.py backend/src/main.py
git commit -m "feat: 프로덕션 설정 — CORS 동적 설정 + 로그 레벨 + cors_origins 환경변수"
```

---

### Task 2: Dockerfile + .dockerignore

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

- [ ] **Step 1: Dockerfile 작성**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

# 시스템 의존성 (ffmpeg: 카카오톡 m4a 변환용)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 의존성 먼저 설치 (캐시 활용)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 소스 복사
COPY alembic.ini ./
COPY alembic/ alembic/
COPY src/ src/

EXPOSE 8000

# 시작 시 마이그레이션 자동 실행 → 서버 시작
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000"]
```

- [ ] **Step 2: .dockerignore 작성**

```
# backend/.dockerignore
.venv/
__pycache__/
tests/
.pytest_cache/
*.pyc
.env
.env.*
.git/
```

- [ ] **Step 3: 로컬 Docker 빌드 테스트**

```bash
cd backend && docker build -t kairos-api .
```

Expected: 빌드 성공 (마지막 줄 `Successfully tagged kairos-api:latest`)

- [ ] **Step 4: 로컬 Docker 실행 테스트**

```bash
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="$DATABASE_URL" \
  -e CLERK_SECRET_KEY="$CLERK_SECRET_KEY" \
  -e CLERK_WEBHOOK_SECRET="$CLERK_WEBHOOK_SECRET" \
  -e R2_ACCOUNT_ID="$R2_ACCOUNT_ID" \
  -e R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID" \
  -e R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY" \
  -e R2_BUCKET_NAME="$R2_BUCKET_NAME" \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  kairos-api
```

별도 터미널에서:
```bash
curl http://localhost:8000/api/v1/health
```

Expected: `{"status":"ok","version":"0.1.0"}`

- [ ] **Step 5: 커밋**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "feat: Dockerfile — Python 3.12 + uv + ffmpeg + alembic auto-migrate"
```

---

## Slice 2: Cloud Run 배포

### Task 3: GCP Artifact Registry + Cloud Run 배포

이 Task는 GCP 콘솔/CLI에서 수행하는 인프라 작업입니다.

**사전 조건:**
- `gcloud` CLI 설치 + 로그인 (`gcloud auth login`)
- GCP 프로젝트 생성 또는 기존 프로젝트 사용

- [ ] **Step 1: Artifact Registry 저장소 생성**

```bash
# GCP 프로젝트 설정 (자신의 프로젝트 ID로 변경)
export GCP_PROJECT_ID="your-gcp-project-id"
gcloud config set project $GCP_PROJECT_ID

# Artifact Registry API 활성화
gcloud services enable artifactregistry.googleapis.com

# Docker 저장소 생성
gcloud artifacts repositories create kairos \
  --repository-format=docker \
  --location=asia-northeast3 \
  --description="Kairos API Docker images"

# Docker 인증 설정
gcloud auth configure-docker asia-northeast3-docker.pkg.dev
```

- [ ] **Step 2: Docker 이미지 빌드 + push**

```bash
cd backend

# 빌드
docker build -t asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest .

# push
docker push asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest
```

- [ ] **Step 3: Cloud Run 배포**

```bash
gcloud services enable run.googleapis.com

gcloud run deploy kairos-api \
  --image asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --min-instances 0 \
  --max-instances 3
```

배포 후 URL이 출력됩니다: `https://kairos-api-xxx-du.a.run.app`

- [ ] **Step 4: Cloud Run 환경변수 설정**

Cloud Run 콘솔 또는 CLI에서 환경변수 설정:

```bash
gcloud run services update kairos-api \
  --region asia-northeast3 \
  --set-env-vars "\
APP_ENV=production,\
LOG_LEVEL=WARNING,\
CORS_ORIGINS=https://kairos-xxx.vercel.app,\
DATABASE_URL=<neon-prod-connection-string>,\
CLERK_SECRET_KEY=<prod>,\
CLERK_WEBHOOK_SECRET=<prod>,\
R2_ACCOUNT_ID=<value>,\
R2_ACCESS_KEY_ID=<value>,\
R2_SECRET_ACCESS_KEY=<value>,\
R2_BUCKET_NAME=<value>,\
GEMINI_API_KEY=<value>,\
OPENAI_API_KEY=<value>"
```

> 실제 값은 사용자가 `.env` 또는 Neon/Clerk/R2 대시보드에서 복사.

- [ ] **Step 5: 검증**

```bash
curl https://kairos-api-xxx-du.a.run.app/api/v1/health
```

Expected: `{"status":"ok","version":"0.1.0"}`

---

## Slice 3: Neon prod + Vercel 배포

### Task 4: Neon prod 브랜치 생성

인프라 작업 (Neon 대시보드).

- [ ] **Step 1: Neon 대시보드에서 prod 브랜치 생성**

1. https://console.neon.tech → 프로젝트 선택
2. Branches → Create Branch
3. Name: `prod`, Parent: `main`
4. Connection string 복사 → Cloud Run `DATABASE_URL`에 설정

- [ ] **Step 2: Cloud Run 환경변수 업데이트**

```bash
gcloud run services update kairos-api \
  --region asia-northeast3 \
  --update-env-vars "DATABASE_URL=<neon-prod-connection-string>"
```

- [ ] **Step 3: 검증 — 마이그레이션 자동 실행 확인**

Cloud Run 로그에서 `Running upgrade ... -> ...` 확인 (Alembic 마이그레이션이 시작 시 실행됨).

```bash
gcloud run services logs read kairos-api --region asia-northeast3 --limit 20
```

---

### Task 5: prod 브랜치 + Vercel 배포

**Files:**
- Git: `prod` 브랜치 생성

- [ ] **Step 1: prod 브랜치 생성**

```bash
git checkout main
git checkout -b prod
git push -u origin prod
```

- [ ] **Step 2: Vercel 프로젝트 설정**

1. https://vercel.com → New Project
2. GitHub repo 연결
3. Framework Preset: Next.js
4. Root Directory: `frontend/`
5. Build Command: (자동 감지)
6. Production Branch: `prod`

- [ ] **Step 3: Vercel 환경변수 설정**

Vercel 대시보드 → Settings → Environment Variables:

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<prod-publishable-key>
CLERK_SECRET_KEY=<prod-secret-key>
NEXT_PUBLIC_API_URL=https://kairos-api-xxx-du.a.run.app
```

> `NEXT_PUBLIC_API_URL`은 Task 3에서 받은 Cloud Run URL.

- [ ] **Step 4: 배포 트리거**

Vercel이 `prod` 브랜치에서 자동 배포합니다. 대시보드에서 배포 완료 확인.

- [ ] **Step 5: CORS URL 업데이트**

Vercel 배포 URL (예: `https://kairos-xxx.vercel.app`) 확인 후, Cloud Run 환경변수 업데이트:

```bash
gcloud run services update kairos-api \
  --region asia-northeast3 \
  --update-env-vars "CORS_ORIGINS=https://kairos-xxx.vercel.app,http://localhost:3000"
```

> `localhost:3000`도 유지하여 로컬 개발 계속 가능.

- [ ] **Step 6: 검증**

브라우저에서 `https://kairos-xxx.vercel.app` 접속:
- Clerk 로그인 성공
- 대시보드 표시
- RAG 패널 동작

---

## Slice 4: GitHub Actions + 배포 가이드

### Task 6: GitHub Actions 테스트 워크플로우

**Files:**
- Create: `.github/workflows/test.yml`

- [ ] **Step 1: 워크플로우 파일 작성**

```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [main, prod]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Install dependencies
        run: uv sync

      - name: Run tests
        run: uv run pytest --ignore=tests/services/test_transcription.py -v
        env:
          DATABASE_URL: "postgresql://fake:fake@localhost:5432/fake"
          CLERK_SECRET_KEY: "sk_test_fake"
          CLERK_WEBHOOK_SECRET: "whsec_fake"
          R2_ACCOUNT_ID: "fake"
          R2_ACCESS_KEY_ID: "fake"
          R2_SECRET_ACCESS_KEY: "fake"
          R2_BUCKET_NAME: "fake"
          GEMINI_API_KEY: "fake"
          OPENAI_API_KEY: "fake"

  frontend-build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "pnpm"
          cache-dependency-path: frontend/pnpm-lock.yaml

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build (includes type check)
        run: pnpm build
        env:
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: "pk_test_fake"
          NEXT_PUBLIC_API_URL: "http://localhost:8000"
```

- [ ] **Step 2: 커밋 + push로 워크플로우 동작 확인**

```bash
mkdir -p .github/workflows
git add .github/workflows/test.yml
git commit -m "ci: GitHub Actions — backend pytest + frontend build"
git push origin main
```

GitHub Actions 탭에서 워크플로우 실행 확인.

---

### Task 7: 배포 가이드 문서

**Files:**
- Create: `docs/guides/deployment.md`

- [ ] **Step 1: 배포 가이드 작성**

```markdown
# Kairos 배포 가이드

## 사전 준비

### 필요한 계정/도구
- GCP 계정 + 프로젝트 (Cloud Run, Artifact Registry)
- Vercel 계정
- Neon 계정 (PostgreSQL)
- `gcloud` CLI (설치: https://cloud.google.com/sdk/docs/install)
- Docker Desktop

### 환경변수 목록

| 변수 | 설명 | 어디서 얻는지 |
|------|------|-------------|
| DATABASE_URL | Neon PostgreSQL 연결 문자열 | Neon 대시보드 → Connection Details |
| CLERK_SECRET_KEY | Clerk 비밀 키 | Clerk 대시보드 → API Keys |
| CLERK_WEBHOOK_SECRET | Clerk 웹훅 시크릿 | Clerk 대시보드 → Webhooks |
| R2_ACCOUNT_ID | Cloudflare 계정 ID | Cloudflare 대시보드 |
| R2_ACCESS_KEY_ID | R2 접근 키 | Cloudflare R2 → API Tokens |
| R2_SECRET_ACCESS_KEY | R2 시크릿 키 | 위와 동일 |
| R2_BUCKET_NAME | R2 버킷 이름 | Cloudflare R2 |
| GEMINI_API_KEY | Google Gemini API 키 | Google AI Studio |
| OPENAI_API_KEY | OpenAI API 키 | OpenAI Platform |
| CORS_ORIGINS | 허용 오리진 (쉼표 구분) | Vercel 배포 URL |
| NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY | Clerk 공개 키 | Clerk 대시보드 |
| NEXT_PUBLIC_API_URL | 백엔드 API URL | Cloud Run 배포 URL |

---

## 백엔드 배포 (GCP Cloud Run)

### 1. Artifact Registry 설정 (최초 1회)

```bash
export GCP_PROJECT_ID="your-project-id"
gcloud config set project $GCP_PROJECT_ID
gcloud services enable artifactregistry.googleapis.com run.googleapis.com
gcloud artifacts repositories create kairos \
  --repository-format=docker \
  --location=asia-northeast3
gcloud auth configure-docker asia-northeast3-docker.pkg.dev
```

### 2. 빌드 + 배포

```bash
cd backend
docker build -t asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest .
docker push asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest
gcloud run deploy kairos-api \
  --image asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --min-instances 0 \
  --max-instances 3
```

### 3. 환경변수 설정

Cloud Run 콘솔 → kairos-api → 수정 → 환경변수 탭에서 위 목록 설정.

### 4. 검증

```bash
curl https://<cloud-run-url>/api/v1/health
# {"status":"ok","version":"0.1.0"}
```

---

## 프론트엔드 배포 (Vercel)

### 1. Vercel 프로젝트 설정

1. vercel.com → New Project → GitHub repo 연결
2. Root Directory: `frontend/`
3. Production Branch: `prod`

### 2. 환경변수 설정

Vercel → Settings → Environment Variables에서 설정.

### 3. 배포

`prod` 브랜치에 push하면 자동 배포.

---

## DB (Neon)

### prod 브랜치 생성

Neon 대시보드 → Branches → Create Branch → Name: `prod`
Connection string을 Cloud Run `DATABASE_URL`에 설정.

---

## 트러블슈팅

### CORS 에러
- Cloud Run `CORS_ORIGINS`에 Vercel URL이 포함되어 있는지 확인
- `http://` vs `https://` 확인
- trailing slash 없어야 함

### DB 연결 실패
- Neon connection string에 `?sslmode=require` 포함 확인
- Cloud Run에서 외부 연결 허용 확인

### Clerk 인증 실패
- 프로덕션 키 사용 확인 (development 키 아님)
- Vercel의 `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`와 Cloud Run의 `CLERK_SECRET_KEY`가 같은 Clerk 인스턴스인지 확인

### Cold Start 느림
- Cloud Run min-instances를 1로 올리면 해결 (비용 증가)
```

- [ ] **Step 2: 커밋**

```bash
git add docs/guides/deployment.md
git commit -m "docs: 배포 가이드 — GCP Cloud Run + Vercel + Neon 단계별 설명"
```

---

## Slice 5: 프로덕션 QA

### Task 8: 프로덕션 E2E QA

배포 완료 후 프로덕션 URL에서 수행하는 수동 QA입니다.

- [ ] **Step 1: 헬스체크**

```bash
curl https://<cloud-run-url>/api/v1/health
```

Expected: `{"status":"ok","version":"0.1.0"}`

- [ ] **Step 2: Clerk 프로덕션 로그인**

브라우저에서 `https://kairos-xxx.vercel.app` 접속 → 로그인

- [ ] **Step 3: 회의 업로드 → AI 요약**

오디오 파일 업로드 → 3분 이내 요약 + 액션 추출 확인

- [ ] **Step 4: RAG 질문 → 스트리밍 답변**

업로드된 회의에 대해 질문 → 2초 이내 스트리밍 답변 + 소스 표시

- [ ] **Step 5: 노트 CRUD**

/notes → 새 노트 → Tiptap 에디터 → 내용 입력 → 자동저장 확인

- [ ] **Step 6: 기존 기능 확인**

- Inbox 표시
- 프로젝트 CRUD
- 액션 아이템 칸반
- Cmd+K RAG 모드
- 반응형 (모바일 뷰포트)

- [ ] **Step 7: 버그 수정 + 커밋**

QA에서 발견된 버그 수정 후:

```bash
git add -A && git commit -m "fix: 프로덕션 QA 버그 수정"
```

- [ ] **Step 8: PRD 현재 컨텍스트 업데이트**

`docs/requirements/prd.md` §8 현재 컨텍스트를 Sprint 4 완료 반영으로 업데이트.

```bash
git add docs/requirements/prd.md
git commit -m "docs: Sprint 4 완료 — PRD 현재 컨텍스트 업데이트"
```

---

## Sprint 5 후보 (명시적 제외)

| 항목 | 이유 |
|------|------|
| RBAC (Owner/Admin/Member/Viewer) | 내부 5명 MVP 불필요 |
| 초대 링크 + 이메일 초대 | RBAC과 함께 |
| Sentry 모니터링 | Cloud Run 기본 로깅으로 시작 |
| CI/CD 자동 배포 | 수동 배포로 충분 |
| 커스텀 도메인 | 기본 도메인으로 시작 |
| Cohere Rerank v3 | Sprint 3에서 이월 |
| pgvector → Qdrant | 판매 준비 시점 |
