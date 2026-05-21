# 통합 결함 매트릭스 — Sprint 25 Multi-Agent QA

> 작성: 2026-05-21 (KST), session: cosmic-knitting-island
> 페르소나 3종 통합 + cross-verify 공통 발견 표시
> **2026-05-21 정정**: 사용자 Clerk Production 발급 SKIP 결정 반영 → BUG-CASUAL-001 정책 재분류 + T-SEC-2 제거 + BUG-SENTINEL-005 권고 → endpoint 비활성화

## Composite Health Score (codex 권고로 3축 분리 적용)

### Legacy Composite (참고용)

가중치: Sentinel 0.50 + Curious 0.25 + Casual 0.25 → **Composite 5.19 / 10** (Sprint 24 5.9 대비 Δ -0.71)

### 3축 분리 점수 (codex review 권고 채택)

> "보안 점수와 마케팅 신뢰 점수를 단일 health로 합치는 건 왜곡입니다." — codex review

| 축 | 정의 | 점수 |
|----|------|------|
| **Security** | Sentinel S1~S4 (보안/데이터 격리/회귀) | **4.55 / 10** |
| **Product** | Casual U1~U3 (과업 직관성/용어/a11y) + Sentinel S2/S3 일부 | **4.6 / 10** |
| **GTM** | Curious C1~C4 (TTFV/룰/경쟁사) + Casual U4 (디자인) | **7.0 / 10** |

**해석**: GTM(7.0)은 비교적 양호. Security/Product(4.5x)가 동시에 5 미만 → **베타 단계에서 시스템 신뢰 확보(Security)가 GTM 작업의 선결 조건**. Sprint 24 Wave 2 fix bundle 후에도 sync_user Critical + Clerk dev URL 노출이 Security를 끌어내림.

## 공통 발견 (★★★ Cross-Verify)

| 공통 ID | 페르소나 | 결함 | 우선순위 격상 |
|---------|----------|------|---------------|
| ★★★ TRUST | Curious + Casual | 신뢰 신호 0개 (로고/펀딩/보안 배지 0) | P0 (격상) |
| ★★★ PRICING | Curious + Casual | 가격 페이지 부재 + "요금" 메뉴 = `#cta` 앵커 | P0 (격상) |
| ★★ PRODUCT-SHOT | Curious + Casual (부분) | 실 제품 스크린샷 0개 (Cmd+K 모의 1개만) | P1 (격상) |

## 통합 매트릭스 (우선순위순)

| ID | 페르소나 | 분류 | 우선순위 | 페이지/도메인 | 제목 | 공수 | 의존 |
|----|----------|------|---------|---------------|------|------|------|
| **BUG-SENTINEL-005** | Sentinel | **Critical** | **P0** | `POST /api/v1/users/sync` | 인증/Svix 서명 없이 임의 user 생성. **권고 정정: endpoint 비활성화 (404/410)** — Clerk webhook 사용자 SKIP 결정(2026-05-21)이므로 Svix 검증 무의미. | 1h | — |
| ~~BUG-CASUAL-001~~ | Casual | **정책 (BUG 아님)** | **Out-of-Sprint** | `/sign-up` | Clerk dev 인스턴스 노출 = **사용자 의도적 Pre-GA 정책** (memory `project_gcp_migration_jetaime_dev_done.md`). GA launch blocker. UX 완화는 T-GTM-6 (P2). | — | — |
| **★★★ TRUST** (BUG-CURIOUS-001 + Casual 공통) | Curious + Casual | High | **P0** | landing | 신뢰 신호 0개 (고객 로고/펀딩/보안 배지/G2/SOC 2). B2B 의사결정 결재 보고서 작성 불가. | 6h | — |
| **★★★ PRICING** (BUG-CURIOUS-003 + BL-CAS-006 공통) | Curious + Casual | High | **P0** | landing nav + `/pricing` | 가격 페이지 부재. "요금" 메뉴 = `#cta` 앵커 (가격표 아님). | 3h | 가격 정책 결정 |
| **BUG-SENTINEL-003** | Sentinel | High | **P1** | `POST upload/file` | 파일 크기/MIME/확장자 검증 누락. 메모리 DoS + 위장 파일 R2 적재 가능. | 4h | — |
| **★★ PRODUCT-SHOT** (BUG-CURIOUS-002 + BUG-CASUAL-002 공통) | Curious + Casual | High/Medium | **P1** | landing | 실 제품 스크린샷 0개 → vaporware 의심. 노트/Inbox/RAG UI 데모 추가. | 5h | UI 정합 캡처 |
| **BUG-CASUAL-003** | Casual | High | **P1** | landing+UI | 용어 해독률 32.5% (RAG 0%, Distill 10%, promote 10%). 한글 부연 라벨 필요. | 4h | — |
| **BUG-CURIOUS-004** | Curious | Medium | **P1** | landing | "CODE" 약자 첫 노출 시 풀어쓰기 부재. | 1h | — |
| **BUG-CURIOUS-005** | Curious | Medium | **P1** | landing | 한국팀 타깃 명시 부재 ("Built for Korean teams" 없음). | 2h | — |
| **BUG-CURIOUS-006** | Curious | Medium | **P1** | landing | "5분 설정" 분 단위 분해 부재. | 1h | — |
| **BUG-SENTINEL-004** | Sentinel | Medium | **P2** | `POST meetings/capture` | `transcript_text` max_length 누락. Gemini 비용 폭증 위험. | 0.5h | — |
| **BL-CAS-009** | Casual | Serious (a11y) | **P2** | CTA 박스 | `#94A3B8` on dark 대비 의심. | 1h | — |
| **BL-CAS-007/008/010** | Casual | Moderate (a11y) | **P2** | a11y | `<main>` 랜드마크 + skip-link + prefers-reduced-motion + 장식 aria-hidden | 3h | — |
| **BL-CAS-001** | Casual | Medium | **P2** | nav | 모바일 햄버거 부재. | 2h | — |
| **BL-CAS-002** | Casual | Medium | **P2** | CSS | reduced-motion 미확인. | 1h | — |
| **BL-CAS-005** | Casual | Medium | **P2** | theme | light 토큰 검증 누락. | 2h | — |
| **BL-SNT-CANDIDATE-A** | Sentinel | Medium | **P2** | `/api/v1/ready` | 1.1~2.0s latency. connection pool reuse 검토. | 2h | — |
| **BL-SNT-CANDIDATE-B** | Sentinel | Low | **P2** | `/api/v1/docs` | Swagger 프로덕션 노출. | 0.5h | — |
| **BL-CUR-001** | Curious | Backlog | **P3** | landing | 15초 비디오 데모. | 8h | — |
| **BL-CUR-002** | Curious | Backlog | **P3** | landing | ROI 계산기. | 6h | — |
| **BL-CUR-003** | Curious | Backlog | **P3** | landing | 경쟁사 비교 페이지 (한국팀 관점). | 4h | — |
| **BL-CAS-003/004** | Casual | Low | **P3** | CTA + body | CTA 카피 통일 + 모바일 17px→16px. | 1h | — |
| **BL-068 (carry)** | Sentinel | Carry | **P3** | WorkspaceSwitcher | Playwright 재현 (e2e 인프라 의존). | (Playwright + Clerk e2e 인프라 8-12h) | Clerk Prod |
| **BL-069 (carry)** | Sentinel | Carry | **P3** | Inbox dismiss | Playwright 재현 (e2e 인프라 의존). | 위와 동반 | Clerk Prod |

## 페르소나별 점수 (히트맵)

| 페르소나 \ 시나리오 | S1 | S2 | S3 | S4 | C1 | C2-C4 | U1 | U2 | U3 | U4 |
|---------------------|----|----|----|----|----|--------|----|----|----|----|
| Sentinel (S1-S4) | 7.0 | 6.0 | 3.5 | 1.5 | — | — | — | — | — | — |
| Curious (C1-C4) | — | — | — | — | TTFV ↓ | gap 5축 | — | — | — | — |
| Casual (U1-U4) | — | — | — | — | — | — | 4.0 | 3.3 | 6.5 | 7.85 |

## 회귀 점검 결과

| Sprint | 영역 | Sprint 25 결과 |
|--------|------|----------------|
| Sprint 13/17 | RAG visibility 3-layer IDOR | PARTIAL — 정적 정합 PASS, 실 IDOR 실증은 Playwright e2e 후속 |
| Sprint 22 | OBN-01~04 (오디오/노트/배지) | UNVERIFIED — 인증 게이트 안쪽 |
| Sprint 23 | cozy-crystal D1~D4 (BL-068/069) | 정적 정합 PASS, e2e carry-over |
| Sprint 24 Wave 2 | trusty-heron P0/P1 16 task | sync_user 핸들러는 fix 누락 — **BUG-SENTINEL-005**가 신규 회귀 |
| ADR-019 Phase B | Gemini 3.1-flash-lite swap | LLM 직접 호출 미실증, post-swap delta 보고서(2026-05-20) 베이스 유지 |
| 풀버전 단일화 (dd2d5b0) | 랜딩 통합 | Curious TTFV/룰 개선 확인, 다만 신뢰 신호/가격 결손 부각 |

## 우선순위 매트릭스 (Impact × Effort)

| Impact \ Effort | Low (≤2h) | Medium (3-6h) | High (>6h) |
|-----------------|------------|---------------|-------------|
| **Very High** | BL-SNT-B (Swagger) | **BUG-S-005 (sync_user)**, **★★★ PRICING** | **★★★ TRUST**, **BUG-CASUAL-001 (Clerk Prod)** |
| **High** | BUG-CURIOUS-004 (CODE), BUG-CURIOUS-006 (5분), BUG-S-004 (max_length) | **BUG-S-003 (upload)**, **★★ PRODUCT-SHOT**, BUG-CAS-003 (용어), BUG-CURIOUS-005 (한국팀) | (없음) |
| **Medium** | BL-CAS-009 (대비) | BL-CAS-007/008/010 (a11y), BL-CAS-001 (모바일 nav), BL-SNT-A (ready latency) | BL-CUR-001 (비디오) |
| **Low** | BL-CAS-003/004 | BL-CUR-003 (비교 페이지) | BL-CUR-002 (ROI) |

## Sprint 25 진입 권고 (codex partial flip 반영)

> codex challenge: TRUST/PRICING은 베타에서 P0 아닌 GA launch blocker → P1 강등

**Wave 1 (P0, ~1h)** — 공격면 제거:
- BUG-SENTINEL-005 (sync_user endpoint **비활성화**) — 1h
- 동반: 더미 user 정리 (사용자 SQL 수동, T-CLEANUP-1)
- ~~BUG-CASUAL-001 (Clerk Production 발급)~~ → **사용자 SKIP 결정으로 out-of-sprint**

**Wave 2 (P1, ~28h)** — GA launch blocker + 시스템 견고성:
- BUG-SENTINEL-003 (upload validation + R2/DB 정합성) — 4h
- ★★★ TRUST (신뢰 신호) — 6h
- ★★★ PRICING (가격 페이지) — 3h
- ★★ PRODUCT-SHOT (실 제품 스크린샷) — 5h
- BUG-CASUAL-003 (용어 해독) — 4h
- BUG-CURIOUS-004/005/006 (CODE/한국팀/5분) — 4h
- 인증 게이트 안쪽 CRUD/RBAC e2e 인프라 동반 — Playwright + Clerk Prod 인프라 도입

**Wave 3 (P2, ~12h)** — 품질/관측:
- a11y 묶음 (BL-CAS-007/008/009/010) — 4h
- BUG-SENTINEL-004 (max_length) — 0.5h
- BL-SNT-A/B (ready latency / Swagger) — 2.5h
- BL-CAS-001/002/005 (mobile nav/reduced-motion/theme) — 5h
- ADR-019 Phase B post-swap LLM 직접 호출 실증

**P3 (Sprint 26 후보)**: BL-CUR-001/002/003 + BL-068/069 + BL-CAS-003/004
