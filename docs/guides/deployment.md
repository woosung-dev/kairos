# Kairos 배포 가이드

---

## 사전 준비

### 필요한 계정/도구

- GCP 계정 + 프로젝트 (Cloud Run, Artifact Registry)
- Vercel 계정
- Neon 계정 (PostgreSQL)
- `gcloud` CLI ([설치 가이드](https://cloud.google.com/sdk/docs/install))
- Docker Desktop

### 환경변수 목록

| 변수 | 설명 | 어디서 얻는지 |
|------|------|-------------|
| `DATABASE_URL` | Neon PostgreSQL 연결 문자열 | Neon 대시보드 → Connection Details |
| `CLERK_SECRET_KEY` | Clerk 비밀 키 | Clerk 대시보드 → API Keys |
| `CLERK_WEBHOOK_SECRET` | Clerk 웹훅 시크릿 | Clerk 대시보드 → Webhooks |
| `R2_ACCOUNT_ID` | Cloudflare 계정 ID | Cloudflare 대시보드 |
| `R2_ACCESS_KEY_ID` | R2 접근 키 | Cloudflare R2 → API Tokens |
| `R2_SECRET_ACCESS_KEY` | R2 시크릿 키 | 위와 동일 |
| `R2_BUCKET_NAME` | R2 버킷 이름 | Cloudflare R2 |
| `GEMINI_API_KEY` | Google Gemini API 키 | Google AI Studio |
| `OPENAI_API_KEY` | OpenAI API 키 | OpenAI Platform |
| `CORS_ORIGINS` | 허용 오리진 (쉼표 구분) | Vercel 배포 URL |
| `LOG_LEVEL` | 로그 레벨 | `WARNING` (프로덕션) |
| `APP_ENV` | 환경 구분 | `production` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk 공개 키 (FE) | Clerk 대시보드 |
| `NEXT_PUBLIC_API_URL` | 백엔드 API URL (FE) | Cloud Run 배포 URL |

---

## 1. Neon DB prod 브랜치

1. [Neon 대시보드](https://console.neon.tech) → 프로젝트 선택
2. **Branches** → **Create Branch**
3. Name: `prod`, Parent: `main`
4. Connection string 복사 (다음 단계에서 사용)

---

## 2. 백엔드 배포 (GCP Cloud Run)

### 2.1 초기 설정 (최초 1회)

```bash
# GCP 프로젝트 설정
export GCP_PROJECT_ID="your-project-id"
gcloud config set project $GCP_PROJECT_ID

# API 활성화
gcloud services enable artifactregistry.googleapis.com run.googleapis.com

# Artifact Registry 저장소 생성
gcloud artifacts repositories create kairos \
  --repository-format=docker \
  --location=asia-northeast3 \
  --description="Kairos API Docker images"

# Docker 인증 설정
gcloud auth configure-docker asia-northeast3-docker.pkg.dev
```

### 2.2 빌드 + 배포

```bash
cd backend

# Docker 빌드
docker build -t asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest .

# Push
docker push asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest

# Cloud Run 배포
gcloud run deploy kairos-api \
  --image asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --min-instances 0 \
  --max-instances 3
```

배포 완료 시 URL 출력: `https://kairos-api-xxx-du.a.run.app`

### 2.3 환경변수 설정

```bash
gcloud run services update kairos-api \
  --region asia-northeast3 \
  --set-env-vars "\
APP_ENV=production,\
LOG_LEVEL=WARNING,\
DATABASE_URL=<neon-prod-connection-string>,\
CORS_ORIGINS=https://kairos-xxx.vercel.app,\
CLERK_SECRET_KEY=<value>,\
CLERK_WEBHOOK_SECRET=<value>,\
R2_ACCOUNT_ID=<value>,\
R2_ACCESS_KEY_ID=<value>,\
R2_SECRET_ACCESS_KEY=<value>,\
R2_BUCKET_NAME=<value>,\
GEMINI_API_KEY=<value>,\
OPENAI_API_KEY=<value>"
```

또는 Cloud Run 콘솔 → kairos-api → 수정 → 환경변수 탭에서 GUI로 설정.

### 2.4 검증

```bash
curl https://kairos-api-xxx-du.a.run.app/api/v1/health
# {"status":"ok","version":"0.1.0"}
```

---

## 3. 프론트엔드 배포 (Vercel)

### 3.1 프로젝트 설정

1. [vercel.com](https://vercel.com) → **New Project**
2. GitHub repo 연결
3. Framework Preset: **Next.js** (자동 감지)
4. Root Directory: **`frontend/`**
5. Production Branch: **`prod`**

### 3.2 환경변수 설정

Vercel → Settings → Environment Variables:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk 프로덕션 공개 키 |
| `CLERK_SECRET_KEY` | Clerk 프로덕션 비밀 키 |
| `NEXT_PUBLIC_API_URL` | `https://kairos-api-xxx-du.a.run.app` |

### 3.3 배포

`prod` 브랜치에 push하면 자동 배포:

```bash
git checkout prod
git merge main
git push origin prod
```

### 3.4 CORS 업데이트

Vercel 배포 URL 확인 후 Cloud Run 환경변수 업데이트:

```bash
gcloud run services update kairos-api \
  --region asia-northeast3 \
  --update-env-vars "CORS_ORIGINS=https://kairos-xxx.vercel.app,http://localhost:3000"
```

---

## 4. Git 브랜치 전략

```
main (개발) → 기능 완성 + 테스트 통과
  ↓ merge (수동)
prod (프로덕션)
  → Vercel: 자동 배포
  → Cloud Run: 수동 (docker build + push + deploy)
```

### 재배포 (코드 변경 시)

```bash
# 1. main에서 개발 완료
git checkout prod
git merge main
git push origin prod    # → Vercel 자동 배포

# 2. Cloud Run 수동 배포
cd backend
docker build -t asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest .
docker push asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest
gcloud run deploy kairos-api \
  --image asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/kairos/api:latest \
  --region asia-northeast3
```

---

## 5. 트러블슈팅

### CORS 에러

- Cloud Run `CORS_ORIGINS`에 Vercel URL 포함 확인
- `http://` vs `https://` 확인
- trailing slash 없어야 함 (`https://kairos.vercel.app` ✅, `https://kairos.vercel.app/` ❌)

### DB 연결 실패

- Neon connection string에 `?sslmode=require` 포함 확인
- Cloud Run은 기본적으로 외부 연결 허용

### Clerk 인증 실패

- **프로덕션 키** 사용 확인 (development 키 아님)
- Vercel `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`와 Cloud Run `CLERK_SECRET_KEY`가 같은 Clerk 인스턴스인지 확인
- Clerk 대시보드에서 프로덕션 URL을 Allowed Origins에 추가

### Cold Start 느림 (첫 요청 5-10초)

- `--min-instances 1`로 변경 (비용 증가, ~$20/월)
- MVP에서는 cold start 허용 권장

### 마이그레이션 실패

- Cloud Run 로그 확인: `gcloud run services logs read kairos-api --region asia-northeast3 --limit 20`
- `DATABASE_URL`이 올바른지 확인
