# Casual User Report — Sprint 18 → 19 Multi-Agent QA

| 항목 | 값 |
|---|---|
| 검증 시각 | 2026-05-17 KST |
| 페르소나 | Casual (smoke) — 일반 사용자 |
| 환경 | local (FE :3000 + BE :8000) — Sentinel A 로그인 |
| Cap | 40분 |
| 자동화 | Playwright MCP + axe-core 4.10.0 |

## 1. Executive Summary
| 항목 | 결과 |
|---|---|
| 총 결함 카운트 | **9 (Critical 0, High 2, Medium 5, Low 2)** (H-3 정정으로 H→M 이동) |
| Persona Health Score | **4.0/10** = max(0, 10 - (0×3 + 2×1.5 + 5×0.5 + 2×0.1)) = 10 - 5.7 → 4.3. RAG 라벨 모호 + a11y 가중 → **4.0** |
| 가장 큰 발견 | `/meetings` / `/projects` 핵심 라우트 404 + a11y color-contrast 4페이지 49 노드 위반. 사이드바·dashboard에서 진입 시도 시 곧바로 막힘. |

## 2. 결함 상세

| # | 영역 | 결함 | Severity | Confidence | 재현 | 권고 |
|---|---|---|---|---|---|---|
| H-1 | 라우팅 | `/meetings` 404. dashboard "최근 활동"에 미팅 데이터가 보이지만 list view 진입점 없음. | High | H | `/meetings` → 404 페이지 | meetings list view 신설 또는 `/inbox` redirect 정의 |
| H-2 | 라우팅 | `/projects` 404. dashboard "빠른 접근" 카드 4개 중 1개가 깨진 링크. | High | H | `/projects` → 404. dashboard 진입 후 "프로젝트" 카드 click | projects list view 신설 (sprint 7 ProjectMember 도입 이후 미구현 추정) |
| H-3 | 단축키 (정정) | Meta+K는 **동작** (Casual 시도에서 `[role="dialog"]` selector 미매치로 오인 — palette는 `.fixed.inset-0.z-50` div, role 누락). 다만 시퀀스 단축키 (G I/G P/C 등) UI에 표시되어 있는데 실제 키 핸들러 미연결. Power 보고서 H-1 참고. | Medium | H | dashboard → Meta+K → palette `.fixed.inset-0.z-50` 표시 ✅, Esc 닫힘 ✅. 단 role="dialog" 부재. | role/aria 패치는 Power M-1로 이전 |
| M-1 | 시드 데이터 / Distill 품질 | Inbox 16건 회의 요약이 거의 동일한 문구 ("금일 회의에서는 현재 진행 중인 프로젝트의...") 반복. Distill diversity 부족. | Medium | H | `/inbox` → 16 항목 텍스트 비교 → 80% 이상 어휘 동일 | seed fixture 다양화 + LLM temperature 상향 또는 prompt 다양성 강제 |
| M-2 | a11y / color-contrast | 4 페이지 axe-core serious 49 노드. dashboard 10 / inbox 27 / notes 7 / memory 5. WCAG 2 AA 위반. | Medium | H | 각 페이지 axe.run() → violations[0].id="color-contrast" | DESIGN.md 색상 토큰 audit + muted-foreground 명도 조정 |
| M-3 | a11y / Skip link | dashboard `Tab` 시작 시 sidebar `Kairos` 로고로 진입 → main content까지 25 tab 소요. skip link 부재. | Medium | H | dashboard `Tab` 1회 → 첫 focusable = "Kairos" 로고 | `<a href="#main-content" class="skip-link">메인으로 건너뛰기</a>` 추가 |
| M-4 | 라벨 / 직관 | RAG 검색 결과 카드에 "의미 매칭" 라벨 노출. 일반 사용자에게 벡터 검색 의미 모호. | Medium | M | `/memory` → "스프린트 계획" 검색 → 각 카드 좌상단 라벨 | "AI 추천" / "유사 매칭" 등으로 rewrite. tooltip 추가 |
| L-1 | 사이드바 카운트 정합성 | dashboard 사이드바 Inbox 옆 "16" 배지 표시 → `/inbox` 진입 시 배지 사라짐. | Low | M | dashboard ↔ `/inbox` 사이드바 비교 | 라우트 변경 시 카운트 prop 유지 (Zustand persist) |
| L-2 | Notes empty state | `/notes` 초기 로딩 "로딩 중..." 텍스트 노출 후 3초 지연. 시각 skeleton 부재. | Low | M | `/notes` 첫 진입 → 1~3초 텍스트만 보임 | Skeleton loader 적용 |

## 3. a11y 결과 매트릭스

| 페이지 | axe.run violations | severity | nodes |
|---|---|---|---|
| `/` (dashboard) | 1 | serious | 10 (color-contrast) |
| `/inbox` | 1 | serious | 27 (color-contrast) |
| `/notes` | 1 | serious | 7 (color-contrast) |
| `/memory` | 1 | serious | 5 (color-contrast) |
| `/` (anonymous 랜딩) | (측정 불가 — 로그인 상태에서 자동 redirect) | — | — |

모든 페이지 **color-contrast serious** 단일 유형. text/background 명도 차이 부족.

## 4. 산출물
- 스크린샷
  - `casual/inbox-empty.png` (Inbox 데이터 16건 표시)
  - `casual/memory-search.png` (RAG 검색 결과 3건)
- trace zip: Critical 0건 → 미생성
- 추가 메모: 워크스페이스 자동 매핑이 "E2E 테스트 워크스페이스" (founder 추정 X — 시드 이전 생성된 셋업)로 고정. Sentinel A 시드 워크스페이스 진입 안 됨 (Curious 보고서 H-2 참고). 본 보고서의 모든 결과는 "E2E 테스트 워크스페이스" 컨텍스트.
