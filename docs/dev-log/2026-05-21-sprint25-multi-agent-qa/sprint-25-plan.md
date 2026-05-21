# Sprint 25 — Multi-Agent QA 결과 반영 계획

> 작성: 2026-05-21 (KST), session: cosmic-knitting-island
> 베이스라인: Sprint 24 Wave 2 trusty-heron (PR #101) 머지 + ADR-019 Phase B 적용
> Multi-Agent QA Composite (3축): **Security 4.55 / Product 4.6 / GTM 7.0**
> 본 plan은 codex review의 partial flip(TRUST/PRICING → P1)을 채택
> **2026-05-21 정정**: 사용자 결정 반영 — Clerk Production 발급 SKIP + Clerk webhook SKIP (memory `project_gcp_migration_jetaime_dev_done.md` 2026-05-21). T-SEC-2 제거, BUG-CASUAL-001 정책 재분류, T-SEC-1 방향 endpoint 비활성화로 변경.

## 1. 목표

**한 줄**: `/api/v1/users/sync` endpoint를 비활성화하여 sync_user IDOR 공격면을 제거하고, GA launch blocker(TRUST/PRICING/PRODUCT-SHOT)를 P1로 해소하며, dev Clerk key 기반 e2e 인프라를 도입한다.

## 2. 범위

### In-Scope
- **Wave 1 (P0)**: BUG-SENTINEL-005 (sync_user endpoint 비활성화) — 1건만
- **Wave 2 (P1)**: GA launch blocker 3건 + 시스템 견고성 4건 + dev Clerk key 기반 e2e 인프라
- **Wave 3 (P2)**: a11y 묶음 + 관측/품질 보강 + ADR-019 Phase B 실증
- **Pre-Sprint cleanup**: production DB 더미 user 1건 정리

### Out-of-Scope (Sprint 26 후보 또는 별도)
- **Clerk Production 발급** — 사용자 의도적 SKIP (2026-05-21 결정). GA launch 시점 별도 sprint.
- **BUG-CASUAL-001 Clerk dev URL 노출** — BUG 아닌 Pre-GA 운영 정책. UX 완화 옵션 "베타 멤버 전용" 텍스트는 P2 권고 (T-GTM-6).
- BL-CUR-001 (15초 비디오 데모) — 별도 마케팅 sprint 권고
- BL-CUR-002 (ROI 계산기) — 별도 마케팅 sprint
- BL-068/069 — Wave 2의 e2e 인프라 도입 후 동반 verify로 자동 carry-over
- agy CLI hang 별도 BL 등재 (시스템 외부 도구 이슈)

## 3. 작업 분해

### Pre-Sprint cleanup (~0.5h)

| Task | 대상 | 변경 | 검증 |
|------|------|------|------|
| **T-CLEANUP-1** | production DB | Neon SQL editor에서 `DELETE FROM users WHERE clerk_id='user_QA20260521_sentinel_test_doNotUse'` 실행 (사용자 작업) | SELECT 후 0건 확인 |

### Wave 1 — P0 (~1h)

| Task | 대상 파일 | 변경 | 시간 | 의존 | 검증 |
|------|-----------|------|------|------|------|
| **T-SEC-1 (정정)** | `backend/src/auth/router.py`, `backend/src/main.py` | `POST /api/v1/users/sync` endpoint 비활성화 — handler 제거 또는 `raise HTTPException(404)`. `app.include_router(auth_router)`는 다른 라우트(`/api/v1/users/me`, `/api/v1/users/me/onboarding` 등) 유지. 헌법 §4.2 영향 없음. | 1h | — | curl POST `/api/v1/users/sync` → **404 또는 410 Gone**. 다른 `/api/v1/users/me` 라우트는 정상 (회귀 0). 회귀 테스트 `backend/tests/test_auth_sync_disabled.py` 추가 |
| ~~T-SEC-2~~ | — | **제거** — Clerk Production 발급은 사용자 의도적 SKIP (2026-05-21 결정, memory 기록). GA launch 시점 별도 sprint. | — | — | — |

### Wave 2 — P1 (~28h)

| Task | 대상 파일 | 변경 | 시간 | 의존 | 검증 |
|------|-----------|------|------|------|------|
| **T-SEC-3** | `backend/src/upload/router.py`, `backend/src/upload/service.py`, `backend/src/upload/exceptions.py` | size limit env (`MAX_UPLOAD_BYTES=500MB`) + MIME 화이트리스트 (audio/* + application/pdf + text/*) + 확장자 검증 + python-magic sniff + R2 putObject 트랜잭션 정합 (DB record와 동기) | 4h | — | 0byte 400 / 위장 MIME 415 / 초과 size 413 / 정상 200. 회귀 테스트 4 case |
| **T-GTM-1** | `frontend/src/components/landing/`, `frontend/src/app/page.tsx` | 신뢰 신호 section 신설 — (a) 베타 로고 또는 "Used by N teams" 카테고리 신호, (b) Clerk/Neon/R2 인프라 보안 배지, (c) 창업자 LinkedIn 링크 | 6h | 로고 자산 / 보안 배지 디자인 | Curious cross-verify pass (Trust 2.0 → 6+) |
| **T-GTM-2** | `frontend/src/app/pricing/page.tsx` (신설), nav 메뉴 `frontend/src/components/landing/Header.tsx` | `/pricing` 라우트 신설 + 3-tier 윤곽(Free Beta/Team/Enterprise) 또는 "Pricing coming soon — 베타 무료" + "요금" nav 링크 `/pricing`으로 교체 (현재 `#cta`) | 3h | 가격 정책 결정 | Casual cross-verify pass + Curious 도입 결정 ROI 계산 가능 |
| **T-GTM-3** | `frontend/src/components/landing/` (PRODUCT-SHOT section), `public/landing/` | 실 제품 스크린샷 3장: Cmd+K Q&A / Inbox / Distill L1-L4 UI 실 캡처 + 풀버전 단일화 후 모달/모션 동영상 1장 (선택) | 5h | UI 정합 캡처 환경 | Curious vaporware 의심 해소 + 5초/30초/1분 룰 3/3 PASS |
| **T-GTM-4** | `frontend/src/components/landing/` 한국어 부연 라벨 | "Distill(증류) — AI 자동 요약", "L1-L4(요약 레벨)", "promote(개인→팀 승격)", "RAG(검색 강화 생성)" 한국어 fallback 라벨 + tooltip | 4h | — | Casual 용어 해독 32.5% → 60%+ 목표 |
| **T-GTM-5** | `frontend/src/components/landing/Hero.tsx`, 서브헤드 | "CODE = Capture · Organize · Distill · Express" 풀어쓰기 + "한국팀을 위한 세컨드 브레인" 명시 + "5분 설정 = 워크스페이스/회의 업로드/AI 요약" 분 단위 분해 | 4h | — | Curious 6.17 → 7.5+ 목표 |
| **T-INFRA-1 (정정)** | `frontend/e2e/` (Playwright + dev Clerk key), `frontend/playwright.config.ts` | **Dev Clerk key 기반** e2e 인프라 — auth.setup.ts 갱신 + Owner/Viewer storageState + qa-* spec 부활. BL-068 (Workspace switcher) + BL-069 (Inbox dismiss) Playwright spec 추가. Clerk dev test mode 기능 활용 (test email / OTP bypass). | 5-7h | dev Clerk test account 셋업 | 인증 게이트 안쪽 CRUD/RBAC e2e 1차 실행 + BL-068/069 verify |

### Wave 3 — P2 (~13h)

| Task | 대상 파일 | 변경 | 시간 | 의존 | 검증 |
|------|-----------|------|------|------|------|
| **T-GTM-6 (신규, UX 완화)** | `frontend/src/components/landing/Header.tsx`, `frontend/src/app/sign-up/page.tsx` | "현재 베타 멤버 전용 — Pre-GA" 텍스트 + Clerk redirect 직전 안내 모달(선택). Pre-GA dev Clerk 운영 정책 UX 완화. | 1h | — | 30대 사용자 피싱 의심 신호 완화 |
| **T-A11Y-1** | `frontend/src/app/`, `frontend/src/components/landing/` | `<main>` 랜드마크 + skip-link + `prefers-reduced-motion` CSS + 장식 C/O/D/E 글자 `aria-hidden="true"` + CTA 박스 `#94A3B8` 대비 보정 | 4h | — | axe-core violations 0 (Serious + Moderate) |
| **T-SEC-4** | `backend/src/meetings/schemas.py:28-32` | `CaptureTextRequest.transcript_text` `max_length=200_000` 추가 | 0.5h | — | pytest 추가 |
| **T-SEC-5** | `backend/src/main.py`, `backend/src/core/config.py` | production env `docs_url=None, redoc_url=None` (env `APP_ENV=production` 분기) + Cloud Run env 갱신 | 0.5h | — | `/api/v1/docs` 404 in prod |
| **T-SEC-6** | `backend/src/main.py` lifespan, `/ready` 핸들러 | ready check connection pool reuse 또는 lightweight `SELECT 1` ping | 2h | — | `/ready` RTT 200ms 이하 |
| **T-UI-1** | `frontend/src/components/layout/MobileNav.tsx` (신설), Header | 모바일 햄버거 메뉴 + 모바일 17px→16px body | 5h | — | viewport 375x667 nav 동작 |
| **T-AI-1** | `backend/tests/test_ai_pipeline.py` 신설 또는 보강 | ADR-019 Phase B post-swap LLM 직접 호출 실증 — Distill/Extract Actions 스키마 정합 + Sprint 16 baseline 비교 + due_date hallucinate 재현(BL-024 carry) | (Wave 2 T-INFRA-1과 동반 가능) | T-INFRA-1 | better 4/same 1/worse 0 PASS 회복 또는 추가 fix |

### 자의 결정 라벨 (프로젝트 컨벤션 follow)

- ~~Clerk Production 발급 가정~~ → **사용자 SKIP 결정 (2026-05-21)**. 본 plan에서 의존 제거.
- `[확인 필요]` — T-GTM-2 가격 정책 결정. 사용자 확인 필요.
- `[가정]` — T-GTM-3 실 제품 스크린샷 캡처 가능 환경 (dev key 기반 로컬 또는 dev key 배포 production). 정합 캡처 위해 dev key staging-like 환경 권고.

## 4. 검증 기준

### Sprint 25 종료 시 충족 조건

- [ ] BUG-SENTINEL-005 fix verified (`/api/v1/users/sync` 404/410 + 회귀 테스트 추가)
- [x] ~~BUG-CASUAL-001 fix~~ → 정책 결정으로 재분류, T-GTM-6 UX 완화 텍스트로 부분 대응
- [ ] Wave 2 GA launch blocker 3건 (TRUST + PRICING + PRODUCT-SHOT) 해소
- [ ] e2e 인프라 도입 (dev Clerk key 기반) + BL-068/069 verify 완료
- [ ] a11y axe-core violations 0 (Serious + Moderate)
- [ ] ADR-019 Phase B post-swap LLM 실증 baseline 갱신
- [ ] **Composite 3축 목표**: Security 4.55 → 7.0+ / Product 4.6 → 6.5+ / GTM 7.0 → 8.0+
- [ ] production DB 더미 user 정리 (T-CLEANUP-1)
- [ ] backend pytest 전체 통과 + frontend vitest + e2e qa-* spec 정상 통과
- [ ] docs sync: backend `auth/CONTEXT.md` (sync 엔드포인트 제거 반영) + `upload/CONTEXT.md` + `CONTEXT-MAP.md` §2/§4 patch + ADR-021 신설 (Clerk webhook SKIP 정책 + sync_user endpoint 비활성화 결정 기록)

### 새 회귀 테스트 (코드 산출물 포함)

- `backend/tests/test_auth_sync_disabled.py` — `/api/v1/users/sync` 비활성화 verify (POST → 404/410, `/api/v1/users/me` 등 다른 라우트 정상 200)
- `backend/tests/test_upload_validation.py` — size/MIME/확장자 4 case
- `frontend/e2e/qa-onboarding.spec.ts` — onboarding 0→4 e2e (dev Clerk key 기반)
- `frontend/e2e/qa-workspace-switcher.spec.ts` — BL-068 verify
- `frontend/e2e/qa-inbox-dismiss.spec.ts` — BL-069 verify

## 5. 위험 + 완화책

| # | 위험 | 영향 | 완화 |
|---|------|------|------|
| ~~R1~~ | ~~Clerk Production 발급 지연~~ | — | **제거** — 사용자 SKIP 결정 (2026-05-21). 본 plan 의존 0 |
| R2 (정정) | `/api/v1/users/sync` endpoint 비활성화 시 다른 라우트(`/api/v1/users/me/onboarding` 등) 동반 회귀 | auth 도메인 회귀 | `app.include_router(auth_router)` 유지 + sync handler만 제거. 회귀 테스트로 `/users/me` 라우트 정상 verify |
| R3 | T-GTM-1/2/3 (TRUST + PRICING + PRODUCT-SHOT) 동시 진행 시 마케팅 일관성 부재 | 디자인 톤 깨짐 | DESIGN.md baseline 준수 + ui-ux-pro-max 5축 7.85 유지 검증 (post-Sprint 25 재측정) |
| R4 | Playwright + Clerk Prod e2e 인프라 도입이 5h 초과 | Wave 2 일정 깨짐 | T-INFRA-1을 자체 sub-sprint로 분리 가능. 실패 시 Wave 3 fallback (BL-068/069 carry-over 유지) |
| R5 | 더미 user 정리 누락 시 production DB 오염 누적 | data hygiene | T-CLEANUP-1을 Sprint 25 첫 commit 전 사용자 직접 수동 처리. SELECT 후 0건 확인 후 진행 |

## 6. 예상 일정 (총 ~42h, 사용자 Clerk Prod 의존 제거로 -4h)

| 일차 | 작업 | 누적 |
|------|------|------|
| Day 0 | Pre-Sprint cleanup (T-CLEANUP-1, 사용자) | — |
| Day 1 | Wave 1 T-SEC-1 (sync_user endpoint 비활성화) | 1h |
| Day 1 | Wave 2 T-SEC-3 (upload validation) | 5h |
| Day 2 | Wave 2 T-INFRA-1 (dev Clerk key 기반 e2e 인프라) | 12h |
| Day 3 | Wave 2 T-GTM-1 (TRUST) | 18h |
| Day 3 | Wave 2 T-GTM-2 (PRICING, 가격 정책 결정 후) | 21h |
| Day 4 | Wave 2 T-GTM-3 (PRODUCT-SHOT) | 26h |
| Day 4 | Wave 2 T-GTM-4 (용어 라벨) | 30h |
| Day 5 | Wave 2 T-GTM-5 (CODE/한국팀/5분) | 34h |
| Day 6 | Wave 3 T-GTM-6 + T-A11Y-1 + T-SEC-4/5/6 + T-UI-1 + T-AI-1 | 41h |
| Day 7 | 통합 회귀 + docs sync + retrospective | 42h |

**총 6-7 영업일 권고** (가격 정책 결정 시간 별도)

## 7. ADR 신설 후보

- **ADR-021 (정정)**: Clerk webhook SKIP 정책 + `/api/v1/users/sync` endpoint 비활성화 결정 기록 (2026-05-21 사용자 결정 lock-in)
- **ADR-022 (선택)**: Composite Health Score 3축 분리 (Security/Product/GTM) — codex review 권고 채택 결정 기록

## 8. 후속 권고

- Sprint 26 후보: BL-CUR-001 비디오 데모 + BL-CUR-002 ROI 계산기 + BL-CUR-003 경쟁사 비교 페이지 → 별도 마케팅 sprint로 묶기 권고
- agy CLI hang 별도 BL 등재: 시스템 외부 도구 이슈, Sprint 25 본 작업과 분리
- Multi-Agent QA 프로세스 개선: Phase 0 자동탐색에서 FE URL 추정 결과를 사용자에게 명시적 확인 (이번 `kairos.vercel.app` vs `kairos-zeta-ebon.vercel.app` 혼선 재발 방지) — 다음 Multi-Agent QA 진행 시 템플릿에 반영
