# Sprint 25 진입 전 Multi-Agent QA — 실행 요약

> 진행: 2026-05-21 (KST)
> Session: cosmic-knitting-island
> Plan: `/Users/woosung/.claude/plans/cosmic-knitting-island.md`
> **정정**: 2026-05-21 사용자 Clerk Production 발급 SKIP 결정 반영 (memory `project_gcp_migration_jetaime_dev_done.md` 기록 인지 누락 수정)

## 산출물

| 파일 | 용도 |
|------|------|
| [environment.txt](environment.txt) | 환경 fingerprint (FE/BE URL 정정 기록 포함) |
| [qa-sentinel/report.md](qa-sentinel/report.md) | Sentinel(QA) 결과 — Composite **4.55/10** |
| [curious/report.md](curious/report.md) | Curious(잠재 사용자) 결과 — Composite **6.17/10** |
| [casual/report.md](casual/report.md) | Casual(일반 사용자) 결과 — Composite **5.50/10** |
| [casual/uiux-promax-score.md](casual/uiux-promax-score.md) | ui-ux-pro-max 5축 점수 — **7.85/10** |
| [casual/axe-results.json](casual/axe-results.json) | a11y 정적 추정 |
| [integrated-defect-matrix.md](integrated-defect-matrix.md) | 통합 결함 매트릭스 (codex flip 반영) |
| [integrated-report.html](integrated-report.html) | 통합 HTML 보고서 (Tailwind, 인쇄 친화) |
| [cross-check-agy.md](cross-check-agy.md) | agy 검증 (CLI hang → 메인 세션 직접 검증) |
| [cross-check-codex.md](cross-check-codex.md) | codex review + challenge — partial flip |
| [sprint-25-plan.md](sprint-25-plan.md) | Sprint 25 실행 계획 (Wave 1/2/3) |

## 결과 요약

### Composite Health (codex 권고 3축 분리)

| 축 | 점수 | 해석 |
|----|------|------|
| Security | **4.55 / 10** | sync_user Critical + Clerk dev URL 노출이 끌어내림 |
| Product | **4.6 / 10** | 용어 해독 32.5% + 인증 게이트 미실증 |
| GTM | **7.0 / 10** | hero/value 양호, 신뢰 신호/가격/스크린샷 결손 |

Legacy Composite (Sentinel 0.5/Curious 0.25/Casual 0.25) = **5.19/10** (Sprint 24 5.9 대비 Δ -0.71)

### 결함 통계 (codex partial flip 반영)

| 우선순위 | 건수 | 핵심 |
|----------|------|------|
| **P0** | 1 | BUG-SENTINEL-005 (sync_user **endpoint 비활성화**) |
| **P1** | 7 | BUG-SENTINEL-003, ★★★ TRUST, ★★★ PRICING, ★★ PRODUCT-SHOT, BUG-CASUAL-003, BUG-CURIOUS-004/005/006, T-INFRA-1 (dev Clerk e2e) |
| **P2** | 9 | T-GTM-6 (UX 완화) + a11y 4 + BL-SNT-A/B + BL-CAS-001/002/005 + BUG-SENTINEL-004 + ADR-019 Phase B 실증 |
| **P3** | 6+ | BL-CUR-001/002/003 + BL-068/069 + BL-CAS-003/004 |
| **정책 (Out-of-Sprint)** | 1 | ~~BUG-CASUAL-001~~ Clerk dev URL = 사용자 의도적 Pre-GA 정책 (GA launch blocker) |

### Cross-Verify ★★★ 공통 발견

- **★★★ TRUST**: Curious + Casual 공통 — 신뢰 신호 0개
- **★★★ PRICING**: Curious + Casual 공통 — 가격 페이지 부재, "요금" = `#cta` 앵커
- **★★ PRODUCT-SHOT**: Curious + Casual 부분 공통 — 실 제품 스크린샷 0개

### Cross-Check 결과

- **codex review**: **fail** (보안 결함과 GTM 결손 같은 P0 버킷 → 우선순위 왜곡)
- **codex challenge**: **partial flip** — BUG-SENTINEL-005 no-flip, TRUST/PRICING P0 → P1
- **agy**: hang (CLI 11분 응답 없음, kill exit 144) → 메인 세션 직접 도메인 검증으로 보강
- **메인 세션 도메인 검증**: BL-068/069 carry-over 정합 / ADR-019 Phase B post-swap 실증 누락 / 헌법 §4.2 정합 검증 필요

## 정정 사항 (Phase 0 자동탐색 오류 → 메인 세션 정정)

| 항목 | 오류 | 정정 |
|------|------|------|
| FE 프로덕션 URL | `kairos.vercel.app` (다른 사이트, 영어, theme #00CEE8) | `kairos-zeta-ebon.vercel.app` (실제 Kairos FE, ko 한국어) |
| BUG-SENTINEL-006 (CORS) | False-positive — 잘못된 URL 기준 진단 | **REJECTED** (실제 URL은 CORS 200 + 헤더 echo 정상) |
| Composite Sentinel | 4.25 | 4.55 (CORS 정정 +0.30) |

## 데이터 정리 필요

production DB에 BUG-SENTINEL-005 PoC 잔존:
- clerk_id: `user_QA20260521_sentinel_test_doNotUse`
- email: `qa-sentinel-2026-05-21@kairos.test`
- 정리 SQL: `DELETE FROM users WHERE clerk_id='user_QA20260521_sentinel_test_doNotUse'`
- 실행 위치: Neon SQL editor (사용자 작업)
- 시점: Sprint 25 첫 commit 전

## Sprint 25 진입 신호

→ [sprint-25-plan.md](sprint-25-plan.md) 참조
- Wave 1 (P0, ~1h): BUG-SENTINEL-005 endpoint 비활성화 + T-CLEANUP-1 더미 user 정리
- Wave 2 (P1, ~28h): BUG-S-003 + GTM 5건 (TRUST/PRICING/PRODUCT-SHOT/용어/CODE-한국팀-5분) + T-INFRA-1 dev Clerk e2e
- Wave 3 (P2, ~13h): T-GTM-6 UX 완화 + a11y + 관측 + ADR-019 Phase B 실증

**총 ~42h (약 6-7 영업일, 가격 정책 결정 시간 별도)**

## 사용자 협력 필요 (정정)

1. **production DB 더미 user 정리** — Neon SQL `DELETE FROM users WHERE clerk_id='user_QA20260521_sentinel_test_doNotUse'`
2. **가격 정책 결정** — T-GTM-2 의존 (3-tier 또는 "Pricing coming soon")
3. ~~Clerk Production 발급~~ → **사용자 SKIP 결정 (2026-05-21)**. Sprint 25 의존 0.

## 한계 (이번 QA 공통)

- Playwright MCP 메인 세션 점유 → 모든 페르소나가 정적 분석 + WebFetch fallback
- Clerk Production 미발급 → 인증 게이트 안쪽 (대시보드/inbox/search/memory/projects) 검증 0
- Curious의 가입→첫 노트 TTFV 실측 불가 → 추정치만 (60~90s 추정)
- Sentinel S1 RAG IDOR 실 IDOR 시도는 정적 분석에 의존 (JWT 미획득)
