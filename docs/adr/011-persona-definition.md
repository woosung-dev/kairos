# ADR-011: Persona Definition — 페르소나 ID 체계·필수 필드·갱신 정책

> **날짜:** 2026-05-11
> **상태:** Accepted
> **작성자:** Claude Opus 4.7 (1M context) + 사용자 (Phase B Stage 1 retrofit)
> **관련:** ADR-009(Stage 1 retrofit 총괄), ADR-010(Future-Fit Thesis), ADR-004(세컨드 브레인 피벗), CONTEXT-MAP.md §2 별칭 금지·§3 CODE 가치 흐름·§7 D-1
> **출처:** `~/.gstack/projects/woosung-dev-kairos/woosung-docs-stage1-meta-review-design-20260511.md` (office-hours design doc, Q3 + Q4)
> **참고:** 본 ADR 이 인용하는 `.ai/*` 경로는 2026-08-15 [ADR-029](029-ai-rules-relocation.md) 로 이전·삭제됐다. 본문은 당시 기록이라 수정하지 않는다.

---

## 배경

Phase B Stage 1 office-hours에서 6 forcing question 중 **Q3 (Target User)** 가 두 번째 큰 갭으로 식별되었다.

> design doc §"Target User & Narrowest Wedge" 인용:
> "PRD에 '팀/팀원/지식 노동자' 카테고리 라벨만, 구체적 페르소나 (이름/일상/승진·해고 기준) 부재. retrofit 출처는 본인 + 지인 1-2명."

기존 PRD §2 "타겟 유저"는 다음 수준:

- 매주 3~5회 회의를 주도하는 팀 리더
- 여러 프로젝트를 동시에 관리하는 PM
- 과거 의사결정 맥락을 자주 다시 찾아야 하는 구성원

이것은 **카테고리 라벨**이지 페르소나가 아니다. 페르소나는 의사결정 입력으로서 (a) 이 사람의 일상이 어떤가 (b) 무엇으로 평가받는가 (c) Kairos를 쓰면 무엇이 바뀌는가가 한 자리에 모여야 wedge 선정·기능 우선순위·demand 시그널 정의의 근거가 된다.

본 ADR은 **페르소나 정의 정책 ADR**이다. 실제 페르소나 3개는 `docs/requirements/personas.md`(Plan 산출 #5)에 명세. 본 ADR이 그 명세의 규칙·ID 체계·갱신 주기·폐기 기준을 정한다.

### 페르소나 1차 데이터 현황 (사용자 확정 사항, AD-4)

design doc §"The Assignment"에서 사용자에게 "지인 2명 인터뷰" 과제 부여. 본 retrofit 진입 시점 인터뷰 **미진행**. 따라서 personas.md는 **본인 도그푸딩 1명(PERSONA-001) + 가상 2명(PERSONA-002~003, `[가설]` 라벨)**으로 1차 작성. 후속 인터뷰 결과로 패치 PR.

본 ADR은 1차 작성 시 가상 페르소나에 적용할 `[가설]` 라벨 정책을 강제한다.

### 자의 결정 라벨 (본 산출에서 추가)

- **AD-10**: 페르소나 ID는 3자리 zero-pad (`PERSONA-001`) — ADR ID 3자리 패턴(`010-`, `011-`)과 표기 정합. ID 한 번 부여되면 변경 금지, 삭제된 ID 재사용 금지 (`.ai/common/global.md` §2 ID 체계 정책 그대로 적용).
- **AD-11**: 페르소나 필수 필드 7개 채택. Lean UX 표준 페르소나 6개 필드(이름/역할/목표/pain/insight/quote)에 "**해고 기준**"을 추가한 7개 구성. 이유: founder context에서 해고 기준은 product survival과 직결 — 사용자가 Kairos를 쓰지 않으면 자기 평가에서 어떤 손해를 입는가가 demand 강도의 직접 지표.
- **AD-12**: Wedge 후보 4개 한정 (W1~W4). design doc §"Q4 Finding" 명시 그대로 — 자의 X. 추가 wedge는 페르소나 검증 후 별도 ADR 갱신.

---

## 결정

### 1. 페르소나 ID 체계

- **포맷**: `PERSONA-NNN` (3자리 zero-pad). 예: `PERSONA-001`, `PERSONA-002`, `PERSONA-003`.
- **불변성**: 한 번 부여된 ID는 변경 금지. 폐기된 페르소나의 ID 재사용 금지(`.ai/common/global.md` §2).
- **상태 라벨**: 각 페르소나는 다음 넷 중 하나 — `interview-confirmed` (외부 인터뷰 ≥1명 검증) / `self-confirmed` (본인 도그푸딩 1명 기록 검증, 강도 약함) / `[가설]` (외부 검증 전 본인 추론) / `deprecated` (검증 실패·폐기).
- **강도 차이 명시**: `self-confirmed`는 외부 인터뷰 응답자와 의미적 동일 강도 아님. `[가설]` 보다 강하지만 `interview-confirmed` 보다 약함 — wedge 선정 입력 가중치 낮음.
- **후속 (closeout 2026-05-11, ADR-011-vivid-clarke patch)**: `.ai/`가 의도적 `.gitignore` 포함 (커밋 흐름 5adf9f7→231f660 "fix(rest): reset ai rules")로 표 갱신 PR 자체 불가. 로컬 `.ai/common/global.md` 표는 직접 갱신. **본 §1이 `PERSONA-` 접두사 정의의 권위 출처** — 외부 참조 시 ADR-011 §1을 1차 인용. (발견 출처: Sprint 6 plan vivid-clarke §10 T-F10)

### 2. 페르소나 필수 필드 7개

각 페르소나는 다음 7개 필드를 모두 명시해야 한다. 3개 이상 미입력 시 **드래프트 상태**로 페르소나로 인정하지 않는다 (폐기 기준 §4 참조).

| # | 필드 | 의미 | 의사결정 용도 |
|---|---|---|---|
| 1 | **이름 (가명)** | 페르소나 호명용 가명 | 팀 내부 호명·인터뷰 시 익명성 유지 |
| 2 | **역할** | 직무·직급·소속 산업 | wedge 후보와 직무 일치 검증 |
| 3 | **일상 (1주일 routine)** | 회의 빈도·노트 작성 빈도·자료 검색 빈도 | Capture/Organize/Distill/Express 단계별 사용 빈도 추정 |
| 4 | **일상적 압박** (매일/매주 반복 마찰) | 매일~매주 부딪히는 마이크로 pain — 회의 직후 노트 정리·자료 검색·액션 추적의 반복 마찰 | wedge별 일상 ROI 추정 (시간 절감 정량화 가능 영역) |
| 5 | **승진 기준** | KPI·평가 지표·성공의 모습 (분기/연간 시점) | Kairos가 이 페르소나의 평가 지표를 올릴 수 있는가 |
| 6 | **시스템적 실패 기준** (분기/연간 평가 risk) | 평가 하락·구조조정·해고 risk를 야기하는 분기/연간 시점 실패 조건 (필드 4의 매일 마찰과 시간 스케일 분리) | demand 강도 — 이 페르소나가 Kairos를 쓰지 않으면 입는 큰 손해 |
| 7 | **Kairos 사용 시 변화** | 사용 전 vs 후의 1주일 routine 차이 | wedge별 ROI 추정·demand 시그널 정의 입력 |

필드 작성 정책:

- 모든 필드는 **구체적**이어야 한다. "효율적으로 일한다" 같은 추상 금지. "월 5회 임원 보고 자료 작성 시 직전 회의 결정사항 5개를 검색하는 데 평균 30분 소요" 수준.
- `interview-confirmed`/`self-confirmed` 페르소나의 1주 routine·승진 기준·실패 기준은 **출처 명시 필수** — 형식: `YYYY-MM-DD / 행동 / 소요 시간 / 빈도` 또는 `인터뷰 YYYY-MM-DD / 응답자 코드 R-NNN / 인용 1줄`.
- `[가설]` 페르소나는 **추론 근거 1줄 필수** — 왜 그렇게 추정하는가.
- 필드 4(일상적 압박)와 필드 6(시스템적 실패 기준)이 같은 내용으로 적히면 시간 스케일 분리 실패 — 폐기 기준 §4-a 트리거.

### 3. 페르소나-Wedge 우선순위 매트릭스

페르소나가 wedge 선정의 입력으로 작동하려면, 각 페르소나가 4개 wedge 후보에 매기는 우선순위를 명시한다.

| Wedge | 대체 대상 | 헌법 §3 CODE 매핑 |
|---|---|---|
| **W1** | 회의 요약·액션 추출 (Otter 대체) | Capture + Distill L1/L2 (`meetings`/`actions` 도메인) |
| **W2** | Inbox 자동 분류 (Reflect 대체) | Organize (`inbox`/`projects` 도메인) |
| **W3** | 프로젝트 RAG Q&A (Mem/Notion AI 대체) | Express (`rag` 도메인, 6-Layer) |
| **W4** | 노트 → 검색 (Reflect/Tana 대체) | Capture + Express (`notes`/`rag` 도메인) |

매트릭스 작성 정책:

- 페르소나마다 4개 wedge에 **1~4 우선순위** (1=가장 필요, 4=가장 덜 필요)를 매긴다.
- 우선순위 근거는 **§2 7번 필드 (Kairos 사용 시 변화)** 와 정합해야 한다.
- 페르소나 3개가 모두 같은 1순위 wedge를 매기면 페르소나 분화가 의미 없음 — 페르소나 재정의 또는 wedge 후보 추가 트리거 (폐기 기준 §4-c).

### 4. 폐기 / 재정의 기준

페르소나는 다음 3개 조건 중 하나에 해당하면 `deprecated` 또는 재정의한다.

- **a. 데이터 누락**: 7개 필드 중 3개 이상 미입력 상태가 다음 Sprint 종료까지 유지 → `deprecated`. 필드 4(일상적 압박) ≡ 필드 6(시스템적 실패 기준) 동일 내용 작성 시 시간 스케일 분리 실패로 카운트.
- **b. 가설 검증 실패 (정량 트리거)**: `[가설]` 페르소나에 대해 외부 인터뷰(Sprint 7+) 결과 **응답자 N명 중 ≥60% 가 페르소나 7개 필드 중 3개 이상에서 불일치**하면 → `deprecated` + 신규 페르소나로 대체. 60% 임계값은 ADR-010 AD-8 정합 (Thesis 외부 검증 임계값과 동일 단위).
- **c. 분화 의미 없음 (hedge 포함)**: 페르소나 3개가 모두 같은 1순위 wedge → 페르소나 재정의 트리거. **단, 외부 demand 시그널(ADR-009)이 동일 wedge에 ≥60% 집중을 동반하면 페르소나 분화 실패가 아니라 wedge 시그널 명확으로 해석 — 페르소나 재정의 대신 wedge 우선화 ADR 신규 작성 (본 ADR §AD-12 후속). wedge 후보 추가가 필요하면 본 ADR을 supersedes 하는 신규 ADR 작성 (§5 본 ADR 갱신 정책과 정합).**

폐기된 페르소나는 personas.md에서 삭제하지 않고 `## Deprecated` 섹션으로 이동 + 폐기 사유 1줄 명시.

### 5. 갱신 주기

- **매 Sprint 종료 (2주마다)**: 페르소나 검증/조정. 새 도그푸딩·인터뷰 데이터로 필드 갱신. 폐기 기준 점검.
- **외부 인터뷰 5-10명 (Sprint 7+ 후속)**: design doc §"What I noticed about how you think" 사용자 product-first 정책 유지. Sprint 6(멤버십+Private) 완료 후 demand 시그널 정의(ADR-009)와 함께 외부 인터뷰 실시. 결과로 `[가설]` 페르소나의 `confirmed`/`deprecated` 전환.
- **본 ADR 갱신 시점**: 페르소나 필수 필드 추가/삭제 또는 wedge 후보 변경 시 본 ADR 자체를 새 버전으로 작성 (Nygard 형식 supersedes).

### 6. 도메인 용어 정합 (§2 별칭 금지)

페르소나 필드 작성 시 다음 정식 용어를 사용한다. 별칭 사용 금지:

- **Workspace** (Team/Tenant/Org 금지)
- **WorkspaceMember** (User-Role/Membership 금지)
- **Project** (Area/Folder/Category 금지)
- **InboxItem** (Note/Capture/Item 금지 — Note는 Tiptap 노트 전용)
- **Meeting** (Recording/Session 금지)
- **ActionItem** (Task/Todo 금지)
- **Note** (Memo/Doc 금지)

페르소나의 일상·압박·변화 필드는 사용자 입장에서 쓰이지만, ADR/personas.md에서는 위 정식 용어로 매핑된다.

**한정 명시**: 본 매핑은 페르소나 문맥 핵심 7개 한정. 페르소나 필드에 다른 엔티티(WorkspaceInvite, TranscriptSegment, MeetingSummary, MeetingProjectLink, EmbeddingChunk, SemanticCache, User) 등장 시 CONTEXT-MAP §2 14개 전체 별칭 금지 표 그대로 적용.

---

## 결과

- `docs/requirements/personas.md`가 본 ADR을 출처로 PERSONA-001~003 명세 (Plan 산출 #5).
- PRD §2 "타겟 유저" 섹션이 personas.md 링크 + 페르소나 요약으로 PATCH (Plan 산출 #4).
- Sprint 7+ 외부 인터뷰 설계 시 본 ADR의 필수 필드 7개가 인터뷰 질문 가이드의 입력.
- Wedge 선정 (Sprint 6 완료 후 별도 ADR)이 페르소나-Wedge 매트릭스를 입력으로 사용.
- 본 ADR이 ADR-010 thesis 검증 시그널(AD-8: 60% 외부 인터뷰)과 ADR-009 demand 시그널 정의의 입력.

---

## 비용 / 리스크

- **`[가설]` 페르소나 2개가 1차 정의를 좌우한다.** 인터뷰 0명 시점이라 PERSONA-002/003이 본인 추론이며 wedge 선정에 편향 위험. Sprint 7+ 인터뷰 완료 전까지는 모든 페르소나 기반 의사결정에 "1차 입력 미검증" 경고를 동반.
- **필수 필드 7개가 너무 많을 가능성.** 인터뷰 1회당 30~45분 소요 예상. 5-10명 인터뷰 시 총 3~8시간 + 정리. 1인 풀스택 founder가 감당 가능한 범위인지 Sprint 7+ 진입 시 재평가.
- **승진/해고 기준 필드가 답변 거부 위험.** 응답자가 본인 평가 지표를 외부에 드러내기 꺼릴 수 있음. 인터뷰 가이드 작성 시 "구체 KPI" 대신 "성공/실패의 모습 1주 routine 차이" 식으로 우회 질문 설계 필요.
- **Wedge 매트릭스 우선순위 1~4 매김이 자의적.** 페르소나가 매기는 우선순위가 응답 거부 시 본인 추론 기반. `[가설]` 라벨 강제로 부분 완화.
- **§7 D-1(visibility 미구현)·D-6(개인↔팀 경계 등 5건 미해결) 의존.** 페르소나-Wedge 매트릭스의 W2 (Inbox 자동 분류)는 개인 vs 팀 경계가 명확해야 의미. 멤버십 Sprint 6 미완료 상태에서는 W2 우선순위가 잠정.

---

## 검증 기준

- [ ] `docs/requirements/personas.md`가 PERSONA-001~003 모두 7개 필수 필드 + 상태 라벨(`interview-confirmed`/`self-confirmed`/`[가설]`/`deprecated` 중 하나) + Wedge 매트릭스 명시.
- [ ] PERSONA-001은 `self-confirmed` + 도그푸딩 기록 포맷(`YYYY-MM-DD / 행동 / 소요 시간 / 빈도`) 출처 명시. PERSONA-002~003은 `[가설]` + 추론 근거 1줄 명시.
- [ ] 페르소나 필드 작성 시 §2 정식 용어 사용 (Workspace/WorkspaceMember/Project/InboxItem/Meeting/ActionItem/Note). 별칭 사용 시 본 ADR 위반.
- [ ] Wedge 매트릭스 W1~W4가 §3 CODE 가치 흐름 매핑과 정합.
- [ ] Sprint 7+ 외부 인터뷰 5-10명 완료 후 본 ADR §4 폐기 기준 점검 사이클 동작.
- [ ] PRD §2 "타겟 유저" 섹션이 personas.md를 정확히 참조.

---

## 후속

- **personas.md 작성** — 본 ADR을 출처로 PERSONA-001~003 명세 (Plan 산출 #5).
- **Wedge 선정 ADR (신규)** — Sprint 6 완료 후 페르소나-Wedge 매트릭스 + demand 시그널(ADR-009) + thesis 검증(ADR-010)로 W1~W4 중 우선 wedge 결정.
- **외부 인터뷰 가이드** — Sprint 7+ 진입 시 본 ADR 7개 필수 필드 + AD-8 60% 임계값 + 승진/해고 기준 우회 질문 설계 별도 문서.
- **페르소나 갱신 사이클** — 매 Sprint 종료 retrospective에 페르소나 검증 5분 항목 추가 (`/retro` 스킬과 정합).
- ~~**`.ai/common/global.md` §2 ID 체계 표 갱신 PR**~~ **(closeout 2026-05-11)** — `.ai/`가 의도적 `.gitignore`(5adf9f7→231f660 reset 흐름)로 PR 불가. 로컬 표는 직접 갱신 완료(git 외부). 본 ADR §1이 `PERSONA-` 접두사 정의의 권위 출처로 확정. 발견 + 결정 출처: Sprint 6 plan vivid-clarke §10 T-F10 차단 → 옵션 (f) 사용자 승인.
