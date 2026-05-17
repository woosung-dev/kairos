# Mobile User Report — Sprint 18 → 19 Multi-Agent QA

| 항목 | 값 |
|---|---|
| 검증 시각 | 2026-05-17 KST |
| 페르소나 | Mobile (smoke) — 모바일 사용자 |
| 환경 | local (FE :3000 + BE :8000) — Sentinel A 로그인 |
| Cap | 60분 |
| 자동화 | Playwright MCP (375×667 / 393×852 / 412×892) |

## 1. Executive Summary
| 항목 | 결과 |
|---|---|
| 총 결함 카운트 | **6 (Critical 0, High 2, Medium 3, Low 1)** |
| Persona Health Score | **4.4/10** = max(0, 10 - (0×3 + 2×1.5 + 3×0.5 + 1×0.1)) = 10 - 4.6 → 5.4. Casual H-1/H-2(404) carry-over로 모바일 영향 가중 +1 → **4.4** |
| 가장 큰 발견 | BottomNav의 5개 primary 아이템 중 1개("프로젝트")가 404. 모바일에서 가장 빈번한 네비게이션 경로가 실패. |

## 2. 결함 상세

| # | 영역 | 결함 | Severity | Confidence | 재현 | 권고 |
|---|---|---|---|---|---|---|
| H-1 | BottomNav / 라우팅 | BottomNav "프로젝트" 탭 클릭 → `/projects` 404. 모바일 primary navigation 5개 중 1개 깨짐. | High | H | 모바일 viewport → dashboard → BottomNav "프로젝트" 탭 click → 404 | `/projects` 구현 또는 BottomNav에서 "프로젝트" 제거하고 `/inbox` 또는 `/memory`로 대체 |
| H-2 | a11y / 터치 타겟 | BottomNav 아이콘 width 36~40px (높이는 53~57px 충족). avatar "U" 36×36px. WCAG AAA 44pt 권장 위반. | High | H | iPhone SE → 각 BottomNav 아이콘 BoundingRect 측정 → `홈:36×53, 메모:36×53, U:36×36` | min-width 44px 강제 (icon 영역 padding 확대) |
| M-1 | a11y / 시맨틱 | BottomNav `<nav>` 에 `role` / `aria-label` 미설정 → 스크린리더 사용자에게 "탐색" 컨텍스트 미전달. | Medium | H | `nav.fixed.bottom-0` 속성 검사 | `<nav aria-label="모바일 주 메뉴">` 추가 |
| M-2 | 정보 구조 | desktop 사이드바 = `홈/Inbox/Memory NEW/빠른 메모/+추가`. mobile BottomNav = `홈/프로젝트/추가/Inbox/메모`. Memory(RAG 검색) 항목이 모바일에서 빠짐. 모바일 사용자는 RAG 검색 진입점 없음 (상단 ⌘K 버튼만). | Medium | H | desktop sidebar vs mobile BottomNav 비교 | BottomNav에 "메모리(검색)" 추가 또는 "메모" 라벨을 "메모리"로 통일 |
| M-3 | 워크스페이스 전환 | 모바일에서 상단 "워크스페이스 전환" 칩 width 221px → 매우 좁은 공간 차지 + 텍스트 잘림 가능성. | Medium | M | iPhone SE dashboard 상단 → 워크스페이스 칩 확인 | 모바일에서는 아이콘 only + bottom sheet 드롭다운 패턴 |
| L-1 | iOS 키보드 안전 | `/memory` 검색 input 위치 187px → iOS 키보드 290px 침범 시 안전. 다만 `/new` 회의 제목 input 위치는 더 아래 (rect 측정 미완료). | Low | L | 이번 smoke 미커버 — `/new` 회의 제목 input 좌표 측정 후 확정 | viewport bottom padding 추가 또는 input auto-scroll into view |

## 3. viewport 매트릭스

| viewport | width × height | 가로 스크롤 | BottomNav | 비고 |
|---|---|---|---|---|
| iPhone SE | 375×667 | 없음 ✅ | 표시 ✅ | smallTargets 9개 ≤ 44px 위반 |
| iPhone 14 | 393×852 | 없음 ✅ | 표시 ✅ | 동일 BottomNav structure |
| Pixel 7 | 412×892 | 없음 ✅ | 표시 ✅ | 동일 |

**터치 타겟 위반 상세** (iPhone SE 기준):
- BottomNav 5 아이콘: 36~40px (≤ 44 위반)
- avatar "U": 36×36 (위반)
- 상단 "워크스페이스 전환" 칩 height 28px (위반)
- "팀 지식 검색 ⌘K" 38px (위반)
- 추천 질문 카드 height 42px (위반)

**Inbox action 버튼은 height 44px exact**로 양호 ✅. 다만 width 60~106px이라 검지 손가락 정확도 좋음.

## 4. 산출물
- 스크린샷
  - `mobile/iphone-se-dashboard.png` (iPhone SE 375)
  - `mobile/iphone-se-projects-404.png` (BottomNav "프로젝트" 404)
  - `mobile/iphone-se-inbox.png` (Inbox 모바일 레이아웃)
  - `mobile/pixel7-new-capture.png` (Pixel 7 새 콘텐츠 추가)
  - `mobile/pixel7-recording.png` (직접 녹음 패널)
- trace zip: Critical 0건 → 미생성
- 3G throttle: 본 smoke 제외 (cap 절약)
