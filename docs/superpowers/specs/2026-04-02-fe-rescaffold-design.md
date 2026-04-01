# FE 재스캐폴딩 설계: 세컨드 브레인 방향

> **목적:** PARA 기반 FE를 세컨드 브레인(CODE)/프로젝트 중심 구조로 완전 재구축
> **작성일:** 2026-04-02
> **선행:** ADR-004 (PARA → 세컨드 브레인 전환)

---

## 설계 결정 요약

| 결정 | 선택 | 근거 |
|------|------|------|
| 재스캐폴딩 방식 | 완전 새 프로젝트 | 제로 오염. 100% 깨끗한 출발. |
| 라우트 구조 | RAG 홈 중심 + 랜딩 페이지 | RAG가 핵심 경험. 앱 열면 바로 질문. |
| Mock data | 없음 (빈 껍데기 + empty state) | mock→real 전환 비용 제거. Vertical Slice. |
| 랜딩 페이지 | 최소 히어로 (Sprint 4+에서 고도화) | 제품 얼굴은 있되 Sprint 1 집중. |

---

## 1. 프로젝트 초기화

### 기존 프로젝트 삭제 + 새로 생성

```bash
# 기존 삭제
rm -rf frontend/

# 새 프로젝트
pnpm create next-app@latest frontend --typescript --tailwind --app --src-dir --import-alias "@/*"

# shadcn 초기화
cd frontend && pnpm dlx shadcn@latest init

# 의존성
pnpm add @clerk/nextjs @tanstack/react-query zustand
pnpm add react-hook-form zod
pnpm add -D @types/node
```

### 필요한 shadcn 컴포넌트

```bash
pnpm dlx shadcn@latest add button card badge avatar tooltip dialog
pnpm dlx shadcn@latest add dropdown-menu separator scroll-area tabs sheet input
```

### DESIGN.md 토큰 적용

**globals.css:**
```css
:root {
  /* Dark Mode (기본) */
  --background: #0A0A0B;
  --surface: #141416;
  --surface-hover: #1A1A1E;
  --surface-active: #222226;
  --border: #2A2A2E;
  --border-subtle: #1E1E22;
  --text-primary: #EDEDEF;
  --text-secondary: #8E8E93;
  --text-muted: #5C5C63;
  --accent: #3ECFB4;
  --accent-hover: #35B39C;
  --accent-subtle: rgba(62,207,180,0.1);

  /* Project Status Colors */
  --status-active: #3ECFB4;
  --status-completed: #F0963C;
  --status-archived: #6B6B73;

  /* Semantic */
  --success: #34D399;
  --warning: #FBBF24;
  --error: #F87171;
  --info: #60A5FA;

  /* Typography */
  --font-display: 'Satoshi', sans-serif;
  --font-body: 'Pretendard Variable', sans-serif;
  --font-mono: 'Geist Mono', monospace;

  /* Spacing: 4px base */
  --space-2xs: 2px;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;

  /* Border Radius */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-full: 9999px;
}

[data-theme="light"] {
  --background: #FAFAFA;
  --surface: #FFFFFF;
  --surface-hover: #F5F5F5;
  --surface-active: #EFEFEF;
  --border: #E5E5E5;
  --border-subtle: #F0F0F0;
  --text-primary: #111111;
  --text-secondary: #6B6B73;
  --text-muted: #9E9EA6;
  --accent: #0FA889;
  --accent-hover: #0D9278;
  --accent-subtle: rgba(15,168,137,0.08);
}
```

**폰트 로드 (layout.tsx에서):**
```
Satoshi: Google Fonts
Pretendard: cdn.jsdelivr.net/gh/orioncactus/pretendard
Geist Mono: Google Fonts
```

---

## 2. 라우트 구조

```
src/app/
├── layout.tsx                          # 루트 (ClerkProvider, QueryClientProvider, ThemeProvider)
├── page.tsx                            # 랜딩 페이지 (비로그인)
│                                       #   히어로: "Kairos — 팀의 세컨드 브레인"
│                                       #   한 줄 설명 + CTA "시작하기"
├── (auth)/
│   ├── sign-in/[[...sign-in]]/page.tsx
│   └── sign-up/[[...sign-up]]/page.tsx
├── (app)/                              # 인증 필요 영역
│   ├── layout.tsx                      # 3-Panel (sidebar + children + RAG panel)
│   ├── page.tsx                        # RAG 홈 ("뭐든 물어보세요" + 최근 질문 + 빠른 접근)
│   ├── projects/
│   │   └── [id]/page.tsx               # 프로젝트 상세 (콘텐츠 통합 리스트 + 탭)
│   ├── inbox/page.tsx                  # Inbox (AI 추천 + 프로젝트 연결)
│   ├── new/page.tsx                    # 콘텐츠 추가 (회의/노트/자료 선택)
│   ├── meetings/[id]/page.tsx          # 회의 상세 (요약 + 트랜스크립트)
│   └── search/page.tsx                 # RAG 전체 검색 (중앙 확장, RAG 패널 숨김)
└── not-found.tsx
```

### 레이아웃 구조

```
/ (랜딩)         → 풀스크린, 사이드바 없음
/sign-in, /sign-up → 인증 페이지, 사이드바 없음
/(app)/*         → 3-Panel (사이드바 220px | 중앙 flex-1 | RAG 패널 320px)
/(app)/search    → 2-Panel (사이드바 | 중앙=RAG 전체, 우측 패널 숨김)
```

---

## 3. 컴포넌트 + 타입 구조

### features/

```
src/features/
├── projects/
│   ├── types.ts              # Project, ProjectStatus, ProjectVisibility
│   ├── api.ts                # API 호출 + Query Key Factory (빈 상태, BE 연결 시 채움)
│   ├── hooks.ts              # useProjects, useProject, useCreateProject
│   └── components/
│       ├── project-list.tsx
│       ├── project-card.tsx
│       └── create-project-dialog.tsx
├── inbox/
│   ├── types.ts              # InboxItem, InboxSourceType
│   ├── api.ts
│   ├── hooks.ts
│   └── components/
│       ├── inbox-list.tsx
│       ├── inbox-item-card.tsx     # AI 추천 뱃지 + confidence
│       └── classify-dialog.tsx     # 프로젝트 연결 (N:M)
├── meetings/
│   ├── types.ts              # Meeting, MeetingDetail, TranscriptSegment, MeetingSummary
│   └── components/
│       ├── meeting-summary.tsx
│       └── transcript-viewer.tsx
├── actions/
│   ├── types.ts              # ActionItem, ActionStatus, ActionPriority
│   └── components/
│       ├── action-list.tsx
│       └── action-kanban.tsx
└── rag/
    ├── types.ts              # RagMessage, RagSource, SearchScope
    ├── api.ts                # RAG 질문 API (SSE 스트리밍)
    ├── hooks.ts              # useRagChat, useSearchHistory
    └── components/
        ├── rag-home.tsx          # RAG 홈 풀스크린
        ├── rag-panel.tsx         # 우측 상시 패널
        ├── rag-chat.tsx          # 채팅 UI (질문 + 답변 + 소스 인용 + 신선도)
        ├── rag-input.tsx         # 질문 입력 필드
        └── search-scope.tsx      # 검색 범위 selector
```

### 레이아웃 컴포넌트

```
src/components/
├── ui/                       # shadcn (재설치, 수정 금지)
├── layout/
│   ├── sidebar.tsx           # 프로젝트 네비 (Inbox 뱃지, 프로젝트 리스트, 탐색, +콘텐츠)
│   ├── panel-layout.tsx      # 3-Panel 조립 (사이드바 + children + RAG 패널)
│   ├── header.tsx            # breadcrumb + 워크스페이스 전환 + 사용자 아바타
│   ├── cmd-k.tsx             # Cmd+K 커맨드 팔레트
│   └── theme-toggle.tsx      # 다크/라이트 전환
└── empty-state.tsx           # 공통 빈 상태 ("프로젝트가 없습니다" + CTA)
```

### 공통 타입

```typescript
// src/types/index.ts
export type UUID = string;

export interface Timestamped {
  createdAt: string; // ISO 8601
  updatedAt: string;
}

export interface UserBrief {
  id: UUID;
  displayName: string;
  avatarUrl: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
}
```

### 핵심 도메인 타입

```typescript
// features/projects/types.ts
export type ProjectStatus = "active" | "completed" | "archived";
export type ProjectVisibility = "public" | "draft" | "private";

export interface Project extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  title: string;
  description: string | null;
  status: ProjectStatus;
  visibility: ProjectVisibility;
  tags: string[];
  sortOrder: number;
  createdBy: UserBrief;
  contentCount: number;
  meetingCount: number;
  actionItemCount: number;
}

// features/rag/types.ts
export type SourceFreshness = "recent" | "normal" | "stale";

export interface RagMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: RagSource[];
  createdAt: string;
}

export interface RagSource {
  title: string;
  type: "meeting" | "note" | "attachment";
  date: string;
  speaker?: string;
  freshness: SourceFreshness;
}

export interface SearchScope {
  projectId?: UUID;
  timeRange?: "all" | "1m" | "3m" | "6m";
  sourceType?: "all" | "meeting" | "note" | "attachment";
}

// features/inbox/types.ts
export type InboxSourceType = "meeting" | "note" | "attachment";

export interface InboxItem extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  title: string;
  summary: string | null;
  sourceType: InboxSourceType;
  sourceId: UUID;
  aiSuggestedProjectId: UUID | null;
  aiSuggestedProjectTitle: string | null;
  aiSuggestedTags: string[];
  aiConfidence: number | null;
  isProcessed: boolean;
}

// features/meetings/types.ts
export type MeetingStatus = "uploading" | "transcribing" | "summarizing" | "completed" | "failed";

export interface Meeting extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  title: string;
  recordedAt: string | null;
  durationSec: number | null;
  status: MeetingStatus;
  hasTranscript: boolean;
  hasSummary: boolean;
  actionItemCount: number;
  createdBy: UserBrief;
}

export interface MeetingSummary {
  summary: string;
  keyDecisions: string[];
  topics: string[];
}

export interface TranscriptSegment {
  speaker: string;
  startSec: number;
  endSec: number;
  text: string;
}

export interface MeetingDetail extends Meeting {
  transcript: TranscriptSegment[] | null;
  summary: MeetingSummary | null;
  projects: { id: UUID; title: string }[];
}

// features/actions/types.ts
export type ActionPriority = "high" | "medium" | "low";
export type ActionStatus = "todo" | "in_progress" | "done" | "cancelled";

export interface ActionItem extends Timestamped {
  id: UUID;
  meetingId: UUID | null;
  projectId: UUID | null;
  title: string;
  description: string | null;
  assignee: UserBrief | null;
  dueDate: string | null;
  priority: ActionPriority;
  status: ActionStatus;
}
```

---

## 4. Zustand Store

```typescript
// src/store/ui.ts
interface UIState {
  sidebarOpen: boolean;
  ragPanelOpen: boolean;
  cmdKOpen: boolean;
  toggleSidebar: () => void;
  toggleRagPanel: () => void;
  toggleCmdK: () => void;
}
```

---

## 5. 각 페이지별 내용 (빈 껍데기)

### / (랜딩)
- 히어로: "Kairos — 팀의 세컨드 브레인"
- 부제: "회의, 노트, 자료가 쌓일수록 조직이 똑똑해집니다"
- CTA: "시작하기" → /sign-up
- 다크 배경, DESIGN.md 토큰 적용

### /(app) (RAG 홈)
- 중앙 큰 검색 바: "무엇이든 질문하세요... (Cmd+K)"
- 최근 질문 리스트 (빈 상태: "아직 질문이 없습니다")
- 빠른 접근: 프로젝트 카드 (빈 상태: "첫 프로젝트를 만들어보세요")

### /(app)/projects/[id]
- 프로젝트 제목 + 상태 뱃지 + 공개 범위
- 4 stat 카드 (회의 0, 노트 0, 액션 0, RAG 검색 0)
- 탭: 전체 | 회의 | 노트 | 액션 | 자료
- 콘텐츠 리스트 (빈 상태: "콘텐츠를 추가하세요")

### /(app)/inbox
- 필터: 전체 | 미처리 | 처리완료
- Inbox 카드 리스트 (빈 상태: "처리할 항목이 없습니다")

### /(app)/new
- 3개 카드: 회의 녹음 / 노트 작성 / 자료 업로드
- 선택 시 해당 폼 표시

### /(app)/search
- RAG 전체 화면 (3-Panel의 RAG 패널이 중앙으로 확장)
- 범위 필터 + 채팅 히스토리

---

## 6. proxy.ts (Clerk 미들웨어)

```typescript
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
]);

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});
```

---

## 7. 범위 외 (이번 스펙에서 안 함)

- 백엔드 (Sprint 1에서 별도)
- 실제 API 연결 (Sprint 1에서)
- 풀 랜딩 페이지 (Sprint 4+)
- Cmd+K 실제 기능 구현 (Sprint 1에서 검색 API 연결 시)
- 모바일 반응형 (Sprint 4)
