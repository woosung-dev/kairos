# Sentinel QA 페르소나 최종 보고서

> Sprint 25 Multi-Agent QA — Sentinel 페르소나 결과
> 작성: 2026-05-21 (KST), session: cosmic-knitting-island
> sub-agent ID: a35c7f6ded9b48474
> **정정**: BUG-SENTINEL-006(CORS)는 잘못된 FE URL 가정에 기반한 false-positive였음 — 메인 세션 검증으로 확인 후 본 보고서 갱신

## 1. Executive Summary

- 프로덕션 BE `/api/v1` 의 비인증/위조 토큰 차단은 전반 PASS. RAG visibility 3-layer + tenant boundary 검증 코드 정합 양호 (Codex F-2 fix 반영 확인).
- **Critical 1건 — `POST /api/v1/users/sync` 가 인증/Svix 서명 없이 임의 사용자 생성·email/display_name 덮어쓰기 허용**. PoC 실측 200 OK + 더미 user 생성 성공 (`[QA-2026-05-21]` prefix).
- ~~High 1건 — CORS allowlist 누락~~ → **false-positive 정정**: sub-agent가 잘못 가정한 `kairos.vercel.app`(Kairos 아닌 다른 사이트)에 대해서만 차단되었고, 실제 FE URL `kairos-zeta-ebon.vercel.app`은 preflight/GET 모두 정상 200 + 헤더 echo 통과. 메인 세션 정정 검증 완료.
- **High 1건 — `POST upload/file` 프록시: 파일 크기·MIME·확장자 검증 누락**. 메모리 DoS + 위장 파일 R2 적재 가능.
- Medium/Low 3건 (max_length 누락, ready latency, Swagger 노출). BL-068/069는 carry-over 유지, 정적 분석은 정합.

## 2. 환경 정보

| 항목 | 값 |
|------|-----|
| FE | https://kairos-zeta-ebon.vercel.app (자동탐색 가정 `kairos.vercel.app`은 잘못된 URL — 정정됨) |
| BE | https://kairos-api-imrsiyibaa-du.a.run.app |
| API base | `/api/v1` |
| Health | `/api/v1/health` → 200 (0.09s) |
| Ready | `/api/v1/ready` → 200 (1.14~2.00s) |
| Swagger | `/api/v1/docs` → 200 (공개) |
| OpenAPI | `/api/v1/openapi.json` → 200 |
| 검증 시간 | 약 55분 |
| 검증 방법 | API curl + 정적 코드 분석 (Playwright MCP 점유 중으로 브라우저 자동화 불가) |

## 3. 시나리오별 결과

| ID | 시나리오 | 결과 | 결함 |
|----|----------|------|------|
| S1 | RAG visibility 3-layer + cache IDOR | **PARTIAL** | ~~BUG-SENTINEL-006~~ (false-positive 정정) |
| S2 | Workspace switcher + Memory promote | **PARTIAL** | (BL-068/069 carry-over) |
| S3 | 오디오 chunking 파이프라인 (입력 검증) | **FAIL** | BUG-SENTINEL-003, BUG-SENTINEL-004 |
| S4 | Onboarding step 0→4 e2e | **FAIL** | BUG-SENTINEL-005 (Critical) |
| S5 | 부수 발견 | INFO | BL-SNT-CANDIDATE-A/B |

## 4. 결함 상세

### BUG-SENTINEL-005 — `POST /api/v1/users/sync` 인증·서명 검증 부재 (계정 위장)
- **분류**: Critical · **Confidence**: H · **발견 시간**: T+38min
- **엔드포인트**: `POST /api/v1/users/sync`
- **재현 절차**:
  1. `curl -X POST https://kairos-api-imrsiyibaa-du.a.run.app/api/v1/users/sync -H 'Content-Type: application/json' -d '{"data":{"id":"user_QA20260521_sentinel_test_doNotUse","email_addresses":[{"email_address":"qa-sentinel-2026-05-21@kairos.test"}],"first_name":"[QA-2026-05-21]","last_name":"Sentinel"}}'`
  2. 응답: `HTTP 200 {"synced":true}` (실측)
- **기대 동작**: Svix(Clerk webhook) 서명 검증 후 통과, 미서명은 401/403
- **실제 동작**: 임의 페이로드로 User row 생성/덮어쓰기 통과
- **Root cause**: `backend/src/auth/router.py:18-43` `sync_user` 핸들러에 `Depends`(인증 기본 의존성) 없음 + `# TODO: Svix 서명 검증 추가` 미구현. `AuthService.sync_user`는 기존 user를 `clerk_id` 일치로 찾으면 email/display_name/avatar_url 무조건 덮어쓴다(`service.py:48-50`).
- **공격 시나리오**:
  - 무작위 clerk_id로 무한 user 생성 → DB pollution + observability 비용 증가
  - victim의 clerk_id를 알면(또는 `get_me` 응답에서 노출됨) email/display_name 임의 덮어쓰기 → UI 표시 위변조
- **회귀 위험도**: H — `# TODO` 마커가 있는 상태로 production 배포.
- **사용자 의도적 결정 (2026-05-21, memory `project_gcp_migration_jetaime_dev_done.md`)**: Clerk Production 인스턴스 미발급 + Clerk webhook 갱신 SKIP. 등록된 endpoint는 옛 로컬 ngrok URL이고 path `/api/webhooks/clerk`도 backend `/api/v1/users/sync`와 불일치 (webhook 안 쓰는 상태).
- **권고 (사용자 확정 방향)**: **endpoint 비활성화(404 반환)** — Svix 검증 추가는 webhook 안 쓰는 상태에서 무의미. `backend/src/auth/router.py`에서 `sync_user` 핸들러 제거 또는 410 Gone 반환. `backend/src/main.py:132 app.include_router(auth_router)` 의존 함수 정리.

### ~~BUG-SENTINEL-006~~ — false-positive 정정
- **상태**: REJECTED (메인 세션 검증으로 정정)
- **원래 가설**: 프로덕션 BE CORS allowlist에서 FE origin 누락
- **정정 근거**:
  1. sub-agent가 자동탐색의 `kairos.vercel.app` (영어, theme #00CEE8 — Kairos 아닌 별개 사이트)을 FE로 가정
  2. 실제 FE URL은 `https://kairos-zeta-ebon.vercel.app` (Cloud Run env `CORS_ORIGINS`에 정확히 설정됨)
  3. 메인 세션 재검증: `OPTIONS` preflight HTTP 200 + `access-control-allow-origin: https://kairos-zeta-ebon.vercel.app` echo, GET HTTP 200 + 동일 헤더 echo
- **교훈 (Sprint 25 process improvement)**: Phase 0 자동탐색에서 FE URL 추정 결과를 사용자에게 확인받지 않고 진행하면 페르소나가 잘못된 환경으로 검증한다. environment.txt에 실제 URL 명시적 기록 절차 강화.

### BUG-SENTINEL-003 — `POST upload/file` 프록시 입력 검증 부재
- **분류**: High · **Confidence**: H · **발견 시간**: T+27min
- **엔드포인트**: `POST /api/v1/workspaces/{wid}/upload/file`
- **재현 절차**: 정적 분석 (`backend/src/upload/router.py:42-56`) — `file.content_type or "application/octet-stream"`으로 클라이언트 제공 헤더 그대로 신뢰. 크기/확장자 화이트리스트 없음. `await file.read()`로 전체 바이트를 RAM에 로드.
- **기대 동작**: 0byte → 400 reject / MIME 화이트리스트 / 최대 크기 cap (예: 500MB) / 확장자 화이트리스트
- **실제 동작**: 모든 검증 누락
- **회귀 위험도**: M — Sprint 15 audio chunking BL-T2-003 관련. 메모리 DoS / 위장 mime / 의도 외 파일 적재 가능.
- **권고**: ① pydantic-multipart size limit ② python-magic 또는 sniff로 실제 MIME 추출 + 화이트리스트 ③ `MAX_UPLOAD_BYTES` env

### BUG-SENTINEL-004 — `CaptureTextRequest.transcript_text` max_length 누락
- **분류**: Medium · **Confidence**: H · **발견 시간**: T+33min
- **엔드포인트**: `POST /api/v1/workspaces/{wid}/meetings/capture`
- **재현 절차**: 정적 (`backend/src/meetings/schemas.py:28-32`) — `Field(alias="transcriptText", min_length=50)`. **max_length 없음**.
- **기대 동작**: 합리적 cap (예: 200_000 chars ≈ Gemini 8k token cushion 5배)
- **실제 동작**: 무제한 입력 가능 → Gemini API 호출 비용 폭증 + AI 처리 timeout 위험
- **권고**: `max_length=200_000` 추가

### BL-SNT-CANDIDATE-A — `/api/v1/ready` 1.1~2.0s 지연
- **분류**: Medium · **Confidence**: M
- **재현**: 3회 연속 RTT 1.14/1.19/1.36s. cold start 아닌 warm 상태에서도 일관 지연.
- **가설**: ready check가 매 호출마다 새 asyncpg connection 발급/ping
- **권고**: connection pool reuse 또는 lightweight ping(`SELECT 1`)

### BL-SNT-CANDIDATE-B — Swagger `/api/v1/docs` 프로덕션 노출
- **분류**: Low · **Confidence**: M
- **재현**: `curl https://kairos-api-imrsiyibaa-du.a.run.app/api/v1/docs` → 200 HTML
- **권고**: production 환경에서 `docs_url=None, redoc_url=None` 또는 admin auth 게이트

### BL-068 / BL-069 carry-over (정적 정합 PASS)
- 둘 다 Sprint 23 D1/D3 fix가 현 코드에 반영되어 정적 분석 PASS. Playwright e2e Clerk 인프라 도입 시 동반 verify 필요(Sprint 25+).

## 5. Composite Sentinel Score

가중치: S1 30% · S2 20% · S3 25% · S4 25%

| ID | 결과 | Score | 가중 |
|----|------|-------|------|
| S1 | PARTIAL (CORS 정정) | 7.0 | 2.10 |
| S2 | PARTIAL | 6.0 | 1.20 |
| S3 | FAIL | 3.5 | 0.875 |
| S4 | FAIL (Critical) | 1.5 | 0.375 |

**Composite Sentinel = 4.55 / 10** (BUG-006 정정 후 +0.30)

## 6. 후속 권고 (Sprint 25 우선순위)

| 순위 | 항목 | 예상 공수 | 의존 |
|------|------|-----------|------|
| P0 | BUG-SENTINEL-005 sync_user 비활성/Svix 검증 | 2h | — |
| ~~P0~~ | ~~BUG-SENTINEL-006 CORS~~ → false-positive 정정 | — | — |
| P1 | BUG-SENTINEL-003 upload/file 입력 검증 | 4h | — |
| P1 | BUG-SENTINEL-004 max_length 추가 | 0.5h | — |
| P2 | BL-SNT-CANDIDATE-A ready latency 개선 | 2h | — |
| P2 | BL-SNT-CANDIDATE-B Swagger prod 차단 | 0.5h | — |
| P3 | Playwright + Clerk e2e 인프라 (BL-068/069 동반) | 8-12h | — |

## 7. 검증 한계 / 잔여 리스크

- Playwright MCP 점유 중으로 실 브라우저 자동화 미진행 → workspace switcher UI · onboarding step transition UI · RAG SSE 실 cache hit 동작은 미실증.
- Owner/Viewer JWT 미획득 → IDOR 실증, cache hit 시 visibility filter 실증 모두 정적 분석에 의존.
- 4h 오디오 실 업로드은 abuse 우려로 미수행.
- **데이터 오염**: BUG-SENTINEL-005 PoC 산출물로 production DB에 더미 user 1건 생성됨
  - `clerk_id=user_QA20260521_sentinel_test_doNotUse`
  - `email=qa-sentinel-2026-05-21@kairos.test`
  - **정리 권고**: 검증 종료 시 Neon SQL editor에서 `DELETE FROM users WHERE clerk_id='user_QA20260521_sentinel_test_doNotUse'` 실행

## 8. 핵심 파일 경로

| 파일 | 라인 | 관련 결함 |
|------|------|-----------|
| `backend/src/auth/router.py` | 18-43 | sync_user 핸들러 (BUG-005) |
| `backend/src/auth/service.py` | 31-53 | sync_user 서비스 |
| `backend/src/main.py` | 65-82 | CORS 미들웨어 (BUG-006) |
| `backend/src/core/config.py` | 15-16 | `cors_origins` env |
| `backend/src/upload/router.py` | 42-56 | upload/file 프록시 (BUG-003) |
| `backend/src/meetings/schemas.py` | 28-32 | CaptureTextRequest (BUG-004) |
| `backend/src/rag/router.py` + `pipeline_service.py` | — | visibility/tenant gate (PASS 근거) |
| `backend/src/auth/rbac.py` | — | RoleChecker (PASS 근거) |
