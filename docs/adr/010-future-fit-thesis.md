# ADR-010: Future-Fit Thesis — ChatGPT/Notion AI/Granola 흡수 위험에 대한 moat 분석

> **날짜:** 2026-05-11
> **상태:** Accepted
> **작성자:** Claude Opus 4.7 (1M context) + 사용자 (Phase B Stage 1 retrofit)
> **관련:** ADR-004(세컨드 브레인 피벗), ADR-007(L4 조직 인사이트, Phase 4), ADR-009(Stage 1 retrofit 총괄), CONTEXT-MAP.md §1·§3·§6 I-6~I-10·§7 D-1
> **출처:** `~/.gstack/projects/woosung-dev-kairos/woosung-docs-stage1-meta-review-design-20260511.md` (office-hours design doc, Q6)

---

## 배경

워크플로우 `.ai/templates/workflow.md` 정식 Stage 1을 누락하고 Sprint 5 + 온보딩 직전 릴리즈 스프린트까지 product-first로 진행해 왔다. Phase B Stage 1 office-hours에서 6 forcing question을 적용한 결과, **Q6 (Future-Fit)** 이 가장 큰 갭으로 식별되었다.

> 사용자 자기 인식 인용 (office-hours design doc §"What I noticed about how you think"):
> "future-fit thesis 명확하지 않음." — rising tide argument(AI가 좋아지니까 우리도 좋아짐)를 펴지 않고 정직하게 갭 인정.

이 갭이 위험한 이유는 시장 동시 진행 흐름이다.

- **ChatGPT**: memory + Projects + 파일 첨부로 점점 일반 사용자의 "회의/노트 RAG" 영역을 잠식.
- **Notion AI**: Notion 워크스페이스 안에서 회의록 + RAG + 액션 추출을 통합 진행 중.
- **Granola**: 회의 요약 single-purpose에서 RAG + 외부 연동(Confluence/Notion 등)으로 확장 흐름.

Kairos의 차별점이 위 세 통합 도구가 동일 기능을 흡수할 때 buyer가 Kairos를 계속 선택할 만한가 — 본 ADR이 그 답이다. 답이 약하면 retrofit 7개 산출 전체가 표면 정리에 머문다. 답이 강해야 Sprint 6+ 의 우선순위가 흔들리지 않는다.

본 ADR은 **결정(decision) ADR**이 아니라 **분석 + thesis 정립 ADR**이다. 결과로 PRD에 Future-Fit 섹션이 박히고, Sprint 6+ 다음 우선순위 결정 시 본 thesis가 입력이 된다.

### 자의 결정 라벨 (본 산출에서 추가)

- **AD-5**: ADR 파일명은 기존 3자리 패턴 유지 (`010-future-fit-thesis.md`). 헌법 §7에서 "ADR-009 후보"로 이미 3자리 명명함.
- **AD-6**: 위협 도구는 ChatGPT(memory+Projects), Notion AI, Granola 3개로 한정. design doc 명시 — 자의 가공 X. Mem/Reflect/Tana 등 소형 경쟁자는 `competitive-analysis.md`에서 별도 다룸 (위협 시나리오와 경쟁 분석 분리).
- **AD-7**: Moat 4번째 항목으로 "L4 조직 인사이트(ADR-007 Phase 4, 미구현)"를 채택. design doc 명시 — 자의 X. 강도 평가는 본 ADR에서 자의: 가장 강한 후보이되 timeline risk로 단기 약점.
- **AD-8**: Thesis 외부 검증 임계값 60% (≥60% 응답자가 "통합 도구로 대체 어려움" 답변 시 1차 검증). 임의 수치 — Sprint 7+ 시장 관찰 결과로 조정 가능.
- **AD-9**: §4 timeline risk의 O1/O2/O3 옵션 본문 및 후속 섹션에서 "L4 = Sprint 7" 시점으로 호명한 매핑은 자의 — PRD §5 Phase 4는 "Sprint 5+ 시기 미정"이며 정확한 Sprint 번호는 Sprint 6 완료 후 별도 ADR에서 결정. 본 ADR은 표기 편의상 "Sprint 7+"로 호명.

---

## 결정

### 1. 3-year vision (2029년 Kairos 생존 thesis)

> **"Kairos는 팀의 시간 위에 누적된 조직 인사이트(L4, ADR-007)로 일반 AI 도구와 차별화한다. 단일 사용자 컨텍스트가 아닌 워크스페이스 단위 시간 누적이 moat이며, 자동화된 Inbox + 계층 청킹 RAG가 그 누적을 가능하게 한다."**

핵심 단어 세 개:

- **시간 위에 누적** — 단일 회의 요약은 누구나 만들 수 있다. **[가설]** 한 워크스페이스에서 1년치 회의·노트·자료가 쌓일 때 발생하는 크로스 프로젝트 패턴(L4)이 단일 사용자 ChatGPT memory가 따라가기 어려운 영역. 본 명제는 §4 timeline risk와 "비용/리스크"에서 자기 진술 thesis임을 인정하며, Sprint 7+ 외부 인터뷰로 검증.
- **워크스페이스 단위** — `workspace_id` 격리(I-9)가 헌법 불변식. 개인 GPT memory와 달리 팀 공통 공유 자산. 멤버십(Sprint 6), Public/Draft/Private(ADR-004 §5)이 본 thesis의 전제.
- **자동화된 Inbox** — `workspace.inbox_threshold`(I-10, 기본 0.9) 기반 자동 확정. 사용자 개입 최소화가 데이터 누적 속도를 결정. 수동 분류 기반 통합 도구 대비 비교 우위.

### 2. 위협 시나리오 3개 (각 가능성·도래 시점·Kairos 대응)

| # | 위협 | 가능성 | 도래 시점 [가설] | Kairos 대응 |
|---|---|---|---|---|
| T1 | **ChatGPT**: Projects가 파일 첨부 RAG + 시간 누적 memory + 검색을 통합해 "팀 단위 RAG"까지 확장 | 高 | 12~24개월 | 워크스페이스 단위 격리(I-9) + 멤버십 권한 + Inbox 자동화는 ChatGPT가 직접 도입 시 사용자 ID-org 매핑·결제·권한 모델 재설계 필요. 약 12개월 우위. 그 사이 L3/L4로 누적 차별 확보. |
| T2 | **Notion AI**: Notion 워크스페이스 안에서 회의 업로드 → 요약·액션·RAG·인사이트 통합 (현재 부분 진행) | 高 | 6~12개월 | Notion은 문서·DB 중심, 회의/STT는 외부 의존. 회의 파이프라인 일관성·계층 청킹(L1/L2, I-7) 깊이가 단기 차별. L4 조직 인사이트는 Notion이 따라하기 어려운 데이터 모델(크로스 프로젝트 시계열). |
| T3 | **Granola**: 회의 단일 요약에서 RAG + 외부 도구 연동으로 확장 | 中 | 6~18개월 | Granola는 회의 시점 캡처 강점, post-meeting 누적·크로스 프로젝트는 약점. CODE 가치 흐름(§3) 전반 통합이 Kairos 우위. |

> **[가설] 라벨** — 위 표의 도래 시점·Kairos 대응·우위 기간 추정(예: "약 12개월 우위", "Notion이 따라하기 어려운 데이터 모델", "Granola post-meeting 누적 약점") 모두 외부 검증 전 자기 진술이다. competitive-analysis.md 작성 시 공개 로드맵·릴리즈 노트·각 사 공식 발표로 보강.
>
> **도래 시점 추정 근거 (모두 [가설])**:
> - **T1 ChatGPT (12~24개월)** — OpenAI Projects 출시(2025) 이후 파일 첨부 RAG·memory 통합 속도 + Team plan 권한 모델·결제·org 단위 데이터 모델 재정비 필요 추론. 단일 사용자 → 팀 단위 확장은 ID-org 매핑 등 모델 재설계가 필요해 보수적 추정 [확인 필요 — Projects 출시 시점·Team plan 권한 모델 사실 확인].
> - **T2 Notion AI (6~12개월)** — Notion AI가 이미 워크스페이스 내 요약·RAG·액션 추출 일부 제공 중. 회의 STT만 외부 의존이지만 통합 페이스가 빠른 것으로 관찰 [확인 필요 — Notion AI 현재 회의 처리 기능 공개 범위].
> - **T3 Granola (6~18개월)** — 현재 회의 single-purpose 강점. 외부 연동 확장 단서 있으나 post-meeting 누적·크로스 프로젝트 데이터 모델은 후행 추정. 시점 폭이 가장 넓은 이유는 외부 시장 관찰 부재 때문.

### 3. Moat 후보 4개 + 강도 평가

| Moat | 강도 | 강도 근거 | 약점 |
|---|---|---|---|
| **M1. 계층 청킹 + 프로젝트 단위 RAG** | 中 | L1/L2 분리(I-7), 1536d OpenAI 임베딩(I-6), 멀티테넌시 격리(I-9), Semantic Cache TTL 7일+0.93 임계값(I-8). RAG 6-Layer(Cache Lookup → Query Processing → Hybrid Search → Rank Fusion (RRF, k=60, Gemini re-rank 아님) → Generation → Cache Store; `backend/src/rag/CONTEXT.md` §4 + PRD §RAG)의 깊이. | ChatGPT Projects + 파일 첨부가 점차 모방 가능. 청킹 전략은 공개 기술 — 단독으로는 약함. |
| **M2. 자동화된 Inbox** | 中 | `workspace.inbox_threshold`(I-10) 기반 AI confidence 자동 확정. 사용자 개입 최소화 = 누적 속도 ↑. ChatGPT/Notion AI는 수동 분류 중심. | 임계값 정책은 공개 모방 가능. 진짜 차별은 누적된 분류 결과의 품질이지 메커니즘이 아님. |
| **M3. CODE 가치 흐름 통합** | 中 | Capture→Organize→Distill→Express가 한 제품 안에서 일관(§3). [가설] 사용자가 Otter+Notion+Linear+Mem 조합 대신 Kairos 하나를 선택할 것 — Sprint 7+ 외부 인터뷰로 검증 필요. 통합 비용 감소 = 사용자 lock-in. | 일관성 자체가 약점이기도 — 통합 도구 한 곳에서 모방 시 사용자 전환 비용이 낮음. 디테일 깊이로 보강 필요. |
| **M4. L4 조직 인사이트 (ADR-007, 미구현)** | **강(잠재)** | 크로스 프로젝트 패턴 + 시간 누적 복리. 일반 AI 도구는 단일 컨텍스트(사용자 또는 단일 워크스페이스 단기)에서 작동. 1년치 누적된 워크스페이스 단위 인사이트는 모방하려면 동일 데이터 모델 + 시간 + 권한 모델 모두 필요. | **timeline risk** — Phase 4 예정, 현재 미구현. ChatGPT memory가 사용자 단위 1년 누적되면 부분 잠식 가능. |

> **자의 결정 (AD-7 강도 평가)**: M4를 유일하게 "강(잠재)"로 평가. M1~M3은 "中" — 단독으로는 흡수 위험. M4가 thesis의 핵심이지만 timeline 의존. 평가가 너무 후할 가능성에 대한 약점 인정은 §"비용/리스크"에 명시.

### 4. L4 Timeline Risk (자의 평가 약점 인정)

L4가 thesis의 핵심 강도라면 timeline이 thesis 자체의 약점이다.

- ADR-007은 **Phase 4 예정** (TODO.md / `docs/requirements/prd.md` §5 Phase 4 후보 목록).
- 현재 코드 구현 상태: L0~L2 완성, L3 부분(프로젝트 인사이트 일부), L4 미구현 (CONTEXT-MAP §1 "현재 구현 위치").
- ChatGPT memory는 사용자 단위로 이미 누적 진행 중 [확인 필요 — OpenAI memory 정식 공개 일자·현재 누적 깊이]. 같은 시간이 흐를 때 Kairos의 L4가 미구현이면 누적 격차 발생.

**대응 옵션 (Sprint 6 완료 후 별도 ADR로 결정)**:

| 옵션 | 내용 | 트레이드오프 |
|---|---|---|
| O1 | L4(ADR-007)를 Sprint 7로 우선화 | thesis 핵심을 빠르게 lock-in. 그러나 멤버십(Sprint 6) 없이 워크스페이스 단위 데이터 정합성 위험. |
| O2 | Sprint 6(멤버십+Private) → Sprint 7 L4 순서 유지 | 의존성 자연. 멤버십이 L4의 전제(개인 vs 팀 경계 명확). L4 구현 진입 더 늦어짐. |
| O3 | L3 깊이부터(주간/월간 자동 종합) → L4 점진 | 현재 부분 구현된 L3를 완성 후 L4로 자연 이행. 시간 가장 길지만 점진적 검증 가능. |

> **본 ADR 결정 보류**: 옵션 선택은 Sprint 6 완료 후 demand 시그널(ADR-009) + 페르소나 검증(ADR-011) 결과로 별도 ADR. 본 ADR은 thesis와 timeline risk를 명시화하는 것까지가 책임.

> **추가 timeline risk — Thesis 전제 미충족**: 본 thesis의 전제(워크스페이스 단위 멤버십·Public/Draft/Private)도 부분 미충족이다. Project `visibility`는 ADR-004 §5에 정의되어 있으나 `models.py`에 미구현(CONTEXT-MAP §7 D-1). 따라서 thesis는 (a) L4(ADR-007 Phase 4 예정) + (b) 멤버십·visibility(Sprint 6 예정, D-1) 두 미구현 전제에 동시 걸려 있다. Sprint 6(멤버십+Private) → Sprint 7+ L4 의존 순서는 자연이며, 두 전제가 모두 lock-in 되어야 thesis가 외부 검증 가능 상태가 된다.

### 5. Conclusion — Thesis 1줄 + 약점 인정 + 검증 시그널

**Thesis**: "Kairos는 팀의 시간 위에 누적된 조직 인사이트(L4)로 일반 AI 도구와 차별화한다."

**약점 인정**: 핵심 차별점 L4가 미구현이다. 그동안 단기(1년 이내) 차별은 M1(계층 RAG) + M2(자동화된 Inbox) + M3(CODE 통합)으로 버틴다. 이 단기 moat는 약하다 — M1~M3 모두 "中". 사용자가 Kairos를 선택할 이유가 "L4 예정"에 걸려 있으면 demand가 식는다.

**검증 시그널 (Sprint 6+, ADR-009에서 정의)**:

- 본 thesis는 외부 검증 전 자기 진술. Sprint 7+ 외부 인터뷰 5-10명에게 "통합 도구 대신 Kairos 쓸 이유" 질문 → 답변 분석으로 thesis 강도 측정.
- Sprint 6 완료 후 도그푸딩 사용자 1-3명 행동 관찰(5분 사용자 세션) → "어느 단계에서 ChatGPT/Notion으로 빠지는가" 시그널.
- 측정 임계값: 외부 인터뷰 응답자의 ≥60%가 "통합 도구로 대체 어려움" 답변 시 thesis 1차 검증. 미만이면 thesis 조정 또는 wedge 재선정. **AD-8**: 60% 임계값은 임의 — Sprint 7+ 시장 관찰 결과로 조정 가능.

---

## 결과

- `docs/requirements/prd.md`에 "Future-Fit Thesis" 섹션이 본 ADR을 출처로 추가 (PRD batch PATCH 단계).
- Sprint 6+ 다음 우선순위 결정 시 본 thesis(특히 L4 timeline risk)가 입력.
- 외부 인터뷰(Sprint 7+) 설계 시 thesis 검증 질문이 포함.
- 본 ADR이 demand 시그널 정의(ADR-009)와 페르소나 정의(ADR-011)의 상위 thesis로 작동.

---

## 비용 / 리스크

- **Thesis가 외부 검증 없이 자기 진술이다.** office-hours 사용자 자기 인식 + 본인 도그푸딩이 1차 입력. 외부 인터뷰 5-10명 완료(Sprint 7+) 전까지는 "정직한 가설" 수준이다.
- **M4 강도 평가가 후할 가능성.** L4 미구현 상태에서 "강(잠재)"로 평가 — 구현 후 평가 재조정 가능. 만약 L4 구현해도 ChatGPT memory + Notion AI가 워크스페이스 단위로 확장하면 "강" → "中"으로 하향 가능. Sprint 7+ thesis 재검토 ADR로 갱신.
- **L4 timeline 의존이 thesis를 약하게 만든다.** 단기(1년 이내)는 M1+M2+M3로 버텨야 — 이 셋이 모두 "中"이므로 단기 가치 제안이 약함. Sprint 6+ wedge 선정 시 M1~M3 중 가장 강한 영역에 마케팅 집중 필요.
- **위협 시나리오 도래 시점이 가설.** competitive-analysis.md 작성 시 공개 로드맵·릴리즈 노트로 보강 필요.

---

## 검증 기준

- [ ] CONTEXT-MAP.md §1·§3·§6 I-6~I-10 위반 없음 (특히 도메인 용어 별칭 금지 §2 — Workspace/WorkspaceMember/InboxItem/EmbeddingChunk/SemanticCache 정식 용어 사용).
- [ ] 위협 시나리오 3개 모두 가능성·도래 시점·대응 명시.
- [ ] Moat 4개 모두 강도 + 근거 + 약점 3쌍 명시.
- [ ] L4 timeline risk가 회피 없이 명시되어 Sprint 6+ ADR 입력으로 사용 가능.
- [ ] PRD Future-Fit 섹션이 본 ADR을 정확히 참조 (PRD batch PATCH 단계 후).
- [ ] Sprint 7+ thesis 검증 시그널 정의가 ADR-009와 정합.

---

## 후속

- **PRD Future-Fit 섹션 PATCH** — ADR-010/011/009 모두 PASS 후 batch (Plan 산출 #4).
- **Sprint 6+ wedge 선정 ADR (신규)** — Sprint 6 완료 후 demand 시그널(ADR-009) + 페르소나(ADR-011)로 M1~M4 중 우선 영역 결정.
- **L4 우선화 검토 ADR (신규)** — 위 O1/O2/O3 옵션 선택. Sprint 6 완료 시점 별도 ADR.
- **Thesis 외부 검증** — Sprint 7+ 외부 인터뷰 5-10명. 결과로 본 ADR 갱신 또는 후속 ADR.
- **competitive-analysis.md** — Otter/Granola/Reflect/Mem/Tana 비교 + Kairos 차별점(M1~M4) 정렬 (Plan 산출 #6).
