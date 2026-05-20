# TTFV Gap Analysis: Kairos vs Granola vs Notion AI (North Star)

> **gemini F2 직면**: "버그 39개보다, Granola를 쓰는 사용자가 Kairos로 넘어와야 할 '결정적 30초'를 증명하거나 격차를 직면"

## 측정 일자: 2026-05-19 KST 23:09 (UTC 14:09)

## 측정자: Curious 페르소나 (AI 회의 도구 도입 검토 PM)

---

## TTFV 표

| 도구 | 가입 시작 | 첫 가치 본 순간 | TTFV (초) | 5초 룰 | 30초 룰 | 1분 룰 |
|---|---|---|---|---|---|---|
| **Kairos** | 14:09:23.824Z | 14:13:39.364Z | **255.5** | FAIL | FAIL | Maybe |
| **Granola** | n/a (macOS native) | n/a (web 측정 불가) | n/a | **PASS** | **PASS** | **PASS, Yes** |
| **Notion AI** | (기존 계정) | n/a | n/a | **PASS** | **PASS** | **PASS** |

> Granola TTFV web 측정 불가 (macOS app). 그러나 **landing TTFV** (= "이 도구가 뭐고 가입할 가치가 있는가" 판단까지) 비교:
> - Granola: **5초** (5초 룰 PASS = 가치 판단 완료)
> - Kairos: **>30초** (FAIL = 가치 판단 지속 실패)

---

## Gap 분석

### 격차의 주된 원인 (Sprint 24+ 후속 권고)

1. **Landing이 단일 viewport** — Features/How it works/Social proof/Pricing 섹션 0개
2. **Onboarding step 1~4 미발화** — Sprint 22 OBN-01~04 dogfood fix 후에도 신규 가입자에게 실제 발화 안 됨 → 회귀 가능성 (Sentinel 정적 분석은 PASS 였으나 dogfood에서 FAIL)
3. **핵심 wedge 미증명** — "한국어 회의 RAG + 소스 인용"이 landing에 0 표시
4. **신뢰 신호 부재** — 가격/약관/SOC2 등 0 (Granola Series C / Notion AI SOC2 대비)
5. **액션 아이템 hallucinate (P0)** — 마감일 2024년 자동 생성 → PM 신뢰 차단

### Kairos가 Granola를 대체할 수 있는 wedge (3개)

| Wedge | 검증된 강점 | Granola 격차 | Notion AI 격차 |
|---|---|---|---|
| **한국어 회의 native** | UI / RAG 답변 / 소스 인용 모두 한국어 | Granola 영어 only | Notion AI 한국어 약함 |
| **소스 인용 클릭 가능** | 회의/노트 deep-link, evidence 제공 | Granola 미측정 | Notion AI page link (회의 detail 약함) |
| **회의 STT + 화자 분리 + 액션 추출** | Sprint 11 audio record / Sprint 19~22 promote pipeline | Granola 동급 | Notion AI 미지원 |

하지만 **이 3개 wedge가 landing 5초/30초 안에 보이지 않는다** → 사용자 acquisition 차단.

---

## 30초 룰 달성 여부

**결과: FAIL**

Kairos의 30초 룰을 PASS 하려면 다음 모두 필요:
1. Landing headline에 한국어 회의 RAG wedge 명시 ("한국어 회의를 위한 AI 세컨드 브레인" 등)
2. 30초 안에 demo screenshot / GIF / video 1개 노출
3. Use case 카테고리 (Granola 패턴: 1on1 / 회의록 / 의사결정 / 액션 추적)
4. Pricing 1줄 + Privacy/ToS 링크

---

## 결정적 30초 결론 (gemini F2 응답)

> "Kairos 30초 룰: **FAIL**"
>
> "Granola → Kairos" 결정적 이유 후보 (현재 상태):
> - **없음**.
>
> 잠재력은 "한국어 native RAG + 소스 인용 + 회의/노트/자료 통합" 3개 wedge. 그러나 landing에서 0초 증거 → 사용자 acquisition 차단.
>
> **Sprint 24+ 마케팅 sprint 필요**: T-LAND-01 (wedge headline) + T-LAND-02 (use case) + T-LAND-03 (pricing/ToS).

---

## Sprint 24+ 후속 권고 (TTFV 단축 / 30초 룰 달성)

### P0 (Sprint 24 1차 후보)

| 후속 | 영역 | 효과 | 비용 |
|---|---|---|---|
| **T-LAND-01** | Landing wedge headline + RAG demo screenshot | 5초/30초 룰 PASS 직접 목표 | M (FE 작업 + copy) |
| **T-OBN-05** | Onboarding step 1~4 발화 검증 (Sprint 22 회귀 fix) | 신규 사용자 self-discovery 부담 -50% | M (dogfood + fix) |
| **T-AI-DATE** | 액션 아이템 마감일 hallucinate 수정 | PM 신뢰 회복 (P0 차단 요인) | L (prompt fix) |

### P1 (Sprint 24+ 또는 별도 marketing sprint)

| 후속 | 영역 | 효과 | 비용 |
|---|---|---|---|
| **T-CMD-K-FIX** | Dashboard 추천 질문 dead-click fix | UX 마찰 -1 | L |
| **T-LAND-02** | Use case 카테고리 (5종) | 페르소나 매칭 직접화 | M |
| **T-LAND-03** | Pricing 1줄 + Privacy/ToS | B2B evaluation 진입 차단 해소 | L (legal 필요) |

### P2 (별도 sprint)

| 후속 | 영역 | 효과 |
|---|---|---|
| **T-INT-NOTION** | Export to Notion API | Dual-tool 시나리오 |
| **T-EXP-PDF** | PDF export 추가 | 외부 공유 마찰 |

---

## 본 산출물의 가치 (gemini F2 응답 종결)

이 문서는 단순 QA 보고서를 넘어 **Kairos의 사용자 acquisition 가능성에 대한 현실 직면**:

- Sentinel이 정적 분석으로 ALL PASS 했지만 **실제 사용자가 landing에서 5초/30초 안에 가치 인식 못함**
- 액션 아이템 hallucinate (P0)는 dogfood 없이 발견 못 했음 → multi-agent QA의 직접 가치
- 결정적 30초 wedge 증명 없이는 Granola/Notion AI 대비 acquisition 차단

**Sprint 24가 ADR-019 Phase B (Gemini 모델 swap)만 다룬다면 본 wedge 격차는 해소되지 않음**. T-LAND-01/T-OBN-05/T-AI-DATE 3 P0를 Sprint 24+ 또는 별도 marketing/onboarding sprint로 진입 권장.
