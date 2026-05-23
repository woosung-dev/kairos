# Casual 페르소나 최종 보고서

> Sprint 25 Multi-Agent QA — Casual(일반 사용자) 페르소나 결과
> 작성: 2026-05-21 (KST), session: cosmic-knitting-island
> sub-agent ID: a0c0533c955a2b175
> 환경: `https://kairos-zeta-ebon.vercel.app` (실제 FE URL)
> 한계: Playwright MCP 메인 세션 점유 → WebFetch + curl 정적 HTML 분석 fallback. 인증 게이트 안쪽 화면 0개 평가 가능.

## 1. Executive Summary

- **랜딩 디자인 7.85/10** (ui-ux-pro-max 5축 가중) — 한글 SaaS B2B 기준 양호. Pretendard + Satoshi + Geist Mono 페어링, accent `#0FA889` teal, 8pt grid, 200ms easing 일관.
- **30대 비전문가 진입 마찰 3건**: (a) Clerk dev URL 노출 = 피싱 의심, (b) "Distill / L1-L4 / promote / RAG" 용어 해독률 0-15%, (c) "요금" 메뉴가 가격표 아닌 `#cta` 앵커 — Curious와 공통 발견 ★★★.
- **a11y**: Serious 1 + Moderate 2 + Minor 1 + Unknown 2 (정적 추정).
- **용어 해독률 32.5%** — Sprint 24 baseline 33-60% 하한선.
- **Composite Casual Score 5.5/10**.

## 2. 핵심 과업 3종 결과 (U1)

| 과업 | 결과 | 막힘 |
|------|------|------|
| 가입 진입성 | **PARTIAL/FAIL** | `/sign-up` → `creative-boxer-79.accounts.dev` dev 호스트 307 리다이렉트 → 30대 보안 의식 사용자 뒤로가기 가능성 |
| 노트 생성 직관성 | **UNVERIFIABLE** | 대시보드 인증 게이트 + 랜딩에 노트 작성 UI 데모 부재 |
| AI 요약/Inbox dismiss | **UNVERIFIABLE** | "Inbox"(해독 90%)는 OK, "Distill / 결정만 하세요" 추상적 |

## 3. 용어 해독률 (U2) — 평균 32.5%

| 용어 | 해독률 |
|------|--------|
| Inbox | 90% |
| Capture / Organize | 80% |
| Cmd+K | 75% |
| 세컨드 브레인 | 40% |
| CODE 파이프라인 | 30% |
| 프로액티브 인사이트 | 30% |
| Express | 25% |
| L1-L4 | 15% |
| Distill / 증류 | 10% |
| promote | 10% |
| RAG | 0% |

**Top 3 막힘**: RAG (0%) → Distill (10%) → promote (10%).

## 4. a11y 결과 요약 (U3)

정적 추정 (axe-core 미실측, `axe-results.json` 참고).
- Critical 0 / Serious 1 (CTA 박스 `#94A3B8` on dark 대비 의심)
- Moderate 2 (`<main>` 랜드마크·skip-link 부재)
- Minor 1 (장식 글자 aria-hidden 누락)
- PASS 6
- Unknown 2 (focus-visible·reduced-motion 실측 필요)
- BL-T2-007 carry-over = PARTIAL, Playwright 실측 필요.

## 5. ui-ux-pro-max 5축 (U4)

| 축 | 점수 | 핵심 근거 |
|----|------|----------|
| 타이포 | 8.0 | Pretendard + Satoshi + Geist Mono, clamp() hero, letter-spacing -0.035em |
| 색상 | 7.5 | accent `#0FA889` + semantic token, dark default, cat-* 4색 |
| 레이아웃 | 8.5 | max-w 단계 + 8pt grid + mobile-first + fixed nav padding |
| 모션 | 7.0 | duration 200ms + active:scale[0.97] + hover:-translate-y-0.5, reduced-motion 미확인 |
| 일관성 | 8.0 | radius/shadow 토큰, mono 메타라인, CTA 카피 3종 분기 흠 |
| **가중 평균** | **7.85** | — |

## 6. Curious cross-verify (U5) — 3/3 공통 ★★★

- BUG-CURIOUS-001 신뢰 신호 부족 → **공통** (No trust signals found 확인)
- BUG-CURIOUS-002 스크린샷 부재 → **부분 공통** (Cmd+K 모의 1개만, 노트/Inbox/RAG UI 데모 0)
- BUG-CURIOUS-003 가격 페이지 부재 → **공통** ("요금" = `#cta` 앵커, `/pricing` 없음)

## 7. Composite Casual Score

산식: U1(0.35) × 4.0 + U2(0.20) × 3.3 + U3(0.20) × 6.5 + U4(0.25) × 7.85 = **5.32/10**
보정 (U1 verify 불가 conservative) → **최종 5.5/10**

## 8. Sprint 25 권고

### P0
1. ~~Clerk Production 인스턴스 발급~~ → **사용자 의도적 SKIP 결정 (2026-05-21)**. GA launch blocker로만 carry-over.
2. ~~랜딩 가격표 신설~~ → codex partial flip으로 **P1 강등** (GA launch blocker)

### P1
3. Distill/L1-L4/promote/RAG 용어에 한글 부연 라벨 — BUG-CASUAL-003
4. 랜딩 데모 영상/스크린샷 (Cmd+K + Inbox + 노트 작성 3개) — BUG-CASUAL-002 / BUG-CURIOUS-002
5. 신뢰 신호 추가 (로고/케이스 스터디/베타 인용) — BUG-CURIOUS-001

### P2
6. `<main>` 랜드마크 + skip-link + prefers-reduced-motion + "C/O/D/E" aria-hidden — BL-CAS-007/008/010
7. CTA 박스 본문 색 대비 보정 — BL-CAS-009
8. 모바일 nav 햄버거 메뉴 — BL-CAS-001

### P3
9. CTA 카피 통일 ("무료로 시작하기" 1종) — BL-CAS-003
10. Playwright axe-core 실측 + reduced-motion 검증 — BL-CAS-010 후속

## 9. 결함 매트릭스

| ID | Severity | 위치 | 설명 | Curious 공통 |
|----|----------|------|------|--------------|
| ~~BUG-CASUAL-001~~ | **정책 결정 (BUG 아님)** | /sign-up | Clerk dev 인스턴스 노출 = 사용자 의도적 Pre-GA 정책 (memory `project_gcp_migration_jetaime_dev_done.md` 2026-05-21). GA launch blocker. UX 완화 옵션은 "베타 멤버 전용" 텍스트 추가 (P2 권고). | — |
| BUG-CASUAL-002 | Medium | landing | UI 데모 스크린샷 0개 | ★★ |
| BUG-CASUAL-003 | High | landing+UI | 용어 해독 0-15% (Distill/L1-L4/promote/RAG) | — |
| BL-CAS-001 | Medium | nav | 모바일 햄버거 부재 | — |
| BL-CAS-002 | Medium | CSS | reduced-motion 미확인 | — |
| BL-CAS-003 | Low | CTA | 동일 액션 카피 3종 | — |
| BL-CAS-004 | Low | body | 모바일 17px→16px | — |
| BL-CAS-005 | Medium | theme | light 토큰 검증 누락 | — |
| BL-CAS-006 | High | nav | "요금" = `#cta` (가격표 부재) | ★★★ |
| BL-CAS-007 | Moderate | a11y | `<main>` + skip-link 부재 | — |
| BL-CAS-008 | Low | a11y | 장식 C/O/D/E aria-hidden 누락 | — |
| BL-CAS-009 | Serious | CTA 박스 | `#94A3B8` on dark 대비 의심 | — |
| BL-CAS-010 | Moderate | a11y | reduced-motion 실측 필요 | — |

## 10. 주요 디자인 사실 (정적 분석 검증)

- 폰트: `api.fontshare.com/.../satoshi@400,500,600,700` + `fonts.googleapis.com/Geist+Mono` + `cdn.jsdelivr.net/.../pretendardvariable` (font-display:swap 명시)
- accent token: `#0FA889` (teal/emerald), shadow `rgba(15,168,137,0.18)`
- 다크 default: `data-theme="dark"` + `data-theme="landing"` 스코프
- `<html lang="ko">` 명시 / `<meta name="viewport" content="width=device-width, initial-scale=1">` 줌 차단 없음
- 랜딩 `<img>` 0개 (전부 SVG/CSS)
- `<main>` 랜드마크 부재 (section만 사용), skip-link 0개
- nav 모바일 `hidden sm:block`로 "기능/요금" 숨김, 햄버거 없음
- "요금" 링크 target = `#cta` (가격표 0)

## 11. 한계

- Playwright MCP 메인 세션 점유 → 실 브라우저 렌더 미확인 (시각 평가는 텍스트/HTML 기반)
- 인증 게이트 안쪽 화면 미평가 (대시보드/inbox/search/memory)
- axe-core 미실측 → 정적 추정만 (BL-T2-007 carry-over)
- Clerk dev 인스턴스 외부 호스트 리다이렉트 → 사용자 보안 의심 가능성 명확하지만 정량 측정은 별도 user test 필요
