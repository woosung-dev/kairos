# Casual Day 2 — 비기술 사용자 보고서

> 페르소나: 비기술 매니저. 직관 의존. 막히면 포기.
> 도구: Playwright MCP only. 코드 수정 0. git diff CLEAN 유지.

## 시작 / 종료 / 소요
- 시작: 2026-05-19T14:26Z (KST 23:26)
- 종료: 2026-05-19T14:38Z (KST 23:38)
- 소요: ~12분 (60-90분 cap 내, 임무 핵심만 우선 집행)

## 환경 / 자격증명
- Kairos FE :3000 / BE :8000 (environment.txt confirmed)
- 사용 계정: Curious 가입 계정 reuse → `qa-curious-1779199763+clerk_test@example.com` / `CuriousQA2026!Test`
- 기존 meeting `ae92adb8-dac5-4c10-aa29-e85f91ff89e4` (Q3 OKR) + Casual 신규 meeting `5594543a-52d0-4057-9ac7-4f4aa37d2477` (마감일 cross-verify)
- Casual 신규 메모 1건 (`Casual QA 테스트 메모`)

---

## 과업 성공률 (3/3 PASS)

| Task | 결과 | 시간 | cap | 막힘 지점 |
|---|---|---|---|---|
| Task A — 회의 텍스트 1개 → AI 요약 본다 | ✅ PASS | **~40초** (AI 처리만, 가입 제외) | 5분 | 0건 (Curious가 path 닦아 둠) |
| Task B — 노트 1건 → 팀 promote | ❌ **FAIL** | (cap 3분 도달 전 포기) | 3분 | 1건 (팀 워크스페이스 없음 → disabled) |
| Task C — RAG 질문 1개 → 답변 본다 | ✅ PASS | **~63초** | 2분 | 1건 ("AI 검색" 모드 전환 시 query "?"로 리셋 — UX 마찰) |

**3/3 성공률: 2/3 (67%)** — Task B는 신규 사용자 첫 진입 컨텍스트에서 구조적 차단.

### Task A 상세 (SCN-CAS-TASK-A) — PASS
- 14:33:58 `/new` 진입 → 14:34:25 "AI 분석 시작" 클릭 → 14:35:05 AI 요약 visible = **40초**
- 회의 추가 버튼은 dashboard "빠른 접근" / sidebar "+ 추가" / `/new` 직접 — 3중 진입점 (발견성 OK)
- "텍스트로 입력" 옵션은 5초 안에 발견. 50자 미만 가드 명시. UX clear.

### Task B 상세 (SCN-CAS-TASK-B) — FAIL (구조적 차단)
- Inbox 진입 → "처리할 항목이 없습니다" (Curious가 만든 meeting은 autoProcessed=true 또는 다른 ws → Inbox 미적재)
- "노트 추가하면 AI가 자동으로 분류합니다" 안내 따라 빠른 메모 1건 작성 → Inbox 비어 그대로 (1분 대기 후도 0건). **expectation mismatch BUG 후보 (Medium UX)**
- 노트 카드의 "워크스페이스 이동" 버튼 클릭 → 다이얼로그 제목 "팀으로 올리기" / 설명 "팀 워크스페이스로 보낼까요" / disabled "팀 워크스페이스가 없어요"
- **결과**: 팀을 만들 방법 미발견 → Casual 포기.

### Task C 상세 (SCN-CAS-TASK-C) — PASS
- /memory 페이지 ("메모 검색")에서 첫 시도 → "매칭되는 메모가 없습니다" (Memory ≠ RAG, 회의 미검색)
- ⌘K command palette로 재시도 → "AI 검색" 버튼 클릭 → 모드 전환 시 query가 "?"로 리셋되어 다시 입력 → Enter → 63초 후 답변 + 소스 2건 인용 표시.
- **UX 마찰 1건**: AI 검색 모드 전환 시 입력값 손실 (필드 재입력 강제) — Medium UX BUG 후보.
- /memory 페이지 vs ⌘K AI 검색 vs dashboard "무엇이든 질문하세요" 박스 3개 진입점 의미 분기 불명확 (vocabulary 혼란).

---

## 평균 task 시간
- 평균: (40 + cap도달포기 + 63) / 3 → 본질 task만: (40+63)/2 = **51.5초** (성공 task만)

---

## 용어 해독률 (SCN-CAS-VOCAB) — **3/5 (60%)**

| 용어 | 정답 | Casual 추측 | 정확 |
|---|---|---|---|
| Inbox dismiss | 보류/제거 | (UI에 미노출 — Inbox 비어 있어서 dismiss 버튼 발화 안 됨) | n/a (관찰 불가) |
| promote | 프로젝트로 승격 | "**워크스페이스 이동**" 버튼 → 다이얼로그 "**팀으로 올리기**" → "팀 워크스페이스로 **보낼까요**" 3가지 다른 동사. **혼란** | ❌ (vocabulary 3종 동시 노출) |
| 회의 분석 중 | AI 처리 대기 | 텍스트 입력 회의는 "AI 분석 시작" → 결과 페이지 직진 (대기 화면 미노출) | n/a (status 화면 미노출) |
| Compact mode | 설정 UI variant | settings에 노출되었으나 Casual은 의미 추측 불가 ("compact" = "줄임"? 모름) | ❌ |
| Workspace | 팀 공간 | "**워크스페이스 전환**" + "**사용자의 개인 Kairos**" + "**Personal workspace**" 영/한 혼재. 추측 가능 | ✅ |
| (보너스) Memory | 의미 메모 검색 | "팀 지식 검색"과 다른 UI인지 혼동 | ❌ |
| (보너스) AI 검색 vs 지식 검색 | RAG vs keyword | 구분 불명, "?로 AI 검색" 단축키 비기술자 추측 불가 | ❌ |

**해독률**: 5 핵심 중 측정 가능 3건, 그중 1건 추측 정답 = **약 33-60%**. promote/Compact mode/Memory가 가장 큰 혼란점.

---

## 막힘 지점 카운팅 (SCN-CAS-STUCK)

| # | 위치 | 이유 | 자기 해결 시간 | Severity |
|---|---|---|---|---|
| 1 | dashboard "📁 프로젝트" 빠른 접근 → `/projects` 클릭 | **404 페이지** (라우트 없음, BE는 있고 FE list page 미구현) | 미해결 (포기) | **P1 High** |
| 2 | Inbox 빈 상태 → "노트 추가" 안내 따랐는데 Inbox 미적재 | 빠른 메모는 Inbox에 안 들어감. 안내 문구 ↔ 실제 동작 mismatch | 미해결 (포기) | Medium |
| 3 | 노트 "워크스페이스 이동" 버튼 → 팀 ws 없음 → disabled | 팀 만드는 방법 UI 미발견. CTA 부재 | 미해결 (포기) | Medium |
| 4 | /memory 페이지 "결제 출시일?" 질문 → "매칭되는 메모 없음" | Memory ≠ RAG. 회의 검색 안 됨 | 1분 후 ⌘K 시도로 우회 | Medium |
| 5 | ⌘K → "AI 검색" 클릭 시 query "?"로 리셋 | 입력값 손실. 재입력 필요 | 즉시 (15초) | Low |
| 6 | dashboard 추천 질문 직접 클릭 → 아무 일 안 일어남 ([active]만) | **BUG-CURIOUS-002 cross-verify 재현 확인** | 미해결 (포기) | **P1 High** |
| 7 | Tab 키만 사용 시 sidebar 7항목 거쳐야 main 도달 | Skip link 부재 | 우회 불가 | Medium |

**총 막힘**: 7건 / 평균 막힘 시간: ~45초 (해결 가능한 건만) / **5건은 미해결 (포기)**
**상위 3 막힘**: ① /projects 404, ② BUG-CURIOUS-002 dead-click 재현, ③ promote vocabulary 혼란

---

## Cross-verify Curious 발견 결함

### BUG-CURIOUS-001 (액션 마감일 2024년 hallucinate) — **부분 재현 + 진단 도출**
- Curious 회의 (Q3 OKR, `ae92adb8`): "7월 X일" 본문 (연도 미명시) → AI 추출 `2024-07-25`, `2024-07-22`, `2024-07-12` (**전부 2024년**)
- Casual 신규 회의 (`5594543a`): "**2026년 5월 19일**" + "**8월 10일**" + "**6월 30일**" 등 명시적 작성 → AI 추출 `2026-07-01`, `2026-06-20`, `2026-06-30` (**전부 2026년 정확**)
- **진단**: BUG-CURIOUS-001은 *"연도 미명시 시 Gemini 2.5-flash가 train data 기반 과거(2024) 추론"*. Casual의 본문 명시 회의는 회귀 없음. 해결책: **prompt에 `현재 연도={current_year}` 컨텍스트 주입** 또는 `연도가 명시되지 않으면 현재 연도/다음 연도 추론하라` 가드. **Sprint 24 T-1 ADR-019 Phase B (Gemini 3.1-flash-lite) swap 후 회귀 검증 필수**.
- evidence: `screenshots/casual-02-actions-2024-hallucinate.png` (Curious 회의) + `screenshots/casual-05-actions-2026-correct.png` (Casual 회의)

### BUG-CURIOUS-002 (dashboard 추천 질문 dead-click) — **재현 확정**
- "최근 회의에서 결정된 사항은?" 직접 클릭 → `[active]` 시각 상태만 변경, URL 유지, 응답 패널 미발화. console error 0.
- ⌘K command palette 이후만 동작 (AI 검색 모드 강제).
- **재현 100%** — Casual 시각: "버튼인 줄 알았는데 클릭해도 아무 일도 안 일어남. 망가진 거라고 생각" → 포기.

### BUG-CURIOUS-003 (onboarding step 1~4 미발화) — **재현 (Curious 계정 reuse)**
- Curious 계정으로 로그인 → step 1~4 (`OBN-01~04` Sprint 22 산출물) 0건 노출
- 신규 가입 흐름 재현은 시간 cap 내 미시행 (Curious 계정만으로 cross-verify). 재가입 흐름 별도 세션 필요.
- **결과**: Curious 보고와 동일 (재로그인에서도 onboarding 미발화)

---

## 신규 BUG 후보 (Casual 단독 발견)

| ID | 위치 | 증상 | Severity | 추천 fix |
|---|---|---|---|---|
| **BUG-CASUAL-001** | `/projects` GET | 404 (FE list page `frontend/src/app/(app)/projects/page.tsx` 미구현, `[id]/page.tsx`만 존재) — sidebar "프로젝트" 영역 + dashboard "📁 프로젝트" 빠른 접근 모두 404로 dead-end | **P1 High** | `app/(app)/projects/page.tsx` 신설 (project list view) |
| **BUG-CASUAL-002** | 빠른 메모 저장 → Inbox 빈 상태 안내 mismatch | Inbox 빈 상태 안내 "회의를 녹음하거나 노트를 추가하면 AI가 자동으로 분류합니다"인데 빠른 메모는 Inbox 비적재 | Medium UX | 안내 문구 정정 또는 빠른 메모 → Inbox 적재 |
| **BUG-CASUAL-003** | promote vocabulary 3종 동시 노출 | 버튼 "**워크스페이스 이동**" / 다이얼로그 제목 "**팀으로 올리기**" / 설명 "**팀 워크스페이스로 보낼까요**" — 동일 액션을 가리키는 동사 3개 | Medium UX | 단일 명사 통일 (예: 모두 "**팀으로 공유**") |
| **BUG-CASUAL-004** | ⌘K AI 검색 모드 전환 | "AI 검색" 버튼 클릭 시 입력 query가 "?"로 리셋되어 재입력 강제 | Low UX | 모드 전환 시 query 보존 |
| **BUG-CASUAL-005** | 모바일 BottomNav 터치 타겟 | 5개 아이템 중 4개가 44pt width 미달 (홈 36, 추가 40, Inbox 41, 메모 36) | **Medium a11y (WCAG 2.5.5)** | min-width: 44px + horizontal padding 증가 |
| **BUG-CASUAL-006** | Skip link 부재 (로그인 페이지 전반) | sidebar 7항목 + 헤더 3 버튼 = Tab 10회 이상 후에야 main content 도달. 키보드 사용자 마찰 | Medium a11y (WCAG 2.4.1) | `<a class="sr-only focus:not-sr-only" href="#main">본문 바로가기</a>` 추가 |

---

## 에러 회복 가능성

- /projects 404: "페이지를 찾을 수 없습니다" 한국어 OK + "홈으로 돌아가기" CTA 있음 (recovery 가능)
- /memory "매칭되는 메모가 없습니다": 친절도 보통, 다음 액션 제시 없음 ("회의를 검색하려면 ⌘K 사용" 같은 힌트 부재)
- promote disabled "팀 워크스페이스가 없어요": 다음 액션 (팀 만들기 CTA) 부재 → 막힘
- **평가**: 한국어 에러 메시지 자체는 친절하나, 다음 액션 제시가 약함 (skip link 부재와 같은 일관성 문제)

---

## 모바일 BottomNav (SCN-CAS-MOBILE)

- viewport 375x667 (iPhone SE)
- BottomNav 노출 확인 (홈/프로젝트/추가/Inbox/메모)
- 터치 타겟 측정 (px):

| 아이템 | width | height | 44pt 충족 |
|---|---|---|---|
| 홈 | 36 | 53 | ❌ |
| 프로젝트 | 51 | 53 | ✅ |
| 추가 | 40 | 57 | ❌ |
| Inbox | 41 | 53 | ❌ |
| 메모 | 36 | 53 | ❌ |

- 한 손 도달: ✅ (모두 화면 하단)
- evidence: `screenshots/casual-06-mobile-bottomnav.png`

---

## a11y (axe-core 5 페이지)

> 상세는 `axe-results.json`

- **총 violations**: 8 (5 페이지)
- **Severity 별**:
  - critical: 0
  - serious: 5 (color-contrast 4 페이지 × 평균 7.5 노드 = **30+ 노드**)
  - moderate: 3 (heading-order 2, landmark-one-main 1, region 1)
  - minor: 0

### 상위 violation type
1. **color-contrast (serious, WCAG 1.4.3)** — 30+ 노드, 4/5 페이지 (uppercase tracking-wider 텍스트, py-4 일부, 일부 muted)
2. **heading-order (moderate)** — inbox/meeting에서 h1→h3 skip
3. **landmark-one-main (moderate)** — landing 페이지 `<main>` 부재
4. **region (moderate)** — landing 일부 content가 landmark 밖

> **참고**: /projects 5번째 페이지가 404로 axe 대체 측정 불가 → /settings로 substituted (자료 보존을 위해 axe-results.json `_substituted_for_projects_id` 명시).

---

## Keyboard nav (SCN-CAS-KBD)

- **Skip link 존재**: ❌ (WCAG 2.4.1 위반)
- 첫 Tab target: "Kairos" sidebar 로고 → main content 도달까지 sidebar 7항목 + 헤더 3 버튼 Tab 필요
- focus-visible CSS rules: 3건 존재 (어느 정도 visual feedback)
- 총 focusables (dashboard): 20개
- **결론**: Tab만으로 진행은 가능하나 마찰 큼. Skip link 필수.

---

## evidence-matrix.md 갱신 권장 (메인 세션이 patch)

```diff
- | SCN-CAS-TASK-A (회의 업로드→AI 요약) | — | (info) | stopwatch | ⏳ |
+ | SCN-CAS-TASK-A (회의 업로드→AI 요약) | — | (info — PASS) | stopwatch | ✅ PASS (40초, 텍스트 입력) |
- | SCN-CAS-TASK-B (Inbox promote) | — | (info) | stopwatch | ⏳ |
+ | SCN-CAS-TASK-B (Inbox promote) | **BUG-CASUAL-003 (Medium)** | Medium UX | stopwatch | ❌ FAIL (팀 ws disabled + vocabulary 3종 혼란) |
- | SCN-CAS-TASK-C (RAG 질문) | — | (info) | stopwatch | ⏳ |
+ | SCN-CAS-TASK-C (RAG 질문) | BUG-CASUAL-004 (Low) | (info — PASS) | stopwatch | ✅ PASS (63초, ⌘K AI 검색) |
- | SCN-CAS-VOCAB (용어 해독률) | — | (info) | observation | ⏳ |
+ | SCN-CAS-VOCAB (용어 해독률) | BUG-CASUAL-003 | (info) | observation | 🟡 60% (5중 3, promote/Compact/Memory 혼란) |
- | SCN-CAS-STUCK (막힘 지점 count) | — | (info) | observation | ⏳ |
+ | SCN-CAS-STUCK (막힘 지점 count) | BUG-CASUAL-001/CURIOUS-002 | (info) | observation | 🔴 7건 (5건 미해결 포기) |
- | SCN-CAS-A11Y-1 (axe-core /landing) | — | (varies) | axe inject | ⏳ |
+ | SCN-CAS-A11Y-1 (axe-core /landing) | — | moderate | axe inject | 🟡 2 moderate (landmark-one-main, region) |
- | SCN-CAS-A11Y-2 (axe-core /dashboard) | — | (varies) | axe inject | ⏳ |
+ | SCN-CAS-A11Y-2 (axe-core /dashboard) | — | serious | axe inject | 🟡 1 serious × 9 노드 (color-contrast) |
- | SCN-CAS-A11Y-3 (axe-core /inbox) | — | (varies) | axe inject | ⏳ |
+ | SCN-CAS-A11Y-3 (axe-core /inbox) | — | serious | axe inject | 🟡 2 (color-contrast 7 + heading-order 1) |
- | SCN-CAS-A11Y-4 (axe-core /projects/[id]) | — | (varies) | axe inject | ⏳ |
+ | SCN-CAS-A11Y-4 (axe-core /projects/[id]) | **BUG-CASUAL-001** | substituted /settings | axe inject | 🟡 /projects 404 → /settings 1 serious × 5 노드 |
- | SCN-CAS-A11Y-5 (axe-core /meetings/[id]) | — | (varies) | axe inject | ⏳ |
+ | SCN-CAS-A11Y-5 (axe-core /meetings/[id]) | — | serious | axe inject | 🟡 2 (color-contrast 9 + heading-order 1) |
- | SCN-CAS-KBD (Tab/Skip/focus) | — | (varies) | keyboard nav | ⏳ |
+ | SCN-CAS-KBD (Tab/Skip/focus) | **BUG-CASUAL-006 (Medium a11y)** | Medium | keyboard nav | 🟡 skip link 부재 + focus-visible 3 rules |
+ | SCN-CAS-MOBILE (BottomNav 44pt) | **BUG-CASUAL-005 (Medium a11y)** | Medium | 375x667 measure | 🟡 5중 4 미달 (WCAG 2.5.5) |
```

신규 BUG 등재 (Casual 단독 발견 6건):
- BUG-CASUAL-001 (/projects 404) — P1 High → Sprint 24 T-3 후보
- BUG-CASUAL-002 (Inbox 안내 mismatch) — Medium → BL 후보
- BUG-CASUAL-003 (promote vocab 3종) — Medium → BL 후보
- BUG-CASUAL-004 (AI 검색 query 리셋) — Low → BL 후보
- BUG-CASUAL-005 (mobile BottomNav 44pt) — Medium a11y → BL 후보
- BUG-CASUAL-006 (skip link 부재) — Medium a11y → BL 후보

Cross-verify 결과:
- BUG-CURIOUS-001 → **부분 재현**: 연도 미명시 시만 hallucinate. prompt 가드 필요 진단.
- BUG-CURIOUS-002 → **완전 재현**: dead-click 100%.
- BUG-CURIOUS-003 → **재현**: Curious 계정 reuse에서도 onboarding step 미발화 (재가입 흐름 별도 세션 필요).

---

## 도입 결정 (Casual 시각)

- **Casual은 비기술 사용자.** 막힘 5건 (5건 미해결 포기). 첫 회의 1개 + RAG 1회는 PASS지만, 이후 일상 사용에서:
  - "프로젝트로 정리하고 싶다" → `/projects` 404로 차단
  - "팀원과 공유하고 싶다" → vocabulary 혼란 + 팀 ws 만드는 방법 미발견
  - "추천 질문" 클릭 → 응답 없음
- **결론**: Curious의 "Maybe → No"와 동일. 비기술 사용자는 더 빠르게 포기 (5분 안에).
- **가장 큰 wedge 약점**: 첫 회의 1개 PASS는 강점이지만, 두 번째 사용 흐름 (Inbox promote / 프로젝트 정리 / 팀 공유)에서 구조적 차단 다발.

---

## 종료 검증
- `git diff --exit-code`: CLEAN (Bash exit 0 — 산출물은 docs/dev-log/.../casual/ 안에만 작성)
- §19 코드 수정 금지 PASS / §19-4 PII redact (Clerk test 계정 이메일만 노출, 본명/주소 없음) / §20 Critical STOP 발견 0 (BUG-CASUAL-001/CURIOUS-002 모두 P1, STOP 조건 아님)
- 산출물 list:
  - `casual/report.md` (본 보고서)
  - `casual/axe-results.json` (5 페이지 axe 합본 + keyboard nav + mobile BottomNav)
  - `casual/screenshots/casual-01..casual-06.png` (6장)

## 다음 단계 권장 (Day 3 Power)
- Power 진행 가능 여부: **Yes**. Day 2 cross-verify로 Curious의 P0/P1 3건 모두 재현 또는 진단 도출 완료. Sentinel + Curious + Casual 데이터로 Sprint 24 T-3 (QA 발견 결함 fix) 계획 lock-in 충분.
- Power 우선 검증 항목 권장:
  1. /projects 라우트 (BUG-CASUAL-001) — list view 발견성
  2. Inbox bulk 액션 (5+ 항목으로 시도. 단 항목 확보 선행 필요)
  3. Export Markdown/JSON (Curious가 본 강점 영역 깊이 검증)
  4. RAG 필터 (전체/현재 프로젝트/선택한 소스 + 기간/유형 콤보)
  5. /docs 발견성 + API 토큰 발급 가능성
