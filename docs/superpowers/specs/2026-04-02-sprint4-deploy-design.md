# Sprint 4 설계: 배포 — "내부 팀에게 전달"

> **날짜:** 2026-04-02
> **상태:** 설계 리뷰 중
> **근거 문서:** PRD §Sprint 4
> **접근법:** Backend-First 배포, RBAC은 Sprint 5로 분리

---

## 1. 목표

> 내부 팀 5명이 실제 사용 가능한 수준으로 배포

Sprint 1~3에서 만든 기능(회의 업로드 → AI 요약 → 액션 → Inbox → RAG → 노트)을 프로덕션에 올려서, 내부 팀이 `https://kairos-xxx.vercel.app`에서 사용할 수 있게 한다.

---

## 2. 설계 결정 요약

| 결정 | 선택 | 근거 |
|------|------|------|
| RBAC | **Sprint 5로 분리** | 내부 5명 신뢰 기반 팀, 배포가 P0 |
| BE 배포 | GCP Cloud Run | 기존 GCP 경험, 서버리스 + Docker |
| FE 배포 | Vercel | Next.js 네이티브 지원, prod 브랜치 자동 배포 |
| DB | Neon prod 브랜치 | dev/prod 데이터 분리 |
| 도메인 | 기본 도메인 | `.vercel.app` + `.run.app`, 커스텀 도메인은 추후 |
| CI/CD | **최소** — 테스트만 자동, 배포는 수동 | MVP에서 CI/CD 파이프라인 오버엔지니어링 방지 |
| 모니터링 | Cloud Run 기본 로깅 | Sentry는 Sprint 5+ |
| Region | asia-northeast3 (서울) | 한국 사용자 대상 |

---

## 3. 백엔드 프로덕션 설정

### 3.1 Config 확장

`backend/src/core/config.py`에 추가:

```python
cors_origins: str = "http://localhost:3000"  # 쉼표 구분
log_level: str = "INFO"
```

### 3.2 CORS 동적 설정

`backend/src/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3.3 Dockerfile

```dockerfile
FROM python:3.12-slim

# ffmpeg (카카오톡 m4a 변환용)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 의존성 설치
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 소스 복사
COPY alembic.ini ./
COPY alembic/ alembic/
COPY src/ src/

EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000"]
```

### 3.4 .dockerignore

```
.venv/
__pycache__/
tests/
.pytest_cache/
*.pyc
.env
.env.*
```

---

## 4. GCP Cloud Run 배포

### 4.1 배포 명령 (수동)

```bash
# 1. Docker 빌드
docker build -t kairos-api ./backend

# 2. 태그 + push (Artifact Registry)
docker tag kairos-api asia-northeast3-docker.pkg.dev/<PROJECT_ID>/kairos/api:latest
docker push asia-northeast3-docker.pkg.dev/<PROJECT_ID>/kairos/api:latest

# 3. Cloud Run 배포
gcloud run deploy kairos-api \
  --image asia-northeast3-docker.pkg.dev/<PROJECT_ID>/kairos/api:latest \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars "APP_ENV=production,LOG_LEVEL=WARNING"
```

### 4.2 Cloud Run 설정

| 항목 | 값 | 이유 |
|------|-----|------|
| Region | asia-northeast3 (서울) | 한국 사용자 |
| Memory | 1Gi | Gemini + OpenAI + ffmpeg |
| Min instances | 0 | 비용 절약 (cold start 허용) |
| Max instances | 3 | 내부 5명 MVP |
| Port | 8000 | uvicorn |
| 인증 | 미인증 허용 | Clerk JWT 앱 레벨 인증 |

### 4.3 환경변수 (Cloud Run 콘솔에서 설정)

```
APP_ENV=production
DATABASE_URL=<neon-prod-connection-string>
CORS_ORIGINS=https://kairos-xxx.vercel.app
LOG_LEVEL=WARNING
CLERK_SECRET_KEY=<prod-key>
CLERK_WEBHOOK_SECRET=<prod-key>
R2_ACCOUNT_ID=<same>
R2_ACCESS_KEY_ID=<same>
R2_SECRET_ACCESS_KEY=<same>
R2_BUCKET_NAME=<same>
GEMINI_API_KEY=<same>
OPENAI_API_KEY=<same>
```

---

## 5. Neon DB 프로덕션 브랜치

- Neon 대시보드에서 `main` → `prod` 브랜치 생성
- 별도 connection string 발급 → Cloud Run `DATABASE_URL`에 설정
- 마이그레이션: Cloud Run 시작 시 `alembic upgrade head` 자동 실행
- dev 데이터와 분리

---

## 6. Vercel 프론트엔드 배포

### 6.1 설정

- GitHub repo 연결
- Framework: Next.js (자동 감지)
- Root Directory: `frontend/`
- Production Branch: `prod`

### 6.2 환경변수

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<prod-key>
CLERK_SECRET_KEY=<prod-key>
NEXT_PUBLIC_API_URL=https://kairos-api-xxx.run.app
```

### 6.3 코드 변경 없음

`api-client.ts`가 이미 `process.env.NEXT_PUBLIC_API_URL`을 사용하므로 코드 수정 불필요.

---

## 7. prod 브랜치 전략

```
main (개발) → 기능 완성 + 테스트 통과
  ↓ merge (수동)
prod (프로덕션)
  → Vercel 자동 배포
  → Cloud Run 수동 배포 (docker build + push + deploy)
```

---

## 8. GitHub Actions — 테스트 자동화

```yaml
# .github/workflows/test.yml
name: Test
on:
  push:
    branches: [main, prod]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: cd backend && uv sync && uv run pytest --ignore=tests/services/test_transcription.py

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: cd frontend && pnpm install && pnpm build
```

- 배포 자동화 없음 (수동)
- 테스트 실패 시 GitHub에서 빨간불 표시

---

## 9. 배포 가이드 문서

`docs/guides/deployment.md` 신규 작성:
- 사전 준비 (GCP, Vercel, Neon 계정)
- 백엔드 배포 단계별 가이드
- 프론트엔드 배포 단계별 가이드
- 환경변수 목록 + 설정 방법
- 트러블슈팅 (CORS, DB 연결 등)

---

## 10. Vertical Slice 분해

### Slice 1: 백엔드 프로덕션 설정

- Config 확장 (cors_origins, log_level)
- CORS 동적 설정
- Dockerfile + .dockerignore
- 로컬 docker build + run 검증

### Slice 2: Cloud Run 배포

- GCP Artifact Registry 설정
- Docker push + Cloud Run 배포
- 환경변수 설정
- 검증: health check + API 응답

### Slice 3: Neon prod + Vercel 배포

- Neon prod 브랜치 생성
- Vercel 프로젝트 설정 + 환경변수
- prod 브랜치 생성 + push
- 검증: 프론트엔드 로그인 + API 연결

### Slice 4: GitHub Actions + 배포 가이드

- `.github/workflows/test.yml`
- `docs/guides/deployment.md`
- 검증: push 시 테스트 자동 실행

### Slice 5: 프로덕션 QA

- 전체 E2E 체크리스트 (Playwright 또는 수동)
- 버그 수정
- 검증: 모든 항목 통과

---

## 11. QA 체크리스트

- [ ] 헬스체크 (`/api/v1/health`)
- [ ] Clerk 프로덕션 로그인
- [ ] 회의 업로드 → AI 요약 (3분 이내)
- [ ] RAG 질문 → 스트리밍 답변 (2초 이내)
- [ ] 노트 생성/편집/자동저장
- [ ] Inbox 표시
- [ ] 프로젝트 CRUD
- [ ] 액션 아이템 칸반
- [ ] 반응형 (모바일 뷰포트)
- [ ] Cmd+K RAG 모드

---

## 12. Sprint 5 후보 (명시적 제외)

| 항목 | 이유 |
|------|------|
| RBAC (Owner/Admin/Member/Viewer) | 내부 5명 MVP 불필요 |
| 초대 링크 + 이메일 초대 | RBAC과 함께 |
| Sentry 모니터링 | Cloud Run 기본 로깅으로 시작 |
| CI/CD 자동 배포 | 수동 배포로 충분 |
| 커스텀 도메인 | 기본 도메인으로 시작 |
| Cohere Rerank v3 | Sprint 3에서 이월 |
| 노트 Inbox 연동 | Sprint 3에서 이월 |
| pgvector → Qdrant | 판매 준비 시점 |

---

## 13. 완료 기준

- [ ] `https://kairos-api-xxx.run.app/api/v1/health` → `{"status": "ok"}`
- [ ] `https://kairos-xxx.vercel.app` → Clerk 로그인 성공
- [ ] 프로덕션에서 회의 업로드 → RAG 질문 → 답변 E2E 동작
- [ ] GitHub Actions 테스트 자동 실행
- [ ] 배포 가이드 문서 작성 완료
