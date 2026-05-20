# Curious TTFV Measurement — Kairos 가입 → 첫 AI 요약

> stopwatch evidence: `mcp__playwright__browser_evaluate` Date.now() 기준
> 측정 일자: 2026-05-19 KST 23:09 (UTC 14:09)

## 전체 TTFV: **255.5초 / 4분 16초**

## 단계별 timestamp

| 단계 | T (epoch ms) | ISO | 누적 (sec) | 단계 소요 (sec) |
|---|---|---|---|---|
| **T0**: 시작하기 클릭 (signup 시작) | 1779199763824 | 2026-05-19T14:09:23.824Z | 0.0 | — |
| 이메일 입력 완료 | (생략) | — | ~25 | 25 |
| Verification 코드 입력 (`424242` clerk test) | (생략) | — | ~55 | 30 |
| Clerk callback 완료 (workspace seed 직전) | (생략) | — | ~110 | 55 |
| **Dashboard 도착** (가입 완료) | 1779199892526 | 2026-05-19T14:11:32.526Z | **128.7** | 18.7 (workspace seed) |
| Dashboard 둘러봄 (3초 멈춤) | — | — | ~135 | ~7 |
| 회의 추가 버튼 클릭 (사이드바 발견) | — | — | ~150 | ~15 |
| 회의 제목 입력 ("Q3 OKR 리뷰") | — | — | ~160 | ~10 |
| 텍스트 본문 입력 (500자) | — | — | ~170 | ~10 |
| **AI 분석 시작** 클릭 | 1779199936279 | 2026-05-19T14:12:16.279Z | 172.5 | 2.5 |
| 처리 중 화면 (Gemini call) | — | — | ~250 | ~78 |
| **T1**: AI 요약 visible (NORTH STAR) | 1779200019364 | 2026-05-19T14:13:39.364Z | **255.5** | ~5 |

## 단계별 분석

### Stage 1 — Clerk 가입 (128.7초, 50%)
- 이메일 입력 → verification → callback → workspace seed
- 마찰: verification 코드 단계 표준이지만 +30s
- 한국어 UI 중에 영어 placeholder "Create a password" 잔재
- ToS / Privacy 링크 부재 (-2 신뢰 신호)

### Stage 2 — Onboarding 부재 → self-discovery (43.8초)
- 🚨 **Sprint 22 OBN-01~04 (onboarding step 1~4)가 실제 dashboard에 발화되지 않음**
- 신규 사용자가 "다음 뭐?" 답을 self-discovery로 찾아야 함
- "회의 추가" 발견까지 ~15초 (사이드바·hero·빠른접근 3곳에 있어서 빠름)
- 텍스트 입력 + AI 분석 클릭까지 ~28초

### Stage 3 — AI 처리 (83.1초)
- Gemini 호출 ~78초 (500자 input)
- UX "AI 분석 중 / 처리가 완료되면 자동으로 업데이트됩니다" 친절
- 그러나 **진행도 표시 0%** — 사용자는 "끝났나? 멈췄나?" 답답

## TTFV 단축 방안 (Sprint 24+ 후속 T-N)

| 후속 | 단계 | 예상 단축 (sec) | 비용 |
|---|---|---|---|
| Clerk verification skip (test mode) | 1 | -30 | 0 (개발 환경만) |
| Onboarding step 1~4 실제 발화 (OBN-04 dogfood fix) | 2 | -15~30 | M |
| AI 처리 진행도 표시 + 부분 결과 streaming | 3 | -50~70 perceived | H |
| Onboarding "sample 회의" 옵션 (1-click 데모) | 2 | -40 | L |

**목표 TTFV**: 60-90초 (Granola의 5초 룰 PASS 후 첫 가치 직접 측정 가능 시점)

## 비교 대상

- **Granola TTFV** (web 측정 불가, macOS app 진입 후 첫 가치까지 시간 ≥ Kairos 일 가능성)
- **Notion AI** (기존 계정 가정, TTFV n/a)

## 결론

Kairos TTFV 255.5초는 nominal 수치. 그러나:
- Landing 5초/30초 룰 FAIL → TTFV 발화될 기회 자체가 없음
- 가입 도달 사용자 한정 4분 16초 — Granola의 perceived "1분 안에 가치 본다" 인상 대비 열위
- **사용자 acquisition을 위한 진짜 목표 TTFV는 landing 30초 룰 PASS + 가입 후 60초 안에 첫 가치**

→ Sprint 24 T-LAND-01 (Landing wedge) + T-OBN-05 (Onboarding 발화) + T-AI-DATE (hallucinate fix) 3개 P0 권장.
