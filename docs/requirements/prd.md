# Kairos — Product Requirements Document

> *그리스어 καιρός — 흘러가는 시간(Chronos) 속 결정적 순간.*
> *흘러가는 모든 정보 흐름에서 결정적 순간만 골라 영구 자산화하는 AI memory layer.*

> **버전:** 3.0
> **최종 수정:** 2026-05-14
> **주요 갱신 (v3.0):** AI memory layer 비전 통합 + Input 축(v1~v5) × Visibility 축(v1.5~v2.0) 2축 로드맵 + Personal↔Team promotion IA + Qdrant 마이그레이션 트리거 lock-in.
> **방향 전환 이력:** ADR-004 PARA → 팀 세컨드 브레인 (v2.0) → AI memory layer (v3.0, 본 갱신)

---

## 0. 프로젝트 철학

**Kairos(καιρός)**는 그리스어로 단순히 흘러가는 시간(Chronos)과 달리,
**결정적인 순간, 포착해야 할 기회의 시간**을 뜻한다.

회의·메신저 스레드·운전 중 떠올린 음성 메모·이메일·웹 클리핑 — 정보가 만들어지는 모든 표면에는 놓치면 사라지는 카이로스가 있다. Kairos는 **AI memory layer**로서 입력 형태에 구애받지 않고 그 결정적 순간을 골라 **개인 → 팀으로 점진 승격**시키며 영구 자산화한다.

### 핵심 프레임워크: CODE (Personal & Team Second Brain)

Tiago Forte의 세컨드 브레인을 **AI가 자동화**하여, **개인 입력 → 팀 자산 승격(promote)** 모델로 확장한다.

```
Capture  → 회의·음성 메모·메신저·이메일·웹 — input 가리지 않음 (v1~v5)
Organize → 프로젝트 자동 연결 + AI 태그 (사용자 선택적 조정)
Distill  → AI 핵심 추출 (Kairos 차별점)
  ├── L1: 개별 콘텐츠 요약
  ├── L2: 결정사항 + 액션 아이템
  ├── L3: 프로젝트 인사이트 (주간/월간 자동 종합)
  └── L4: 조직 인사이트 (크로스 프로젝트 패턴)
Express  → RAG 검색 + 프로액티브 인사이트 + Cmd+K
Promote  → 개인 영역에서 검증된 결정만 팀 자산으로 승격 (v1.5~v2.0)
```

**"개인의 두 번째 뇌가 팀의 첫 번째 기억이 된다"** — Kairos의 핵심 가치.

> **마케팅 핵심 메시지** (자세히 §7-Marketing):
> _"흘러간 시간을 다시 검색할 수 있다면."_
> _"Notion은 정리해야 합니다. Kairos는 정리됩니다."_
> _"당신의 두 번째 뇌, 그리고 팀의 첫 번째 기억."_

---

## 1. 문제 정의

### 현재 상황 — 3가지 통증

| 통증 | 사용자 행동 | 비용 |
|------|------------|------|
| **P1 — 입력이 4곳에 흩어짐** | 회의(Zoom 녹화) + 노트(Notion) + 메신저(Slack/카톡) + 음성 메모(iOS) | 검색·통합 불가, 같은 정보 4번 복붙 |
| **P2 — 사후 정리 노력** | 회의 끝나고 노트 도구로 옮겨 적기 / 카톡 결정 메시지 복사 / 음성 메모 받아쓰기 | 1인당 일평균 1시간 [가설] — Casual 페르소나 직간접 보고 |
| **P3 — 개인 메모 → 팀 공유 흐름 부재** | "내 머릿속에만 있는데 팀에도 알릴 가치 있어. 어디에 정리해서 공유하지?" 마찰 | 결정·아이디어가 조직 자산화되지 않음 |

→ Notion·Otter·Granola·Mem 등 기존 도구는 1-2가지만 부분 해결. **4 통증을 동시에 다루는 통합 도구 부재**.

### 해결하고자 하는 것
> **"입력 형태는 자유, 구조화는 자동, 공유는 점진."**
>
> 회의·메신저·음성 메모·이메일을 그냥 던져두면 AI가 정리하고, 개인 영역에서 충분히 익은 결정만 팀 자산으로 승격된다.

단순한 회의록 도구가 아니라, **개인↔팀 양방향 AI memory layer — 입력 표면에 구애받지 않고, 시간이 지날수록 조직이 똑똑해지는 복리 지식 플랫폼.**

---

## 2. 타겟 유저

### 진입 전략 — Personal-first (YC "single-player first" 격언)

Kairos는 **개인이 혼자 가치를 얻은 뒤 팀으로 확장**하는 IA를 채택한다. Notion(80% 개인 사용에서 시작 [확인 필요]), Slack(DM이 80% 트래픽), Figma(drafts→published) 등 성공한 팀 도구의 공통 패턴.

- **1차 사용자**: 정보를 음성·메신저·메모로 빠르게 만들고 사후 정리할 시간 없는 **knowledge worker 개인**
- **2차 확장**: 1차 사용자가 팀 합류하면 검증된 personal 자산을 **promote** 해 팀 지식으로 승격
- **3차 (Phase 4 L4)**: 팀 단위 시간 누적으로 조직 인사이트 — 복리 효과

### 페르소나 명세 (1차, Sprint 7+ 인터뷰 후 갱신)

상세는 `docs/requirements/personas.md` 참조. 정의 정책은 ADR-011 (`docs/adr/011-persona-definition.md`).

| ID | 이름 (가명) | 역할 | 상태 | 1순위 wedge |
|---|---|---|---|---|
| **PERSONA-001** | WS | 1인 풀스택 founder + product owner | `self-confirmed` (도그푸딩 1명, 강도 약함) | W3 (프로젝트 RAG Q&A) |
| **PERSONA-002** | 김PM | 30대 IT PM, 5-8명 팀 리더 | `[가설]` | W1 (회의 요약·액션 추출) |
| **PERSONA-003** | 박PM | 40대 컨설팅/에이전시 PM, 3-5개 프로젝트 동시 | `[가설]` | W3 (프로젝트 RAG Q&A) |

### Personal-first 사용 시나리오 (PERSONA-001, v1.5~v2.0 기준)

```
T+0     가입 → "WS의 개인 Kairos" personal workspace 자동 생성
T+1일   운전 중 떠올린 제품 아이디어를 iOS 음성 메모 (v2 input)
        → Kairos가 자동 transcribe + 요약 + 태그 5개
T+7일   개인 영역에 회의 3건, 음성 메모 5건, 노트 12건 축적
        AI: "최근 'pricing model' 토픽이 12회 반복됐어요" (프로액티브)
T+14일  공동창업자 합류 → "Kairos Team" workspace 신설 + 초대
T+15일  pricing 노트 5건을 선택 → "Promote to Team" 액션 (v1.6)
        → Team admin (본인) review queue 자동 통과 (1인 → 2인 신뢰)
T+30일  팀 RAG Q&A에서 신규 합류자 질문 "왜 freemium 채택?"
        → 12회 누적된 의사결정 흐름이 출처 [n] 인용으로 답변
```

→ **단일 사용자 가치 → 팀 가치 → 조직 가치** 점진적 확장. YC 관점에서 가장 안전한 PLG 진입.

> **Wedge 분화 점검**: W3 (PERSONA-001/003 1순위) + W1 (PERSONA-002 1순위) — 1순위 2개로 분화. 3명 모두 W3가 1-2순위 우선 → Sprint 7+ 외부 demand 시그널(ADR-009 S5/S6) ≥60% 집중 시 wedge 우선화 ADR(ADR-009 F6) 트리거.

> **갱신 정책**: PERSONA-002~003 `[가설]`은 Sprint 7+ 외부 인터뷰 5-10명 결과 ADR-011 §4-b (≥60% 응답자가 7필드 중 ≥3개 불일치) 트리거 시 `deprecated` + 신규 페르소나 대체, 미만이면 `interview-confirmed` 전환.

---

## 2.5. 경쟁 분석 (Status Quo)

상세는 `docs/requirements/competitive-analysis.md` 참조. ADR-009 §2 Q2 보강 + ADR-010 thesis moat 검증 입력.

### 5축 비교 — Input 다양성 × Ingestion × Output 신뢰 × Personal↔Team × Promotion

| 도구 | Input 다양성 | AI Ingestion | 출처 인용 | Personal↔Team | Promote 액션 |
|------|------------|-------------|---------|--------------|------------|
| **Kairos (v2.0 목표)** | 회의·음성·메신저·이메일·웹 | 자동 (CODE) | ✅ 인라인 [n] 강제 | Personal+Team workspace 분리 | ✅ explicit + AI 추천 |
| Otter | 회의만 | 부분 | 부분 | 없음 | 없음 |
| Granola | 회의 (macOS) | 부분 | 부분 | 개인만 | 없음 |
| Mem | 노트·일부 통합 | 자동 | 부분 | 개인만 | 없음 |
| Notion AI | 텍스트만 | 수동 | 약함 | Private page + Team | drag-drop 수동 |
| Reflect | 노트 | 자동 | 부분 | 개인만 | 없음 |
| Tana | 노트·DB | 부분 | 없음 | 기본 | 수동 |
| Glean (Enterprise) | 전사 검색 | 검색 only | ✅ | 전사 only (개인 X) | N/A |

→ **5축 모두 우월한 도구는 현재 없음** `[확인 필요 — 2026-05 기준 시장 조사 1회 더 필요]`. Kairos v2.0 목표가 이를 점유.

### Moat 정렬 (ADR-010 thesis M1~M4 + 신규 M5)

- **M1 계층 RAG** (中, 단독 약함) — Tana만 워크스페이스 범위 AI Q&A, 계층 청킹·6-Layer·1536d 임베딩·Semantic Cache 깊이는 Kairos 우위.
- **M2 자동 Inbox** (中) — Mem과 **직접 경쟁** (Mem도 AI 자동 분류). 차별 anchor = `workspace.inbox_threshold` 0.9 (I-10) + 사용자 행동 시그널 S4 80%.
- **M3 CODE 통합** (中) — Tana가 가장 근접 위험. Capture+Organize+Distill L2+Express 일관성 우위이나 모방 risk 높음.
- **M4 L4 조직 인사이트** (강, 잠재 — **미구현 timeline risk**) — 5개 경쟁자 누구도 L4 영역 진입 X (단일 사용자·단일 워크스페이스 단기 범위).
- **M5 Personal↔Team graph** (강, 잠재 — v1.5~v2.0 신설) — 개인 활동 패턴 + 팀 활동 패턴 동시 학습으로 **promotion 추천 AI** 가능. Notion·Granola·Mem 누구도 양축 동시 보유 X. v2.0 ship 시 4 도구 사용자가 Kairos로 통합 전환 트리거.

---

## 3. 핵심 가치 제안

| 기존 방식 | Kairos |
|-----------|--------|
| 회의 후 수동으로 회의록 작성 | 녹음 업로드 → AI 자동 요약/액션 추출 |
| 주제별 폴더 정리 | 프로젝트 + AI 태그 자동 분류 (사용자는 선택적 조정) |
| 끝난 프로젝트 = 죽은 데이터 | Archive → AI 인사이트 추출 → 조직 자산 재활용 |
| "어디 있더라?" 검색 | RAG: 자연어 질문 → 하이브리드 검색 + 소스 신선도 표시 |
| 새 팀원 = 몇 주간 맥락 파악 | RAG에 "이 프로젝트 배경이 뭐야?" 질문 → 즉시 답변 |
| 개인 머릿속 암묵지 | 개인 지식 → 팀 승격 → 조직 자산으로 복리 축적 |

---

## 3.5. Future-Fit Thesis (3-year vision)

상세는 ADR-010 (`docs/adr/010-future-fit-thesis.md`) 참조.

### Thesis (1줄, v3.0 갱신)

> **"Kairos는 입력 표면에 구애받지 않는 AI memory layer다. 회의·음성 메모·메신저·이메일이 자동 구조화되어 개인 영역에 축적되고, 검증된 결정만 팀으로 승격되어 조직 인사이트(L4)로 복리화된다. 단일 사용자 컨텍스트가 아닌 Personal↔Team graph + 워크스페이스 단위 시간 누적이 moat다."**

### Long-game (1-pager 슬로건)

> _"AI memory layer for people who think out loud."_
>
> ChatGPT가 '전 인류의 검색'이라면, Kairos는 '내 팀의 검색 + 내 머리의 저장소'.

### 위협 시나리오 (통합 도구 흡수 risk) `[전부 가설]`

| # | 위협 | 도래 시점 [가설] |
|---|---|---|
| T1 | **ChatGPT** (memory + Projects 확장으로 팀 단위 RAG) | 12~24개월 |
| T2 | **Notion AI** (워크스페이스 안 회의·RAG·인사이트 통합) | 6~12개월 |
| T3 | **Granola** (회의 single-purpose → RAG·외부 연동 확장) | 6~18개월 |

> 도래 시점 추정 근거는 ADR-010 §"위협 시나리오" 표 아래 단락 — 모두 외부 검증 전 `[가설]`. `competitive-analysis.md` 후속 보강(B2: 공식 문서 WebFetch)으로 출처 라벨 해제 예정.

### Moat 5개 + 강도 (v3.0 — M5 신설)

| Moat | 강도 |
|---|---|
| **M1** 계층 청킹 + 프로젝트 단위 RAG (L1/L2, 1536d, Semantic Cache TTL 7일·0.93) | **中** (단독 약함, 청킹 전략 공개 기술) |
| **M2** 자동화된 Inbox (`workspace.inbox_threshold` 기본 0.9, I-10) | **中** (메커니즘 모방 가능, 차별은 누적 품질) |
| **M3** CODE 가치 흐름 통합 (Capture→Organize→Distill→Express 일관) | **中** (일관성 자체가 약점 — 모방 시 전환비용 낮음) |
| **M4** L4 조직 인사이트 (ADR-007 Phase 4, **미구현**) — 워크스페이스 단위 격리(I-9) + 시간 누적 복리 | **강(잠재)** — 가장 강한 후보이나 timeline risk |
| **M5** Personal↔Team graph (v1.5~v2.0 신설) — 개인 활동 + 팀 활동 동시 학습 → promotion 추천 AI | **강(잠재)** — 양축 동시 보유 도구 없음, ship 시 카테고리 정의 가능 |

### 약점 인정 + 검증 시그널

- 단기(L4 구현 전, ~Sprint 10 추정)는 M1+M2+M3 中 셋이 차별 anchor. 가치 제안 단기 약함 — ChatGPT memory 누적 격차 risk.
- Thesis 전제 미충족: L4(ADR-007 Phase 4 예정)만 남음. ~~멤버십·visibility(D-1 미구현)~~ **[해소 Sprint 6, 2026-05-11 PR #12]** — Project.visibility 컬럼 + ProjectMember 엔티티 + visibility 권한 분기 모두 구현. ADR-014 옵션 A로 orchestrator 경계까지 정합.
- M5 Personal↔Team graph (v1.5~v2.0)는 v3.0 새 thesis 핵심 — **Sprint 15-16 ship 안 되면 thesis 일부 깨짐**. M5 timeline risk가 M4보다 단기.
- 검증: Sprint 7+ 외부 인터뷰 응답자의 ≥60%가 "통합 도구로 대체 어려움" 답변 시 thesis 1차 검증 (ADR-010 AD-8, ADR-009 S5와 동일 임계값).

---

## 3.6. IA 2축 로드맵 (v3.0 신설)

기존 PRD는 Sprint 단위 1차원 phase 로드맵이었다. v3.0부터는 **2축 매트릭스**로 재구성:

- **X축 = Input source 다양성** (v1~v5)
- **Y축 = Visibility/IA — Personal↔Team** (v1.5~v2.0)

```
           [X축 — Input source 다양화]
           ┌─────────────────────────────────────────────────────┐
           │ v1      v2          v3         v4         v5        │
           │ 회의    음성 메모    Slack       카톡 봇   웹/이메일  │
           │ ✅      ⏳ Sprint    ⏳ Sprint   ⏳ Sprint  ⏳ Sprint │
           │ 완료    16~17        18~19       20         21~22    │
           │                                                     │
           │ [Y축 — Visibility / Personal↔Team]                  │
           │                                                     │
[v1.5]  Personal workspace 자동 생성 + workspace switcher       │
        Sprint 15 (1차 우선순위, IA가 다른 축에 영향)             │
                                                                 │
[v1.6]  Promote action — 아이템 → 다른 workspace로 복제           │
        Sprint 16                                                │
                                                                 │
[v1.7]  Promotion review queue (admin auto-accept or review)    │
        Sprint 17                                                │
                                                                 │
[v1.8]  Cross-workspace RAG (Personal + Team 통합 검색)         │
        Sprint 18 + 헌법 R-13 신설                                │
                                                                 │
[v2.0]  Promotion 추천 AI ("이 메모는 {Team}에 올리면 좋겠어요") │
        Sprint 22+ (M5 moat 핵심)                                │
           └─────────────────────────────────────────────────────┘
```

### Ship 우선순위 (Sprint 15부터)

| Sprint | 축 | 작업 | 근거 |
|--------|----|------|------|
| 15 | Y (v1.5) | Personal workspace + switcher | IA 결정이 다른 축에 영향, 먼저 lock-in |
| 16 | Y (v1.6) + X (v2) | Promotion action + 음성 메모 ingest | Y v1.6 + X v2 같은 인프라 재사용 (STT) |
| 17 | Y (v1.7) | Promotion review queue | v1.6 ship 후 사용자 행동 데이터 확보 |
| 18-19 | X (v3) + Y (v1.8) | Slack ingest + cross-workspace RAG | 결정·메시지 RAG 풀 — B2B 진입 |
| 20 | X (v4) | 카톡 봇 | 한국 시장 wedge |
| 21-22 | X (v5) + Y (v2.0) | 이메일/웹 + Promotion 추천 AI | M5 moat 완성 |

### 핵심 원칙

1. **IA 먼저, Input 다음** — Visibility 모델 결정이 RAG·임베딩·권한 코드 전체에 영향. 잘못 ship 하면 v2 이후 모든 input pipeline retrofit 필요.
2. **인프라 재사용 우선** — v2 음성 메모는 v1 STT 재사용, v1.8 cross-workspace RAG는 기존 6-Layer 재사용.
3. **헌법 갱신 명시** — Y 축 ship마다 헌법 신규 불변식 (R-13 cross-workspace RAG opt-in 등) ADR 작성.

상세는 `git history` 등 sprint plan에 작성.

---

## 4. 시스템 아키텍처 요약

```
[Capture] 오디오/영상/노트/자료 입력
  → Cloudflare R2 업로드
  → (오디오) Whisper STT + pyannote 화자 분리

[Organize] AI 자동 구조화
  → Gemini API: 요약 + 액션 아이템 + 프로젝트 연결 + 태그 자동 부여
  → Inbox 적재 (AI 자동 연결, 사용자 선택적 조정)

[Distill] AI 핵심 추출
  → L1: 개별 콘텐츠 요약
  → L2: 결정사항 + 액션 아이템
  → L3: 프로젝트 인사이트 (주간 자동 종합)

[Express] 지식 활용
  → 벡터 임베딩 저장 → RAG 검색 & Q&A
  → 프로액티브 인사이트 (AI가 먼저 알려줌)
  → Cmd+K 통합 검색
```

**Tech Stack:** Next.js 16 + FastAPI + PostgreSQL + Cloudflare R2 + Gemini API + Whisper

### 4.1 RAG 성능 KPI (Sprint 16 ADR-020 신설)

> 당근(Karrot) DB 밋업 pgvector 최적화 노하우 적용 — `docs/adr/020-pgvector-hnsw-halfvec.md`. Layer 3 (Hybrid Search) 기준 측정.

| KPI | Baseline (ivfflat) | 목표 (HNSW + halfvec) | 합격선 |
|---|---|---|---|
| recall@10 | 측정 기준값 (Stage 5 fixture) | ≥ baseline × 0.95 | < 0.95 시 ADR-020 rollback |
| p50 latency | Stage 5 측정 | ≤ baseline × 1.0 | regression 금지 |
| p95 latency | Stage 5 측정 | ≤ baseline × 1.2 | 20% 이상 회귀 금지 |
| 벡터 저장공간 | 6KB/row (fp32 × 1536d) | 3KB/row (fp16 × 1536d) | 50% 절감 |
| 인덱스 빌드 시간 | ivfflat baseline | 측정 후 ADR-020 §"비용/리스크" 갱신 | 운영 한계 사전 인지 |
| RBAC/visibility 포스트필터 결과 부족 빈도 | iterative_scan 미지원 → 발생 가능 | iterative_scan(relaxed_order) → 자동 해소 | "결과 0건" 시그널 감소 |

**측정 fixture**: `apps/backend/tests/embeddings/fixtures/recall_corpus.json` (1000 chunk + 50 query, Sprint 16 Stage 3 신설).
**측정 도구**: `apps/backend/scripts/bench_vector_search.py` (Sprint 16 Stage 4 신설).
**검증 시점**: Sprint 16 Stage 5 (alembic upgrade 후 baseline vs after 비교).
**모니터링 후속**: Sprint 15 R7 metrics infra(`MemoryEvent.recall_latency_ms`)와 통합 검토.

---

## 5. Phase 로드맵

> **실행 전략:** Vertical Slice Sprint — Phase 순차 진행 대신 핵심 가치 흐름을 FE+BE 관통.
> 의사결정 근거: `docs/adr/002-execution-strategy.md`

---

### Phase 0 — 문서 구체화 + 아키텍처 검증 (Sprint 0, ~3일)

**목표:** Phase 1~4 실행에 필요한 문서 병목 해소.

- [x] `docs/api/endpoints.md` — 32개 REST API 명세 (Sprint 1~2 상세)
- [x] `docs/architecture/backend-scaffolding.md` — 백엔드 초기 셋업 가이드
- [x] 본 PRD Sprint 분해 완료 (이 섹션)

**완료 기준:** API 명세 + 백엔드 셋업 가이드 작성 완료, 다음 Sprint 즉시 착수 가능

---

### Phase 1 — 프론트엔드 스캐폴딩 (Mock Data) ✅ 진행 중

**목표:** 백엔드 없이 UI/UX를 먼저 완성해 흐름을 검증한다.

#### 완료
- [x] Next.js 16 프로젝트 초기화
- [x] 3-Panel 레이아웃 (사이드바 / 메인 / RAG 패널)
- [x] Inbox 뷰 UI (mock data)
- [x] ~~PARA 아이템 CRUD~~ (mock data) — ADR-004: 프로젝트 구조로 전환 필요

#### 남은 작업 (Sprint 1에서 Phase 2와 병합)

| 작업 | 우선순위 | 예상 (CC) | 의존성 | Sprint |
|------|----------|-----------|--------|--------|
| Clerk 인증 연동 (FE 전용: proxy.ts + 컴포넌트) | P0 | 1h | 없음 | Sprint 1 |
| 회의 업로드 페이지 (드롭존 + 녹음 UI) | P0 | 2h | Clerk | Sprint 1 |
| 회의 상세 페이지 (트랜스크립트 뷰어) | P1 | 2h | 업로드 | Sprint 2 |
| 액션 아이템 칸반 보드 | P1 | 2h | 없음 | Sprint 2 |
| 프로젝트 연결 워크플로우 (PARA 대체) | P1 | 1h | Inbox UI | Sprint 2 |

> Phase 1 남은 작업은 Phase 2와 동시 진행 (Vertical Slice 전략).
> FE는 worktree에서 병렬로, BE 스캐폴딩과 동시에 진행한다.

---

### Sprint 1 (Week 1-2): "회의 → AI 요약" Vertical Slice

**목표:** 녹음 업로드 → AI 요약 출력까지 FE+BE End-to-End 동작.

#### 백엔드 (Phase 2 착수)
- [ ] FastAPI 프로젝트 구조 셋업 (uv, SQLModel, Alembic)
- [ ] DB 마이그레이션 (User, Workspace, Meeting, MeetingSummary)
- [ ] Clerk JWT 검증 미들웨어
- [ ] Cloudflare R2 파일 업로드 API
- [ ] `POST /meetings` (202 Accepted + BackgroundTasks)
- [ ] `GET /meetings/{id}/status` (polling)
- [ ] Whisper API + pyannote-audio 화자 분리
- [ ] Gemini 요약 파이프라인 (1개 프롬프트: MEETING_SUMMARY)

#### 프론트엔드 (Phase 1 잔여 + API 연결)
- [ ] Clerk 인증 연동 (proxy.ts + sign-in/up)
- [ ] 회의 업로드 페이지 (드롭존 → R2 → BE 호출)
- [ ] 회의 상세 페이지 (요약 표시, 트랜스크립트 뷰어)

**완료 기준:** 녹음 파일 업로드 → 2분 내 AI 요약 확인 가능
**병렬화:** FE(Clerk + 업로드)는 worktree-A, BE(스캐폴딩)는 main에서 동시 진행

---

### Sprint 2 (Week 3-4): "Inbox + 프로젝트 연결 + 액션" 확장

**목표:** 업로드 → 요약 → 액션 추출 → Inbox → 프로젝트 연결 완전 체인.

#### 백엔드
- [ ] Gemini 액션 아이템 추출 + 프로젝트 연결/태그 추천 파이프라인
- [ ] Inbox CRUD API (`GET /inbox`, `POST /inbox/{id}/classify`, `POST /inbox/{id}/dismiss`)
- [ ] Project CRUD API (`GET/POST/PATCH/DELETE /projects`, `POST /projects/{id}/archive`)
- [ ] ActionItem CRUD API (`GET/POST/PATCH /action-items`)
- [ ] 오케스트레이터 통합 (MeetingPipelineService)
- [ ] Inbox 자동 적재 (AI confidence ≥ 0.9 자동 확정, 임계값 사용자 조절 가능 — ADR-006 §7)

#### 프론트엔드
- [ ] Mock → Real API 전환 (Inbox, Project, ActionItem)
- [ ] React Query 뮤테이션 연동
- [ ] 액션 아이템 칸반 보드
- [ ] 프로젝트 연결 워크플로우 (AI 추천 → 자동/수동 확정)
- [ ] 업로드 진행률 UI

**완료 기준:** 업로드 → 요약 → 액션 → Inbox → 프로젝트 연결까지 전체 흐름 동작
**Phase 1 남은 작업 완료 시점:** 이 Sprint 종료 시 Phase 1 + Phase 2 핵심 모두 완료

---

### Sprint 3 (Week 5-6): RAG + 노트 — "질문할 수 있는 지식"

**목표:** 쌓인 데이터를 자연어로 질문 가능한 자산으로 전환.

> 상세 설계: `docs/architecture/rag-pipeline.md`

#### 백엔드
- [ ] 임베딩 서비스 (계층적 청킹: 회의→화자 구간→문단)
- [ ] 하이브리드 검색 API (pg_trgm + vector + RRF)
- [ ] Semantic Cache (유사도 ≥ 0.93 즉시 반환)
- [ ] `POST /rag/ask` (SSE 스트리밍)
- [ ] Note CRUD API

#### 프론트엔드
- [ ] RAG 채팅 패널 (프로젝트 범위 지정, 시간/소스 필터) + Cmd+K
- [ ] Tiptap 블록 에디터 (StarterKit + Placeholder + CharacterCount)
- [ ] debounce 자동 저장 (500ms)
- [ ] 노트 → 임베딩 자동 등록

#### Archive
- [ ] Project 완료 → Archive 전환 (Resource 보존 옵션)
- [ ] Archive 데이터 RAG 소스 포함

**완료 기준:** "지난 회의에서 CMS 관련 결정이 뭐였지?" → 2초 내 스트리밍 답변

---

### Sprint 4 (Week 7-8): Polish + Auth + 배포 — "내부 팀에게 전달"

**목표:** 내부 팀 5명이 실제 사용 가능한 수준으로 마무리.

#### RBAC + 보안
- [ ] 역할 4단계: Owner / Admin / Member / Viewer
- [ ] 워크스페이스 단위 권한 설정
- [ ] 초대 링크 + 이메일 초대

#### 배포
- [ ] GCP Cloud Run 배포 (Docker)
- [ ] Vercel 프론트엔드 배포
- [ ] 환경변수 관리 (production)
- [ ] 헬스체크 + 모니터링 기본 셋업

#### 품질 보증
- [ ] 전체 QA (gstack /qa)
- [ ] UI 디자인 감사 (gstack /design-review)
- [ ] 보안 감사 (gstack /cso)
- [ ] 성능 기준선 측정 (gstack /benchmark)

**완료 기준:** 내부 5명 온보딩 + 실제 회의 업로드 + RAG 검색 사용

---

### Phase 4 — 보고서 생성 + 외부 연동 (Sprint 5+, 시기 미정)

**목표:** MVP 검증 후 확장 기능 추가.

> Phase 4는 내부 팀 피드백 기반으로 우선순위를 재조정한다.
> 아래는 후보 목록이며, Sprint 4 완료 후 `/office-hours`로 재검토.

#### AI 문서 생성 (후보)
- [ ] 주간/월간 보고서 자동 생성 (프로젝트 활동 요약)
- [ ] 슬라이드 발표 자료 초안 생성

#### 외부 연동 (후보)
- [ ] Google Meet 녹화본 자동 연동
- [ ] Zoom 클라우드 녹화 연동
- [ ] Slack 알림 (액션 아이템 마감 리마인더)

---

### Sprint 전환 기준

| 조건 | 다음 Sprint 진입 가능 |
|------|:---:|
| 해당 Sprint "완료 기준" 충족 | O |
| 핵심 기능 동작 (버그 있어도 흐름 완성) | O |
| 핵심 기능 미동작 (흐름 끊김) | X — 해당 Sprint 연장 |
| QA Health score 8 미만 | 주의 — 버그 수정 후 진입 권장 |

---

## 6. UI/UX 레퍼런스

| 영역 | 벤치마킹 |
|------|----------|
| 전체 레이아웃 | Linear.app (3-panel, 다크모드 우선) |
| 액션 아이템 | Jira 칸반보드 + 리스트 뷰 |
| 노트 에디터 | Notion 블록 에디터 |
| 지식 검색 (핵심) | NotebookLM 스타일 RAG 채팅 + Cmd+K |
| 지식 관리 | Slite (팀 지식 + 신선도) + Mem.ai (낮은 입력 마찰) |
| 프로젝트 네비게이션 | 사이드바 프로젝트 리스트 + 태그 필터 |

---

## 7. 성공 지표 (MVP 기준)

- 회의 업로드 → Inbox 적재까지 **3분 이내** (Sprint 10 검증: 7.5초)
- AI 액션 아이템 추출 정확도 **80% 이상** (사용자 체감)
- RAG 질문 → 답변 스트리밍 시작까지 **2초 이내**
- Phase 1~2 완료 후 내부 테스트 사용자 **5명 이상** 온보딩

---

## 7-Marketing. 마케팅 메시지 (v3.0 신설)

### Tagline 후보 (외부 노출 5개)

1. **"흘러간 시간을 다시 검색할 수 있다면."** — 감성, founder 타겟
2. **"당신의 모든 결정을, 출처 보장 검색으로."** — 신뢰 강조, B2B
3. **"Notion은 정리해야 합니다. Kairos는 정리됩니다."** — 비교 우위
4. **"회의·메신저·음성 메모 — 입력 형태는 자유, 구조화는 자동."** — Input 다양성 + AI ingest
5. **"Personal memory layer for people who think out loud."** — 영문 deck

> 외부 테스트 후 1개 lock-in (Sprint 15 action item, 인디해커즈/X DM 50명 A/B 반응 측정).

### One-line pitch (투자자 / B2B 세일즈)

> _"We're building the **memory layer for the AI era**. Voice notes, meetings, Slack threads, emails — Kairos automatically extracts your team's καιρός (decisive moments) and makes them permanently searchable with cited sources."_

### 메시지 매트릭스 (청자별)

| 청자 | 메시지 |
|------|--------|
| **1인 founder** | "노트 도구 0개로 가능. 녹음만 하면 끝." |
| **스타트업 PM** | "Notion에 사후 정리하지 마세요. AI가 회의 → Notion 수준 구조로 자동." |
| **컨설턴트** | "인터뷰 50건이 RAG 데이터셋이 됩니다. 보고서 작성 시간 80% 감소." |
| **CTO / 데이터팀** | "팀 회의 = 검색 가능한 임베딩. SSO + private 격리 + 출처 보장." |
| **투자자** | "M1+M5 lock-in moat. 1년 사용자 retention >90% [가설]." |

### 차별화 4축 (마케팅 deck용)

1. **Input source 다양성** — 회의·음성·메신저·이메일 모두 (경쟁 도구는 1-2개만)
2. **AI-first ingestion** — 사용자 수동 정리 0 (Notion은 수동)
3. **출처 보장 RAG** — 인라인 [n] 인용 강제, 환각 차단
4. **Personal↔Team graph** — 개인 → 팀 promotion + AI 추천 (Notion/Granola/Mem 없음)

### 가격 포지셔닝 `[가설]`

| Tier | 가격 | 포함 | 타겟 |
|------|------|------|------|
| Free | $0 | 회의 5건/월, Personal workspace only | trial / 1인 founder 진입 |
| Pro | $19/월 | 무제한 input, Personal+1 Team workspace, RAG | 1인 founder · 프리랜서 |
| Team | $12/사용자/월 | 5+ 사용자, RBAC, Promote review queue, cross-workspace RAG | 5~15인 스타트업 |
| Enterprise | $80/사용자/월 | SSO, SOC 2, 감사로그, 데이터 격리 | 50+ 조직 |

> 비교: Otter Pro $16.99 / Notion AI $10 add-on / Granola Business $14. Kairos는 **5축 통합 + Personal↔Team** 가치로 $19 책정 가능. Sprint 15 willingness-to-pay 인터뷰로 검증.

---

## 7.5. Demand Signal Definition (Sprint 6+ 계획)

상세는 ADR-009 §3 (`docs/adr/009-stage1-retrofit.md`) 참조. Q1(Demand) product-first 결정 + Sprint 6+ 후 demand 검증 정합.

### Product-first 결정

Sprint 6(멤버십+Private) 완료 후 demand 검증 시작. demand 시그널이 의미 있는 시점은 다음 3개 조건이 모두 충족된 후:

1. Sprint 6 완료 (D-1 visibility 구현·WorkspaceMember 권한 분기 동작).
2. 도그푸딩 사용자 ≥1명 (본인 + 핵심 사용자 1-2명) 1개월+ 사용.
3. 외부 인터뷰 가이드 작성 (ADR-009 F3, `docs/requirements/interview-guide.md`).

### Demand 시그널 6개 (S1~S6) 정량 임계값

> 모두 임의 수치 (ADR-009 AD-14) — Sprint 6+ 실측 후 조정 가능.

| 시그널 | 측정 대상 | 임계값 | 측정 시점 | Moat cross-link |
|---|---|---|---|---|
| **S1** | DAU (도그푸딩 사용자) | ≥1명 (본인 제외, 1개월+ 지속) | Sprint 6 완료 후 | 1차 핵심 사용자 진입 |
| **S2** | 회의 업로드 빈도 (사용자당) | 주 ≥2회 | Sprint 6 완료 후 | §3 Capture 정착 |
| **S3** | RAG 질의 응답 만족도 | ≥70% | Sprint 6 완료 후 | §3 Express 정착, M1 검증 |
| **S4** | Inbox 자동 분류 수용률 (수정·되돌리기 없는 비율) | ≥80% | Sprint 6 완료 후 | I-10 + M2 검증 (아래 두 임계값 분리 주의) |
| **S5** | 외부 인터뷰 "통합 도구로 대체 어려움" 응답률 | ≥60% (Sprint 7+ 5-10명) | Sprint 7+ | M4 thesis 검증 |
| **S6** | 페르소나-Wedge 매트릭스 분화 | PERSONA-001~003 1순위 wedge ≥2개 분화 | Sprint 7+ | ADR-011 §4-c hedge |

> **S4 두 임계값 분리 주의**: I-10 `workspace.inbox_threshold` 0.9 = **AI confidence 자동 확정 임계값(메커니즘)**; S4 80% = 그렇게 자동 확정된 InboxItem 중 **사용자가 수정·되돌리기 없이 수용한 비율(행동 시그널)**. 두 임계값은 다른 측정 대상이며, S4 임계값 조정이 I-10 헌법 불변식 변경을 의미하지 않음.

### 60% 임계값 통일 (ADR-010/011/009)

ADR-010 AD-8(thesis PASS) / ADR-011 §4-b(페르소나 FAIL) / 본 S5(thesis PASS) — **측정 모집단**(Sprint 7+ 외부 인터뷰 5-10명 응답자)은 통일, **트리거 방향은 ADR별 다름**. 같은 응답이 ADR-010 PASS 시그널인 동시에 ADR-011 폐기 시그널일 수 있음.

### 시그널 충족 후 (ADR-009 §3 시그널 해석 정책 정합)

- **S1~S6 모두 PASS**: "demand 검증 완료" 선언 → 별도 ADR로 기록 (ADR-009 후속 F4/F6/F7 연동).
- **S5 미달 (Sprint 7+ 외부 인터뷰 ≥60% "통합 도구 대체 어려움" 답변률 미달)**: ADR-010 thesis 조정(supersedes 또는 갱신 PR) + ADR-011 §4-b 트리거로 PERSONA-002~003 `deprecated` 또는 wedge 재정의.
- **S1~S4 미달 (Sprint 6+ 행동 시그널)**: 도그푸딩 시나리오 재설계 + Sprint 6 산출 재검토. ADR-010 thesis 즉시 갱신은 불요(외부 시장 시그널이 아니라 내부 사용 시그널이므로 thesis 직접 영향 X).
- **S6 미달 (페르소나-Wedge 분화 부재)**: ADR-011 §4-c hedge 트리거 — 페르소나 재정의 vs wedge 우선화 ADR(F6) 신규 분기 결정.

---

## 8. 현재 컨텍스트

- **방향 전환:** PARA → 팀 세컨드 브레인 (ADR-004, 2026-04-02)
- **현재 Phase:** Sprint 10 완료 (E2E 검증) — **Sprint 1~10 진행 중 (2026-05-12)**
- **Sprint 1-2:** 회의 업로드 → STT → AI 요약 → 액션 → Inbox → 프로젝트 연결 ✅
- **Sprint 3:** 임베딩(pgvector) + Hybrid Search + SSE RAG + 노트 + Semantic Cache ✅
- **Sprint 4:** GCP Cloud Run + Vercel + Neon prod 배포, GitHub Actions CI ✅
- **Sprint 5-6:** RBAC + 초대 시스템 + Visibility 권한 분기 + ProjectMember 신설 ✅
- **Sprint 7-10:** 도그푸딩 8 자동 케이스 + E2E 검증 + R2 CORS 수정 ✅
- **Sprint 11:** E2E 자동화 + 마이크 녹음 + (선택) BL-002 리팩토링 (진행 중, 2026-05-12~)
- **프로덕션 URL:** FE `https://kairos.woosung.dev` / BE `https://kairos-api.woosung.dev` (2026-08-14 ADR-028 오라클 셀프호스팅 전환)
- **다음 작업:** Sprint 11 (E2E + 마이크 녹음)

### Phase/Sprint/Stage 용어 매핑

| 체계 | 의미 | 출처 |
|------|------|------|
| **Phase 0~4** | 제품 로드맵 단계 (장기) | 이 문서 §5 |
| **Sprint 1~5** | 2주 단위 실행 주기 (Phase 내부) | 이 문서 §5 |
| **Plan → Code → Test** | 세션 워크플로우 (설계→구현→검증). 옛 8-Stage 는 Sprint 26 폐지 | `AGENTS.md` §4 |

---

## 9. MVP 명시적 제외 목록

아래 기능은 MVP 범위에서 **의도적으로 제외**한다. Phase 2 이후 검토.

- NotebookLM 스타일 인포그래픽/슬라이드 자동 생성
- 실시간 라이브 트랜스크립션 (회의 중 실시간 STT)
- ~~크로스 프로젝트 RAG (조직 전체 검색)~~ — **v1.8 Cross-workspace RAG로 재진입** (Sprint 18+)
- ~~Jira / Slack / 외부 캘린더 연동~~ — **v3 Slack ingest로 재진입** (Sprint 18-19)
- 주간/월간 보고서 자동 생성 — L3 프로젝트 인사이트로 대체 가능
- 모바일 네이티브 앱 (PWA로 대체)

---

## 부록 A — Competitor 비교 매트릭스 (Personal↔Team 축, v3.0 신설)

| 도구 | Personal 영역 | Team 영역 | Promotion 메커니즘 | Kairos 학습 포인트 |
|------|-------------|----------|-----------------|----------------|
| **Notion** | Personal workspace (Plus) + Team 내 Private page | Team workspace | drag-drop 수동 | "Personal Plus → Team" 패턴 차용 |
| **Slack** | DM + 본인 채널 + drafts | Public/Private 채널 | "send to channel" 명시적 | drafts → published 명시 액션 |
| **Figma** | Drafts | Team Files | "Move to project" | drafts UX 단순함 |
| **GitHub** | Personal repos | Org repos | Transfer ownership | git mental model 비유 (사용자 의견) |
| **Linear** | Personal inbox / drafts | Team issues | "Convert to issue" | inbox→issue triage |
| **Confluence** | Personal space | Team spaces | "Move page" | space 메타포 |
| **Apple Notes** | 개인 노트 | Shared notes | "Share with..." | invite-based promotion |
| **Mem** | 개인만 | 없음 | N/A | 팀 영역 부재 — Kairos 우위 |
| **Granola** | 개인 회의만 | 없음 | N/A | 팀 영역 부재 — Kairos 우위 |
| **Glean** | 없음 | 전사 검색만 | N/A | 개인 영역 부재 — Kairos 우위 |

**Kairos v2.0의 unique position**: 개인↔팀 양축 동시 보유 + **promotion 추천 AI** (M5 moat). 위 9개 도구 누구도 양축에 AI 추천 미보유.

---

## 부록 B — 인프라 마이그레이션 트리거 (Qdrant 등)

현재 RAG 인프라는 **pgvector** (Postgres 내장). 다음 트리거 1개라도 충족 시 **Qdrant 전환** 검토.

| # | 트리거 조건 | 측정 방법 | 현재 |
|---|-----------|---------|------|
| 1 | 활성 사용자 1,000+ | DAU 집계 | ❌ 수십 명 [추정] |
| 2 | 벡터 수 5M+ | `SELECT count(*) FROM embedding_chunks` | ❌ 1M 미만 [추정] |
| 3 | RAG p95 응답 시간 >500ms | OpenTelemetry / Sentry 메트릭 | ❌ 측정 권장 (Sprint 15 sub-task) |
| 4 | 동시 payload filter 4+ (ws × proj × visibility × source × time × ...) | RAG query 패턴 audit | ❌ |
| 5 | 마케팅 GA 트랙 진입 (Sprint 17+) | 마케팅 sprint 진입 시 | ❌ 아직 |

### 전환 결정 근거 lock-in (v3.0)

- **현 시점 미전환** — Repository 추상화 완료 (`EmbeddingRepository` 5 메서드), 전환 비용 1-2주로 유지. 메모리 `project_qdrant_deferred.md` (2026-04~) 그대로 유효.
- **Sprint 15 sub-task로 모니터링 메트릭 추가** — RAG p50/p95 + 벡터 수 카운터. 트리거 #3 자동 감지.
- **마케팅 GA 시점 전환 권장** — Qdrant Cloud + HNSW + scalar quantization → "scale-ready" 신호로 enterprise 세일즈에 활용.

---

## 부록 C — 헌법 / ADR 갱신 예정 (v3.0)

본 PRD 갱신에 따라 추가/갱신 예정 ADR:

| # | 제목 | 시점 | 트리거 |
|---|------|------|------|
| 신규 | ADR-016 Personal↔Team IA + Promotion flow | Sprint 15 킥오프 시 | v1.5 ship 직전 |
| 신규 | ADR-017 Cross-workspace RAG 권한 모델 (R-13 헌법 신설) | Sprint 18 킥오프 시 | v1.8 ship 직전 |
| 신규 | ADR-018 Promotion 추천 AI (M5 moat 핵심) | Sprint 22+ 킥오프 시 | v2.0 ship 직전 |
| 신규 | ADR-019 Qdrant 마이그레이션 결정 | 트리거 1+ 충족 시 | 부록 B 트리거 |
| 갱신 | ADR-010 Future-Fit Thesis | v3.0 PRD 갱신 직후 | M5 moat 추가 반영 |
| 갱신 | ADR-011 Persona 정의 | F4 외부 인터뷰 결과 후 | Sprint 7+ |
