# Kairos — Product Requirements Document

> *그리스어 καιρός — 흘러가는 시간(Chronos) 속 결정적 순간.*
> *모든 업무 속에는 포착해야 할 카이로스가 있고, 이 플랫폼은 그것을 조직의 자산으로 만든다.*

> **버전:** 2.0
> **최종 수정:** 2026-04-02
> **방향 전환:** ADR-004 PARA → 팀 세컨드 브레인 (`docs/dev-log/004-second-brain-pivot.md`)

---

## 0. 프로젝트 철학

**Kairos(καιρός)**는 그리스어로 단순히 흘러가는 시간(Chronos)과 달리,
**결정적인 순간, 포착해야 할 기회의 시간**을 뜻한다.

업무 속 회의, 아이디어, 자료 조사 — 모든 곳에 놓치면 사라지는 카이로스가 있고,
이 플랫폼은 **팀의 세컨드 브레인**으로서 그것을 포착해 조직의 자산으로 만든다.

### 핵심 프레임워크: CODE (팀 세컨드 브레인)

Tiago Forte의 세컨드 브레인을 **팀 단위로, AI가 자동화**하여 적용한다.

```
Capture  → 회의 녹음, 노트, 자료 업로드 (마찰 최소화)
Organize → 프로젝트에 자동 연결 + AI 태그 (사용자는 선택적 조정)
Distill  → AI가 핵심 추출 (Kairos의 차별점)
  ├── L1: 개별 콘텐츠 요약
  ├── L2: 결정사항 + 액션 아이템
  ├── L3: 프로젝트 인사이트 (주간/월간 자동 종합)
  └── L4: 조직 인사이트 (크로스 프로젝트 패턴)
Express  → RAG 검색 + 프로액티브 인사이트 + Cmd+K
```

**"팀의 지식이 시간이 지날수록 복리로 쌓인다"** — 이것이 Kairos의 핵심 가치.

---

## 1. 문제 정의

### 현재 상황
- 회의록, 노트, 자료가 Notion/Drive 등에 **파편화**되어 쌓이지만, 이후 활용되지 않음
- 프로젝트를 하면서 쌓이는 지식이 **개인의 머릿속에만** 존재 (암묵지)
- 쌓인 데이터는 "검색하면 나오는 파일" 수준이고, **인사이트로 활용되지 않음**
- 프로젝트가 끝나면 그 안의 맥락(결정사항, 교훈)이 **사장**됨
- 새 팀원이 합류하면 기존 맥락 파악에 **몇 주가 소요**됨

### 해결하고자 하는 것
> **"회의든 노트든 자료든, 넣기만 하면 AI가 정리하고, 지식이 쌓이고, 나중에 질문하면 인사이트가 나온다."**

단순한 회의록 저장 도구가 아니라, **팀의 세컨드 브레인 — 데이터가 쌓일수록 조직이 똑똑해지는 복리 지식 플랫폼.**

---

## 2. 타겟 유저

- **주요:** 사내 전체 직원 (부서 간 협업 프로젝트 진행자)
- **카테고리 라벨:**
  - 매주 3~5회 회의를 주도하는 팀 리더
  - 여러 프로젝트를 동시에 관리하는 PM
  - 과거 의사결정 맥락을 자주 다시 찾아야 하는 구성원

### 페르소나 명세 (1차, Sprint 7+ 인터뷰 후 갱신)

상세는 `docs/requirements/personas.md` 참조. 정의 정책은 ADR-011 (`docs/dev-log/011-persona-definition.md`).

| ID | 이름 (가명) | 역할 | 상태 | 1순위 wedge |
|---|---|---|---|---|
| **PERSONA-001** | WS | 1인 풀스택 founder + product owner | `self-confirmed` (도그푸딩 1명, 강도 약함) | W3 (프로젝트 RAG Q&A) |
| **PERSONA-002** | 김PM | 30대 IT PM, 5-8명 팀 리더 | `[가설]` | W1 (회의 요약·액션 추출) |
| **PERSONA-003** | 박PM | 40대 컨설팅/에이전시 PM, 3-5개 프로젝트 동시 | `[가설]` | W3 (프로젝트 RAG Q&A) |

> **Wedge 분화 점검**: W3 (PERSONA-001/003 1순위) + W1 (PERSONA-002 1순위) — 1순위 2개로 분화. 3명 모두 W3가 1-2순위 우선 → Sprint 7+ 외부 demand 시그널(ADR-009 S5/S6) ≥60% 집중 시 wedge 우선화 ADR(ADR-009 F6) 트리거.

> **갱신 정책**: PERSONA-002~003 `[가설]`은 Sprint 7+ 외부 인터뷰 5-10명 결과 ADR-011 §4-b (≥60% 응답자가 7필드 중 ≥3개 불일치) 트리거 시 `deprecated` + 신규 페르소나 대체, 미만이면 `interview-confirmed` 전환.

---

## 2.5. 경쟁 분석 (Status Quo)

상세는 `docs/requirements/competitive-analysis.md` 참조. ADR-009 §2 Q2 보강 + ADR-010 thesis moat 검증 입력.

| # | 서비스 `[전부 확인 필요]` | 1줄 요약 | Kairos wedge 매칭 |
|---|---|---|---|
| C1 | **Otter** | 실시간 회의 STT + AI 요약 + Slack/Zoom 통합 | W1 직접 경쟁 |
| C2 | **Granola** | macOS native 회의 요약 (시스템 오디오) | W1 경쟁 (ADR-010 T3 양쪽 등장, AD-17) |
| C3 | **Reflect** | 노트 + AI 검색 + 백링크 그래프 | W4 경쟁 |
| C4 | **Mem** | AI 자동 분류 노트 + RAG Q&A | W3 + M2 경쟁 |
| C5 | **Tana** | 노트 + 데이터베이스 + 슈퍼태그 + AI Q&A | M3 + W3 경쟁 |

**Kairos 차별점 (ADR-010 thesis moat M1~M4 정렬)**:

- **M1 계층 RAG** (中, 단독 약함) — Tana만 워크스페이스 범위 AI Q&A, 계층 청킹·6-Layer·1536d 임베딩·Semantic Cache 깊이는 Kairos 우위.
- **M2 자동 Inbox** (中) — Mem과 **직접 경쟁** (Mem도 AI 자동 분류). 차별 anchor = `workspace.inbox_threshold` 0.9 (I-10) + 사용자 행동 시그널 S4 80%.
- **M3 CODE 통합** (中) — Tana가 가장 근접 위험. Capture+Organize+Distill L2+Express 일관성 우위이나 모방 risk 높음.
- **M4 L4 조직 인사이트** (강, 잠재 — **미구현 timeline risk**) — 5개 경쟁자 누구도 L4 영역 진입 X (단일 사용자·단일 워크스페이스 단기 범위).

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

상세는 ADR-010 (`docs/dev-log/010-future-fit-thesis.md`) 참조.

### Thesis (1줄)

> **"Kairos는 팀의 시간 위에 누적된 조직 인사이트(L4, ADR-007)로 일반 AI 도구와 차별화한다. 단일 사용자 컨텍스트가 아닌 워크스페이스 단위 시간 누적이 moat이며, 자동화된 Inbox + 계층 청킹 RAG가 그 누적을 가능하게 한다."**

### 위협 시나리오 (통합 도구 흡수 risk) `[전부 가설]`

| # | 위협 | 도래 시점 [가설] |
|---|---|---|
| T1 | **ChatGPT** (memory + Projects 확장으로 팀 단위 RAG) | 12~24개월 |
| T2 | **Notion AI** (워크스페이스 안 회의·RAG·인사이트 통합) | 6~12개월 |
| T3 | **Granola** (회의 single-purpose → RAG·외부 연동 확장) | 6~18개월 |

> 도래 시점 추정 근거는 ADR-010 §"위협 시나리오" 표 아래 단락 — 모두 외부 검증 전 `[가설]`. `competitive-analysis.md` 후속 보강(B2: 공식 문서 WebFetch)으로 출처 라벨 해제 예정.

### Moat 4개 + 강도

| Moat | 강도 |
|---|---|
| **M1** 계층 청킹 + 프로젝트 단위 RAG (L1/L2, 1536d, Semantic Cache TTL 7일·0.93) | **中** (단독 약함, 청킹 전략 공개 기술) |
| **M2** 자동화된 Inbox (`workspace.inbox_threshold` 기본 0.9, I-10) | **中** (메커니즘 모방 가능, 차별은 누적 품질) |
| **M3** CODE 가치 흐름 통합 (Capture→Organize→Distill→Express 일관) | **中** (일관성 자체가 약점 — 모방 시 전환비용 낮음) |
| **M4** L4 조직 인사이트 (ADR-007 Phase 4, **미구현**) — 워크스페이스 단위 격리(I-9) + 시간 누적 복리 | **강(잠재)** — 가장 강한 후보이나 timeline risk |

### 약점 인정 + 검증 시그널

- 단기(L4 구현 전, ~Sprint 10 추정)는 M1+M2+M3 中 셋이 차별 anchor. 가치 제안 단기 약함 — ChatGPT memory 누적 격차 risk.
- Thesis 전제 미충족: L4(ADR-007 Phase 4 예정)만 남음. ~~멤버십·visibility(D-1 미구현)~~ **[해소 Sprint 6, 2026-05-11 PR #12]** — Project.visibility 컬럼 + ProjectMember 엔티티 + visibility 권한 분기 모두 구현. ADR-014 옵션 A로 orchestrator 경계까지 정합.
- 검증: Sprint 7+ 외부 인터뷰 응답자의 ≥60%가 "통합 도구로 대체 어려움" 답변 시 thesis 1차 검증 (ADR-010 AD-8, ADR-009 S5와 동일 임계값).

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

---

## 5. Phase 로드맵

> **실행 전략:** Vertical Slice Sprint — Phase 순차 진행 대신 핵심 가치 흐름을 FE+BE 관통.
> 의사결정 근거: `docs/dev-log/002-execution-strategy.md`

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

- 회의 업로드 → Inbox 적재까지 **3분 이내**
- AI 액션 아이템 추출 정확도 **80% 이상** (사용자 체감)
- RAG 질문 → 답변 스트리밍 시작까지 **2초 이내**
- Phase 1~2 완료 후 내부 테스트 사용자 **5명 이상** 온보딩

---

## 7.5. Demand Signal Definition (Sprint 6+ 계획)

상세는 ADR-009 §3 (`docs/dev-log/009-stage1-retrofit.md`) 참조. Q1(Demand) product-first 결정 + Sprint 6+ 후 demand 검증 정합.

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
- **현재 Phase:** Sprint 4 완료 (배포) — **Sprint 1~4 전체 코드 검증 완료 (2026-04-04)**
- **Sprint 1-2:** 회의 업로드 → STT → AI 요약 → 액션 → Inbox → 프로젝트 연결 ✅
- **Sprint 3:** 임베딩(pgvector) + Hybrid Search + SSE RAG + 노트 + Semantic Cache ✅
- **Sprint 4:** GCP Cloud Run + Vercel + Neon prod 배포, GitHub Actions CI ✅
- **프로덕션 URL:** BE `https://kairos-api-467254555861.asia-northeast3.run.app` / FE `https://kairos-zeta-ebon.vercel.app` (둘 다 라이브 확인)
- **ADR-006:** 서비스 전면 UI/UX 개편 — 9/11 구현 완료, 2/11 부분 (임계값 UI, 내보내기)
- **다음 작업:** Sprint 5 (RBAC + 초대 시스템)

### Phase/Sprint/Stage 용어 매핑

| 체계 | 의미 | 출처 |
|------|------|------|
| **Phase 0~4** | 제품 로드맵 단계 (장기) | 이 문서 §5 |
| **Sprint 1~5** | 2주 단위 실행 주기 (Phase 내부) | 이 문서 §5 |
| **8 Stage** | 세션 워크플로우 (설계→구현→마무리) | `guides/development-methodology.md` |

---

## 9. MVP 명시적 제외 목록

아래 기능은 MVP 범위에서 **의도적으로 제외**한다. Phase 2 이후 검토.

- NotebookLM 스타일 인포그래픽/슬라이드 자동 생성
- 실시간 라이브 트랜스크립션 (회의 중 실시간 STT)
- 크로스 프로젝트 RAG (조직 전체 검색) — Sprint 3~4에서 검토
- Jira / Slack / 외부 캘린더 연동
- 주간/월간 보고서 자동 생성 — L3 프로젝트 인사이트로 대체 가능
- 모바일 네이티브 앱 (PWA로 대체)
