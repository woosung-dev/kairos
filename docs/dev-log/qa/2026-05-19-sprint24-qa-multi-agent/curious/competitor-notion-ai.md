# Curious 경쟁사 비교 — Notion AI (notion.so)

> 비교 일자: 2026-05-19. Notion AI는 기존 계정 가정 (OAuth 차단). **Landing 시각 + 공개 정보 분석**.

## Notion AI 첫인상

### 5초 룰 — **PASS**
- 본 것: "나를 위한 전담 AI 팀"
- "Notion = 워크스페이스 + AI" 정체성 즉시
- evidence: `curious-08-notion-ai.png`

### 30초 룰 — **PASS**
- 발견: Free / Plus / Business / Enterprise 4 tier / SOC2 / ISO 27001 / "AI 학습 제외" 정책 명시
- 가입 의향: 8/10 (이미 사용 중이면 추가 features 추가)

## 신뢰 신호

- **SOC2 + ISO 27001** 인증 명시
- "Your data is yours alone" — AI 학습 제외 정책
- 글로벌 회사 (Coda, Anthropic, Figma 등 고객 logo)
- Free/Plus/Business/Enterprise 가격 명시

## Notion AI vs Kairos — RAG/Q&A 관점

### Kairos 강점
1. **한국어 native RAG** — Notion AI는 영어 우선 (한국어 답변은 가능하나 source 인용 한국어 매칭 약함)
2. **소스 인용 클릭 가능** — Kairos는 회의/노트 detail로 deep-link, Notion AI는 page 링크
3. **회의 특화** — Kairos는 STT + 화자 분리 + 액션 추출. Notion AI는 일반 텍스트 우선

### Notion AI 강점
1. **무한 데이터 통합** — 모든 Notion DB / page 검색 가능
2. **DB query + AI** — Notion DB schema + AI 조합
3. **Export 풀세트** — Notion 자체 export (HTML/PDF/MD/CSV)
4. **신뢰 인증** — SOC2 / ISO 27001 명시
5. **무료 tier** — 무제한 AI query 일부

### 둘 다 약점
- 한국어 회의 STT 정확도 (모두 미측정)
- 회의 화자 분리 (Notion AI 미지원)

## 비교표

| 차원 | Kairos | Notion AI | Winner |
|---|---|---|---|
| RAG/Q&A 정확도 (회의 내용) | **8** (한국어 + 인용) | 미측정 | Kairos (추정) |
| RAG/Q&A 정확도 (지식 베이스) | 미측정 | **9** (Notion DB) | Notion AI |
| 한국어 native | **10** | 7 (지원하나 영어 우선) | Kairos |
| 회의 특화 (STT/화자분리) | **9** | 0 (지원 안 함) | Kairos |
| 통합 데이터 범위 | 4 (회의/노트/파일만) | **10** (전 워크스페이스) | Notion AI |
| Export | 6 (MD/JSON) | **9** (HTML/PDF/MD/CSV) | Notion AI |
| 신뢰 신호 | 2 | **9** (SOC2/ISO 27001) | Notion AI |
| 가격 명시 | 0 | **8** (4 tier) | Notion AI |
| 도입 결정 | Maybe→No | **Yes** (이미 사용) | Notion AI |

## Notion AI 도입 사용자가 Kairos 추가 도입할 이유?

**답**: 한국어 회의 + STT + 화자 분리 + 액션 자동 추출이 필요한 PM/매니저라면 Notion AI를 보완하는 도구로 Kairos 검토 가능. 그러나:
- Notion AI 사용자 = Notion 워크스페이스 사용자 = 워크플로우 = Notion → Notion AI에 추가 도구 진입 마찰
- Kairos 도입 결정 위해서는 **"Notion에 회의 transcribe 안 되는데 Kairos는 된다"** 같은 wedge 필요
- + 가격 명시 + Privacy/ToS + Notion API 통합 (export to Notion) 가 있으면 dual-tool 시나리오 가능

## 후속 권고

1. **T-INT-NOTION (P2)** — Export to Notion API 통합 검토 (회의 요약을 Notion page로 직접 push)
2. **Marketing wedge**: "Notion AI는 텍스트만, Kairos는 한국어 회의 STT + 화자분리" 한 줄
