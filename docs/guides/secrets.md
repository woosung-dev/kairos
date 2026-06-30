# 환경변수 & 시크릿 관리 가이드

> **한 줄 원칙:** 로컬은 파일로 관리(BE: `.env` / FE: `.env.local`), CI/프로덕션 모두 **GitHub Secrets**를 단일 진실 원천(SoT)으로 사용. 이미지는 GCP **Artifact Registry(GAR)**에 푸시. AWS 이전 시 `deploy.yml` 마지막 부분 + GH Secret 2개(`GCP_*` → `AWS_ROLE_ARN`)만 교체.
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
| `DATABASE_URL` 🔒 | ✅ | ➖ fake | GitHub Secret | [Neon 대시보드](https://console.neon.tech) → Connection Details |
| `CLERK_SECRET_KEY` 🔒 | ✅ | ➖ fake | GitHub Secret | [Clerk 대시보드](https://dashboard.clerk.com) → API Keys |
| `CLERK_WEBHOOK_SECRET` 🔒 | ✅ | ➖ fake | GitHub Secret | Clerk 대시보드 → Webhooks |
| `R2_ACCOUNT_ID` 🔒 | ✅ | ➖ fake | GitHub Secret | Cloudflare 대시보드 → 우측 상단 Account ID |
| `R2_ACCESS_KEY_ID` 🔒 | ✅ | ➖ fake | GitHub Secret | Cloudflare R2 → Manage R2 API tokens |
| `R2_SECRET_ACCESS_KEY` 🔒 | ✅ | ➖ fake | GitHub Secret | 위와 동일 (토큰 생성 시 1회만 표시) |
| `R2_BUCKET_NAME` | ✅ | ➖ fake | GitHub Secret | Cloudflare R2 버킷 이름 |
| `GEMINI_API_KEY` 🔒 | ✅ | ➖ fake | GitHub Secret | [Google AI Studio](https://aistudio.google.com) → Get API key |
| `OPENAI_API_KEY` 🔒 | ✅ | ➖ fake | GitHub Secret | [OpenAI Platform](https://platform.openai.com/api-keys) |

---

### 프론트엔드 (`frontend/.env.local`)

| 변수명 | 로컬 | CI (build) | 프로덕션 | 발급처 |
|---|:---:|:---:|:---:|---|
| `NEXT_PUBLIC_API_URL` | ✅ `http://localhost:8000` | ➖ fake | Vercel 환경변수 | Cloud Run 배포 URL |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | ✅ | ➖ fake | Vercel 환경변수 | Clerk 대시보드 → API Keys |
| `CLERK_SECRET_KEY` 🔒 | ✅ | ➖ fake | Vercel 환경변수 | Clerk 대시보드 → API Keys |

---

### CI 전용 — GitHub Secrets (배포 자동화 + 앱 시크릿)

> GitHub repo → Settings → Secrets and variables → Actions → **Secrets** 탭
> 값은 `backend/.env`에서 복사

**배포 인증 (WIF)**

| Secret 이름 | 값 |
|---|---|
| `GCP_WIF_PROVIDER` | `deployment.md §2.5.1-B` 출력값 |
| `GCP_DEPLOYER_SA` | `kairos-deployer@woosung-dev.iam.gserviceaccount.com` |
| `CORS_ORIGINS` | `https://kairos-zeta-ebon.vercel.app` |
| `FRONTEND_URL` | `https://kairos-zeta-ebon.vercel.app` |

**앱 시크릿 (클라우드 무관 — AWS 이동 시 그대로 재사용)**

| Secret 이름 | 값 위치 |
|---|---|
| `DATABASE_URL` 🔒 | `backend/.env` |
| `CLERK_SECRET_KEY` 🔒 | `backend/.env` |
| `CLERK_WEBHOOK_SECRET` 🔒 | `backend/.env` |
| `R2_ACCOUNT_ID` 🔒 | `backend/.env` |
| `R2_ACCESS_KEY_ID` 🔒 | `backend/.env` |
| `R2_SECRET_ACCESS_KEY` 🔒 | `backend/.env` |
| `R2_BUCKET_NAME` | `backend/.env` |
| `GEMINI_API_KEY` 🔒 | `backend/.env` |
| `OPENAI_API_KEY` 🔒 | `backend/.env` |

> **이미지 (GAR)**: `kairos-deployer` SA의 `roles/artifactregistry.writer` 권한으로 push. 별도 시크릿 불필요.
> **AWS 이동 시**: `GCP_WIF_PROVIDER` + `GCP_DEPLOYER_SA` → `AWS_ROLE_ARN`으로만 교체. 앱 시크릿 9개는 변경 없음.

---

### CI 전용 — GitHub Secrets (E2E 테스트)

> E2E 잡은 `E2E_ENABLED = true` Variable이 설정된 경우에만 실행됨

| 이름 | 탭 | 값 |
|---|---|---|
| `E2E_CLERK_PUBLISHABLE_KEY` | Secrets | Clerk dev 공개 키 (`pk_test_...`) |
| `E2E_CLERK_SECRET_KEY` | Secrets | Clerk dev 비밀 키 (`sk_test_...`) |
| `E2E_API_URL` | Secrets | `https://kairos-api-imrsiyibaa-du.a.run.app` |
| `E2E_USER_EMAIL` | Secrets | 테스트 계정 이메일 |
| `E2E_USER_PASSWORD` | Secrets | 테스트 계정 비밀번호 |
| `E2E_ENABLED` | **Variables** | `true` |

---

## 자주 하는 실수

| 실수 | 결과 | 방지 |
|---|---|---|
| `.env.local`을 git add | 시크릿 유출 | `.gitignore`에 `.env.local` 확인 |
| 프로덕션 키를 로컬에서 사용 | 실수로 프로덕 DB 조작 | 로컬은 항상 dev/test 키 사용 |
| `--clear-secrets` 없이 env_vars만 적용 | 기존 Secret Manager reference와 타입 충돌로 배포 실패 (PR #23 사고) | `deploy.yml`에서 `--clear-secrets` 사전 호출 |
| R2 Secret Access Key 재발급 없이 분실 | 재발급 필요 | 발급 직후 즉시 GitHub Secret에 저장 |
