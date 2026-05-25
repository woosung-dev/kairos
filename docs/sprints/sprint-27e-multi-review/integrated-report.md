# Sprint 27e — 4-Reviewer Multi-Agent Audit 통합 보고서

> Sprint 27d (product/UX 6 agent audit, GO 8.02/10) 후속 **기술 deep audit**. 보안 / 성능 / 테스트커버리지 / 아키텍처 4 전문 reviewer 가 Personal + Team 2 시나리오 모두 검증.
>
> baseline commit: `1b24898` (main, Sprint 27d 완료) · 작업 branch: `sprint-27e/multi-review` · 검사 일시: 2026-05-25 KST · 환경: 로컬 FE/BE down → 정적 분석 + pytest/vitest + dependency audit · production/Sentry/Clerk Production audit SKIP (사용자 정책)

---

## 0. Fix Status (post-audit, 2026-05-25 KST)

audit 후 차단 6건 모두 fix 적용 완료 → **NEEDS-FIX → GO (외부 5명 dogfooding 진입 또는 production 진입 unlocked)**.

| ID | 상태 | commit-level 적용 |
|---|---|---|
| BUG-S27e-SEC-1 | ✅ RESOLVED | `pnpm up @clerk/nextjs@^7.2.1` → 7.4.1 (GHSA-vqx2-fgx2-5wq9 사라짐) |
| BUG-S27e-SEC-2 | ✅ RESOLVED | `pnpm up next@^16.2.5` → 16.2.6 (middleware bypass + SSRF advisory 사라짐) |
| BUG-S27e-SEC-3 | ✅ RESOLVED | `core/config.py` + `auth/dependencies.py` 의 jwt.decode 에 issuer + audience 명시 + production validator |
| BUG-S27e-SEC-4 | ✅ RESOLVED | `core/config.py` field_validator — production + dev fallback 평문 거부 |
| BUG-S27e-TEST-1 | ✅ RESOLVED | BE `tests/test_security_hardening.py` 2 case append + FE `e2e/tests/security-headers.spec.ts` 신설 |
| BUG-S27e-TEST-2 | ✅ RESOLVED | BE `tests/auth/test_personal_workspace_race_concurrent.py` 신설 (asyncio.gather N=5/10 race) |

**검증 결과**:

- backend pytest: **482 PASS / 1 skip** (이전 469 PASS 에서 +13 신규 — config 5 + JWT 4 + security headers 2 + concurrent race 2)
- frontend vitest: **56 PASS** (변경 없음)
- frontend typecheck: **PASS** (tiptap transitive 버전 충돌 type 경고 — BL-S27e-D PERF-11 dynamic import 동반 처리)
- frontend build: **PASS**
- `pnpm audit --audit-level critical`: **0 critical** (SEC-1/2 advisory 사라짐). `--audit-level high`: 2 high (fast-uri transitive — **Round 2 errata 정정**: Sentry 가 아닌 `shadcn@4.1.2 > @modelcontextprotocol/sdk@1.29.0 > ajv > fast-uri` 경로. shadcn devDependencies 이동으로 해소 가능, BUG-S27e-SEC-r2-1/r2-5 참조)

---

## 1. Executive Summary

### audit 시점 Verdict — **NEEDS-FIX** → fix 후 **GO**

| GO 조건 (SCOPE) | 기준 | 측정 | 판정 |
|---|---:|---:|---|
| 차단 (Blocking) 결함 | **0건** | **6건** | **FAIL** |
| OWASP top 10 carry | ≤ 3건 (각 P2 이하) | 7건 (P0×2 + P1×2 + P2×3 + P3×4 중 P2 이하 = 7건) → **8 항목 중 P2/P3 7건** | (carry side OK, but P0/P1 4건이 차단) |
| 성능 critical path p95 | RAG ≤ 15s / API ≤ 500ms / 회의 ≤ 60s | **실측 SKIP** (환경 미실행) — 정적 추정 모두 헤드룸 작음 (RAG 4-12s, 회의 30-60s) | UNKNOWN |
| 테스트 커버리지 | 신규 기능 cover ≥ 80% / 통합 핵심 5/5 | **72.7% (8/11) / 3/5** | **FAIL** |
| 헌법 정합성 | CONTEXT-MAP + ADR-* 위반 0 | 7건 (P1 1 + P2 3 + P3 3, 차단 0) | (차단 0, doc stale carry) |

→ **GO 조건 4/4 중 1건 충족 (헌법, 차단 0)**. **production 진입 또는 외부 5명 dogfooding 진입 전 차단 6건 fix 필수**.

### 차단/비차단 분류

| | P0 | P1 | P2 | P3 | **합계** |
|---|---:|---:|---:|---:|---:|
| **차단 (Blocking)** | 4 (SEC-1/2, TEST-1/2) | 2 (SEC-3/4) | 0 | 0 | **6** |
| 비차단 (Non-blocking, BL carry) | 0 | 7 (PERF-1~5 + TEST-3 + ARCH-1) | 11 (SEC-5~7 + PERF-6~11 + TEST-4~7 + ARCH-2/3/4/6) | 11 (SEC-8~11 + PERF-12~15 + TEST-8~10 + ARCH-5/7) | 37 (요청자 측 사후 정량 — TEST-8/9/10 P2 가 일부 P1 carry 와 중첩 가능) |

### 가장 critical 3건 (전체 audit)

1. **BUG-S27e-SEC-1** — `@clerk/nextjs@7.0.8` middleware route protection bypass (critical CVE GHSA-vqx2-fgx2-5wq9). `frontend/src/proxy.ts:15-19` 의 `clerkMiddleware + auth.protect()` 패턴이 advisory 직격. **fix = `pnpm up @clerk/nextjs@^7.2.1` 1줄**. 외부 5명 진입 시 인증 우회 가능 → 모든 protected route 노출. **차단**.
2. **BUG-S27e-SEC-4** — `cron_secret_token` 평문 기본값 fallback (`backend/src/core/config.py:39`). production env 미설정 1회 누락 시 누구나 `POST /api/v1/admin/memory/r2-cleanup?days=365` 호출 가능 → 전체 사용자 voice 메모 R2 무차별 삭제 (audit log 없음). **fix = default 제거 + lifespan validator**. 단일 사용자가 다인 데이터 파괴 가능 → **차단**.
3. **BUG-S27e-TEST-1** — Sprint 27d BUG-S27d-4 보안 헤더 4종 fix 의 **회귀 가드 0건** (`backend/src/main.py:103-108` + `frontend/next.config.ts:5-15`). middleware reorder / next.config.ts 정리 시 헤더 누락이 CI 에서 감지 불가. 27d 의 fix 가 1 PR 만에 회귀 가능 → **차단**.

---

## 2. 4 Reviewer 별 발견 매트릭스 (전체 통합)

심각도 + 차단 우선순위. file:line + 권장 fix 는 각 reviewer 산출물 참조.

| ID | Reviewer | OWASP / 영역 | 심각도 | 차단 | 시나리오 | file:line | 발견 요약 | 권장 fix |
|---|---|---|:-:|:-:|:-:|---|---|---|
| **BUG-S27e-SEC-1** | 보안 | A06 deps CVE | **P0** | **YES** | both | `frontend/package.json` `@clerk/nextjs@7.0.8` | Clerk middleware route protection bypass (critical, GHSA-vqx2-fgx2-5wq9). `proxy.ts:15-19` 직격. | `pnpm up @clerk/nextjs@^7.2.1` |
| **BUG-S27e-SEC-2** | 보안 | A06 deps CVE | **P0** | **YES** | both | `frontend/package.json` `next@16.2.2` | Next.js 다중 high CVE (Middleware/Proxy bypass + SSRF + DoS + cache poisoning), patched 16.2.5. | `pnpm up next@^16.2.5` |
| **BUG-S27e-SEC-3** | 보안 | A02/A07 | **P1** | **YES** | both | `backend/src/auth/dependencies.py:111-124` | Clerk JWT 검증에서 `verify_aud=False` + issuer 검증 누락. ADR-024 cutover 직격. | `audience=` + `issuer=` 명시 + JWKS URL 환경별 분리 |
| **BUG-S27e-SEC-4** | 보안 | A05 | **P1** | **YES** | both | `backend/src/core/config.py:39` | `cron_secret_token` 평문 fallback `"dev-cron-secret-CHANGE-ME-IN-PROD"`. env miss 시 R2 voice 메모 전수 삭제 가능. | default 제거 + lifespan validator |
| **BUG-S27e-TEST-1** | 테스트 | 신규 기능 회귀 가드 | **P0** | **YES** | both | `backend/src/main.py:103-108` + `frontend/next.config.ts:5-15` | Sprint 27d BUG-S27d-4 보안 헤더 4종 fix 의 회귀 가드 0건. middleware reorder 시 누락 감지 불가. | BE pytest 2 case + FE e2e `security-headers.spec.ts` 1 spec |
| **BUG-S27e-TEST-2** | 테스트 | 에지 race | **P0** | **YES** | Personal | `backend/tests/auth/test_personal_workspace_race.py` (주석 명시) | BL-S27c-1 lazy seed 의 진정한 concurrent race (별개 connection asyncio.gather) 미검증. 현재 spec 은 "sequential 만 검증" 자체 주석. | `asyncio.gather` 진정한 동시성 integration 테스트 |
| BUG-S27e-PERF-1 | 성능 | 리소스 | P1 | NO | both | `backend/src/common/r2.py:14,27,55,73,87` + `memory/service.py:636,654` | aioboto3 client + S3 client 가 매 호출마다 재생성 (BL-008 carry) | R2Service singleton `_ensure_client()` + lifespan teardown |
| BUG-S27e-PERF-2 | 성능 | DB | P1 | NO | both | `meetings/models.py:17` + `actions/models.py:32` + `inbox/models.py:22` | `workspace_id` 인덱스 누락 (ListBy queries seq scan) | 3 alembic composite covering 인덱스 |
| BUG-S27e-PERF-3 | 성능 | sync blocking | P1 | NO | both | `backend/src/upload/router.py:91` + `common/r2.py:62` | `await file.read()` 500MB OOM 위험 (concurrent 5×500MB = 2.5GB > Cloud Run 1-2GB) | SpooledTemporaryFile → boto3 `upload_fileobj` streaming |
| BUG-S27e-PERF-4 | 성능 | AI | P1 | NO | both | `services/ai_processing.py:81,127,151` + `memory/service.py:682` | Gemini `generate_content` timeout 0 + retry 0 + circuit breaker 0 | `asyncio.wait_for(timeout=30)` + tenacity + half-open circuit breaker |
| BUG-S27e-PERF-5 | 성능 | SSE 리소스 | P1 | NO | both | `rag/router.py:30-42` + `rag/service.py:166-172` | SSE `event_generator()` `request.is_disconnected()` 체크 없음 → 클라이언트 close 후 Gemini 토큰 끝까지 소진 | `await request.is_disconnected()` per-yield check |
| BUG-S27e-ARCH-1 | 아키텍처 | I-1 | P1 | NO | both | `backend/src/onboarding/service.py:18-34` + `repository.py:14` | OnboardingService 가 AsyncSession 직접 보유 + raw `text()` SQL 실행 — I-1 명백 위반 | Repository 경유 + typed `select(User.onboarding_step)` + `session.exec()` |
| BUG-S27e-TEST-3 | 테스트 | 정량 | P1 | NO | FE | `frontend/vitest.config.ts` `coverage.include` 미설정 | FE 171 source 파일 vs unit test 6 파일 — 실 cov < 6% (구조적 갭) | `coverage.include: ['src/**']` + service/util/store unit |
| BUG-S27e-TEST-4 | 테스트 | 정량 | P1 | NO | BE | `workspaces` 모듈 branch 4% | invite_service / member role branch case 부족 | invite_service branch 검증 |
| BUG-S27e-TEST-5 | 테스트 | 통합 | P1 | NO | Team | invite accept happy-path 갭 | 생성 → 공유 → 수락 → role 부여 e2e | `invite-accept.spec.ts` 신설 |
| BUG-S27e-TEST-6 | 테스트 | 통합 | P1 | NO | both | 회의 retry (M-3 carry) | failed → 재처리 e2e | `meeting-retry.spec.ts` |
| BUG-S27e-TEST-7 | 테스트 | 신규 기능 | P1 | NO | both | upload mime e2e | proxy + presigned 양쪽 e2e | `upload-mime-rejection.spec.ts` |
| BUG-S27e-SEC-5 | 보안 | A09 | P2 | NO | Team | `workspaces/invite_service.py:159-204` + `member_router.py` | role 변경 / member remove / invite create audit log 부재 | `audit_events` 테이블 + 4 endpoint hook |
| BUG-S27e-SEC-6 | 보안 | A04 | P2 | NO | both | 전 router | rate limit 0건 | slowapi (RAG ≤ 30/min, upload ≤ 10/min) |
| BUG-S27e-SEC-7 | 보안 | A05 | P2 | NO | both | `backend/src/main.py:89-95` | CORS allow_methods + allow_headers wildcard | 메서드/헤더 화이트리스트 |
| BUG-S27e-PERF-6 | 성능 | 캐싱 | P2 | NO | Team | `meetings/service.py:516` + `notes/service.py:469` + `embeddings/repository.py:460` | promote BG 의 ws 전체 SemanticCache wipe | scoped invalidation (`sources::jsonb @>`) |
| BUG-S27e-PERF-7 | 성능 | 캐싱 | P2 | NO | both | `memory/models.py:128-142` | `MemoryQueryEmbeddingCache` 만료 row 정리 cron 없음 → 무한 누적 | 7일 cleanup cron + partial expression index |
| BUG-S27e-PERF-8 | 성능 | DB | P2 | NO | both | `embeddings/repository.py:209-214` | `embedding_chunks.created_at` 인덱스 없음 (time_range filter latency) | partial expression index |
| BUG-S27e-PERF-9 | 성능 | N+1 | P2 | NO | both | `inbox/service.py:100-104` | `for project_id in project_ids: find_by_id(...)` N+1 | `find_by_ids_in_workspace(IN clause)` |
| BUG-S27e-PERF-10 | 성능 | FE | P2 | NO | FE | `frontend/src/app/layout.tsx:23-45` | 3 외부 font CDN — `next/font` 미사용, FOUT/CLS | `next/font/local` self-host |
| BUG-S27e-PERF-11 | 성능 | FE | P2 | NO | FE | `frontend/src/features/notes/components/note-detail.tsx:9-10` 등 | tiptap + dnd-kit 정적 import | `next/dynamic({ ssr: false })` |
| BUG-S27e-ARCH-2 | 아키텍처 | DIP | P2 | NO | BE | `backend/src/services/transcription.py:14` | `from src.meetings.models import TranscriptSegment` — services 가 meetings 역의존 | services 내 DTO + 호출자 ORM 변환 |
| BUG-S27e-ARCH-3 | 아키텍처 | Layered | P2 | NO | BE | `backend/src/common/audit_router.py:14,18` + `promote_helpers.py:173` | common 이 auth.rbac + workspaces.models 상위 import | `backend/src/audit/` 신설 (16 모듈) |
| BUG-S27e-ARCH-4 | 아키텍처 | Atomic Update | P2 | NO | docs | `CONTEXT-MAP.md:43,60` + `docs/architecture/directory-map.md` | "BE 13 모듈 + FE 11 features" stale (실재 BE 15 + FE 14) | 헌법 + directory-map 갱신 |
| BUG-S27e-ARCH-6 | 아키텍처 | SOLID SRP | P2 | NO | BE | `rag/service.py:45` (192 LOC) 외 5 도메인 100+ LOC promote | promote 패턴 산재 + 100+ LOC SRP 위반 | `common/promote_helpers.py` 확장 (3 helper) |
| BUG-S27e-TEST-8 | 테스트 | 에지 | P2 | NO | both | 업로드 거대 입력 unit | 한도 1024 mock 만, 100MB 실 한도 미검증 | 보강 unit 케이스 |
| BUG-S27e-TEST-9 | 테스트 | 에지 | P2 | NO | both | 유니코드 (emoji + RTL) | 회의/노트/검색 유니코드 미검증 | unit 보강 |
| BUG-S27e-TEST-10 | 테스트 | 통합 | P2 | NO | both | Personal+Team 동시 운영 통합 | 시나리오 격리 누출 미검증 | 통합 테스트 |
| BUG-S27e-SEC-8 | 보안 | A03 | P3 | NO | both | `backend/src/common/prompts.py:99-115` | RAG `{sources}` 구분자 부재 (cross-tenant leak 은 visibility filter 가 차단, 영향 제한) | `<<<SOURCE_BLOCK>>>` 구분자 + system prompt 명시 |
| BUG-S27e-SEC-9 | 보안 | A04 | P3 | NO | both | `common/r2.py:23-46` + `upload/service.py:175-194` | `file_key` filename 무가공 (control char / RLO) | `_safe_filename()` + NFC + 길이 200 |
| BUG-S27e-SEC-10 | 보안 | A08 | P3 | NO | CI | `.github/workflows/r2-cleanup.yml` | `astral-sh/setup-uv@v3` SHA 미pin | 다른 yml 패턴으로 통일 |
| BUG-S27e-SEC-11 | 보안 | A09 (정책) | P3 | NO | both | `backend/src/main.py` (Sentry SKIP) | Sentry SKIP 상태 외부 5명 진입 forensic blind | `logging.warning(authz_failure)` + Cloud Run log alert |
| BUG-S27e-PERF-12 | 성능 | FE 캐싱 | P3 | NO | FE | `frontend/src/lib/query-client.tsx:12` | global `refetchOnWindowFocus` default true — 탭 전환 시 모든 query refetch | global false + 명시 곳 true + 도메인별 staleTime |
| BUG-S27e-PERF-13 | 성능 | 알고리즘 | P3 | NO | BE | `backend/src/embeddings/service.py:28-42` | `_chunk_text` 문장/문단 boundary 무시 (char count) | sentence boundary chunker |
| BUG-S27e-PERF-14 | 성능 | 알고리즘 | P3 | NO | BE | `rag/service.py:36-43` + 외 | onboarding hook 매 RAG/회의/note/project 생성 시 추가 commit | repo `increment` 변경 없을 때 commit skip / fire-and-forget BG |
| BUG-S27e-PERF-15 | 성능 | 리소스 | P3 | NO | BE | `memory/service.py:675-682` | GenAI/OpenAI client lazy import + recreate per task | lifespan singleton + DI 주입 |
| BUG-S27e-ARCH-5 | 아키텍처 | Demeter | P3 | NO | BE | `rag/service.py:38-41` | `RagService._advance_onboarding` 가 `embedding_repo.session` 우회 추출 | hook callable 주입 / ARCH-1 해소 시 자연 해결 |
| BUG-S27e-ARCH-7 | 아키텍처 | Atomic Update | P3 | NO | docs | `docs/refactoring-backlog.md:440-471` (BL-005) | BL-005 ★★★★★ P0 등재이나 Sprint 19 PR #1 C10 에서 이미 해소 (verified `self.repo.session.execute` 0 hit) | BL-005 "✅ 완료 (Sprint 19)" 마크 |

---

## 3. 중복 발견 사항 병합

| 통합 ID | reviewer 별 시각 | 단일 권장 fix |
|---|---|---|
| **R2 boto3 reuse (PERF-1 + 메모리 service 캡슐화 우회)** | 성능 = client 재생성 / 아키텍처 = `memory/service.py` 가 `R2Service._session` private 접근 (캡슐화 위반) | R2Service public API (`upload_with_key`) + singleton `_ensure_client()` — 두 시각 동시 해소 |
| **Atomic Update 회귀 (ARCH-4 + ARCH-7)** | 아키텍처 = BE/FE 모듈 수 stale + BL-005 stale | 헌법 §4.1/§4.3 + directory-map.md + refactoring-backlog 일괄 patch 1 PR |
| **보안 헤더 회귀 가드 (TEST-1 + SEC carry)** | 테스트 = 가드 0건 / 보안 = 27d 에서 PASS 이나 향후 회귀 risk | BE pytest 2 case + FE e2e spec 1건 동시 추가 |
| **lazy seed race (TEST-2 + BL-S27c-1 closeout)** | 테스트 = sequential 만 검증 / 보안 = ADR-022 SKIP 상태에서 forensic blind | `asyncio.gather` integration + audit log hook (SEC-5 와 함께) |

---

## 4. 리뷰어 간 충돌 해결

본 audit 에선 reviewer 간 명시적 충돌 0건. 잠재 충돌:

- **보안 SEC-6 rate-limit vs 성능 P12 staleTime**: rate-limit 도입 시 FE refetchOnWindowFocus 정책과 결합. → 본 sprint 우선순위 = **보안 > 아키텍처 > 테스트 > 성능** (SCOPE 명시). rate-limit 먼저 도입, FE staleTime 은 후속.
- **PERF-3 streaming upload vs SEC-9 filename 슬러그**: 둘 다 upload path 수정. → 동일 PR 에서 함께 fix 권고 (비차단, BL carry).

---

## 5. 차단 결함 fix 순서 권고 (사용자 결정 시 참고)

| 순서 | ID | 작업 | 예상 소요 | 위험 |
|:-:|---|---|:-:|---|
| 1 | SEC-1 + SEC-2 | `pnpm up @clerk/nextjs@^7.2.1 next@^16.2.5` + `pnpm build` + breaking change read | 30분-1h | Next 16.2.2→16.2.5 minor 안전, Clerk 7.0.8→7.2.1 minor 안전 |
| 2 | SEC-4 | `cron_secret_token` default 제거 + Settings validator + production startup assert | 30분 | 단순 (1 파일 + 1 test) |
| 3 | SEC-3 | JWT `audience=` + `issuer=` 명시 + Settings 추가 + 2 case test | 1h | Clerk JWT Templates 의 aud 값 확인 필요 |
| 4 | TEST-1 | BE pytest 2 case (`tests/test_security_hardening.py`) + FE e2e 1 spec (`security-headers.spec.ts`) | 1h | 단순 |
| 5 | TEST-2 | `asyncio.gather` integration race (`test_personal_workspace_race_concurrent.py`) | 1h | DB 별개 connection + barrier 패턴 |

**총 예상 ~ 4h**. PR 1개에 6 fix 묶음 가능.

---

## 6. 비차단 결함 carry 권고 (BL-S27e-* 등재)

37건 → BL 묶음 6개로 카테고리:

- **BL-S27e-A** (보안 hygiene): SEC-5 audit_events / SEC-6 rate-limit / SEC-7 CORS 화이트리스트 / SEC-11 logging.warning. ADR-022 재검토 동반.
- **BL-S27e-B** (보안 hardening): SEC-8 prompt injection 구분자 / SEC-9 filename slugify / SEC-10 GHA SHA pin.
- **BL-S27e-C** (성능 P1 cluster): PERF-1 R2 singleton + PERF-2 DB 인덱스 3건 + PERF-3 streaming upload + PERF-4 Gemini timeout + PERF-5 SSE disconnect — **외부 진입 후 일정 규모 도달 시 즉시 발현**.
- **BL-S27e-D** (성능 P2 cluster): PERF-6 cache 무차별 wipe / PERF-7 cache cleanup cron / PERF-8 created_at 인덱스 / PERF-9 inbox N+1 / PERF-10 next/font / PERF-11 dynamic lazy.
- **BL-S27e-E** (테스트 + 정량): TEST-3 vitest.config + TEST-4 workspaces branch + TEST-5 invite accept e2e + TEST-6 회의 retry + TEST-7 upload mime e2e + TEST-8/9/10 에지.
- **BL-S27e-F** (아키텍처 + governance): ARCH-1 OnboardingService I-1 + ARCH-2 services DIP + ARCH-3 common→audit 분리 + ARCH-4 헌법 doc 갱신 + ARCH-5 Demeter + ARCH-6 promote SRP + ARCH-7 BL-005 closed 마크.

---

## 7. Sprint 27d 대비 신규성

- Sprint 27d audit 가 product/UX 시각 → 본 audit 가 깊이 보완.
- 27d 에서 PASS 인 항목 재확인 (regression 없음): IDOR (BE RBAC 가드 100%), upload mime, 보안 헤더 (4종 + CSP carry), RAG cross-tenant leak (visibility filter chunk 단 차단).
- **신규 발견**: dependency CVE (SEC-1, SEC-2 — npm 생태계 1주일 사이 신규 advisory 등록), JWT 검증 미흡, cron token 평문, 보안 헤더 회귀 가드 부재, lazy seed concurrent race 미검증, R2 singleton (BL-008 carry 정량화), Gemini timeout, DB workspace_id 인덱스 누락 (PERF-2).
- 27d 의 verdict (GO 8.02) 와 본 audit 의 verdict (NEEDS-FIX) 충돌 X — 27d 는 product 차원, 본은 기술 차원.

---

## 8. 최종 권고

1. **차단 6건 fix 후 production 진입 또는 외부 5명 dogfooding 진입**. ~4h 소요 추정.
2. fix 후 회귀 검증 (`uv run pytest -x` + `npm run typecheck` + `npm test` + e2e focused).
3. 비차단 37건은 **BL-S27e-A~F 6묶음으로 등재** (`docs/refactoring-backlog.md`) → Sprint 28 dogfooding-stabilize 에서 우선순위별 처리.
4. ADR-024 (Clerk Production 발급) cutover **직전 SEC-3 fix 가 lock-in**.
5. 성능 정량 baseline 은 **로컬 up 후 또는 staging Cloud Run 측정 → BL-S27e-C 진입 신호**.

---

## 산출물 인덱스

| 파일 | 내용 |
|---|---|
| `security-findings.md` | 11건 OWASP A01~A10 + 도메인 |
| `performance-findings.md` | 15건 algorithm / DB / cache / sync / 리소스 / FE |
| `test-coverage-findings.md` | 10건 + 추가 권고 14건 + 정량 baseline (BE 65.69%/41.08%, FE < 6% 구조적, e2e 9/14, 신규 8/11) |
| `architecture-findings.md` | 7건 헌법/ADR/SOLID/결합도/일관성 + 의존성 그래프 + BL 재평가 |
| `integrated-report.md` (본) | 4 통합 + 충돌 해결 + 차단 fix 순서 + BL carry 6묶음 |
| `pr-comment.md` | GitHub PR 직접 첨부 형식 (차단 6건 expanded) |
| `report.html` | 시각화 (dark mode + bug card) |
