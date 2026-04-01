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
- **핵심 페르소나:**
  - 매주 3~5회 회의를 주도하는 팀 리더
  - 여러 프로젝트를 동시에 관리하는 PM
  - 과거 의사결정 맥락을 자주 다시 찾아야 하는 구성원

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
- [ ] Inbox 자동 적재 (AI confidence ≥ 0.8 자동 확정)

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

## 8. 현재 컨텍스트

- **방향 전환:** PARA → 팀 세컨드 브레인 (ADR-004, 2026-04-02)
- **현재 Phase:** Phase 0 완료, Stage 3 디자인 진행 중 (DESIGN.md 완성)
- **다음 작업:** 세컨드 브레인 방향 반영 후 Sprint 1 착수
- **백엔드:** 아직 미착수 (API 명세 + 백엔드 셋업 가이드 완성됨, ERD 수정 필요)

---

## 9. MVP 명시적 제외 목록

아래 기능은 MVP 범위에서 **의도적으로 제외**한다. Phase 2 이후 검토.

- NotebookLM 스타일 인포그래픽/슬라이드 자동 생성
- 실시간 라이브 트랜스크립션 (회의 중 실시간 STT)
- 크로스 프로젝트 RAG (조직 전체 검색) — Sprint 3~4에서 검토
- Jira / Slack / 외부 캘린더 연동
- 주간/월간 보고서 자동 생성 — L3 프로젝트 인사이트로 대체 가능
- 모바일 네이티브 앱 (PWA로 대체)
