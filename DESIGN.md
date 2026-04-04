# Design System — Kairos

## Product Context
- **What this is:** 팀의 세컨드 브레인 — 프로젝트 진행 중 쌓이는 회의, 아이디어, 자료를 AI가 자동 구조화하고 인사이트를 추출하는 복리 지식 플랫폼.
- **Who it's for:** 매주 3~5회 회의하는 팀 리더/PM, 여러 프로젝트를 관리하는 중간관리자/CEO
- **Space/industry:** 지식 관리 + AI 검색 (NotebookLM, Notion, Linear 교차점)
- **Project type:** SaaS 웹 앱 (다크모드 우선, 데이터 밀도 높음)

## Aesthetic Direction
- **Direction:** Industrial/Utilitarian
- **Decoration level:** Minimal — 타이포와 간격이 모든 걸 함. 장식 요소 없음.
- **Mood:** Linear의 정밀함 + NotebookLM의 "뭐든 물어봐" 에너지. 데이터가 주인공인 도구. 꼽꼽한 밀도, 모노스페이스 액센트.
- **Reference sites:** linear.app, notebooklm.google, notion.so

## Typography
- **Display/Hero:** Satoshi (700/600) — 샤프한 기하학적 산세리프. 한국어 본문과 충돌 없이 제목에서 임팩트.
- **Body:** Pretendard Variable (400/500) — 한국어 최적화 산세리프. Apple SD Gothic Neo 대비 가독성 우위.
- **UI/Labels:** Pretendard Variable (500)
- **Data/Tables:** Geist Mono (400/500) — tabular-nums 지원, 숫자 정렬에 최적.
- **Code:** Geist Mono
- **Loading:**
  - Satoshi: Google Fonts (`family=Satoshi:wght@400;500;600;700`)
  - Pretendard: CDN (`cdn.jsdelivr.net/gh/orioncactus/pretendard`)
  - Geist Mono: Google Fonts (`family=Geist+Mono:wght@400;500`)
- **Scale:**
  - h1: 32px / 700 (Satoshi)
  - h2: 24px / 600 (Satoshi)
  - h3: 18px / 600 (Satoshi)
  - body: 15px / 400 (Pretendard) / line-height 1.6
  - small: 13px / 400 (Pretendard)
  - caption: 11px / 400 (Geist Mono)

## Color
- **Approach:** Restrained — 1 accent + neutrals. 색상은 아껴서, 정확하게.

### Dark Mode (기본)
- **Background:** #0A0A0B
- **Surface:** #141416
- **Surface Hover:** #1A1A1E
- **Surface Active:** #222226
- **Border:** #2A2A2E
- **Border Subtle:** #1E1E22
- **Text Primary:** #EDEDEF
- **Text Secondary:** #8E8E93
- **Text Muted:** #5C5C63

### Light Mode
- **Background:** #FAFAFA
- **Surface:** #FFFFFF
- **Surface Hover:** #F5F5F5
- **Surface Active:** #EFEFEF
- **Border:** #E5E5E5
- **Border Subtle:** #F0F0F0
- **Text Primary:** #111111
- **Text Secondary:** #6B6B73
- **Text Muted:** #9E9EA6

### Accent
- **Primary (Dark):** #3ECFB4 — "시간의 길목" 청록. 다크 배경에서 시선을 끔.
- **Primary (Light):** #0FA889 — 라이트 배경용 채도 조절.
- **Accent Hover:** #35B39C
- **Accent Subtle:** rgba(62,207,180,0.1)

### Project Status Colors
- **Active:** #3ECFB4 (청록) — 진행 중 프로젝트
- **Completed:** #F0963C (주황) — 완료된 프로젝트
- **Archived:** #6B6B73 (회색) — 비활성/보관

### Semantic
- **Success:** #34D399
- **Warning:** #FBBF24
- **Error:** #F87171
- **Info:** #60A5FA

### Dark Mode Strategy
- 채도 10~20% 낮춤
- Surface 레이어로 깊이 표현 (bg → surface → surface-hover → surface-active)
- 텍스트는 순백(#FFF) 대신 약간 뮤트된 #EDEDEF

## Spacing
- **Base unit:** 4px
- **Density:** Compact (Linear 수준)
- **Scale:** 2xs(2px) xs(4px) sm(8px) md(16px) lg(24px) xl(32px) 2xl(48px) 3xl(64px)

## Layout
- **Approach:** C|D 2-Panel (ADR-006 §3)
- **구조:**
  - 좌측 사이드바: 고정 220px (프로젝트 네비게이션 + 소스 트리)
  - 중앙 콘텐츠: flex-1 (메인 작업 영역)
  - RAG: 상단 검색바 상시 + Cmd+K 슬라이드 오버레이 380px (상시 패널 아님)
- **Max content width:** 제한 없음 (패널 기반)
- **Border radius:**
  - sm: 4px (버튼, 인풋, 뱃지)
  - md: 6px (카드, 드롭다운)
  - lg: 8px (모달, 패널)
  - full: 9999px (뱃지 카운트, 아바타)

### Responsive Breakpoints
| 이름 | 범위 | Tailwind | 레이아웃 |
|------|------|----------|----------|
| Desktop | ≥1280px | `xl:` (기본) | 2-Panel: 사이드바 220px + 메인 + RAG 오버레이 |
| Compact | 768~1279px | `md:` | 사이드바 아이콘 48px + 메인 + RAG 오버레이 |
| Mobile | <768px | 기본 | 단일 패널 + 하단 네비게이션 바 |

- **Sidebar:** Desktop=220px 텍스트+아이콘, Compact=48px 아이콘만, Mobile=숨김
- **RAG:** Desktop/Compact=Cmd+K 슬라이드 오버레이, Mobile=`/search` 라우트
- **Bottom Nav (Mobile):** [홈] [프로젝트] [+추가] [Inbox] [검색] — `md:hidden`

## Motion
- **Approach:** Minimal-functional — 상태 전환과 패널 토글만.
- **Easing:** enter(ease-out) exit(ease-in) move(ease-in-out)
- **Duration:** micro(50-100ms) short(150-250ms) medium(250-400ms)
- **특이사항:** RAG 응답 스트리밍이 유일한 "애니메이션". 타이핑 효과가 아닌 자연스러운 텍스트 흐름.

## Design Risks (의도적 차별화)
1. **RAG 오버레이 (Cmd+K)** — 상시 패널 대신 검색바+오버레이로 전환 (ADR-006). 메인 콘텐츠 영역을 넓게 확보하면서도 RAG 접근성 유지.
2. **액센트 #3ECFB4 (청록)** — SaaS 표준(파란/보라) 대신 "시간의 포착"이라는 컨셉에 맞는 색상. Color-blind safe.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-01 | Initial design system created | /design-consultation. Linear + NotebookLM 리서치 기반. Industrial/Utilitarian 방향. |
| 2026-04-01 | RAG 패널 상시 노출 결정 | 지식 탐색이 핵심 가치. 숨겨두면 사용 빈도 저하. |
| 2026-04-04 | RAG 상시 패널 → 오버레이 전환 (ADR-006) | C\|D 2-Panel 채택. 메인 콘텐츠 영역 확보 + 검색바/Cmd+K로 접근성 유지. |
| 2026-04-04 | Project Category → Status Colors 전환 | PARA 제거(ADR-004). Area/Resource 색상 → Active/Completed/Archived. |
| 2026-04-01 | 청록 액센트 #3ECFB4 채택 | "결정적 순간의 포착" 컨셉. 다크 배경 대비 우수. |
| 2026-04-01 | Pretendard 한국어 본문 | Apple SD Gothic Neo 대비 가독성, 자간, 웨이트 다양성 우위. |
