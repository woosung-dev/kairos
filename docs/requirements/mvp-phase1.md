# MVP Phase 1 기능 명세

> **방향 전환:** ADR-004에 의해 PARA → 팀 세컨드 브레인(CODE)으로 전환됨.
> 상세: `docs/requirements/second-brain.md`, `docs/adr/004-second-brain-pivot.md`

## 개요

단순한 회의 기록 도구가 아닌, **팀의 세컨드 브레인** — 회의/노트/자료가 쌓일수록
조직이 똑똑해지는 복리 지식 플랫폼.
프론트엔드를 mock data로 먼저 완성한 뒤 백엔드를 연결하는 방식으로 진행한다.

---

## Feature 1: 멀티 소스 콘텐츠 인제스트 (Capture)

- 회의: 파일 업로드 (MP3/MP4/WebM 드래그앤드롭) → R2 → Whisper STT
- 회의: 인앱 녹음 (MediaRecorder API) → 업로드
- 노트: Tiptap 블록 에디터
- 자료: PDF, 이미지, 문서 업로드
- STT 결과: 화자 분리 타임스탬프 트랜스크립트

## Feature 2: AI 콘텐츠 처리 파이프라인 (Organize + Distill)

- 트랜스크립트 → Gemini API → 구조화 출력 → Inbox 자동 적재
- AI 추출: 회의 요약 (3~5줄), 액션 아이템, 핵심 결정사항, 프로젝트 연결 + 태그 추천
- AI Distillation L1~L2 자동 수행

## Feature 3: 프로젝트 + Inbox 지식 관리 시스템 (핵심)

### Inbox (ADR-006 §7 기준)
- 모든 생성 콘텐츠의 1차 진입점
- AI가 프로젝트 연결 + 태그 자동 추천
- **2그룹 스마트 일괄 처리:**
  - confidence ≥ 0.9 → AI 자동 확정 (수정/되돌리기 가능)
  - confidence < 0.9 → 사용자 확인 요청
- 임계값은 사용자 조절 가능 (기본 90%)

### 프로젝트 구조 (PARA 대체)

| 속성 | 설명 |
|------|------|
| **상태** | Active / Completed / Archived |
| **공개** | Public (기본) / Draft / Private |
| **태그** | AI 자동 + 수동 (#보안 #인프라 #디자인) |

### N:M 관계형 연결
- 하나의 회의록이 여러 프로젝트에 동시에 연결 가능
- 태그/관계형 DB 기반 (폴더 계층 X)

## Feature 4: 확장 가능한 컨텍스트

- 텍스트 메모 (Tiptap), 이미지, 음성 클립, 참고 링크
- 모든 콘텐츠 → 벡터 임베딩 → RAG 소스

## Feature 5: 액션 아이템 관리

- Kanban 보드 (To Do / In Progress / Done)
- 담당자, 기한, 우선순위 (High / Medium / Low)
- 회의록 ↔ 액션 아이템 양방향 연결

## Feature 6: RAG 기반 지식 검색 (Express)

- 프로젝트 범위 자연어 질문 → 하이브리드 검색 → Gemini 답변
- Archive 과거 데이터 포함 검색
- 소스 신선도 표시 (🟢최근/🟡보통/🔴오래됨)
- UI: RAG가 홈 + 상시 패널 + Cmd+K

## Feature 7: RBAC 권한 관리

| 역할   | 권한                              |
| ------ | --------------------------------- |
| Owner  | 전체 관리, 멤버 초대/삭제         |
| Admin  | 콘텐츠 CRUD, 멤버 초대            |
| Member | 본인 생성 콘텐츠 CRUD             |
| Viewer | 읽기 전용                          |

---

## UI 스펙

**C|D 2-Panel 레이아웃 (ADR-006 §3):**
- 좌측: 사이드바 220px (Inbox / 내 프로젝트+소스 트리 / 탐색)
- 중앙: 메인 콘텐츠 (flex-1)
- RAG: 상단 검색바 상시 + Cmd+K 슬라이드 오버레이 (상시 패널 아님)

**디자인:** DESIGN.md 참조. Industrial/Utilitarian, 다크모드 우선.

---

## 구현 순서 (Step 1~6)

1. Next.js 16 초기화
2. 3-Panel 대시보드 레이아웃
3. Inbox 뷰 + 프로젝트 연결 워크플로우
4. 프로젝트 CRUD + N:M 연결
5. 콘텐츠 추가 (회의/노트/자료)
6. RAG 검색 홈 + Cmd+K
