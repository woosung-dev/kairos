# Curious 경쟁사 비교 — Granola (granola.ai)

> 비교 일자: 2026-05-19. Granola 가입 흐름은 macOS native app 진입 → 측정 불가. **Landing 시각 평가**로 대체 (MISSION fallback).

## Granola 첫인상

### 5초 룰 — **PASS**
- 본 것: "AI notepad for back-to-back meetings"
- 페르소나 매칭 즉시: back-to-back meeting을 하는 사람 → 본인
- evidence: `curious-06-granola-landing.png`

### 30초 룰 — **PASS**
- 발견: Series C 표시 / Pricing 명시 / How it works / Use case 5종 (CD/1on1/UI/Pitch/Standup) / 고객 로고
- 가입 의향: 7/10 (macOS 사용자 기준)

### 1분 룰 — **PASS, Yes**
- 자기보고: "back-to-back 미팅 페르소나 정확히 일치. $0 free tier로 시작 가능. macOS-only인 것만 단점."

## 가격 정책 (Pricing)

| Tier | 가격/월 | 비고 |
|---|---|---|
| Personal | $0 | free forever (제한 있음) |
| Business | $14 | per user (대부분 회사) |
| Enterprise | $35 | per user (SSO/SOC2 필요 시) |

evidence: `curious-07-granola-pricing.png`

## 신뢰 신호

- **Series C 자금 조달 명시** — investor list (Stripe Climate / a16z / NEA / Spark Capital)
- **고객 로고** — Stripe / Linear / Snap / Lightspeed / Sequoia / Anthropic
- **Privacy / SOC2 / Terms** 링크 footer + privacy page
- **사용 사례별 use case page** (1on1/Customer Discovery/UX Reviews/Pitch/Standup)

## Granola vs Kairos 비교표

| 차원 | Kairos | Granola | Winner |
|---|---|---|---|
| 5초 룰 | FAIL | **PASS** | Granola |
| 30초 룰 | FAIL | **PASS** | Granola |
| 1분 룰 | Maybe | **PASS, Yes** | Granola |
| TTFV (가입→첫 가치) | 255.5초 | n/a (macOS native) | n/a |
| 가입 마찰 (1-10) | 6 (ToS 없음) | n/a | — |
| 디자인 (1-10) | 6 (단조로움) | **9** | Granola |
| 신뢰 신호 (1-10) | 2 | **9** | Granola |
| 가격 명시 (1-10) | 0 | **9** | Granola |
| Use case 명시 | 0 | **9** | Granola |
| RAG/Q&A 인용 신뢰성 | **8** (한국어 + 소스 인용) | 미측정 | Kairos (추정) |
| 한국어 native | **10** | 0 (영어 only) | Kairos |
| 도입 결정 | Maybe→No | **Yes** | Granola |

## Kairos가 Granola를 대체할 수 있는가? (자기보고)

> "현재 상태로는 **아니다**. Kairos만의 강점 = 'RAG /ask + 소스 인용 + 한국어 native UI' 3개는 명확하지만, 5초/30초 landing 안에 *증거*로 보이지 않는다. PM이 evaluation에 올리려면 (1) 5초 landing에서 '한국어 회의 RAG 첫 도구' 같은 wedge claim, (2) Granola/Otter/Notion 비교표 1개, (3) Pricing 페이지 1개, (4) Privacy/ToS 링크가 필요. **Sprint 24+에서 '결정적 30초' wedge를 증명하지 못하면 사용자 acquisition은 차단된다** (gemini F2 직면)."

## 후속 권고 (Sprint 24+ 또는 별도 마케팅 sprint)

1. **T-LAND-01 (P0)** — Landing 5초 룰 PASS 위한 wedge headline
2. **T-LAND-02 (P1)** — Granola use case 패턴 (5 카테고리) 한국어 회의 매핑
3. **T-LAND-03 (P1)** — Pricing 1줄 + Privacy/ToS 링크 추가
4. **T-LAND-04 (P2)** — Granola/Notion AI 비교표 추가 (한국어 회의 RAG 차별점)
