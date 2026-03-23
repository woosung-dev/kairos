---
paths: ["frontend/**/*"]
---

# Frontend Rules (Next.js 16 + TypeScript + Kairos)

> ⚠️ **This is NOT the Next.js you know.**
> 코드 작성 전 `node_modules/next/dist/docs/` 참조 필수.

---

## 1. Tech Stack

| 항목            | 기술                                  |
| --------------- | ------------------------------------- |
| Framework       | Next.js 16 (App Router)               |
| Language        | TypeScript Strict                     |
| Styling         | Tailwind CSS v4 + shadcn/ui v4        |
| Package Manager | `pnpm`                                |
| Server State    | React Query (`@tanstack/react-query`) |
| Client State    | Zustand                               |
| Form            | `react-hook-form` + `zod v4`          |
| Auth            | Clerk (`@clerk/nextjs`)               |
| 에디터          | Tiptap                                |
| 파일 업로드     | `react-dropzone`                      |
| 아이콘          | `lucide-react`                        |
| Toast           | `sonner`                              |
| 배포            | Vercel                                |

---

## 2. 핵심 제약 사항 (Strict Rules)

### Next.js 16 필수 패턴

- `params`, `searchParams`는 **`Promise<>`** 타입 → `await` 필수
- `middleware.ts` 대신 **`proxy.ts`** 사용
- `node_modules/next/dist/docs/` 참조 필수

```typescript
// ✅ Next.js 16
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <Detail id={id} />;
}
```

### Zod v4

- `import { z } from "zod/v4"` 필수 (v3 경로 `"zod"` 금지)

### shadcn/ui v4

- 내부 의존성: `@base-ui/react` (Radix UI 아님)
- `@radix-ui/*` 직접 import 금지
- 추가: `pnpm dlx shadcn@latest add [component]`
- `components/ui/` 직접 수정 금지 → 래핑 컴포넌트

### Clerk (Next.js 16)

- 인증 보호: **`proxy.ts`** 에서 `clerkMiddleware()` 처리
- 서버 컴포넌트: `auth()` 또는 `currentUser()`
- 클라이언트 컴포넌트: `useAuth()`, `useUser()`
- 직접 JWT 파싱 금지

```typescript
// proxy.ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)", "/sign-up(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});
```

### TypeScript

- **Strict 모드 필수**, `any` 사용 엄격히 금지 (부득이한 경우 `unknown` + Type Guard)
- 모든 API 응답 타입은 명시적으로 정의

### 컴포넌트 (Thin Component)

- 페이지/UI 컴포넌트 내부에 비즈니스 로직 직접 작성 금지
- 비즈니스 로직은 커스텀 훅(`features/[domain]/hooks.ts`)으로 분리
- 서버 컴포넌트(RSC) 지향, `"use client"`는 말단 노드에만

---

## 3. 상태 관리 3단계

| 종류          | 도구        | 예시          |
| ------------- | ----------- | ------------- |
| Server State  | React Query | API 데이터    |
| Client Global | Zustand     | 사이드바 토글 |
| Client Local  | useState    | 모달 상태     |

### React Query

- Query Key 하드코딩 금지 → 도메인별 팩토리 패턴
- API 호출은 `features/[domain]/api.ts`에 집중

### Zustand

- 전역 상태는 최소화 — 컴포넌트 트리를 넓게 넘나드는 상태만 관리
- `store/` 디렉토리에 도메인별 분리

---

## 4. 에러 핸들링

- `if (isLoading)` / `if (error)` 남발 금지
- `Suspense` + `ErrorBoundary`로 위임

---

## 5. Directory Structure (FSD)

```
src/
├── app/                    # 라우트 진입점 (Thin)
├── components/
│   ├── ui/                 # shadcn/ui (수정 금지)
│   └── layout/
├── features/               # 도메인별 비즈니스
│   └── [domain]/
│       ├── components/
│       ├── api.ts
│       ├── hooks.ts
│       ├── schemas.ts
│       └── types.ts
├── hooks/                  # 공통 유틸 훅
├── lib/                    # 유틸, 설정
├── store/                  # Zustand
└── types/                  # 공통 유틸 타입만 (UUID, Timestamped 등)
```

---

## 6. Kairos 전용 컴포넌트

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

- `sonner` 사용, `Toaster`는 `app/layout.tsx`에 한 번만 선언

---

## 7. Kairos 라우트 구조

```
app/
├── (auth)/sign-in, sign-up
├── dashboard/
├── inbox/
└── workspace/[workspaceId]/
    ├── projects/[paraId]/
    │   ├── meetings/[meetingId]/
    │   ├── notes/
    │   ├── actions/
    │   ├── files/
    │   └── ask/                    # RAG 채팅
    ├── areas/[paraId]/
    ├── resources/[paraId]/
    └── archives/
```

---

## 8. 네이밍 규칙

- Boolean: `is`, `has`, `should` 접두사
- 이벤트 핸들러: `handle` 접두사
- Props 이벤트: `on` 접두사
- 컴포넌트 파일: PascalCase
- 훅 파일: camelCase `use` 접두사
- 상수: UPPER_SNAKE_CASE

---

## 9. 도메인별 타입 위치

- 공통 유틸 타입 (`UUID`, `Timestamped`, `PaginatedResponse`): `types/index.ts`
- 도메인 타입: `features/[domain]/types.ts`
  - `features/inbox/types.ts` — InboxItem, InboxSourceType
  - `features/para/types.ts` — ParaItem, ParaCategory
  - `features/meetings/types.ts` — Meeting, MeetingSummary
  - `features/actions/types.ts` — ActionItem, ActionPriority
