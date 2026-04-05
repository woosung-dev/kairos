# Sprint 6: 온보딩 준비 — 실사용 품질 달성

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 내부 5명 온보딩이 가능한 실사용 품질 달성 — mock 제거, 에러 피드백, 역할 기반 UI 보호

**Architecture:** 기존 코드에 toast/역할 체크를 추가하는 수평적 개선. 새 파일 생성 없이 기존 hooks.ts와 컴포넌트 파일만 수정. Quick Memo만 mock→real API 전환으로 구조 변경.

**Tech Stack:** React Query mutations (sonner toast), Zustand workspace store (hasRole), existing API client

---

## 파일 맵

| 변경 유형 | 파일 | 역할 |
|-----------|------|------|
| Modify | `frontend/src/features/notes/hooks.ts` | toast 추가 (create/update/delete) |
| Modify | `frontend/src/features/actions/hooks.ts` | toast 추가 (create/update) |
| Modify | `frontend/src/features/projects/hooks.ts` | toast 추가 (create/update/delete/archive) |
| Modify | `frontend/src/features/meetings/hooks.ts` | toast 추가 (create) |
| Modify | `frontend/src/features/notes/components/quick-memo.tsx` | mock→real API 전환 |
| Modify | `frontend/src/features/actions/components/action-kanban.tsx` | viewer 드래그 차단 |
| Modify | `frontend/src/features/meetings/components/action-view.tsx` | viewer 체크박스 차단 |
| Modify | `frontend/src/features/projects/components/project-combobox.tsx` | viewer 생성 차단 |
| Modify | `frontend/src/features/projects/components/project-list.tsx` | viewer 생성 링크 숨김 |
| Modify | `frontend/src/features/projects/components/project-detail.tsx` | viewer 추가 링크 숨김 |
| Modify | `frontend/src/features/projects/components/project-dashboard.tsx` | viewer 버튼 숨김 |
| Modify | `frontend/src/features/inbox/components/inbox-item-card.tsx` | viewer 액션 버튼 숨김 |

---

## Task 1: Mutation Toast — Notes hooks

**Files:**
- Modify: `frontend/src/features/notes/hooks.ts`

**패턴 참조:** `frontend/src/features/members/hooks.ts:77-84` (기존 toast 패턴)

- [ ] **Step 1: notes/hooks.ts에 sonner import 추가 + 3개 mutation에 toast 추가**

```typescript
// 파일 상단에 import 추가
import { toast } from "sonner";

// useCreateNote — onSuccess/onError 추가
onSuccess: () => {
  if (wid) queryClient.invalidateQueries({ queryKey: noteKeys.all });
  toast.success("노트가 생성되었습니다");
},
onError: (error: Error) => {
  toast.error(error.message || "노트 생성에 실패했습니다");
},

// useUpdateNote — onError 추가 (onSuccess 기존 유지)
onSuccess: (_data, variables) => {
  if (wid) {
    queryClient.invalidateQueries({
      queryKey: noteKeys.detail(wid, variables.id),
    });
    queryClient.invalidateQueries({ queryKey: noteKeys.all });
  }
},
onError: (error: Error) => {
  toast.error(error.message || "노트 수정에 실패했습니다");
},

// useDeleteNote — onSuccess/onError 추가
onSuccess: () => {
  if (wid) queryClient.invalidateQueries({ queryKey: noteKeys.all });
  toast.success("노트가 삭제되었습니다");
},
onError: (error: Error) => {
  toast.error(error.message || "노트 삭제에 실패했습니다");
},
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend && pnpm tsc --noEmit 2>&1 | head -20`
Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/features/notes/hooks.ts
git commit -m "feat: 노트 mutation toast 추가 (create/update/delete)"
```

---

## Task 2: Mutation Toast — Actions hooks

**Files:**
- Modify: `frontend/src/features/actions/hooks.ts`

- [ ] **Step 1: actions/hooks.ts에 sonner import + 2개 mutation에 toast 추가**

```typescript
// 파일 상단에 import 추가
import { toast } from "sonner";

// useCreateActionItem — onSuccess/onError 추가
onSuccess: () => {
  if (wid) {
    queryClient.invalidateQueries({ queryKey: actionKeys.list(wid) });
  }
  toast.success("액션 아이템이 생성되었습니다");
},
onError: (error: Error) => {
  toast.error(error.message || "액션 아이템 생성에 실패했습니다");
},

// useUpdateActionItem — onSuccess/onError 추가
onSuccess: () => {
  if (wid) {
    queryClient.invalidateQueries({ queryKey: actionKeys.list(wid) });
  }
  toast.success("액션 아이템이 수정되었습니다");
},
onError: (error: Error) => {
  toast.error(error.message || "액션 아이템 수정에 실패했습니다");
},
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend && pnpm tsc --noEmit 2>&1 | head -20`
Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/features/actions/hooks.ts
git commit -m "feat: 액션 아이템 mutation toast 추가 (create/update)"
```

---

## Task 3: Mutation Toast — Projects hooks

**Files:**
- Modify: `frontend/src/features/projects/hooks.ts`

- [ ] **Step 1: projects/hooks.ts에 sonner import + 6개 mutation에 toast 추가**

```typescript
// 파일 상단에 import 추가
import { toast } from "sonner";

// useCreateProject
onSuccess: () => {
  if (wid) {
    queryClient.invalidateQueries({ queryKey: projectKeys.list(wid) });
  }
  toast.success("프로젝트가 생성되었습니다");
},
onError: (error: Error) => {
  toast.error(error.message || "프로젝트 생성에 실패했습니다");
},

// useUpdateProject
onSuccess: () => {
  if (wid) {
    queryClient.invalidateQueries({ queryKey: projectKeys.all });
  }
  toast.success("프로젝트가 수정되었습니다");
},
onError: (error: Error) => {
  toast.error(error.message || "프로젝트 수정에 실패했습니다");
},

// useDeleteProject
onSuccess: () => {
  if (wid) {
    queryClient.invalidateQueries({ queryKey: projectKeys.list(wid) });
  }
  toast.success("프로젝트가 삭제되었습니다");
},
onError: (error: Error) => {
  toast.error(error.message || "프로젝트 삭제에 실패했습니다");
},

// useArchiveProject
onSuccess: () => {
  if (wid) {
    queryClient.invalidateQueries({ queryKey: projectKeys.all });
  }
  toast.success("프로젝트가 아카이브되었습니다");
},
onError: (error: Error) => {
  toast.error(error.message || "프로젝트 아카이브에 실패했습니다");
},

// useAddMeetingProject
onSuccess: (_data, variables) => {
  if (wid) {
    queryClient.invalidateQueries({
      queryKey: meetingKeys.detail(wid, variables.meetingId),
    });
  }
  toast.success("프로젝트가 연결되었습니다");
},
onError: (error: Error) => {
  toast.error(error.message || "프로젝트 연결에 실패했습니다");
},

// useRemoveMeetingProject
onSuccess: (_data, variables) => {
  if (wid) {
    queryClient.invalidateQueries({
      queryKey: meetingKeys.detail(wid, variables.meetingId),
    });
  }
  toast.success("프로젝트 연결이 해제되었습니다");
},
onError: (error: Error) => {
  toast.error(error.message || "프로젝트 연결 해제에 실패했습니다");
},
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend && pnpm tsc --noEmit 2>&1 | head -20`
Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/features/projects/hooks.ts
git commit -m "feat: 프로젝트 mutation toast 추가 (create/update/delete/archive/link)"
```

---

## Task 4: Mutation Toast — Meetings hooks

**Files:**
- Modify: `frontend/src/features/meetings/hooks.ts`

- [ ] **Step 1: meetings/hooks.ts에 sonner import + useCreateMeeting toast 추가**

```typescript
// 파일 상단에 import 추가
import { toast } from "sonner";

// useCreateMeeting
onSuccess: () => {
  if (wid) {
    queryClient.invalidateQueries({ queryKey: meetingKeys.list(wid) });
  }
  toast.success("회의가 업로드되었습니다. 처리 중...");
},
onError: (error: Error) => {
  toast.error(error.message || "회의 업로드에 실패했습니다");
},
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend && pnpm tsc --noEmit 2>&1 | head -20`
Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/features/meetings/hooks.ts
git commit -m "feat: 회의 mutation toast 추가 (create)"
```

---

## Task 5: Quick Memo — Mock → Real API 전환

**Files:**
- Modify: `frontend/src/features/notes/components/quick-memo.tsx`

**의존성:** `useProjects` (projects/hooks.ts), `useCreateNote` + `useNotes` (notes/hooks.ts), `useWorkspaceStore` (workspaces/store.ts)

- [ ] **Step 1: Quick Memo 컴포넌트를 real API로 전환**

mock 데이터(MOCK_PROJECTS, INITIAL_MEMOS, SavedMemo 인터페이스)를 제거하고, 실제 API 훅으로 교체한다.

```tsx
"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { useProjects } from "@/features/projects/hooks";
import { useNotes, useCreateNote } from "@/features/notes/hooks";

export function QuickMemo() {
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const hasRole = useWorkspaceStore((s) => s.hasRole);
  const canWrite = hasRole("member");

  const { data: projects } = useProjects(wid ?? undefined);
  const { data: notesData } = useNotes(wid ?? undefined);
  const createNote = useCreateNote(wid ?? undefined);

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [isComposing, setIsComposing] = useState(false);

  function handleSave() {
    if (!title.trim() && !content.trim()) {
      toast.error("제목 또는 내용을 입력해주세요");
      return;
    }

    createNote.mutate(
      {
        title: title.trim() || "제목 없음",
        content: { type: "doc", content: [{ type: "paragraph", content: [{ type: "text", text: content.trim() }] }] },
        projectId: selectedProjectId || null,
      },
      {
        onSuccess: () => {
          setTitle("");
          setContent("");
          setSelectedProjectId("");
          setIsComposing(false);
        },
      }
    );
  }

  const notes = notesData?.items ?? [];
  const projectList = projects?.items ?? [];

  return (
    <div className="p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1
            className="text-2xl font-bold mb-1"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            빠른 메모
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            아이디어를 빠르게 기록하세요. 마크다운 문법을 지원합니다.
          </p>
        </div>
        {canWrite && !isComposing && (
          <button
            onClick={() => setIsComposing(true)}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            + 새 메모
          </button>
        )}
      </div>

      {/* 메모 입력 폼 */}
      {isComposing && (
        <div
          className="p-4 rounded-lg border mb-6"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <input
            type="text"
            placeholder="메모 제목"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-transparent text-lg font-semibold outline-none mb-3"
            style={{
              color: "var(--text-primary)",
              fontFamily: "var(--font-display)",
            }}
          />

          <textarea
            placeholder="내용을 입력하세요... (마크다운 지원)"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={6}
            className="w-full bg-transparent text-sm outline-none resize-none leading-relaxed"
            style={{
              color: "var(--text-secondary)",
            }}
          />

          <div
            className="flex items-center justify-between mt-4 pt-3 border-t"
            style={{ borderColor: "var(--border-subtle)" }}
          >
            <div className="flex items-center gap-2">
              <label className="text-xs" style={{ color: "var(--text-muted)" }}>
                프로젝트:
              </label>
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="text-xs px-2 py-1.5 rounded border bg-transparent outline-none"
                style={{
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                <option value="">선택 안 함</option>
                {projectList.map((proj) => (
                  <option key={proj.id} value={proj.id}>
                    {proj.title}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setIsComposing(false);
                  setTitle("");
                  setContent("");
                  setSelectedProjectId("");
                }}
                className="px-3 py-1.5 rounded text-xs font-medium transition-colors border"
                style={{
                  borderColor: "var(--border)",
                  color: "var(--text-muted)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                취소
              </button>
              <button
                onClick={handleSave}
                disabled={createNote.isPending}
                className="px-4 py-1.5 rounded text-xs font-medium transition-colors"
                style={{
                  background: createNote.isPending ? "var(--text-muted)" : "var(--accent)",
                  color: "var(--background)",
                  borderRadius: "var(--radius-sm)",
                  cursor: createNote.isPending ? "not-allowed" : "pointer",
                  minHeight: "44px",
                }}
              >
                {createNote.isPending ? "저장 중..." : "저장"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 저장된 메모 목록 — API 데이터 */}
      {notes.length > 0 ? (
        <div className="grid gap-3">
          {notes.map((note) => (
            <div
              key={note.id}
              className="p-4 rounded-lg border transition-colors"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border-subtle)",
                borderRadius: "var(--radius-lg)",
                cursor: "pointer",
              }}
              onMouseOver={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
              onMouseOut={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
            >
              <div className="flex items-start justify-between mb-1">
                <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                  {note.title || "제목 없음"}
                </h3>
                <span className="text-[10px] shrink-0 ml-2" style={{ color: "var(--text-muted)" }}>
                  {new Date(note.createdAt).toLocaleDateString("ko-KR")}
                </span>
              </div>
              {note.plainText && (
                <p className="text-xs line-clamp-2 mb-2" style={{ color: "var(--text-secondary)" }}>
                  {note.plainText}
                </p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-4xl mb-4">📝</span>
          <h3
            className="text-lg font-semibold mb-2"
            style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
          >
            아직 메모가 없습니다
          </h3>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            빠른 메모를 작성하면 AI가 자동으로 프로젝트에 연결합니다
          </p>
        </div>
      )}
    </div>
  );
}
```

> Note 타입에 `plainText` 필드가 없다면 `note.plainText` 대신 사용 가능한 필드를 확인할 것.

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend && pnpm tsc --noEmit 2>&1 | head -20`
Expected: 에러 없음 (타입 불일치 시 Note 타입 확인 후 수정)

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/features/notes/components/quick-memo.tsx
git commit -m "feat: Quick Memo mock 제거 → real API 연동 (useNotes + useCreateNote)"
```

---

## Task 6: Viewer 역할 차단 — Action Kanban + Meeting Action View

**Files:**
- Modify: `frontend/src/features/actions/components/action-kanban.tsx`
- Modify: `frontend/src/features/meetings/components/action-view.tsx`

**패턴:** `useWorkspaceStore`의 `hasRole("member")`로 쓰기 동작 비활성화

- [ ] **Step 1: action-kanban.tsx에 viewer 드래그 차단 추가**

파일 상단에 import 추가:
```typescript
import { useWorkspaceStore } from "@/features/workspaces/store";
```

컴포넌트 내부에 역할 체크 추가:
```typescript
const hasRole = useWorkspaceStore((s) => s.hasRole);
const canWrite = hasRole("member");
```

드래그 핸들러에서 `canWrite` 체크:
- `onDragStart`에서 `if (!canWrite) return;` 가드 추가
- 또는 DnD 컨텍스트의 `disabled` prop 활용 (구현에 따라 다름)

- [ ] **Step 2: action-view.tsx에 viewer 체크박스 비활성화 추가**

파일 상단에 import 추가:
```typescript
import { useWorkspaceStore } from "@/features/workspaces/store";
```

컴포넌트 내부에 역할 체크 추가:
```typescript
const hasRole = useWorkspaceStore((s) => s.hasRole);
const canWrite = hasRole("member");
```

체크박스 input에 `disabled={!canWrite}` 추가:
```tsx
<input
  type="checkbox"
  checked={...}
  onChange={...}
  disabled={!canWrite}
  className={!canWrite ? "opacity-50 cursor-not-allowed" : ""}
/>
```

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend && pnpm tsc --noEmit 2>&1 | head -20`
Expected: 에러 없음

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/features/actions/components/action-kanban.tsx frontend/src/features/meetings/components/action-view.tsx
git commit -m "feat: viewer 역할 차단 — 액션 칸반 드래그 + 회의 액션 체크박스"
```

---

## Task 7: Viewer 역할 차단 — Project 컴포넌트 (4개)

**Files:**
- Modify: `frontend/src/features/projects/components/project-combobox.tsx`
- Modify: `frontend/src/features/projects/components/project-list.tsx`
- Modify: `frontend/src/features/projects/components/project-detail.tsx`
- Modify: `frontend/src/features/projects/components/project-dashboard.tsx`

**공통 패턴:**

```typescript
import { useWorkspaceStore } from "@/features/workspaces/store";
// 컴포넌트 내부:
const hasRole = useWorkspaceStore((s) => s.hasRole);
const canWrite = hasRole("member");
```

- [ ] **Step 1: project-combobox.tsx — 인라인 프로젝트 생성 버튼 숨김**

`handleCreateAndSelect` 호출 버튼을 `canWrite` 조건으로 감싸기:
```tsx
{canWrite && (
  <button onClick={handleCreateAndSelect}>...</button>
)}
```

- [ ] **Step 2: project-list.tsx — "프로젝트 만들기" 링크 숨김**

empty state의 생성 링크를 `canWrite` 조건으로 감싸기:
```tsx
{canWrite && (
  <Link href="...">프로젝트 만들기</Link>
)}
```

- [ ] **Step 3: project-detail.tsx — "콘텐츠 추가" 링크 숨김**

empty state의 추가 링크를 `canWrite` 조건으로 감싸기:
```tsx
{canWrite && (
  <Link href="...">콘텐츠 추가</Link>
)}
```

- [ ] **Step 4: project-dashboard.tsx — 온보딩 뷰 쓰기 버튼 숨김**

"회의 녹음", "노트 작성" 버튼을 `canWrite` 조건으로 감싸기:
```tsx
{canWrite && (
  <>
    <button>🎙️ 회의 녹음</button>
    <button>📝 노트 작성</button>
  </>
)}
```

- [ ] **Step 5: 빌드 확인**

Run: `cd frontend && pnpm tsc --noEmit 2>&1 | head -20`
Expected: 에러 없음

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/features/projects/components/project-combobox.tsx \
  frontend/src/features/projects/components/project-list.tsx \
  frontend/src/features/projects/components/project-detail.tsx \
  frontend/src/features/projects/components/project-dashboard.tsx
git commit -m "feat: viewer 역할 차단 — 프로젝트 생성/추가/온보딩 버튼 숨김"
```

---

## Task 8: Viewer 역할 차단 — Inbox 액션 버튼

**Files:**
- Modify: `frontend/src/features/inbox/components/inbox-item-card.tsx`

- [ ] **Step 1: inbox-item-card.tsx에 역할 체크 추가**

파일 상단에 import:
```typescript
import { useWorkspaceStore } from "@/features/workspaces/store";
```

컴포넌트 내부:
```typescript
const hasRole = useWorkspaceStore((s) => s.hasRole);
const canWrite = hasRole("member");
```

"확정", "다른 프로젝트", "무시", "수정", "되돌리기" 버튼 그룹을 조건부 렌더링:
```tsx
{canWrite && (
  <div className="flex gap-2">
    <button>✅ 확정</button>
    <button>✏️ 다른 프로젝트</button>
    <button>🗑 무시</button>
  </div>
)}
```

viewer에게는 읽기 전용 상태 표시:
```tsx
{!canWrite && (
  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
    읽기 전용
  </span>
)}
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend && pnpm tsc --noEmit 2>&1 | head -20`
Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/features/inbox/components/inbox-item-card.tsx
git commit -m "feat: viewer 역할 차단 — Inbox 확정/수정/무시 버튼 숨김"
```

---

## Task 9: 랜딩 페이지 QA + TODO.md 업데이트

**Files:**
- Verify: `frontend/src/app/layout.tsx` (suppressHydrationWarning 확인)
- Verify: `frontend/src/components/layout/theme-provider.tsx` (next-themes 설정 확인)
- Modify: `docs/TODO.md`

- [ ] **Step 1: 하이드레이션 관련 코드 확인**

Run: `cd frontend && grep -rn "suppressHydrationWarning\|useTheme\|ThemeProvider" src/ | head -20`
Expected: `layout.tsx`에 `suppressHydrationWarning`, `theme-provider.tsx`에 `ThemeProvider` 확인

- [ ] **Step 2: 프론트엔드 빌드 전체 확인**

Run: `cd frontend && pnpm build 2>&1 | tail -20`
Expected: 빌드 성공

- [ ] **Step 3: TODO.md 업데이트**

Sprint 6 완료 항목 반영:
- `In Progress` 섹션의 ADR-006 잔여 항목 중 해당 없는 것 업데이트
- `Completed` 섹션에 Sprint 6 추가
- `Next Actions`에서 완료 항목 체크

- [ ] **Step 4: 커밋**

```bash
git add docs/TODO.md
git commit -m "docs: Sprint 6 완료 — TODO.md 업데이트"
```

---

## 스프린트 범위 정리

### 포함 (7개 작업)
| # | 작업 | 변경 파일 수 |
|---|------|-------------|
| T1-T4 | Mutation toast 전 도메인 | 4 |
| T5 | Quick Memo mock→API | 1 |
| T6-T8 | Viewer 역할 차단 | 7 |
| T9 | QA + 문서 | 1 |

### 제외 (이미 완료 확인)
- `.env.example` — FE/BE 모두 존재
- Inbox 임계값 UI — 풀스택 완료 (Settings 페이지)
- 랜딩 페이지 하이드레이션 — `suppressHydrationWarning` 이미 적용

### 제외 (P2, Sprint 6c로 이연)
- Header 멤버 수 뱃지
- 온보딩 템플릿 프로젝트 자동 생성
- PDF 내보내기 (MD/JSON만 지원)
- E2E 테스트 환경
