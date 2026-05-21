# ui-ux-pro-max 5축 평가 — Sprint 25 Casual

대상: `https://kairos-zeta-ebon.vercel.app` 랜딩 (인증 게이트 안쪽은 Clerk dev 인스턴스로 우회 불가, 정적 HTML 분석)
평가자: Casual 페르소나 + ui-ux-pro-max v2.5.0 프레임워크
도구 한계: Playwright MCP 점유 → WebFetch + 원본 HTML curl 정적 분석 fallback

## 점수 요약

| 축 | 점수 (0-10) | 근거 (요약) | 우선 개선점 |
|---|---|---|---|
| 타이포그래피 | 8.0 | Pretendard Variable + Satoshi (display) + Geist Mono 3축 페어링. 한글 가독성 양호. clamp() 반응형 + letter-spacing -0.035em로 한글 헤드 가독성 보호. line-height 1.8/1.7 본문 ample. 단 본문 17px 가 모바일 16px 권고 대비 살짝 큼(허용 범위). | mono 폰트(Geist)는 영문 전용 — 한글 fallback이 Pretendard로 가는지 확인 필요. 미세 폰트 사이즈 토큰 일원화. |
| 색상 | 7.5 | accent `#0FA889` (teal/emerald) + 슬레이트 무채. CSS 변수로 토큰화 (`--accent`, `--accent-subtle`, `--accent-bd`, `--text-primary/secondary/muted`, `--cat-project/area/resource/archive`). dark 테마 우선 + `data-theme="landing"` 별도 스코프. accent 단일 + 카테고리 4색은 분명한 시스템. | accent-subtle 위 14px gray 보조 텍스트는 다크 모드에서 4.5:1 미달 위험 — 실측 필요. CTA 박스의 `#94A3B8` on dark bg는 의문 (대비 추정). |
| 레이아웃 | 8.5 | max-w 800/620/960/640/700 명확한 단계 + 16/24/48/72 8pt 그리드 준수. 4개 CODE 카드는 modular grid (모바일 stack, 데스크탑 row). w1/m1/q1 타임라인 좌측 수직 라인 + dot은 정보계층 분명. fixed nav + backdrop-blur 88% 투명. | nav 모바일에서 "기능/요금"은 `hidden sm:block` 으로 숨김 → 모바일에서 가격 도달 경로 약함. CTA 섹션 padding-top 152px hero가 모바일에서 과도할 수 있음. |
| 모션 | 7.0 | `landing-reveal` reveal 애니메이션 클래스 + `active:scale-[0.97]` press feedback + `hover:-translate-y-0.5` 카드. duration 200ms 적정. `prefers-reduced-motion` 대응 여부는 정적 분석 한계로 미확인 — 후속 검증 BL 후보. | `prefers-reduced-motion` 미디어쿼리 적용 여부 확인. scroll-reveal IntersectionObserver 사용 시 a11y 대체 텍스트 보장. |
| 일관성 | 8.0 | radius `var(--radius-lg)` 통일, shadow `var(--shadow-card/card-hover)` 두 단계 통일, mono font (Geist)로 메타데이터/KBD 일관 사용, "WITHOUT/WITH KAIROS" 카드 대칭. CTA 버튼 min-height 36/44 두 단계 명확. | "시작하기"(36px) vs "무료로 시작하기"(44px) vs "무료 체험 시작"(44px) — CTA 카피 3종이 의도와 다르게 보일 수 있음. 통일 후보: "무료로 시작하기" 단일. |

**총점 (가중 평균, 0.25/0.20/0.20/0.15/0.20)**: **7.85 / 10**

가중치 근거: 타이포·일관성·색상이 한글 SaaS landing에서 신뢰 신호로 가장 크게 작용. 레이아웃 다음. 모션은 보조.

## 상세 분석

### 1. 타이포그래피 (8.0)

발견 폰트 링크:
- `https://api.fontshare.com/v2/css?f[]=satoshi@400,500,600,700&display=swap` — display
- `https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500&display=swap` — mono
- `https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css` — body(한글)

**잘된 점**:
- `font-display: swap` 명시 → FOIT 방지 (rule `font-loading` PASS)
- Pretendard Variable Dynamic Subset → 한글 가독성 + 번들 크기 최적화
- clamp(32px, 5.5vw, 52px) hero h1 → 반응형 type scale 우수
- letter-spacing -0.035em → 한글 헤드 좁은 좌우 여백 보정 (한국어 SaaS 표준)
- line-height 1.8 (본문) / 1.65 (카드) → `line-height` rule 통과

**약점**:
- Geist Mono는 한글 글리프 없음 → "L1 콘텐츠 요약" 같은 mixed 텍스트에서 한글이 Pretendard로 빠지는데 mono 11~12px 크기에서 한글이 mono 폭과 어울리지 않음
- 본문 17px 모바일에서는 16px가 표준 — iOS Safari auto-zoom 방어선 (`readable-font-size` rule 부합)

### 2. 색상 (7.5)

토큰 (정적 분석 추정):
- `--accent: #0FA889 (rgba 15,168,137)` — primary teal/emerald
- `--accent-subtle` — accent 5-10% tint 배경
- `--accent-bd` — accent 외곽선
- `--text-primary/secondary/muted` — 3단계 grayscale
- `--cat-project/area/resource/archive` — 4색 카테고리 (L1-L4 매핑)
- `data-theme="dark"` default + `data-theme="landing"` 별도 스코프

**잘된 점**:
- semantic token 일관 적용 (`color-semantic` rule PASS)
- accent + neutral 단순화된 팔레트 (SaaS B2B 적합)
- L1-L4 카테고리 색 분리로 정보 계층 시각화 (`color-not-decorative-only` rule PASS — 텍스트와 함께 사용)

**약점**:
- dark 기본 테마인데 light/dark 토큰 분리 명시가 HTML에서 안 보임 — light mode 검증 필요
- CTA 박스 `color:#94A3B8` (slate-400) on `var(--cta-box-bg)` 다크 배경 → 대비 추정 4.0-4.5:1 경계 (`color-accessible-pairs` 경계선)
- "Cmd+K — 정리된 지식이 이렇게 활용됩니다" `text-muted` 색 (slate-500 추정) on subtle bg → 11px size + 낮은 대비

### 3. 레이아웃 (8.5)

**잘된 점**:
- max-w 단계 (800/620/960/700/600) → `container-width` rule PASS, 단계가 의미적
- 8pt spacing scale 거의 완벽 (py-3.5/4/5/6/8/12/20, mb-1/2/3/5/7/8/12, gap-2.5/3/5)
- mobile-first grid: `grid-cols-1 md:grid-cols-2/3` → `mobile-first` rule PASS
- safe nav: `fixed top-0` + `pt-[152px]` hero → fixed 충돌 방지
- CODE 4 카드: 모바일 stack → 데스크탑 row, 화살표는 90/0 회전으로 방향성 표현 (`hierarchy-motion` 부분 PASS)
- 타임라인 W1/M1/Q1: 좌측 수직 라인 + dot anchor → 정보 시간축 명확

**약점**:
- nav `기능`/`요금` 모바일에서 `hidden sm:block` 으로 숨김 → 모바일에서 가격까지 도달은 hero CTA → CTA 박스 스크롤 의존. 햄버거 메뉴 없음 (`bottom-nav-limit` 무관, 데스크탑 우선 결정)
- "요금" 링크가 `#cta` 앵커 → 사용자 기대 위반 (Curious BUG-CURIOUS-003 가능성 — 가격표 부재)

### 4. 모션 (7.0)

**잘된 점**:
- `transition-all duration-200` micro-interaction (`duration-timing` rule PASS)
- `active:scale-[0.97]` press feedback on CTA (`scale-feedback` rule PASS)
- `hover:-translate-y-0.5` 카드 hover (subtle, transform-only → `transform-performance` rule PASS)
- `backdrop-filter: blur(12px)` nav (`blur-purpose` 모호 — 장식적)

**약점 / 미확인**:
- `landing-reveal` 클래스의 keyframe 정의가 외부 CSS chunk에 있어 정적 분석 불가 — IntersectionObserver scroll-reveal 추정
- `prefers-reduced-motion` 대응 여부 HTML에서 확인 불가 → BL 후보
- 스피너/로딩 상태 없음 (랜딩이라 적용 안 됨)

### 5. 일관성 (8.0)

**잘된 점**:
- radius `var(--radius-lg)` 단일 토큰 (CTA, badge, card)
- shadow 2단계 (`--shadow-card`, `--shadow-card-hover`) 통일
- mono font (Geist) → 메타정보/KBD/숫자 일관 (`number-tabular` 의도)
- `WITHOUT KAIROS` / `WITH KAIROS` 카드 헤더 mono uppercase + letter-spacing 0.04em 통일
- CTA 버튼 두 사이즈 (36px nav, 44px 본문) — 44px가 mobile touch target 표준 (`touch-target-size` rule PASS)

**약점**:
- 최상단 nav `시작하기` (36px) vs hero `무료로 시작하기` (44px) vs CTA 박스 `무료 체험 시작` (44px) — 동일 액션 3개 카피로 분기 → 사용자 인지 부담
- 통일 권고: 메인 CTA = "무료로 시작하기" 1종으로 통일, secondary는 색만 분리

## 우선 개선점 (Sprint 25 권고 후보)

1. **[BL-CAS-001 / Medium]** 모바일 nav 햄버거 메뉴 추가 — 현재 sm 미만에서 `기능`/`요금` 숨김 → 핵심 SaaS 정보 접근성 저하
2. **[BL-CAS-002 / Medium]** `prefers-reduced-motion` 미디어쿼리 명시 대응 — landing-reveal 애니메이션
3. **[BL-CAS-003 / Low]** CTA 카피 통일 — "무료로 시작하기" 단일화
4. **[BL-CAS-004 / Low]** 본문 모바일 17px → 16px 통일
5. **[BL-CAS-005 / Medium]** light mode 대비 검증 — dark 우선 디자인이라 light 토큰 미사용 가능성
6. **[BL-CAS-006 / High]** "요금" → `#cta` 앵커 = 가격표 부재 — Curious BUG와 공통 (가격 페이지 또는 plan 비교 섹션 신설)
