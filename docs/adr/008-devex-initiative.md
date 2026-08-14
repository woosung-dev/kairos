# ADR-008: DevEx 이니셔티브 — E2E 테스트 + BE 배포 자동화

> **날짜:** 2026-04-23
> **상태:** Accepted — **배포 자동화 부분은 2026-08-14 ADR-028 로 대체됨**
> (Cloud Run + WIF + Artifact Registry 철거, 오라클 셀프호스팅 + 수동 배포로 전환).
> E2E 테스트 부분은 유효하다.
> **작성자:** Claude Opus 4.7 (1M context)
> **관련:** ADR-002(실행 전략), ADR-006(UI/UX 개편), Sprint 4(배포 인프라), ADR-028(셀프호스팅)

---

## 배경

Sprint 1~5 + ADR-006 + 온보딩 직전 릴리즈 스프린트까지 완료했으나, 2026-04-22 BE 수동 배포 시도에서 연쇄 장애를 관찰했다.

- `gcloud run deploy` 명령에 `--port 8000` 누락 → 기본값 8080으로 리셋 → health check 실패
- 재시도 시 env 8개 누락 → Pydantic `ValidationError` → 컨테이너 크래시
- 원인 역추적 결과: **prod BE가 2026-04-11 이후 13일간 구코드로 남아 있었음**이 드러남. 구 revision은 `cloud-run-source-deploy/kairos-api` 이미지 + `KAIROS_*` prefix env 기반이라 현재 repo 코드(`da33af5` 이후)와 env 스키마 자체가 다름.

즉 **"배포 진실이 어디에 있는지 코드와 클라우드 양쪽 모두에서 애매한 상태"** 가 누적되었다. 한 번의 수동 배포에 숨은 지식이 너무 많이 필요하고, 그 지식이 문서화되어 있지 않으면 매 배포가 디버깅 세션으로 변질된다.

동시에 E2E 테스트 인프라가 전무하다. 단위 테스트(BE 65, FE typecheck)는 있지만 Capture→Distill→Express 전체 체인이 깨지지 않는지 검증할 자동 수단이 없다. 내부 5명 온보딩을 앞둔 상황에서 회귀 감지 장치가 없으면 온보딩 중 발생하는 버그를 실사용자가 먼저 발견하게 된다.

## 결정

**DevEx 강화를 온보딩 이전 다음 마일스톤으로 삼는다.** 두 축으로 구성한다.

### 1. E2E 테스트 — Playwright 기반

- **선택 이유:** Next.js 16 + React 19 + Clerk 환경에서 신뢰할 수 있는 브라우저 자동화 도구. Cypress보다 Chromium/Firefox/WebKit 병렬 실행 지원이 강하고, trace viewer가 CI 디버깅에 유리.
- **범위 (이 이니셔티브):** 골든패스 2개.
  - **GP1 — 홈 · 네비게이션 렌더:** 테스트 계정 로그인 → `/dashboard` 렌더 → Today 피드 섹션 존재 확인 → 사이드바 프로젝트 클릭 → 프로젝트 대시보드 렌더.
  - **GP2 — RAG + 소스 뷰어:** 프로젝트 페이지에서 질문 입력 → 응답 스트리밍 수신 → `[1]` 클릭 → Source Viewer 열림.
- **범위 외 (이연):** 업로드 → STT → Inbox 전체 체인 (테스트 파일 준비와 비동기 대기 시간 리스크 때문). 초대 플로우. Cmd+K 키보드 내비게이션.
- **인증 전략:** Clerk의 **Testing Tokens**([docs](https://clerk.com/docs/testing/overview))를 사용해 실제 Clerk dev 인스턴스에 자동 로그인. 테스트 계정 1개를 사전 프로비저닝하고, Clerk API 키는 `CLERK_TESTING_TOKEN_API_KEY` env로 주입. 로컬 스토리지 + 쿠키 세션을 Playwright `storageState`로 재사용해 매 테스트 반복 비용을 낮춘다.
- **BE 대상:** 로컬 BE(8001 권장) 또는 프로덕 BE. 기본값은 프로덕 BE — 실제 스키마 드리프트까지 검출. 로컬 BE는 옵션(`TEST_API_URL` env).
- **네트워크 모킹:** GP2에서 RAG SSE 응답은 **모킹하지 않음**. 실제 RAG 호출이 성공하는지 자체가 검증 대상. 대신 Semantic Cache 적중용 고정 질문("이번 주 회의 요약")을 사용해 비용·시간을 절감.
- **CI 통합:** `test.yml`에 `e2e` 잡 추가. 기본은 `main` push와 PR에 대해 실행. 실패 시 `trace.zip`을 artifact로 업로드.

### 2. BE 배포 자동화 — GitHub Actions + Secret Manager

- **트리거:** `main` 브랜치 push. 수동 실행도 허용(`workflow_dispatch`).
- **이미지 빌드:** GitHub Actions에서 `docker buildx` 로 `linux/amd64` 플랫폼 빌드 후 Artifact Registry 푸시. 태그는 `latest` + `commit-sha` 두 가지.
- **인증:** **Workload Identity Federation(WIF)** 방식 채택. Service Account JSON 키를 GitHub Secret에 저장하는 방식은 키 유출 리스크 + 순환 비용이 크므로 회피.
- **Secret 관리:** Cloud Run env를 **모두 Secret Manager 참조로 이관**. 배포 시 `--set-secrets` 플래그로 주입. 평문 env는 `APP_ENV`, `LOG_LEVEL`, `CORS_ORIGINS`, `FRONTEND_URL` 네 개만 유지.
- **이관 대상 secrets(9개):**
  - `database-url` (이미 있음, 재사용)
  - `clerk-secret-key` (신규)
  - `clerk-webhook-secret` (신규)
  - `r2-account-id` (신규)
  - `r2-access-key-id` (신규)
  - `r2-secret-access-key` (신규)
  - `r2-bucket-name` (신규)
  - `gemini-api-key` (이미 있음, 재사용)
  - `openai-api-key` (신규)
- **배포 명령(워크플로 내):**
  ```bash
  gcloud run deploy kairos-api \
    --image asia-northeast3-docker.pkg.dev/$PROJECT/kairos/api:$SHA \
    --region asia-northeast3 \
    --port 8000 \
    --set-env-vars="APP_ENV=production,LOG_LEVEL=INFO,CORS_ORIGINS=$CORS,FRONTEND_URL=$FE" \
    --set-secrets="DATABASE_URL=database-url:latest,CLERK_SECRET_KEY=clerk-secret-key:latest,..." \
    --quiet
  ```
  **`--port 8000`을 명시적으로 박아서 2026-04-22 실수를 예방한다.**
- **롤백:** 실패한 revision은 트래픽 0%로 자동 격리된다(Cloud Run 기본 동작). 수동 롤백은 `gcloud run services update-traffic kairos-api --to-revisions=<prev>=100`.

### 3. 범위 외

- FE 배포(Vercel)는 이미 GitHub push 자동 배포되고 있어 본 이니셔티브 대상 아님.
- Blue/Green, Canary 전략은 트래픽 규모가 커질 때 재검토.
- Migration 자동 실행은 이미 Dockerfile CMD에서 `alembic upgrade head` 가 처리. 별도 step 불필요.
- DB 마이그레이션 롤백 자동화는 이연 (수동 `alembic downgrade -1` 유지).

## 결과

- 한 번 배포할 때 암묵지로 유지되던 `--port 8000`, env 9개, Secret Manager 설정이 **YAML 한 곳**에 박힘. 매번 재학습 비용 0에 수렴.
- 내부 온보딩 이전에 E2E 골든패스 2개가 CI에서 돌기 시작 → 회귀 조기 감지.
- `.env.example` 이 현재 config.py와 일치하도록 동기화. 신규 합류자의 로컬 셋업 마찰 제거.

## 비용 / 리스크

- Clerk Testing Tokens 설정에 1~2시간 예상. 가짜 이메일로 dev 인스턴스 계정 1개 생성하고 API 키를 GitHub Secret에 등록 필요.
- WIF 초기 설정은 GCP 콘솔 작업이 필요하다(Service Account + Workload Identity Pool + Provider + Binding). 본 ADR에서는 명령 시퀀스를 `docs/guides/deployment.md`에 문서화한다.
- E2E 테스트가 프로덕 BE를 치면 프로덕 DB에 더미 레코드가 쌓일 수 있다. 완화: 테스트 전용 워크스페이스 사용 + 테스트 종료 후 cleanup step.

## 검증 기준

- [ ] `pnpm e2e` 가 로컬에서 2개 골든패스 통과 (< 60초)
- [ ] `.github/workflows/test.yml` 의 `e2e` 잡이 PR #7 기준 성공
- [ ] `deploy.yml` 이 수동 실행(`workflow_dispatch`)으로 정상 배포 가능 — 최소 1회 실제 수행
- [ ] `docs/guides/deployment.md` 가 WIF 초기 설정 + Secret Manager 이관 스크립트 포함
- [ ] `backend/.env.example` 이 `config.py` 의 모든 필수 필드를 포함

## 후속

- 본 이니셔티브 완료 후 **L3 프로젝트 인사이트(ADR-007 적용)** 을 다음 마일스톤으로 본다.
- Sprint 6(프로젝트 멤버십/Private)은 내부 5명 온보딩 피드백 이후 스코프 확정.
