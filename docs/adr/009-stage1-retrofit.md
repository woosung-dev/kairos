# ADR-009: Stage 1 Retrofit 총괄 — 6 Forcing Question 결과 + Demand Signal Definition

> **날짜:** 2026-05-11
> **상태:** Accepted
> **작성자:** Claude Opus 4.7 (1M context) + 사용자 (Phase B Stage 1 retrofit)
> **관련:** ADR-008(DevEx 이니셔티브), ADR-010(Future-Fit Thesis), ADR-011(Persona Definition), ADR-004(세컨드 브레인 피벗), ADR-007(L4 조직 인사이트, Phase 4), CONTEXT-MAP.md §1·§3·§6·§7
> **출처:** `~/.gstack/projects/woosung-dev-kairos/woosung-docs-stage1-meta-review-design-20260511.md` (office-hours design doc — Phase B Stage 1)
> **워크플로우:** `.ai/templates/workflow.md` Stage 1 (기획·아키텍처 메타 재검증)

---

## 배경

Kairos는 1인 풀스택 founder가 진행 중인 팀 세컨드 브레인 제품. Phase A(Stage 0 헌법 retrofit, cea0be9)로 도메인 경계·14개 엔티티·16 불변식·11 부채를 CONTEXT-MAP.md에 lock-in 했다. 그러나 워크플로우 `.ai/templates/workflow.md`의 정식 **Stage 1 (기획·아키텍처 — `/office-hours` → `/autoplan`)** 을 그동안 누락한 채 Sprint 5 + 온보딩 직전 릴리즈 스프린트까지 product-first로 진행해 왔다.

> 사용자 자기 인식 (design doc §"What I noticed about how you think" 인용):
> "demand 미테스트", "본인=설계자=사용자 단일", "future-fit thesis 부재" — Stage 1을 누락한 자기 진단.

Phase B는 이 누락을 **메타 retrofit**으로 메운다. 본 ADR-009는 그 retrofit의 **총괄 ADR**이며, ADR-010(Future-Fit Thesis, 9.2/10 PASS)과 ADR-011(Persona Definition, 9.25/10 PASS)을 하위로 묶는다. ADR-009 책임:

- 6 forcing question (YC office-hours 기법) Q1~Q6 결과 기록.
- Q1 (Demand) 의 **product-first 결정** 명시 + Sprint 6+ demand 시그널 정의(정량 임계값).
- ADR-010/011/competitive-analysis.md/personas.md와의 관계 매핑.
- 부채 D-2/D-3(service-to-service 부채) 처리 보류 결정.
- 후속 TODO (외부 인터뷰·wedge·L4·5분 관찰)의 책임자·시점·측정 지표 명시.

본 retrofit은 **코드 변경 없음** — PRD/ADR/문서 patch만. Sprint 6 진입 전 헌법 + PRD + ADR 정합성 확보가 목표.

### 자의 결정 라벨 (본 산출에서 추가)

- **AD-13**: Q1~Q6 우선순위(Q6 > Q3 > Q1 > Q2 > Q5 > Q4)는 design doc §"Premises" 명시 사실 (자의 X). 단 이 우선순위를 retrofit 7개 산출에 매핑한 결과(Q6→ADR-010, Q3→ADR-011+personas.md, Q1→본 ADR §"Demand Signal Definition", Q2→competitive-analysis.md, Q5→본 ADR §"후속", Q4→Sprint 7+ wedge 선정 ADR)는 자의 — 한 Q가 한 산출에 1:1 매핑되지 않는 cross-cutting 관계 있음.
- **AD-14**: Demand 시그널 정량 임계값(DAU 1+, 회의 업로드 주 2회+, RAG 질의 응답 만족도 70%+, ≥60% 외부 인터뷰 "통합 도구 대체 어려움" 답변)은 본 ADR 자의 설정. ADR-010 AD-8(60%) + ADR-011 §4-b(60%) 정합 검토 적용. 임의 수치 — Sprint 6+ 실측 후 조정 가능.
- **AD-15**: 부채 D-2(notes→embeddings.service) / D-3(rag→embeddings.{models,repository,service}) 처리 결정 **보류** — Sprint 6+ 별도 ADR로 분리. design doc 명시 X (이 분리는 자의). 이유: D-2/D-3은 service-to-service 경계 회색지대 부채로 Stage 1 (기획·아키텍처 메타) 범위가 아닌 Stage 2 (구현 설계) 범위. retrofit 7개 산출 스코프 폭주 방지 목적의 의도된 분리.

---

## 결정

### 1. Stage 1 Retrofit 진입 결정 그 자체

워크플로우 정식 Stage 1을 Phase B로 retrofit한다. 그 동안 누락된 Stage 1 산출(기획·아키텍처 메타) 7개를 동시 작성하고 Generator → Evaluator 패턴(Phase A에서 검증)으로 각각 9+/10 PASS 확보 후 머지.

이 결정의 대안은 (a) Stage 1 누락 그대로 Sprint 6 진입 또는 (b) Stage 1을 Sprint 6 완료 후로 미룸. 두 대안 모두 거부 — (a)는 PRD/ADR이 6 forcing question을 견디는지 미검증 상태 유지로 Sprint 6 결정의 기반이 약함, (b)는 Sprint 6 (멤버십+Private)이 thesis 전제(워크스페이스 단위 멤버십)와 직접 결합되어 Stage 1 후행 시 Sprint 6 자체가 미정 thesis 위에서 결정될 위험.

### 2. 6 Forcing Question 결과 (Q1~Q6)

> 출처: design doc §"Demand Evidence"~§"Premises". 우선순위 Q6 > Q3 > Q1 > Q2 > Q5 > Q4 (design doc 명시, AD-13).

| Q | 영역 | 결과 (1줄) | 매핑 산출 |
|---|---|---|---|
| **Q1** | Demand | 미테스트 — product-first 결정 유지. Sprint 6+ 후 demand 시그널 검증 (§"Demand Signal Definition" 정의) | 본 ADR §3 |
| **Q2** | Status Quo | PRD에 부분 있지만 본인 경험 편향. 경쟁 분석(Otter/Granola/Reflect/Mem/Tana) 신규 작성 | `docs/requirements/competitive-analysis.md` |
| **Q3** | Persona | 카테고리 라벨만 존재 — 본인+가상 페르소나 3개로 구체화 (인터뷰 미진행, AD-4) | ADR-011 + `docs/requirements/personas.md` |
| **Q4** | Wedge | Q3 검증 후 결정 (product-first 일관). 4개 후보 W1~W4 만 정의 | 본 ADR §"후속" + 별도 wedge 선정 ADR |
| **Q5** | Observation | 본인=설계자=사용자 단일 — Sprint 7+ 5분 사용자 세션 관찰 + usage analytics 도입 | 본 ADR §"후속" |
| **Q6** | Future-Fit | thesis 부재가 가장 큰 갭 — L4 누적 차별 + 3개 위협 + 4개 moat | ADR-010 |

### 3. Demand Signal Definition (Q1 — product-first 결정 + Sprint 6+ 검증)

> 본 정의는 PRD §"Demand Signal Definition (Sprint 6+ 계획)" 섹션의 출처이며, ADR-010 §"검증 시그널"·ADR-011 §"외부 인터뷰" 정합.

**Product-first 결정**: Sprint 6(멤버십+Private) 완료 후 demand 검증 시작. 그 전까지는 본인 + 핵심 사용자 1-2명에게 보일 수준 도달이 목표. demand 시그널이 의미 있는 시점은 **다음 3개 조건이 모두 충족된 후**:

1. Sprint 6 완료 (멤버십+Private, D-1 visibility 구현).
2. 도그푸딩 사용자 ≥1명 (본인 + 핵심 사용자 1-2명) 1개월+ 사용.
3. 외부 인터뷰 가이드 작성 (ADR-011 §2 필수 필드 7개 기반).

**Demand 시그널 정량 임계값** (AD-14, 모두 임의 수치 — Sprint 6+ 실측 후 조정 가능):

| 시그널 # | 측정 대상 | 임계값 | 출처 정합 |
|---|---|---|---|
| S1 | 도그푸딩 사용자 DAU | ≥1명 (본인 제외, 1개월+ 지속) | 1차 핵심 사용자 진입 시그널 |
| S2 | 회의 업로드 빈도 (사용자당) | 주 ≥2회 | 헌법 §3 Capture 단계 정착 시그널 |
| S3 | RAG 질의 응답 만족도 | ≥70% (긍정 답변 / 전체 질의) | 헌법 §3 Express 단계 정착 시그널, ADR-010 M1 검증 |
| S4 | Inbox 자동 분류 수용률 | ≥80% (사용자 수정/되돌리기 없는 비율) | 헌법 I-10 inbox_threshold 0.9 = **AI confidence 자동 확정 임계값**(메커니즘); S4 80% = 그렇게 자동 확정된 InboxItem 중 **사용자가 수정·되돌리기 없이 수용한 비율**(사용자 행동 시그널). 두 임계값은 다른 측정 대상. ADR-010 M2 검증. |
| S5 | 외부 인터뷰 "통합 도구로 대체 어려움" 응답률 | ≥60% (Sprint 7+ 5-10명) | ADR-010 AD-8 + ADR-011 §4-b 정합 |
| S6 | 페르소나-Wedge 매트릭스 분화 | PERSONA-001~003 1순위 wedge가 ≥2개 분화 | ADR-011 §4-c hedge 트리거 |

**시그널 해석 정책**:

- S1~S4 = **사용 행동 시그널** (Sprint 6+ 진입 시점부터 측정 가능, usage analytics 도입 후).
- S5~S6 = **시장 시그널** (Sprint 7+ 외부 인터뷰 완료 후 측정 가능).
- 시그널 충족 시점 차이로 인해 "demand 검증 완료" 선언은 S1~S6 모두 PASS 후 별도 ADR로 기록.
- S5 미달 시 ADR-010 thesis 조정 + ADR-011 페르소나 deprecated 트리거 (cross-link).

### 4. 부채 D-2/D-3 처리 보류 결정 (AD-15)

CONTEXT-MAP §7 부채:

- **D-2**: `notes/service.py → embeddings.service` 직접 의존 (service-to-service 경계 회색지대).
- **D-3**: `rag/service.py → embeddings.{models, repository, service}` 직접 의존.

본 retrofit에서는 두 부채의 처리 결정을 **보류**한다. 이유:

- D-2/D-3은 service-to-service 경계 처리 결정이며 **Stage 2 (구현 설계)** 범위. Stage 1 (기획·아키텍처 메타)에서 결정하면 retrofit 7개 산출 스코프 폭주 위험.
- 두 부채는 현재 코드 작동에 지장 없음 (헌법 I-2 "마지막 1회 commit" 원칙은 보호되며, 경계 회색은 미래 확장성 문제).
- Sprint 6+ 멤버십 구현 시 권한 모델이 service-to-service 경계와 직접 결합되므로, 그 시점에 D-2/D-3 처리 ADR을 별도 작성하는 것이 자연.

**보류 = 회피 아님**: 본 ADR §"후속"에 별도 ADR 시점(Sprint 6 완료 후)을 명시 + TODO.md에 등재.

### 5. ADR-010 / ADR-011 / 본 ADR 관계 매핑

| 산출 | 책임 영역 | 정량 임계값 | Cross-link |
|---|---|---|---|
| **ADR-009 (본)** | Stage 1 총괄·Q1 product-first·demand 시그널 6개·D-2/D-3 보류 | S1~S6 (위 §3 표) | ADR-010 검증 시그널 + ADR-011 §4-b 폐기 트리거 |
| **ADR-010** | Future-Fit Thesis·3 위협·4 moat·L4 timeline risk | AD-8 60% 외부 인터뷰 응답률 | 본 ADR S5와 동일 임계값 |
| **ADR-011** | Persona 정의 정책·필수 필드 7개·상태 라벨 4개·폐기 기준 a/b/c | §4-b 60% 7필드 중 3개 불일치 | 본 ADR S5 + S6 정합 |

정량 임계값 60%의 **측정 모집단**(Sprint 7+ 외부 인터뷰 5-10명 응답자)은 세 ADR에 통일. **단 트리거 방향은 ADR별 다름** — ADR-010 AD-8 = "통합 도구 대체 어려움" 응답 ≥60%면 thesis **PASS** 임계, ADR-011 §4-b = 페르소나 필드 불일치 ≥60%면 페르소나 **FAIL**(폐기) 임계, 본 ADR S5 = ADR-010 AD-8과 동일 방향(PASS 임계). 세 ADR이 동일 인터뷰 batch로 측정되며, 같은 응답이 ADR-010 PASS 시그널인 동시에 ADR-011 폐기 시그널일 수 있음(예: 응답자가 "Kairos가 통합 도구 대체 가능"이라 답해도 페르소나 일상·압박 필드와 응답이 불일치하면 페르소나 deprecated 트리거).

---

## 결과

- `docs/requirements/prd.md`가 본 ADR을 출처로 "Demand Signal Definition (Sprint 6+ 계획)" 섹션 PATCH (Plan 산출 #4).
- `docs/TODO.md`가 Stage 1 retrofit 완료 마크 + 본 ADR §"후속" 항목 등재 (Plan 산출 #7).
- Sprint 6 진입 시 헌법(CONTEXT-MAP) + PRD + ADR-009/010/011 + personas.md + competitive-analysis.md 6개 문서가 정합 상태.
- Sprint 6 완료 후 demand 시그널 S1~S4 측정 시작, Sprint 7+ S5~S6 측정 시작.
- 부채 D-2/D-3 처리 ADR 작성 시점 Sprint 6 완료 후로 lock-in.

---

## 비용 / 리스크

- **Demand 시그널 6개 임계값이 모두 임의 수치** (AD-14). Sprint 6+ 실측 시 70%/80%/주 2회 등이 비현실적으로 높거나 낮을 위험. 본 ADR의 임계값은 1차 anchor일 뿐 — Sprint 6 완료 후 실측 기반 재설정 ADR 필수.
- **D-2/D-3 보류가 Sprint 6+ 부담 증가시킬 위험**. 멤버십 구현 시 권한 검증을 어느 service 레이어에 둘지 결정이 부채 처리와 결합되어 Sprint 6 자체 스코프 증가 가능. 완화: Sprint 6 진입 직전 D-2/D-3 처리 ADR을 먼저 작성하는 것이 더 안전할 수 있음 — 본 결정은 retrofit 스코프 폭주 방지 vs Sprint 6 스코프 증가 트레이드오프.
- **본 ADR이 ADR-010/011 cross-link을 강하게 가정**. 셋 중 하나가 supersedes 되면 본 ADR의 §5 매핑 표 + §3 시그널 임계값이 즉시 갱신 필요. supersedes 시 본 ADR도 동시 재검토.
- **Q4 Wedge 결정 보류가 demand 검증을 약화시킬 위험**. wedge 미정 상태에서 도그푸딩 + 외부 인터뷰를 진행하면 사용자 응답이 4개 wedge에 분산되어 시그널 해석 어려움. 완화: ADR-011 §4-c hedge로 동일 wedge 집중 시그널이 잡히면 페르소나 분화 대신 wedge 우선화 ADR 트리거 — 자연스러운 wedge lock-in 경로.

---

## 검증 기준

- [ ] PRD "Demand Signal Definition (Sprint 6+ 계획)" 섹션이 본 ADR §3을 정확히 참조 (시그널 S1~S6 + 정량 임계값).
- [ ] `docs/TODO.md`에 Stage 1 retrofit 완료 마크 + 후속 4개 항목(외부 인터뷰 / wedge 선정 ADR / L4 우선화 / D-2-D-3 별도 ADR) 등재.
- [ ] ADR-010 §"검증 시그널" AD-8 60% + ADR-011 §4-b 60% + 본 ADR S5 60% 정합 (3개 ADR 임계값 단위 통일).
- [ ] 6 forcing question 우선순위 Q6 > Q3 > Q1 > Q2 > Q5 > Q4가 design doc §"Premises" 인용.
- [ ] CONTEXT-MAP §1·§3·§6·§7 위반 없음 (§2 별칭 금지 — 본 ADR 본문에 등장하는 도메인 용어 정식 사용).
- [ ] D-2/D-3 보류 결정이 §"후속"에 별도 ADR 시점(Sprint 6 완료 후)으로 명시.

---

## 후속

> 책임자: 사용자 (1인 풀스택 founder). 시점·측정 지표 명시.

| # | 항목 | 시점 | 측정 지표 | 결과물 |
|---|---|---|---|---|
| F1 | **Sprint 6 (멤버십+Private)** | Sprint 6 (현재 다음 작업) | D-1 visibility 구현·WorkspaceMember 권한 분기 동작 | Sprint 6 완료 PR |
| F2 | **Demand 시그널 S1~S4 측정** | Sprint 6 완료 후 1개월 | usage analytics 도입 + S1(DAU)·S2(회의 빈도)·S3(RAG 만족도)·S4(Inbox 수용률) 실측 | demand 시그널 1차 보고서 |
| F3 | **외부 인터뷰 가이드 작성** | Sprint 6 완료 직후 | ADR-011 §2 필수 필드 7개 + 승진/실패 기준 우회 질문 설계 | `docs/requirements/interview-guide.md` |
| F4 | **외부 인터뷰 5-10명 + S5/S6 측정** | Sprint 7+ | ADR-010 AD-8 60% + ADR-011 §4-b 60% + 본 ADR S5/S6 | `docs/requirements/interview-results.md` |
| F5 | **5분 사용자 세션 관찰 도입 (Q5)** | Sprint 7+ | 도그푸딩 사용자 1-3명 5분 세션 녹화 + "어느 단계에서 ChatGPT/Notion으로 빠지는가" 시그널 | 세션 관찰 raw note (`docs/requirements/observation-notes.md`) |
| F6 | **Wedge 선정 ADR (신규)** | Sprint 6 완료 + F2/F4 결과 후 | 페르소나-Wedge 매트릭스(ADR-011 §3) + S5/S6 시그널 | `docs/adr/012-wedge-selection.md` (예정) |
| F7 | **L4 우선화 검토 ADR (신규)** | Sprint 6 완료 + F4 결과 후 | ADR-010 §4 O1/O2/O3 옵션 선택 + ADR-007 Phase 4 진입 결정 | `docs/adr/013-l4-prioritization.md` (예정) |
| F8 | ~~**부채 D-2/D-3 처리 ADR (신규)**~~ **(closeout 2026-05-11)** | Sprint 6 진입 직전 (옵션 a) ADR-014 선작성 후 머지(commit 038fe37, PR #11). D-2/D-3 부채는 Sprint 6 BE-T9~T14 commit 8096314로 해소(notes/rag pipeline_service 도입). CONTEXT-MAP §4.2 + §7 갱신은 Sprint 6 머지 PR에 포함 | `docs/adr/014-service-boundary.md` (Accepted) + CONTEXT-MAP §4.2/§7 patch |
| F9 | **본 ADR 갱신 검토** | Sprint 7+ 외부 인터뷰 완료 후 | S1~S6 실측 결과로 임계값 재조정 필요성 평가 | 본 ADR supersedes 또는 갱신 PR |
| F10 | ~~**`.ai/common/global.md` §2 ID 체계 표 갱신 PR**~~ **(closeout 2026-05-11)** | 본 retrofit 머지 직후 | `.ai/`가 의도적 git ignored(5adf9f7→231f660)로 PR 불가. ADR-011 §1이 `PERSONA-` 정의의 권위 출처로 확정. 로컬 `.ai/common/global.md` 표는 직접 갱신(git 외부) | ADR-011 closeout patch (docs/dev-log/011 §1·§"후속") |

---

## 메모: 본 ADR의 위치

ADR-009는 **Stage 1 retrofit의 총괄 ADR이자 demand 시그널 정의 ADR**이다. ADR-010/011는 각각 future-fit / persona의 정책 ADR. 셋이 cross-linked되어 Sprint 6+ 모든 의사결정의 정합 기준이 된다.

Phase A (Stage 0 헌법 retrofit) → Phase B (Stage 1 메타 retrofit) 흐름으로 워크플로우 Stage 0+1 누락이 모두 해소되며, Sprint 6 진입은 정식 워크플로우 사이클(Stage 2 구현 설계 → Stage 3 구현)로 복귀.
