# Sprint 2 설계: Inbox + 프로젝트 연결 + 액션 + 반응형

> **작성일:** 2026-04-02
> **범위:** Sprint 2 (Week 3-4)
> **선행:** Sprint 1 E2E 완료 (회의 업로드 → AI 요약)
> **완료 기준:** 업로드 → 요약 → 액션 → Inbox → 프로젝트 연결 전체 흐름 + 반응형 3단계 + m4a 호환

---

## 1. 결정사항 요약

| 결정 | 선택 | 근거 |
|------|------|------|
| PARA 잔재 | 완전 제거 — `status` + `tags`로 단순화 | ADR-004, `second-brain.md` |
| 반응형 전략 | 3단계 점진적 축소 (Desktop/Compact/Mobile) | Linear.app 패턴, 기존 Zustand 토글 활용 |
| m4a/ffmpeg | Sprint 2 포함 | 구현 비용 낮음, 한국 사용자 핵심 유스케이스 |
| 칸반 보드 | 드래그 앤 드롭 (`@dnd-kit`) | 읽기 전용 칸반은 UX 어색, 컬럼 내 순서는 제외 |
| 자동 확정 알림 | 인앱 토스트 + 되돌리기 | Gmail 패턴, Sprint 3에서 별도 섹션 검토 |
| 프로젝트 연결 UX | Inbox + 회의 상세 양쪽 | 같은 API 호출, 동기화 문제 없음 |
| 실행 전략 | Vertical Slice + Slice 4 병렬 | Sprint 1 성공 패턴 유지 |

---

## 2. DB 마이그레이션 + 모델 변경

### ERD 변경사항 (PARA 제거)

**Project:**
```
Project {
    uuid id PK
    uuid workspaceId FK
    string title
    string description
    enum status "active | completed | archived"
    jsonb tags "AI 자동 + 사용자 태그"
    int sortOrder
    uuid createdById FK
    timestamp createdAt
    timestamp updatedAt
}
```
- `category` 필드 삭제 (PARA 잔재)
- Area/Resource 구분 → 태그로 대체

**InboxItem:**
```
InboxItem {
    uuid id PK
    uuid workspaceId FK
    string title
    string summary
    enum sourceType "meeting | note | attachment"
    uuid sourceId
    uuid aiSuggestedProjectId
    string aiSuggestedProjectTitle
    jsonb aiSuggestedTags "AI 추천 태그"
    float aiConfidence
    boolean isProcessed
    timestamp createdAt
    timestamp updatedAt
}
```
- `aiSuggestedParaType/Id/Title` → `aiSuggestedProjectId/Title/Tags`로 변경

**ActionItem:**
```
ActionItem {
    uuid id PK
    uuid meetingId FK
    uuid projectId FK
    string title
    string description
    uuid assigneeId FK
    date dueDate
    enum priority "high | medium | low"
    enum status "todo | in_progress | done | cancelled"
    timestamp createdAt
    timestamp updatedAt
}
```

**MeetingProjectLink:**
```
MeetingProjectLink {
    uuid id PK
    uuid meetingId FK
    uuid projectId FK
    UNIQUE(meetingId, projectId)
}
```

### Alembic 마이그레이션 전략
- 단일 마이그레이션 파일로 4개 테이블(Project, InboxItem, ActionItem, MeetingProjectLink) 동시 생성
- FK 참조: `workspaceId → workspaces.id`, `meetingId → meetings.id`, `createdById → users.id`
- `MeetingProjectLink`에 unique constraint: `(meetingId, projectId)`
- 기존 테이블(User, Workspace, WorkspaceMember, Meeting, MeetingSummary, TranscriptSegment) 수정 없음

---

## 3. 백엔드 API

### API 명세 변경 (PARA 제거)

**Project API — category 관련 전부 제거:**

| Method | Path | 변경사항 |
|--------|------|----------|
| `GET /projects` | Query에서 `category` 삭제, `status` + `tag` 필터만 |
| `POST /projects` | Body에서 `category` 제거 |
| `PATCH /projects/{id}` | Body에서 `category` 제거 |
| `POST /projects/{id}/archive` | `preserveAsResource` 제거, 단순 status 전환 |

**Inbox API — PARA 필드명 정리:**

| Method | Path | 변경사항 |
|--------|------|----------|
| `GET /inbox` | 응답: `aiSuggestedParaType/Id/Title` → `aiSuggestedProjectId/Title/Tags` |
| `POST /inbox/{id}/classify` | Body: `{ "projectIds": [...] }` 유지 |

**ActionItem API — 변경 없음.**

### 백엔드 디렉토리 구조 (신규 도메인)

```
backend/src/
├── projects/
│   ├── models.py          # Project, MeetingProjectLink (SQLModel)
│   ├── schemas.py         # ProjectCreate, ProjectUpdate, ProjectResponse
│   ├── repository.py      # AsyncSession CRUD
│   ├── service.py         # archive 전환 등
│   └── router.py          # 6개 엔드포인트
├── inbox/
│   ├── models.py          # InboxItem
│   ├── schemas.py         # InboxItemResponse, ClassifyRequest
│   ├── repository.py
│   ├── service.py         # classify, dismiss
│   └── router.py          # 3개 엔드포인트
├── actions/
│   ├── models.py          # ActionItem
│   ├── schemas.py         # ActionItemCreate, ActionItemUpdate
│   ├── repository.py
│   ├── service.py
│   └── router.py          # 3개 엔드포인트
```

### Inbox classify 로직

```python
# inbox/service.py
async def classify(inbox_id, project_ids):
    # 1. InboxItem.isProcessed = True
    # 2. sourceType이 "meeting"이면 → MeetingProjectLink 생성 (N:M)
    # 3. sourceType이 "note"이면 → Note.projectId 업데이트
    # 4. 연결된 프로젝트의 contentCount 갱신
```

### Archive 로직

```python
# projects/service.py
async def archive(project_id):
    # project.status = "archived"
    # 관련 ActionItem 중 status가 "todo"인 것 → "cancelled"로 변경
```

---

## 4. AI 파이프라인 확장

### 파이프라인 변경

**Sprint 1:**
```
Upload → STT (Whisper) → 요약 (Gemini) → completed
```

**Sprint 2:**
```
Upload → ffmpeg 변환 → STT (Whisper) → 요약 (Gemini)
       → 액션 아이템 추출 (Gemini)
       → 프로젝트 연결 + 태그 추천 (Gemini)
       → Inbox 적재 (confidence ≥ 0.8이면 자동 확정)
       → completed
```

### Meeting 상태 흐름

```
uploading → transcribing → analyzing → completed | failed
```
- `embedding` 단계 제거 (Sprint 3 RAG에서 추가)
- `analyzing`에서 요약 + 액션 추출 + 프로젝트 연결 한 번에 처리

### Gemini 프롬프트 전략 (2개)

| 프롬프트 | 입력 | 출력 |
|----------|------|------|
| `MEETING_SUMMARY` (기존) | 트랜스크립트 | 요약 + keyDecisions + topics |
| `MEETING_ACTIONS_AND_LINKING` (신규) | 트랜스크립트 + 요약 + 기존 프로젝트 목록 | 액션 아이템[] + suggestedProject + suggestedTags + confidence |

2번째 프롬프트에 기존 프로젝트 목록을 컨텍스트로 넘겨야 AI가 기존 프로젝트와 매칭 가능.

**2개로 분리하는 이유:**
- 요약은 트랜스크립트만으로 가능, 프로젝트 연결은 워크스페이스 컨텍스트 필요
- 관심사 분리 — 품질 독립 튜닝
- 부분 실패 허용 (요약 실패해도 액션 추출 시도)

### 프롬프트 출력 스키마

```json
{
  "actionItems": [
    {
      "title": "...",
      "description": "...",
      "priority": "high|medium|low",
      "dueDate": "YYYY-MM-DD | null"
    }
  ],
  "suggestedProject": {
    "existingProjectId": "uuid | null",
    "newProjectTitle": "... | null",
    "confidence": 0.0~1.0
  },
  "suggestedTags": ["태그1", "태그2"]
}
```

- `existingProjectId`가 있으면 기존 프로젝트에 연결
- `null`이면 `newProjectTitle`로 새 프로젝트 생성 제안
- 둘 다 `null`이면 미분류 (confidence = 0)

### Inbox 자동 확정 로직

```python
# services/meeting_pipeline.py (오케스트레이터)
async def process_meeting(meeting_id):
    # 1. ffmpeg 변환 (필요 시)
    # 2. Whisper STT
    # 3. Gemini 요약 (MEETING_SUMMARY)
    # 4. Gemini 액션+연결 (MEETING_ACTIONS_AND_LINKING)
    # 5. ActionItem DB 저장
    # 6. InboxItem 생성
    # 7. confidence ≥ 0.8 → MeetingProjectLink 자동 생성 + isProcessed=True
    #    confidence < 0.8 → isProcessed=False (사용자 확인 대기)
```

### ffmpeg 변환

```python
# services/transcription.py
async def convert_to_wav(file_path: str) -> str:
    """ffmpeg로 입력 파일을 wav로 변환. 이미 wav/mp3면 스킵."""
    # ffprobe로 포맷 감지 → 필요 시 변환
    # 카카오톡 m4a (3GP 컨테이너) 포함 모든 오디오 형식 처리
```

- Docker 이미지에 `ffmpeg` 패키지 추가
- R2에서 다운로드 → ffmpeg 변환 → Whisper 전달 → 임시 파일 삭제

---

## 5. 프론트엔드

### 도메인별 API 레이어 추가

Sprint 1의 `meetings`, `workspaces` 패턴 동일:

```
features/projects/
├── types.ts          # category 제거, tags 추가
├── api.ts            # 신규: CRUD + archive
├── hooks.ts          # 신규: React Query 훅
├── schemas.ts        # 신규: Zod v4 스키마
└── components/       # mock → hook 교체

features/actions/
├── types.ts          # 기존 유지
├── api.ts            # 신규
├── hooks.ts          # 신규
├── schemas.ts        # 신규
└── components/
    ├── action-list.tsx    # hook 연결
    └── action-kanban.tsx  # dnd-kit 재구현

features/inbox/
├── types.ts          # PARA → project 필드 변경
├── api.ts            # 신규
├── hooks.ts          # 신규
└── components/
    ├── inbox-list.tsx       # hook 연결
    └── inbox-item-card.tsx  # 프로젝트 연결 UI
```

### 칸반 보드 (`@dnd-kit`)

```
action-kanban.tsx
├── 3컬럼: Todo | In Progress | Done
├── KanbanColumn (droppable)
│   └── KanbanCard (draggable)
│       ├── 제목
│       ├── 우선순위 뱃지 (red/orange/blue)
│       ├── 담당자 아바타
│       └── 마감일
├── 드래그 시 낙관적 업데이트
│   ├── onDragEnd → 즉시 UI 반영
│   ├── PATCH /action-items/{id} 호출
│   └── 실패 시 롤백 (queryClient.invalidateQueries)
└── 상단 필터: 우선순위 / 프로젝트 (드롭다운)
```

**라이브러리:** `@dnd-kit/core` + `@dnd-kit/sortable` — React 19 호환, 번들 작음, a11y 기본 지원.

### 프로젝트 연결 워크플로우

**Inbox에서:**
```
InboxItemCard
├── AI 추천: "CMS 고도화" (87%) [확정] [변경] [무시]
├── [확정] → POST /inbox/{id}/classify { projectIds: [추천id] }
├── [변경] → ProjectCombobox 열림
└── [무시] → POST /inbox/{id}/dismiss
```

**회의 상세에서:**
```
MeetingDetail 상단
├── "연결된 프로젝트" 섹션
├── 프로젝트 뱃지 + [+ 추가] 버튼
├── [+ 추가] → ProjectCombobox
└── 뱃지 X → MeetingProjectLink 삭제
```

**공통 컴포넌트:** `ProjectCombobox` — 프로젝트 검색 + "새 프로젝트 만들기" 옵션. Inbox와 회의 상세에서 재사용.

### 토스트 알림 (자동 확정)

```typescript
// features/inbox/hooks.ts
useInboxAutoClassifyToast()
// 회의 처리 완료 시 자동 확정된 InboxItem이 있으면
// toast({ title: "CMS 고도화에 연결됨", action: "되돌리기" })
// [되돌리기] → 연결 해제
```

shadcn/ui `sonner` 토스트 사용.

### 업로드 진행률 UI

```
MeetingUploadPage
├── Dropzone (기존)
├── 업로드 중: Progress bar (R2 업로드 %)
├── 처리 중: 단계 표시 (변환 중 → STT 중 → 분석 중)
└── 완료: "회의 보기" 링크 + 자동 확정 토스트
```

---

## 6. 반응형 웹 — 3단계 점진적 축소

### Breakpoint 정의

| 이름 | 범위 | Tailwind | 레이아웃 |
|------|------|----------|----------|
| Desktop | ≥1280px | `xl:` (기본) | 3-Panel 풀: 사이드바 220px + 메인 + RAG 320px |
| Compact | 768~1279px | `md:` | 사이드바 아이콘 48px + 메인 + RAG 접힘(토글) |
| Mobile | <768px | 기본 | 단일 패널 + 하단 네비게이션 바 |

### 컴포넌트별 반응형 동작

**Sidebar:**

| Desktop | Compact | Mobile |
|---------|---------|--------|
| 220px, 텍스트+아이콘 | 48px, 아이콘만 (hover → 오버레이 확장) | 숨김, 하단 nav 대체 |

**RAG Panel:**

| Desktop | Compact | Mobile |
|---------|---------|--------|
| 320px 상시 노출 | 접힘, 버튼 토글 슬라이드 오버 | 전체화면 `/search` 라우트 |

**하단 네비게이션 바 (Mobile 전용):**
```
[홈] [프로젝트] [업로드+] [Inbox] [검색]
```
- 5개 아이콘 탭, 업로드 버튼 강조
- `md:hidden`으로 768px 이상 숨김

**칸반 반응형:**

| Desktop/Compact | Mobile |
|-----------------|--------|
| 3컬럼 가로 배치 | 가로 스크롤 snap |

### 구현 방식

**CSS 변수:**
```css
:root {
  --sidebar-width: 220px;
  --sidebar-collapsed-width: 48px;
  --rag-panel-width: 320px;
}
```

**Zustand 확장:**
```typescript
// store/ui.ts
{
  sidebarOpen: boolean,       // 기존
  sidebarCollapsed: boolean,  // 신규: compact 아이콘 모드
  ragPanelOpen: boolean,      // 기존
  isMobile: boolean,          // 신규: <768px
}
```

**`useMediaQuery` 훅:** breakpoint 감지 → 자동 전환.

### 문서 반영

- **DESIGN.md:** Layout 섹션에 반응형 breakpoint + 패널 동작 추가
- **frontend.md:** 반응형 규칙 섹션 추가 (Desktop-first, CSS 변수 사용)

---

## 7. 실행 순서 — Vertical Slice + 병렬화

### Slice 구조

```
main:      Slice 1 (Project) → Slice 2 (ActionItem) → Slice 3 (Inbox + AI)
worktree:  Slice 4 (ffmpeg + 반응형) ──────────────────────────→ merge
```

### 의존성

| Slice | 선행 조건 | 병렬 |
|-------|-----------|------|
| 1 (Project) | 없음 | Slice 4와 병렬 |
| 2 (ActionItem) | Slice 1의 DB 마이그레이션 | Slice 4와 병렬 |
| 3 (Inbox + AI) | Slice 1 + 2 완료 | - |
| 4 (인프라) | 없음 | Slice 1~3 전부와 병렬 |

### Slice별 범위

**Slice 1 — Project:**
- DB 마이그레이션 (4테이블 동시)
- BE: Project CRUD + MeetingProjectLink
- FE: `features/projects/` API 레이어 + 기존 컴포넌트 hook 연결
- FE: 사이드바 프로젝트 리스트 실데이터

**Slice 2 — ActionItem:**
- BE: ActionItem CRUD
- FE: `features/actions/` API 레이어
- FE: 칸반 보드 (`@dnd-kit` 드래그 앤 드롭)
- FE: 필터 (우선순위/프로젝트)

**Slice 3 — Inbox + AI 파이프라인:**
- BE: `MEETING_ACTIONS_AND_LINKING` 프롬프트
- BE: AI 파이프라인 확장 (오케스트레이터)
- BE: Inbox CRUD + classify/dismiss
- BE: 자동 확정 로직 (confidence ≥ 0.8)
- FE: `features/inbox/` API 레이어
- FE: `ProjectCombobox` 공통 컴포넌트
- FE: 회의 상세 프로젝트 연결 섹션
- FE: 토스트 알림 + 되돌리기
- FE: 업로드 진행률 UI 개선

**Slice 4 — 인프라 (병렬):**
- BE: ffmpeg 변환 (`transcription.py`)
- BE: Docker 이미지 ffmpeg 추가
- FE: 반응형 3단계 (panel-layout, sidebar, rag-panel, 하단 nav)
- FE: `useMediaQuery` 훅 + Zustand 확장
- 문서: DESIGN.md, frontend.md 반응형 규칙 추가

### Slice별 완료 기준

| Slice | E2E 검증 |
|-------|----------|
| 1 | 프로젝트 CRUD가 사이드바에 실시간 반영 |
| 2 | 칸반에서 드래그로 액션 상태 변경, API 동기화 확인 |
| 3 | 회의 업로드 → AI 요약 + 액션 추출 → Inbox → 프로젝트 연결 전체 체인 |
| 4 | 768px 이하 모바일 레이아웃 + 카카오톡 m4a 업로드 성공 |

---

## 8. API 명세 업데이트 필요 목록

`docs/api/endpoints.md` Sprint 2 섹션에서 수정 필요:

1. `GET /projects` — `category` 쿼리 파라미터 삭제, `tag` 추가
2. `POST /projects` — body에서 `category` 제거
3. `PATCH /projects/{id}` — body에서 `category` 제거
4. `POST /projects/{id}/archive` — `preserveAsResource` 제거
5. `GET /inbox` — 응답 필드 PARA → Project로 변경
6. 회의-프로젝트 연결 API 추가:
   - `POST /workspaces/{wid}/meetings/{mid}/projects` — `{ "projectId": "uuid" }` → MeetingProjectLink 생성
   - `DELETE /workspaces/{wid}/meetings/{mid}/projects/{pid}` — MeetingProjectLink 삭제

---

## 9. Sprint 3 검토 사항 (이번 Sprint 제외)

- Inbox 자동 확정 별도 섹션 UI (C 옵션)
- `embedding` 단계 복원 (RAG용)
- cmux 병렬 워크플로우 도입 검토
