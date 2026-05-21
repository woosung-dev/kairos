# Curious 페르소나 최종 보고서

> Sprint 25 Multi-Agent QA — Curious(잠재 사용자) 페르소나 결과
> 작성: 2026-05-21 (KST), session: cosmic-knitting-island
> sub-agent ID: ae374f9e5140b7f8d
> 환경: `https://kairos-zeta-ebon.vercel.app` (실제 FE URL, 자동탐색 정정 후)
> 한계: Playwright MCP 메인 세션 점유로 WebFetch 기반 텍스트/구조 평가, 시각 캡처 0장

## 1. Executive Summary

1. **Kairos hero는 5초 룰 PASS (한국어 의사결정자 기준).** "AI가 정리합니다. 당신은 결정만 하세요." + "CODE 파이프라인"으로 즉시 카테고리 파악 가능.
2. **30초/1분 룰은 조건부 PASS — 결정적 약점**: 실 제품 스크린샷 0개. 모든 데모가 추상 일러스트라 "진짜 작동하나?" 의심이 1분 시점에 발생.
3. **TTFV 베이스라인 대비 개선 추정**: 풀버전 단일화(dd2d5b0) 후 hero 즉시 노출 → Sprint 24의 255.5s 베이스라인 대비 단축 추정. 단 가입 자동화 막혀 정량 측정 불가.
4. **3사 비교에서 진짜 약점은 신뢰 신호 0개**: Granola/Fireflies/Notion AI 모두 customer logo + funding/users + 보안 배지를 hero 근처에 노출. Kairos는 전무.
5. **도입 결정 = Maybe (한국팀 한정 Yes 경향)**.

## 2. TTFV / 5·30·1분 룰

| 룰 | 결과 | 근거 |
|----|------|------|
| **5초 룰** | **PASS** | Hero + Capture/Organize/Distill/Express 네비. 한국어 의사결정자에게 카테고리 즉시 전달. |
| **30초 룰** | **PASS (조건부)** | 서브헤드 "팀의 대화, 노트, 자료가 CODE 파이프라인을 거치면 자동으로 구조화된 지식이 됩니다."로 가치 명확. "CODE" 약자 학습 부담 1단계. |
| **1분 룰** | **CONDITIONAL** | 95%/12x/24h/80%/89% 정량 수치 6개 + 4-Level Distill + Week1/Month1/Quarter1 진화 단계. 단 실 스크린샷 0개 → vaporware 의심. |
| **TTFV (추정)** | **60~90초** (가치 인식), 실 첫 노트 도달은 측정 불가 | Clerk OAuth 자동화 차단으로 본 세션에서 가입→첫 노트는 미측정. Sprint 24 베이스라인 255.5s 대비 랜딩→이해 구간은 명백히 단축. |

종합: 2.5/3 PASS. 1분 룰에서 "실 제품 증거 부재"가 결정타.

## 3. Kairos UX 평가 (6축, 1-10)

| 축 | 점수 | 근거 |
|----|------|------|
| Hero clarity (5초) | **8/10** | 한국어로 즉시 이해. "CODE" 약자 학습 1단계 필요. |
| Value proposition (30초) | **8/10** | "AI 정리, 사용자 결정" + 4단계 파이프라인 + Cmd+K Q&A 예시로 차별성 전달. |
| Trust signals | **2/10** | **치명적**. 로고 0, "trusted by" 0, 사용자 수 0, SOC 2 0, 펀딩 0, 미디어 0. |
| Visual design | **6/10** | 텍스트 평가 한계. 풀버전 단일화로 일관성 개선 추정. |
| Sign-up friction | **7/10** | `/sign-up` 라우팅 정상, Clerk Google OAuth = 1-클릭. "5분 설정"이 무엇인지 불명. |
| Adoption intent | **6/10** | 한국팀 한정 Yes 경향. 가격 페이지/실 스크린샷 부재로 보류. |

**Composite UX = (8+8+2+6+7+6) / 6 = 6.17/10**

## 4. 경쟁사 비교 결론

### Granola (https://granola.ai)
Hero "The AI Notepad for back-to-back meetings"로 카테고리 즉시 명확. 가격 $0/$14/$35 3-tier 투명. 신뢰 신호 압도적: PostHog/Intercom/Ramp/Linear/Brex/Vercel 8개 로고 + $125M 펀딩 + Nat Friedman/Guillermo Rauch 추천. 강점: "back-to-back 회의 1인 사용자" 협소 wedge + 봇 없이 시스템 오디오 캡처. 약점: 영어 중심, 팀 지식 통합 약함. **Kairos는 한국어 + 팀 세컨드 브레인 카테고리에서 차별 가능**.

### Fireflies (https://fireflies.ai)
Hero "The #1 AI Assistant For Your Meetings". 1M+ 기업, G2 4.8/5, SOC 2/GDPR/HIPAA 배지로 신뢰 신호 압도. 100+ 언어 + "AskFred" Q&A + 200+ AI Skills. 강점: recording-first + 엔터프라이즈 보안. 약점: 봇 invite 마찰 + 한국어 명시 안 됨 + 회의 외 지식 통합 약함. **Kairos는 memo-first + 한국어 + CODE 파이프라인 통합으로 차별 가능**.

### Notion AI (https://www.notion.com/product/ai)
Hero "Meet your 24/7 AI team". OpenAI/Figma/Ramp/Nvidia 4개 로고 + SOC 2 Type 2/ISO 27001/HIPAA 배지. Custom Agents + AI Meeting Notes + Enterprise Search 워크스페이스 번들. 강점: 기존 Notion 사용자 락인. 약점: Notion 워크스페이스 종속 + 한국어 지원 미흡 + 회의 워크플로우는 부가. **Kairos는 회의 우선 + 한국팀 + CODE 차별성으로 침투 가능**.

## 5. Gap Matrix (5축)

| 축 | Kairos | Granola | Fireflies | Notion AI |
|----|--------|---------|-----------|-----------|
| **1. Hero clarity** | PASS (한국어) | PASS | PASS | PASS |
| **2. 가치 제안 차별성** | CODE 4단계 + 한국어 + 팀 세컨드 브레인 | 봇 없이 시스템 오디오 + 1인 메모 결합 | recording-first + 100+ 언어 + 200+ AI Skills | 워크스페이스 통합 Custom Agents |
| **3. 가격 투명도** | ❌ 가격 페이지 없음 | ✅ $0/$14/$35 명시 | ⚠️ /pricing 별도 | ⚠️ Business 번들 |
| **4. 신뢰 신호** | ❌ 로고 0, 펀딩 0, 보안 배지 0 | ✅ 로고 8 + $125M + 유명인 추천 | ✅ 1M+ 기업 + G2 4.8/5 + SOC2/GDPR/HIPAA | ✅ 로고 4 + SOC2/ISO27001 |
| **5. 디자인/모던함** | 6/10 추정 | 9/10 | 7/10 | 8/10 |

### Δ vs Sprint 24 베이스라인

| 항목 | Sprint 24 | Sprint 25 | Δ |
|------|-----------|-----------|---|
| TTFV (랜딩→이해) | 255.5s | 추정 60~90s | **개선** (풀버전 단일화 효과) |
| 5초 룰 | PASS | PASS | 유지 |
| 30초 룰 | CONDITIONAL | PASS (조건부) | 미세 개선 |
| 1분 룰 | FAIL | CONDITIONAL | **개선** (정량 수치 추가) |
| 도입 결정 | No | **Maybe** | 개선 |

## 6. 도입 결정 = **Maybe**

**Yes 경향**: 한국어 회의 5-30명 팀 / 회의·노트·자료 통합 욕구 / AI 자동 분류 워크플로우 수용 팀

**No 경향**: 엔터프라이즈 보안 요구 (SOC 2 필수) → Fireflies/Notion / 1인 영어 사용자 → Granola / Notion 헤비유저 → Notion AI

**보류 이유**: 가격 페이지 부재로 ROI 계산 불가 / 실 제품 스크린샷 0개 / 신뢰 신호 전무로 B2B 결재 보고서 작성 어려움

## 7. Composite Curious Score = **6.17 / 10**

해석: hero/value는 강하지만 trust + visual proof 부족으로 "써보고 싶지만 결재는 못 한다" 구간. 베이스라인 5.x 대비 1단계 개선.

## 8. Sprint 25 권고 (Marketing / Hero copy)

### P0 (즉시)
1. **BUG-CURIOUS-001 [High]**: 신뢰 신호 0개. Hero 직후 (a) 베타/얼리액세스 고객 로고 3-5개 (없으면 "Used by [팀 종류 N개]"), (b) 보안 배지 (Clerk 인증 + Neon TLS + R2 암호화), (c) 창업자/팀 신뢰 (LinkedIn, "Built by [이름]")
2. **BUG-CURIOUS-002 [High]**: 실 제품 스크린샷 0개. Cmd+K Q&A 예시 + Inbox 화면 + Distill L1-L4 시각화 실 UI 캡처 3장 추가
3. **BUG-CURIOUS-003 [High]**: 가격 페이지 부재. `/pricing` 라우트 신설 + 3-tier 윤곽 또는 "Pricing coming soon — 베타 무료" 명시

### P1 (Sprint 25 내)
4. **BUG-CURIOUS-004 [Medium]**: "CODE" 약자 학습 부담. Hero 직후 "CODE = Capture · Organize · Distill · Express" 한 줄 명시
5. **BUG-CURIOUS-005 [Medium]**: 한국팀 타깃 명시 부재. "한국팀을 위한" 또는 "Built for Korean teams"
6. **BUG-CURIOUS-006 [Medium]**: "5분 설정" 분 단위 분해 표

### P2 (백로그)
7. **BL-CUR-001**: 15초 비디오 데모 (Granola 수준)
8. **BL-CUR-002**: ROI 계산기
9. **BL-CUR-003**: Comparison 페이지 (한국팀 관점)

### Hero copy A/B 후보

| 현재 | 대안 A (차별 강조) | 대안 B (결과 강조) |
|------|-----|-----|
| "AI가 정리합니다. 당신은 결정만 하세요." | "한국팀의 회의·노트·자료를 한 곳에서 자동 정리하는 세컨드 브레인." | "회의 끝나고 5분, AI가 요약·액션·인사이트까지 끝냅니다." |

## 9. 결함 등재

| ID | 분류 | 제목 |
|----|------|------|
| BUG-CURIOUS-001 | High | 신뢰 신호 0개 (로고/펀딩/보안 배지) |
| BUG-CURIOUS-002 | High | 실 제품 스크린샷 0개 |
| BUG-CURIOUS-003 | High | 가격 페이지 부재 |
| BUG-CURIOUS-004 | Medium | "CODE" 약자 첫 노출 시 풀어쓰기 부재 |
| BUG-CURIOUS-005 | Medium | 한국팀 타깃 명시 부재 |
| BUG-CURIOUS-006 | Medium | "5분 설정" 분해 부재 |
| BL-CUR-001 | Backlog | 15초 비디오 데모 |
| BL-CUR-002 | Backlog | ROI 계산기 |
| BL-CUR-003 | Backlog | 경쟁사 비교 페이지 |

## 10. 한계 / 잔여 리스크

- Playwright MCP 메인 세션 점유 → 텍스트/구조 기반 평가만 (시각 평가 한계, 디자인 6/10은 추정)
- Clerk Google OAuth 자동화 차단 → 가입→첫 노트 실 TTFV 측정 불가, 추정치만
- 스크린샷 캡처 0장 (디렉터리만 생성)

## 11. 핵심 인사이트

1. **약점은 hero copy가 아니라 social proof / visual proof**. 풀버전 단일화로 hero/value 자체는 충분히 강함. 다음 wedge는 신뢰 신호.
2. **한국팀 차별성 명시 부재**. 100+ 언어 vs 한국어 1개는 외형상 열세 → "한국팀 전용 설계" 명시 필요.
3. **Sprint 24 → Sprint 25 개선 폭은 명확** (FAIL → CONDITIONAL → PASS 진행).
