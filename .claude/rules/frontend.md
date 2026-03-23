# ⚡ Frontend Rules (Next.js 14 + TypeScript + Kairos 전용)

Kairos 프론트엔드 개발의 전역 설정이다.
**이 섹션의 모든 규칙은 프론트엔드 코드 작성에 최우선 순위로 적용된다.**

---

## 1. Tech Stack (확정)

| 항목            | 기술                                            |
| --------------- | ----------------------------------------------- |
| Framework       | Next.js 14 (App Router)                         |
| Language        | TypeScript Strict 모드 (`any` 사용 엄격히 금지) |
| Styling         | Tailwind CSS + shadcn/ui                        |
| Package Manager | `pnpm` (npm/yarn 사용 금지)                     |
| Server State    | React Query (`@tanstack/react-query`)           |
| Client State    | Zustand                                         |
| Form            | `react-hook-form` + `zod`                       |
| Auth            | Clerk (`@clerk/nextjs`)                         |
| 에디터          | Tiptap                                          |
| 파일 업로드     | `react-dropzone`                                |
| 아이콘          | `lucide-react`                                  |
| Toast           | `sonner`                                        |
| 배포            | Vercel                                          |

---

## 2. 🚫 핵심 제약 사항 (Strict Rules)

### TypeScript

- `any` 사용 엄격히 금지. 부득이한 경우 `unknown` 사용 후 Type Guard 적용
- 모든 API 응답 타입은 `types/` 또는 `features/[domain]/types.ts`에 명시적으로 정의

### 컴포넌트 책임 분리 (Thin Component)

- 페이지/UI 컴포넌트 내부에 비즈니스 로직 직접 작성 금지
- 컴포넌트는 오직 **데이터 렌더링** 과 **이벤트 바인딩** 만 담당
- 비즈니스 로직은 반드시 `features/[domain]/hooks.ts` 커스텀 훅으로 분리

### 클라이언트 바운더리 최소화

- 기본적으로 서버 컴포넌트(RSC) 지향
- 브라우저 API나 상태 관리가 필수적인 말단(Leaf) 노드에만 `"use client"` 선언
- `"use client"` 를 상위 레이아웃에 선언하지 않는다

### shadcn/ui 사용 규칙

- 컴포넌트 추가: `pnpm dlx shadcn@latest add [component]`
- 원본 수정 금지 → 래핑 컴포넌트 생성
- `components/ui/` 내 파일 직접 수정 금지

### Clerk 사용 규칙

- 인증 보호 라우트: `middleware.ts` 에서 `clerkMiddleware()` 로 처리
- 서버 컴포넌트: `auth()` 또는 `currentUser()` 사용
- 클라이언트 컴포넌트: `useAuth()`, `useUser()` 훅 사용
- 직접 JWT 파싱 금지

```typescript
// middleware.ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)", "/sign-up(.*)"]);

export default clerkMiddleware((auth, req) => {
  if (!isPublicRoute(req)) auth().protect();
});
```

---

## 3. 상태 관리 3단계 분리

| 상태 종류           | 도구                      | 예시                                |
| ------------------- | ------------------------- | ----------------------------------- |
| Server State (API)  | React Query               | 회의록 목록, PARA 아이템            |
| Client Global State | Zustand                   | RAG 패널 열림/닫힘, 선택된 프로젝트 |
| Client Local State  | `useState` / `useReducer` | 모달 토글, 입력 폼                  |

### React Query 규칙

- Query Key는 하드코딩 금지 → 도메인별 팩토리 패턴으로 중앙 관리
- API 호출 함수는 `features/[domain]/api.ts` 에 집중

```typescript
// features/meetings/api.ts
export const meetingKeys = {
  all: ["meetings"] as const,
  byProject: (projectId: string) => [...meetingKeys.all, projectId] as const,
  detail: (id: string) => [...meetingKeys.all, "detail", id] as const,
};

export const fetchMeetings = async (projectId: string): Promise<Meeting[]> => {
  const res = await fetch(`/api/projects/${projectId}/meetings`);
  if (!res.ok) throw new Error("회의록 조회 실패");
  return res.json();
};
```

### Zustand 규칙

- 전역 상태는 최소화 — 컴포넌트 트리를 넓게 넘나드는 상태만 관리
- `store/` 디렉토리에 도메인별로 분리

```typescript
// store/ui.ts — RAG 패널, 사이드바 등 UI 전역 상태
import { create } from "zustand";

interface UIStore {
  isRAGPanelOpen: boolean;
  toggleRAGPanel: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  isRAGPanelOpen: false,
  toggleRAGPanel: () =>
    set((state) => ({ isRAGPanelOpen: !state.isRAGPanelOpen })),
}));
```

---

## 4. 에러 핸들링 (선언적 UI)

- 컴포넌트 내부 `if (isLoading)` / `if (error)` 남발 금지
- 로딩/에러 UI는 상위 `Suspense` 와 `ErrorBoundary` 로 위임

```typescript
// app/projects/[id]/meetings/page.tsx
export default function MeetingsPage() {
  return (
    <ErrorBoundary fallback={<MeetingsError />}>
      <Suspense fallback={<MeetingsSkeleton />}>
        <MeetingsList /> {/* 내부에서 useSuspenseQuery 사용 */}
      </Suspense>
    </ErrorBoundary>
  );
}
```

---

## 5. Directory Structure (FSD 기반)

```
frontend/
└── src/
    ├── app/                           # 라우트 진입점 (Thin)
    │   ├── (auth)/                    # Clerk 인증
    │   ├── dashboard/
    │   ├── inbox/                     # Inbox 뷰
    │   ├── weekly-review/
    │   └── workspace/[id]/
    │       ├── projects/[paraId]/
    │       │   ├── meetings/
    │       │   ├── notes/
    │       │   ├── actions/
    │       │   ├── files/
    │       │   └── ask/               # RAG 채팅
    │       ├── areas/[paraId]/
    │       ├── resources/[paraId]/
    │       └── archives/
    │
    ├── components/                    # 도메인 무관 공통 UI
    │   ├── ui/                        # shadcn/ui 원본 (수정 금지)
    │   └── layout/                    # Sidebar, Header, PanelLayout
    │
    ├── features/                      # ★ 도메인별 비즈니스 레이어
    │   ├── inbox/
    │   │   ├── components/            # InboxItem, ClassifyPanel
    │   │   ├── api.ts
    │   │   ├── hooks.ts
    │   │   ├── schemas.ts             # Zod 스키마
    │   │   └── types.ts
    │   ├── para/
    │   │   ├── components/            # PARANav, PARABadge, LinkSelector
    │   │   ├── api.ts
    │   │   ├── hooks.ts
    │   │   └── types.ts
    │   ├── meetings/
    │   │   ├── components/            # MeetingCard, TranscriptViewer, UploadZone
    │   │   ├── api.ts
    │   │   ├── hooks.ts
    │   │   └── types.ts
    │   ├── actions/
    │   │   ├── components/            # KanbanBoard, ActionItem, ListView
    │   │   ├── api.ts
    │   │   ├── hooks.ts
    │   │   └── types.ts
    │   ├── editor/
    │   │   └── components/            # TiptapEditor (래핑 컴포넌트)
    │   └── rag/
    │       ├── components/            # ChatPanel, MessageBubble
    │       ├── api.ts
    │       └── hooks.ts
    │
    ├── hooks/                         # 도메인 무관 공통 훅
    │   ├── useDebounce.ts
    │   └── useMediaRecorder.ts        # 인앱 녹음
    │
    ├── lib/                           # 서드파티 설정, 유틸
    │   ├── api.ts                     # fetch 기본 설정 (baseURL, 인터셉터)
    │   └── utils.ts                   # cn() 등
    │
    ├── store/                         # Zustand 전역 상태
    │   └── ui.ts                      # RAG 패널, 사이드바 등
    │
    └── types/                         # 전역 공유 타입
        └── index.ts
```

---

## 6. Kairos 전용 컴포넌트 규칙

### 3-Panel 레이아웃

```typescript
// components/layout/PanelLayout.tsx
// 좌측 사이드바 + 메인 콘텐츠 + 우측 RAG 패널 구조
// RAG 패널은 useUIStore의 isRAGPanelOpen 상태로 토글
```

### 파일 업로드 (react-dropzone)

- `features/meetings/components/UploadZone.tsx` 에만 구현
- 허용 파일: `audio/*`, `video/*` (MP3, MP4, WebM)
- 업로드 진행률: React Query mutation + `onUploadProgress` 콜백

### 인앱 녹음 (MediaRecorder)

- `hooks/useMediaRecorder.ts` 커스텀 훅으로 분리
- 브라우저 호환성 체크 포함
- 녹음 완료 시 Blob → File 변환 후 업로드 파이프라인으로 전달

### Tiptap 에디터

- `features/editor/components/TiptapEditor.tsx` 래핑 컴포넌트로만 사용
- 확장: StarterKit + Placeholder + CharacterCount
- 저장: debounce 500ms 후 자동 저장

### Toast 알림

- `sonner` 사용, `Toaster` 는 `app/layout.tsx` 에 한 번만 선언
- 에러: `toast.error()`, 성공: `toast.success()`, 로딩: `toast.loading()`

---

## 7. Naming Convention (네이밍 규칙)

- Boolean 변수: `is`, `has`, `should` 로 시작 (예: `isLoading`, `hasError`)
- 이벤트 핸들러: `handle` 로 시작 (예: `handleSubmit`)
- Props로 전달하는 이벤트: `on` 으로 시작 (예: `onSubmit={handleSubmit}`)
- 컴포넌트 파일: PascalCase (예: `MeetingCard.tsx`)
- 훅 파일: camelCase `use` 접두사 (예: `useMeetings.ts`)
- 상수: UPPER_SNAKE_CASE
