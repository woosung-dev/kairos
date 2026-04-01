# ADR-004: PARA → 팀 세컨드 브레인 방향 전환

> **날짜:** 2026-04-01
> **상태:** 확정
> **결정자:** woo sung

---

## 배경

Kairos는 원래 "회의 녹음 → AI 요약 → PARA 분류 → RAG 검색" 도구로 기획되었다.
개발 진행 중 핵심 가치를 재정의하면서 방향을 전환한다.

### 기존 방향의 문제

1. **회의 녹음이 주인공이었다** — 실제로 회의는 콘텐츠 입력 수단 중 하나일 뿐
2. **PARA 4분류가 팀에 맞지 않았다** — PARA는 개인 생산성 도구. "이게 Area야 Resource야?" 팀원 5명이 5개 다른 답을 함
3. **RAG가 부차적이었다** — 사이드 패널로 밀려 있었지만 실제 핵심 가치는 RAG

---

## 결정

### 핵심 리프레이밍

```
기존: 회의 녹음 도구 + PARA 분류 + RAG 검색 (부가)
변경: 팀의 세컨드 브레인. AI가 CODE 사이클을 자동화한다.
```

### Tiago Forte의 세컨드 브레인 → 팀 확장

세컨드 브레인(Building a Second Brain)은 개인 지식 관리 방법론이다.
핵심 프레임워크는 **CODE**:

- **Capture** — 외부 정보를 수집
- **Organize** — 구조화 (PARA는 이 단계의 한 방법)
- **Distill** — 핵심만 추출 (Progressive Summarization)
- **Express** — 지식을 활용해 산출물 생성

Kairos는 이 CODE를 **팀 단위로, AI가 자동화**하여 적용한다.

```
Capture  → 회의 녹음, 노트, 자료 업로드 (마찰 최소화)
Organize → 프로젝트에 자동 연결 + AI 태그 (PARA 4분류 제거)
Distill  → AI가 자동 핵심 추출 (Kairos의 차별점)
  ├── L1: 개별 콘텐츠 요약
  ├── L2: 결정사항 + 액션 아이템
  ├── L3: 프로젝트 인사이트 (주간/월간 자동 종합)
  └── L4: 조직 인사이트 (크로스 프로젝트 패턴)
Express  → RAG 검색 + 프로액티브 인사이트 + 보고서
```

### 주요 변경 사항

| 항목 | 기존 | 변경 |
|------|------|------|
| 핵심 가치 | 회의 녹음 → AI 요약 | 팀 지식 복리 축적 + AI 인사이트 |
| 조직 구조 | PARA 4분류 (Project/Area/Resource/Archive) | 프로젝트 + 태그 + 상태(Active/Completed/Archived) |
| 분류 방식 | Inbox → AI 추천 → 사용자 필수 확정 | AI 자동 연결 + 사용자 선택적 조정 |
| 홈 화면 | 대시보드 | RAG 검색 + Cmd+K |
| RAG 위치 | 우측 사이드 패널 (숨김 가능) | 핵심 경험. 홈 + 상시 패널 |
| 지식 범위 | 팀 전용 | 개인 + 팀 (승격 모델) |

---

## 개인 + 팀 지식 베이스 (승격 모델)

```
개인 지식 베이스 (자유롭게, 아무거나)
  │
  │ "이거 팀에도 도움 되겠다" → 승격 (사용자 판단 + AI 제안)
  │
  ▼
팀 지식 베이스 (정제된 지식만)
```

- 개인: Capture + Organize (마찰 제로)
- 승격: Distill (사람이 "가치 있다"고 판단 or AI가 제안)
- 팀: Express + Compound (정제된 지식만 축적)
- AI가 승격을 제안: "이 회의에서 CMS 보안 결정사항이 있습니다. 팀에 공유할까요?"

---

## PARA 제거 → 프로젝트 + 태그

### 이유

1. PARA는 개인용. 팀에서 "Area vs Resource" 구분이 혼란
2. "프로젝트"는 모든 팀이 이미 사용하는 자연스러운 단위
3. 태그로 자유 분류 가능 (AI 자동 태그 + 수동)
4. Archive = 프로젝트 상태 "Archived" (별도 카테고리 불필요)

### 새 구조

```
프로젝트
├── 상태: Active / Completed / Archived
├── 공개: Public (기본) / Draft / Private
├── 콘텐츠: 회의, 노트, 자료 (통합)
└── 태그: #보안 #인프라 #디자인 (AI 자동 + 수동)
```

---

## 벤치마킹 기반 채택 요소

| 출처 | 채택 요소 | 적용 시점 |
|------|----------|----------|
| Slite | 지식 신선도 시스템 (소스 경과 시간 표시) | Sprint 3 |
| Slite | 프로젝트 단위 Team/Private 권한 | Sprint 1 |
| Mem.ai | 입력 마찰 제거 (AI 자동 확정, 수동은 선택) | Sprint 2 |
| Mem.ai | PARA 제거 → 프로젝트 + 태그 | 설계 변경 |
| Guru | RAG 답변 신뢰도 + 소스 신선도 표시 | Sprint 3 |
| Spotify | 기본 공개 + Draft 상태 | Sprint 1 |
| 시간 기반 | Archive 시 자동 공개 + 인사이트 추출 | Sprint 3 |
| NotebookLM | RAG UX ("소스 던지고 질문") | 핵심 유지 |
| Linear | UI 밀도 + 투명 모델 | UI 유지 |

---

## UI/UX 변경

### 채택한 제안

1. **RAG를 홈으로** — 앱 열면 바로 질문 가능. Cmd+K로 어디서든 접근.
2. **AI 프로액티브 인사이트** — AI가 먼저 알려줌 ("일정 지연 3주 연속")
3. **Cmd+K 커맨드 팔레트** — 검색, RAG, 네비게이션, 생성 통합 입구
4. **RAG 패널 상시 노출** — 사이드 패널이 아닌 핵심 인터페이스

### 화면 구성 변경

```
기존: 대시보드, 회의 업로드, 회의 상세, Inbox, 칸반
변경: 대시보드(워크스페이스 현황), 프로젝트 상세, 지식 검색(RAG 전용), Inbox, 콘텐츠 추가
```

회의는 "콘텐츠 추가"의 옵션 중 하나로 격하. 프로젝트 상세가 핵심 화면.

---

## 미결정 사항 (추후 논의 필요)

1. **개인↔팀 경계 상세** — 승격 시 복사 vs 링크, 퇴사 시 처리
2. **RAG 검색 범위 UX** — 기본 범위, 전환 방식
3. **회의의 소속** — 팀 자동 vs 개인 자동 vs 선택
4. **CEO/관리자 접근 모델** — 레이어드 공개(아이디어 D) 검토 시기
5. **지식 생명주기** — 오래된 지식 처리, 버전 관리

---

## 영향 범위

### 문서 수정 필요

- `docs/requirements/prd.md` — 핵심 가치, 파이프라인, Phase 로드맵
- `docs/requirements/para-methodology.md` → `second-brain.md` 대체
- `docs/architecture/erd.md` — ParaItem → Project + Tag 구조
- `docs/architecture/ai-pipeline.md` — PARA 분류 → 프로젝트 연결 + 태그
- `docs/architecture/cross-domain-pipeline.md` — PARA 서비스 참조
- `docs/architecture/rag-pipeline.md` — PARA 범위 → 프로젝트 범위
- `docs/api/endpoints.md` — /para-items → /projects 엔드포인트
- `.claude/CLAUDE.md` — 프로젝트 컨텍스트 전체

### ERD 변경 (Sprint 1 착수 전 확정 필요)

```
제거: ParaItem, MeetingParaLink, InboxItem.aiSuggestedParaType
추가: Project (+ status, visibility, tags), ProjectMember, Tag, ContentTag
변경: InboxItem → aiSuggestedProjectId, 각 엔티티 paraItemId → projectId
```

### 코드 변경

```
프론트엔드 features/para/ → features/projects/
프론트엔드 features/inbox/ — 분류 워크플로우 수정
백엔드 para/ → projects/ 도메인 모듈
```
