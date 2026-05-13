# 환경변수 & 시크릿 관리 가이드

> **한 줄 원칙:** 로컬은 파일로 관리(BE: `.env` / FE: `.env.local`), CI는 GitHub Secrets/Variables, 프로덕션은 GCP Secret Manager.
> 코드에 값을 하드코딩하거나 env 파일을 커밋하는 것은 절대 금지.

---

## 빠른 시작 (로컬 셋업)

```bash
# 1. 템플릿 복사
cp backend/.env.example backend/.env        # FastAPI: .env 표준
cp frontend/.env.example frontend/.env.local  # Next.js: .env.local 표준

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

### 백엔드 (`backend/.env`)

| 변수명 | 로컬 | CI (test) | 프로덕션 | 발급처 |
|---|:---:|:---:|:---:|---|
| `APP_ENV` | ✅ `development` | ➖ | Cloud Run env | 직접 입력 |
| `LOG_LEVEL` | ✅ `INFO` | ➖ | Cloud Run env | 직접 입력 |
| `CORS_ORIGINS` | ✅ `http://localhost:3000` | ➖ | GitHub Secret | Vercel 배포 URL |
| `FRONTEND_URL` | ✅ `http://localhost:3000` | ➖ | GitHub Secret | Vercel 배포 URL |
| `DATABASE_URL` 🔒 | ✅ | ➖ fake | GCP Secret Manager | [Neon 대시보드](https://console.neon.tech) → Connection Details |
| `CLERK_SECRET_KEY` 🔒 | ✅ | ➖ fake | GCP Secret Manager | [Clerk 대시보드](https://dashboard.clerk.com) → API Keys |
| `CLERK_WEBHOOK_SECRET` 🔒 | ✅ | ➖ fake | GCP Secret Manager | Clerk 대시보드 → Webhooks |
| `R2_ACCOUNT_ID` 🔒 | ✅ | ➖ fake | GCP Secret Manager | Cloudflare 대시보드 → 우측 상단 Account ID |
| `R2_ACCESS_KEY_ID` 🔒 | ✅ | ➖ fake | GCP Secret Manager | Cloudflare R2 → Manage R2 API tokens |
| `R2_SECRET_ACCESS_KEY` 🔒 | ✅ | ➖ fake | GCP Secret Manager | 위와 동일 (토큰 생성 시 1회만 표시) |
| `R2_BUCKET_NAME` | ✅ | ➖ fake | GCP Secret Manager | Cloudflare R2 버킷 이름 |
| `GEMINI_API_KEY` 🔒 | ✅ | ➖ fake | GCP Secret Manager | [Google AI Studio](https://aistudio.google.com) → Get API key |
| `OPENAI_API_KEY` 🔒 | ✅ | ➖ fake | GCP Secret Manager | [OpenAI Platform](https://platform.openai.com/api-keys) |

---

### 프론트엔드 (`frontend/.env.local`)

| 변수명 | 로컬 | CI (build) | 프로덕션 | 발급처 |
|---|:---:|:---:|:---:|---|
| `NEXT_PUBLIC_API_URL` | ✅ `http://localhost:8000` | ➖ fake | Vercel 환경변수 | Cloud Run 배포 URL |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | ✅ | ➖ fake | Vercel 환경변수 | Clerk 대시보드 → API Keys |
| `CLERK_SECRET_KEY` 🔒 | ✅ | ➖ fake | Vercel 환경변수 | Clerk 대시보드 → API Keys |

---

### CI 전용 — GitHub Secrets (배포 자동화)

> GitHub repo → Settings → Secrets and variables → Actions → **Secrets** 탭

| Secret 이름 | 용도 | 값 |
|---|---|---|
| `GCP_SA_KEY` 🔒 | Cloud Run 배포용 SA JSON 키 | GCP Console → SA → 키 생성 → JSON 전체 내용 |
| `CORS_ORIGINS` | Cloud Run CORS 허용 오리진 | `https://kairos-zeta-ebon.vercel.app` |
| `FRONTEND_URL` | Cloud Run 프론트엔드 URL | `https://kairos-zeta-ebon.vercel.app` |

> **이미지 푸시 (GHCR)**: `GITHUB_TOKEN` 자동 처리 — 별도 시크릿 불필요.

---

### CI 전용 — GitHub Secrets (E2E 테스트)

> E2E 잡은 `E2E_ENABLED = true` Variable이 설정된 경우에만 실행됨

| 이름 | 탭 | 값 |
|---|---|---|
| `E2E_CLERK_PUBLISHABLE_KEY` | Secrets | Clerk dev 공개 키 (`pk_test_...`) |
| `E2E_CLERK_SECRET_KEY` | Secrets | Clerk dev 비밀 키 (`sk_test_...`) |
| `E2E_API_URL` | Secrets | `https://kairos-api-467254555861.asia-northeast3.run.app` |
| `E2E_USER_EMAIL` | Secrets | 테스트 계정 이메일 |
| `E2E_USER_PASSWORD` | Secrets | 테스트 계정 비밀번호 |
| `E2E_ENABLED` | **Variables** | `true` |

---

### 프로덕션 — GCP Secret Manager 등록 이름

> 배포 시 `deploy.yml`이 아래 이름으로 Secret Manager에서 값을 읽어 Cloud Run에 주입

| Secret Manager 이름 | 대응 환경변수 |
|---|---|
| `database-url` | `DATABASE_URL` |
| `clerk-secret-key` | `CLERK_SECRET_KEY` |
| `clerk-webhook-secret` | `CLERK_WEBHOOK_SECRET` |
| `r2-account-id` | `R2_ACCOUNT_ID` |
| `r2-access-key-id` | `R2_ACCESS_KEY_ID` |
| `r2-secret-access-key` | `R2_SECRET_ACCESS_KEY` |
| `r2-bucket-name` | `R2_BUCKET_NAME` |
| `gemini-api-key` | `GEMINI_API_KEY` |
| `openai-api-key` | `OPENAI_API_KEY` |

등록 방법: `deployment.md §2.5.1-A` 참조.

---

## 자주 하는 실수

| 실수 | 결과 | 방지 |
|---|---|---|
| `.env.local`을 git add | 시크릿 유출 | `.gitignore`에 `.env.local` 확인 |
| 프로덕션 키를 로컬에서 사용 | 실수로 프로덕 DB 조작 | 로컬은 항상 dev/test 키 사용 |
| Secret Manager 없이 `--set-env-vars`로 직접 설정 | 배포 시 값 덮어쓰기 | `deploy.yml`은 `--set-secrets`만 사용 |
| R2 Secret Access Key 재발급 없이 분실 | 재발급 필요 | 발급 직후 즉시 Secret Manager에 저장 |
