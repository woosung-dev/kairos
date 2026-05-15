# FE 재스캐폴딩 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PARA 기반 FE를 세컨드 브레인/프로젝트 중심 구조로 완전 재구축. 빈 껍데기 + empty state, mock data 없음.

**Architecture:** 기존 frontend/ 삭제 후 Next.js 16 새 프로젝트 생성. DESIGN.md 토큰 적용. RAG 홈 중심 라우팅 + 3-Panel 레이아웃. 도메인별 features/ 구조 (projects, inbox, meetings, actions, rag).

**Tech Stack:** Next.js 16, TypeScript Strict, Tailwind v4, shadcn/ui v4, Clerk, React Query, Zustand, Zod v4

**참조:**
- 설계 스펙: `docs/superpowers/specs/2026-04-02-fe-rescaffold-design.md`
- 디자인 토큰: `DESIGN.md`
- FE 규칙: `.ai/stacks/nextjs/frontend.md`
- 세컨드 브레인: `docs/requirements/second-brain.md`

---

## File Structure

| 작업 | 파일 | 역할 |
|------|------|------|
| 생성 | `frontend/` (전체) | Next.js 16 새 프로젝트 |
| 생성 | `frontend/src/app/globals.css` | DESIGN.md CSS 변수 |
| 생성 | `frontend/src/proxy.ts` | Clerk 미들웨어 |
| 생성 | `frontend/src/types/index.ts` | 공통 타입 |
| 생성 | `frontend/src/store/ui.ts` | Zustand UI 상태 |
| 생성 | `frontend/src/lib/utils.ts` | cn() 유틸 |
| 생성 | `frontend/src/lib/query-client.tsx` | React Query Provider |
| 생성 | `frontend/src/components/layout/*.tsx` | 레이아웃 (5개) |
| 생성 | `frontend/src/components/empty-state.tsx` | 공통 빈 상태 |
| 생성 | `frontend/src/app/page.tsx` | 랜딩 페이지 |
| 생성 | `frontend/src/app/(auth)/**` | Clerk 인증 페이지 |
| 생성 | `frontend/src/app/(app)/**` | 앱 라우트 (6개 페이지) |
| 생성 | `frontend/src/features/*/types.ts` | 도메인 타입 (5개) |
| 생성 | `frontend/src/features/rag/components/*` | RAG 컴포넌트 (5개) |
| 생성 | `frontend/src/features/projects/components/*` | 프로젝트 컴포넌트 |
| 생성 | `frontend/src/features/inbox/components/*` | Inbox 컴포넌트 |
| 생성 | `frontend/src/features/meetings/components/*` | 회의 컴포넌트 |
| 생성 | `frontend/src/features/actions/components/*` | 액션 컴포넌트 |

---

### Task 1: 프로젝트 초기화

**Files:**
- Delete: `frontend/` (전체)
- Create: `frontend/` (새 Next.js 프로젝트)

- [ ] **Step 1: 기존 frontend/ 삭제**

```bash
rm -rf frontend/
```

- [ ] **Step 2: Next.js 16 새 프로젝트 생성**

```bash
pnpm create next-app@latest frontend --typescript --tailwind --app --src-dir --import-alias "@/*"
```

프롬프트에서:
- ESLint: Yes
- Turbopack: Yes (개발 시)

- [ ] **Step 3: shadcn 초기화 + 컴포넌트 설치**

```bash
cd frontend
pnpm dlx shadcn@latest init
pnpm dlx shadcn@latest add button card badge avatar tooltip dialog dropdown-menu separator scroll-area tabs sheet input
```

shadcn init 프롬프트:
- Style: Default
- Base color: Neutral
- CSS variables: Yes

- [ ] **Step 4: 의존성 설치**

```bash
pnpm add @clerk/nextjs @tanstack/react-query zustand react-hook-form zod
```

- [ ] **Step 5: 빌드 확인**

```bash
pnpm build
```

Expected: 빌드 성공

- [ ] **Step 6: 커밋**

```bash
cd .. && git add frontend/ && git commit -m "feat: Next.js 16 새 프로젝트 초기화 (shadcn + 의존성)"
```

---

### Task 2: DESIGN.md 토큰 적용

**Files:**
- Modify: `frontend/src/app/globals.css`
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: globals.css에 DESIGN.md CSS 변수 적용**

`frontend/src/app/globals.css`를 작성한다. 기존 Tailwind 기본 CSS를 DESIGN.md 토큰으로 교체:

```css
@import "tailwindcss";

:root {
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
  --status-active: #3ECFB4;
  --status-completed: #F0963C;
  --status-archived: #6B6B73;
  --success: #34D399;
  --warning: #FBBF24;
  --error: #F87171;
  --info: #60A5FA;
  --font-display: 'Satoshi', sans-serif;
  --font-body: 'Pretendard Variable', 'Pretendard', sans-serif;
  --font-mono: 'Geist Mono', monospace;
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

body {
  background: var(--background);
  color: var(--text-primary);
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
}
```

- [ ] **Step 2: layout.tsx에 폰트 로드 추가**

`frontend/src/app/layout.tsx`를 작성한다:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kairos — 팀의 세컨드 브레인",
  description: "회의, 노트, 자료가 쌓일수록 조직이 똑똑해집니다",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" data-theme="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Satoshi:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: 브라우저에서 다크 배경 확인**

```bash
cd frontend && pnpm dev
```

http://localhost:3000 접속. 다크 배경(#0A0A0B)이 적용되었는지 확인.

- [ ] **Step 4: 커밋**

```bash
cd .. && git add frontend/src/app/globals.css frontend/src/app/layout.tsx
git commit -m "feat: DESIGN.md 토큰 적용 (CSS 변수 + 폰트 로드)"
```

---

### Task 3: 공통 인프라 (타입, 스토어, 유틸, Clerk)

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/store/ui.ts`
- Create: `frontend/src/lib/query-client.tsx`
- Create: `frontend/src/proxy.ts`

- [ ] **Step 1: 공통 타입**

`frontend/src/types/index.ts`:

```typescript
export type UUID = string;

export interface Timestamped {
  createdAt: string;
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

- [ ] **Step 2: Zustand UI Store**

`frontend/src/store/ui.ts`:

```typescript
import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  ragPanelOpen: boolean;
  cmdKOpen: boolean;
  toggleSidebar: () => void;
  toggleRagPanel: () => void;
  toggleCmdK: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  ragPanelOpen: true,
  cmdKOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleRagPanel: () => set((s) => ({ ragPanelOpen: !s.ragPanelOpen })),
  toggleCmdK: () => set((s) => ({ cmdKOpen: !s.cmdKOpen })),
}));
```

- [ ] **Step 3: React Query Provider**

`frontend/src/lib/query-client.tsx`:

```tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

- [ ] **Step 4: Clerk proxy.ts**

`frontend/src/proxy.ts`:

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

- [ ] **Step 5: layout.tsx에 Providers 추가**

`frontend/src/app/layout.tsx`를 수정하여 ClerkProvider + QueryProvider 래핑:

```tsx
import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { QueryProvider } from "@/lib/query-client";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kairos — 팀의 세컨드 브레인",
  description: "회의, 노트, 자료가 쌓일수록 조직이 똑똑해집니다",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="ko" data-theme="dark">
        <head>
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
          <link
            href="https://fonts.googleapis.com/css2?family=Satoshi:wght@400;500;600;700&display=swap"
            rel="stylesheet"
          />
          <link
            href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500&display=swap"
            rel="stylesheet"
          />
          <link
            href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css"
            rel="stylesheet"
          />
        </head>
        <body>
          <QueryProvider>{children}</QueryProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
```

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/types/ frontend/src/store/ frontend/src/lib/query-client.tsx frontend/src/proxy.ts frontend/src/app/layout.tsx
git commit -m "feat: 공통 인프라 (타입, Zustand, React Query, Clerk)"
```

---

### Task 4: 도메인 타입 파일 생성

**Files:**
- Create: `frontend/src/features/projects/types.ts`
- Create: `frontend/src/features/inbox/types.ts`
- Create: `frontend/src/features/meetings/types.ts`
- Create: `frontend/src/features/actions/types.ts`
- Create: `frontend/src/features/rag/types.ts`

- [ ] **Step 1: 5개 도메인 타입 파일 생성**

스펙의 "핵심 도메인 타입" 섹션을 그대로 각 파일에 작성.

`features/projects/types.ts`: Project, ProjectStatus, ProjectVisibility
`features/inbox/types.ts`: InboxItem, InboxSourceType
`features/meetings/types.ts`: Meeting, MeetingDetail, MeetingSummary, TranscriptSegment, MeetingStatus
`features/actions/types.ts`: ActionItem, ActionPriority, ActionStatus
`features/rag/types.ts`: RagMessage, RagSource, SearchScope, SourceFreshness

모든 타입은 스펙 `2026-04-02-fe-rescaffold-design.md` 섹션 3의 코드를 그대로 사용.

- [ ] **Step 2: 커밋**

```bash
git add frontend/src/features/
git commit -m "feat: 도메인 타입 정의 (projects, inbox, meetings, actions, rag)"
```

---

### Task 5: 레이아웃 컴포넌트

**Files:**
- Create: `frontend/src/components/empty-state.tsx`
- Create: `frontend/src/components/layout/sidebar.tsx`
- Create: `frontend/src/components/layout/rag-panel.tsx`
- Create: `frontend/src/components/layout/panel-layout.tsx`
- Create: `frontend/src/components/layout/header.tsx`
- Create: `frontend/src/components/layout/cmd-k.tsx`
- Create: `frontend/src/components/layout/theme-toggle.tsx`

- [ ] **Step 1: empty-state.tsx**

```tsx
// frontend/src/components/empty-state.tsx
"use client";

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: {
    label: string;
    href: string;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <span className="text-4xl mb-4">{icon}</span>}
      <h3
        className="text-lg font-semibold mb-2"
        style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
      >
        {title}
      </h3>
      {description && (
        <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
          {description}
        </p>
      )}
      {action && (
        <a
          href={action.href}
          className="px-4 py-2 rounded text-sm font-medium"
          style={{
            background: "var(--accent)",
            color: "var(--background)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {action.label}
        </a>
      )}
    </div>
  );
}
```

- [ ] **Step 2: sidebar.tsx**

프로젝트 네비게이션 사이드바 (220px). Inbox 뱃지, 프로젝트 리스트(빈 상태), 탐색, +콘텐츠 버튼.
모든 항목은 빈 상태 — 프로젝트 리스트 영역에 "프로젝트 없음" 표시.
DESIGN.md 토큰 사용 (surface 배경, border-subtle 구분선, accent 색상).

- [ ] **Step 3: rag-panel.tsx**

우측 RAG 상시 패널 (320px). "지식 검색" 헤더 + 검색 범위 selector + 채팅 영역(빈 상태) + 입력 필드.
빈 상태: "프로젝트에 대해 질문하세요..."

- [ ] **Step 4: panel-layout.tsx**

3-Panel 조립: 사이드바(220px) + children(flex-1) + RAG 패널(320px).
Zustand의 sidebarOpen, ragPanelOpen 상태에 따라 패널 토글.

- [ ] **Step 5: header.tsx**

breadcrumb + 사용자 아바타 (Clerk UserButton). 워크스페이스 이름 표시.

- [ ] **Step 6: cmd-k.tsx**

Cmd+K 커맨드 팔레트 (빈 껍데기). Dialog 컴포넌트 사용. 검색 입력 + "검색", "RAG 질문", "프로젝트 이동", "콘텐츠 추가" 그룹.
실제 기능은 Sprint 1에서 구현. 지금은 UI만.

- [ ] **Step 7: theme-toggle.tsx**

다크/라이트 모드 전환 버튼. `document.documentElement.dataset.theme` 토글.

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/
git commit -m "feat: 레이아웃 컴포넌트 (3-Panel, 사이드바, RAG 패널, Cmd+K)"
```

---

### Task 6: 랜딩 + 인증 + 앱 레이아웃

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/(auth)/sign-in/[[...sign-in]]/page.tsx`
- Create: `frontend/src/app/(auth)/sign-up/[[...sign-up]]/page.tsx`
- Create: `frontend/src/app/(app)/layout.tsx`
- Create: `frontend/src/app/(app)/page.tsx`
- Create: `frontend/src/app/not-found.tsx`

- [ ] **Step 1: 랜딩 페이지 (/)**

`frontend/src/app/page.tsx`: 최소 히어로.
- 다크 배경 풀스크린
- "Kairos" 로고 (Satoshi 폰트)
- "팀의 세컨드 브레인" 부제
- "회의, 노트, 자료가 쌓일수록 조직이 똑똑해집니다"
- CTA: "시작하기" → /sign-up, "로그인" → /sign-in
- DESIGN.md 토큰 적용 (accent 색상 CTA)

- [ ] **Step 2: 인증 페이지**

```tsx
// frontend/src/app/(auth)/sign-in/[[...sign-in]]/page.tsx
import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="flex items-center justify-center min-h-screen" style={{ background: "var(--background)" }}>
      <SignIn />
    </div>
  );
}
```

sign-up도 동일 구조 (SignUp 컴포넌트).

- [ ] **Step 3: (app) 레이아웃**

`frontend/src/app/(app)/layout.tsx`: PanelLayout로 래핑.

```tsx
import { PanelLayout } from "@/components/layout/panel-layout";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <PanelLayout>{children}</PanelLayout>;
}
```

- [ ] **Step 4: RAG 홈 (/(app))**

`frontend/src/app/(app)/page.tsx`:
- 중앙 큰 검색 바 "무엇이든 질문하세요... (Cmd+K)"
- 최근 질문 (빈 상태: EmptyState "아직 질문이 없습니다")
- 빠른 접근: 프로젝트 카드 (빈 상태: EmptyState "첫 프로젝트를 만들어보세요")

- [ ] **Step 5: not-found.tsx**

```tsx
export default function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-screen" style={{ background: "var(--background)" }}>
      <div className="text-center">
        <h1 className="text-6xl font-bold mb-4" style={{ fontFamily: "var(--font-display)", color: "var(--text-muted)" }}>
          404
        </h1>
        <p style={{ color: "var(--text-secondary)" }}>페이지를 찾을 수 없습니다</p>
        <a href="/" className="mt-4 inline-block" style={{ color: "var(--accent)" }}>홈으로 돌아가기</a>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/app/
git commit -m "feat: 랜딩 + 인증 + 앱 레이아웃 + RAG 홈"
```

---

### Task 7: 프로젝트 상세 페이지

**Files:**
- Create: `frontend/src/features/projects/components/project-card.tsx`
- Create: `frontend/src/features/projects/components/project-list.tsx`
- Create: `frontend/src/app/(app)/projects/[id]/page.tsx`

- [ ] **Step 1: project-card.tsx**

프로젝트 카드: 제목, 상태 뱃지(Active/Completed/Archived), 공개 범위 뱃지, stat (회의/노트/액션 카운트).
빈 데이터 기반이므로 타입만 import하고 구조만 잡는다.

- [ ] **Step 2: project-list.tsx**

프로젝트 목록 (사이드바에서 사용). 프로젝트 배열을 받아 렌더링. 빈 배열이면 EmptyState.

- [ ] **Step 3: projects/[id]/page.tsx**

프로젝트 상세:
- 제목 + 상태 뱃지 + 공개 범위
- 4 stat 카드 (회의 0, 노트 0, 액션 0, RAG 검색 0)
- 탭: 전체 | 회의 | 노트 | 액션 | 자료
- 콘텐츠 리스트 (EmptyState "콘텐츠를 추가하세요")

```tsx
export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  // BE 연결 전이므로 빈 상태로 렌더링
  return <ProjectDetail projectId={id} />;
}
```

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/features/projects/ frontend/src/app/\(app\)/projects/
git commit -m "feat: 프로젝트 상세 페이지 + 컴포넌트 (빈 상태)"
```

---

### Task 8: Inbox 페이지

**Files:**
- Create: `frontend/src/features/inbox/components/inbox-item-card.tsx`
- Create: `frontend/src/features/inbox/components/inbox-list.tsx`
- Create: `frontend/src/app/(app)/inbox/page.tsx`

- [ ] **Step 1: inbox-item-card.tsx**

Inbox 카드: 제목, 요약 1줄, 소스 타입 뱃지, AI 추천 영역 (프로젝트 + confidence), 분류 확정/무시 버튼.

- [ ] **Step 2: inbox-list.tsx**

필터 탭 (전체/미처리/처리완료) + 카드 리스트. 빈 배열이면 EmptyState "처리할 항목이 없습니다".

- [ ] **Step 3: inbox/page.tsx**

```tsx
import { InboxList } from "@/features/inbox/components/inbox-list";

export default function InboxPage() {
  return <InboxList />;
}
```

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/features/inbox/ frontend/src/app/\(app\)/inbox/
git commit -m "feat: Inbox 페이지 + 컴포넌트 (빈 상태)"
```

---

### Task 9: 콘텐츠 추가 + 회의 상세 + 액션

**Files:**
- Create: `frontend/src/app/(app)/new/page.tsx`
- Create: `frontend/src/features/meetings/components/meeting-summary.tsx`
- Create: `frontend/src/features/meetings/components/transcript-viewer.tsx`
- Create: `frontend/src/app/(app)/meetings/[id]/page.tsx`
- Create: `frontend/src/features/actions/components/action-list.tsx`
- Create: `frontend/src/features/actions/components/action-kanban.tsx`

- [ ] **Step 1: new/page.tsx (콘텐츠 추가)**

3개 카드 선택지: 회의 녹음 / 노트 작성 / 자료 업로드.
각 카드 hover 시 accent border. 선택 시 해당 폼 표시 (빈 폼 껍데기).

- [ ] **Step 2: 회의 상세 컴포넌트**

`meeting-summary.tsx`: AI 요약 카드 + 결정사항 + 토픽 태그. 빈 상태.
`transcript-viewer.tsx`: 화자별 타임스탬프 트랜스크립트. 빈 상태.

- [ ] **Step 3: meetings/[id]/page.tsx**

회의 상세: 메타데이터 + 탭(요약/트랜스크립트) + EmptyState.

```tsx
export default async function MeetingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <MeetingDetail meetingId={id} />;
}
```

- [ ] **Step 4: 액션 컴포넌트**

`action-list.tsx`: 액션 리스트 (제목, 담당자, 마감일, 우선순위, 상태). EmptyState.
`action-kanban.tsx`: 4-column 칸반 (todo/in_progress/done/cancelled). EmptyState.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/app/\(app\)/new/ frontend/src/app/\(app\)/meetings/ frontend/src/features/meetings/ frontend/src/features/actions/
git commit -m "feat: 콘텐츠 추가 + 회의 상세 + 액션 컴포넌트 (빈 상태)"
```

---

### Task 10: 검색 페이지 + RAG 컴포넌트 + 최종 검증

**Files:**
- Create: `frontend/src/features/rag/components/rag-home.tsx`
- Create: `frontend/src/features/rag/components/rag-chat.tsx`
- Create: `frontend/src/features/rag/components/rag-input.tsx`
- Create: `frontend/src/features/rag/components/search-scope.tsx`
- Create: `frontend/src/app/(app)/search/page.tsx`

- [ ] **Step 1: RAG 컴포넌트**

`rag-home.tsx`: RAG 홈 풀스크린용 (큰 검색 바 + 최근 질문 + 빠른 접근).
`rag-chat.tsx`: 채팅 UI (질문 + 답변 + 소스 인용 + 신선도 뱃지). 빈 상태.
`rag-input.tsx`: 질문 입력 필드 + 전송 버튼.
`search-scope.tsx`: 검색 범위 selector (프로젝트/시간/소스 타입 드롭다운).

- [ ] **Step 2: search/page.tsx**

RAG 전체 화면. 3-Panel의 RAG 패널이 중앙으로 확장. 사이드바는 유지, 우측 패널 숨김.

```tsx
import { RagChat } from "@/features/rag/components/rag-chat";
import { RagInput } from "@/features/rag/components/rag-input";
import { SearchScope } from "@/features/rag/components/search-scope";

export default function SearchPage() {
  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        <h1 className="text-lg font-semibold" style={{ fontFamily: "var(--font-display)" }}>
          지식 검색
        </h1>
        <SearchScope />
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <RagChat messages={[]} />
      </div>
      <div className="p-4 border-t" style={{ borderColor: "var(--border-subtle)" }}>
        <RagInput onSubmit={() => {}} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 전체 빌드 검증**

```bash
cd frontend && pnpm build
```

Expected: 빌드 성공, 에러 없음

- [ ] **Step 4: 전체 페이지 네비게이션 검증**

```bash
pnpm dev
```

브라우저에서 모든 라우트 접근 확인:
- `/` — 랜딩 페이지
- `/(app)` — RAG 홈 (Clerk 인증 필요할 수 있음)
- `/(app)/projects/test-id` — 프로젝트 상세
- `/(app)/inbox` — Inbox
- `/(app)/new` — 콘텐츠 추가
- `/(app)/search` — 검색

- [ ] **Step 5: 커밋**

```bash
cd .. && git add frontend/src/features/rag/ frontend/src/app/\(app\)/search/
git commit -m "feat: RAG 컴포넌트 + 검색 페이지 + FE 재스캐폴딩 완료"
```
