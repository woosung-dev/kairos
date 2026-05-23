# ADR-005: 랜딩 페이지 AIDA 리디자인

**날짜:** 2026-04-04
**상태:** 확정
**결정자:** woo sung

## 결정
"t-combined" 디자인(T1 디자인 + T3 후킹 합체)으로 랜딩 페이지 리디자인.
AIDA+α 프레임워크 7섹션 구조. `data-theme="landing"` + `prefers-color-scheme` 자동 전환.

## 배경

### 문제
- 기존 랜딩: "회의가 끝나면, 지식이 시작됩니다" — 기능 나열 중심 (Features 4카드 + Demo 목업 + Pricing)
- "회의 도구"로 인식될 위험. Kairos의 핵심 가치(세컨드 브레인, CODE 파이프라인, Distill 자동화, 복리 지식)가 전달되지 않음
- 다크 모드만 지원 (data-theme="light" 강제)

### 검토한 방안

| 방안 | 메시지 | 디자인 | 점수 |
|------|--------|--------|------|
| T1 Teal | "AI가 정리합니다. 당신은 결정만" | 떠있는 카드, 4색, 깊이감 | 8.17 |
| T2 Indigo | "데이터가 쌓일수록 팀이 똑똑해진다" | Bento Grid, 성장 그래프 | 7.67 |
| T3 Dark | "끝난 프로젝트의 교훈이 다시 살아난다" | 검색 데모, Before/After, 타임라인 | 8.17 |
| **t-combined (채택)** | **T1 메시지 + T3 후킹** | **T1 디자인 + T3 구조** | **9.0** |

### 채택 이유
- T1과 T3가 동점이지만 강점이 정반대 (T1=디자인 최강, T3=후킹 최강) → 합치면 시너지
- AIDA+α 프레임워크: 약속→증거→공감→구조→미래→신뢰→행동. 중복 없는 7섹션
- 소크라테스 논증으로 각 요소의 필요성 검증 완료

## 섹션 구조 (AIDA+α)

```
1. Hero — 약속 ("AI가 정리합니다. 당신은 결정만")
2. SearchDemo — 증거 (교훈 재활용 Cmd+K 시나리오)
3. BeforeAfter — 공감 ("이 문제들, 익숙하지 않으세요?")
4. Pipeline — 구조 (CODE C→O→D→E + Distill 하이라이트)
5. EvolutionTimeline — 미래 (W1→M1→Q1)
6. Stats — 신뢰 (95% / 12x / 24h)
7. CTA — 행동 (다크 반전 박스)
```

## 다크/라이트 전환 전략

`data-theme="landing"` 스코프 방식:
- `:root` (다크, 대시보드) — 변경 없음
- `[data-theme="light"]` — 변경 없음
- `[data-theme="landing"]` — 라이트 기본 + `@media(prefers-color-scheme:dark)` 자동 전환

대시보드 다크 테마에 영향 없이 랜딩만 OS 설정에 따라 자동 전환.

## 파일 변경 목록

### 신규 (8개)
- `frontend/src/hooks/use-reveal.ts` — IntersectionObserver 입장 애니메이션 훅
- `frontend/src/components/landing/search-demo-section.tsx`
- `frontend/src/components/landing/before-after-section.tsx`
- `frontend/src/components/landing/pipeline-section.tsx`
- `frontend/src/components/landing/evolution-timeline.tsx`
- `frontend/src/components/landing/stats-section.tsx`
- `frontend/src/components/landing/cta-section.tsx`
- `docs/dev-log/adr/005-landing-redesign-aida.md` (본 문서)

### 수정 (5개)
- `frontend/src/app/globals.css` — `[data-theme="landing"]` + 애니메이션 + 접근성
- `frontend/src/app/page.tsx` — `data-theme='light'` → `data-theme='landing'`
- `frontend/src/components/landing/hero-section.tsx` — 완전 재작성
- `frontend/src/components/landing/landing-nav.tsx` — 링크/스타일 업데이트
- `frontend/src/components/landing/footer.tsx` — 심플 센터
- `frontend/src/components/landing/landing-page.tsx` — 7섹션 재구성

### 미사용 (삭제 대기)
- `features-section.tsx`, `demo-section.tsx`, `pricing-section.tsx`
