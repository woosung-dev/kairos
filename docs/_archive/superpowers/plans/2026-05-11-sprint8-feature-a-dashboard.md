# Sprint 8 Feature A — 프로젝트 대시보드 데이터 연결 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `ProjectDashboard`에 실제 meetings/notes/actions 데이터를 연결하고, AD-34에서 `ProjectDetail`에 만든 관리 컨트롤(VisibilityBadge, 편집/아카이브/삭제)을 이식한다.

**Architecture:** `/projects/[id]/page.tsx`는 이미 `ProjectDashboard`를 사용 중. `ProjectDetail`은 쓰이지 않는 데드 코드. `ProjectDashboard`에 (1) meetings projectId 필터 수정, (2) 관리 컨트롤 이식, (3) `ProjectMembersPanel` 추가를 한다. 기존 훅(`useMeetings`, `useNotes`, `useActionItems`)은 이미 projectId 필터를 지원하므로 BE 변경 없음.

**Tech Stack:** Next.js (App Router), React 19, TypeScript strict, shadcn/ui v4, @tanstack/react-query v5, Clerk

---

## 파일 구조

| 작업 | 경로 |
|------|------|
| **수정** | `frontend/src/features/projects/components/project-dashboard.tsx` |
| **참조** (변경 없음) | `frontend/src/features/projects/components/project-detail.tsx` (AD-34 구현 참조용) |

---

## Task 1: meetings projectId 필터 수정

**Files:**
- Modify: `frontend/src/features/projects/components/project-dashboard.tsx`

현재 버그: `useMeetings(wid)` — projectId 없이 전체 fetch 후 `.slice(0, 5)`.
수정: `useMeetings(wid, 1, projectId)` 로 교체.

- [ ] **Step 1: `useMeetings` 호출에 `projectId` 전달**

`project-dashboard.tsx`에서 아래 줄을 찾아 교체한다.

기존:
```typescript
const { data: meetingsData, isLoading: meetingsLoading } = useMeetings(wid);
```

교체:
```typescript
const { data: meetingsData, isLoading: meetingsLoading } = useMeetings(wid, 1, projectId);
```

- [ ] **Step 2: 클라이언트 슬라이스 제거**

기존:
```typescript
/* 회의: projectId 기준 클라이언트 필터 */
/* Meeting 타입엔 projectId 필드 없음 — BE API가 projectId 필터 미지원이므로 전체 목록 상위 5개 표시 */
const projectMeetings = (meetingsData?.items ?? []).slice(0, 5);
```

교체:
```typescript
const projectMeetings = meetingsData?.items ?? [];
```

- [ ] **Step 3: TypeScript 컴파일 확인**

```bash
cd /Users/woosung/project/agy-project/kairos/frontend
pnpm tsc --noEmit 2>&1 | head -20
```

Expected: 에러 없음

- [ ] **Step 4: 커밋**

```bash
cd /Users/woosung/project/agy-project/kairos
git add frontend/src/features/projects/components/project-dashboard.tsx
git commit -m "fix(projects): ProjectDashboard meetings projectId 필터 수정 (BE-T14)"
```

---

## Task 2: 관리 컨트롤 이식 — DashboardHeader에 VisibilityBadge + 케밥 메뉴

**Files:**
- Modify: `frontend/src/features/projects/components/project-dashboard.tsx`

`ProjectDetail`(AD-34)에서 만든 VisibilityBadge + 케밥 메뉴(편집/아카이브/삭제)를 `ProjectDashboard`의 `DashboardHeader`로 이식한다. `ProjectDetail` 파일을 참조하여 정확한 코드를 복사한다.

- [ ] **Step 1: import 추가**

`project-dashboard.tsx` 상단에 아래 import를 추가한다 (기존 import 아래에 추가).

```typescript
import { useState } from "react";
import { useRouter } from "next/navigation";
import { MoreHorizontal } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useWorkspaceRole } from "@/features/members/hooks";
import { useArchiveProject, useDeleteProject, useUpdateProject } from "../hooks";
import { EditProjectDialog } from "./edit-project-dialog";
import { VisibilityBadge } from "./visibility-badge";
import { VisibilityChangeDialog } from "./visibility-change-dialog";
```

주의: `project-dashboard.tsx`는 이미 `"use client"`가 없을 수 있다. 파일 상단에 `"use client";` 추가.

- [ ] **Step 2: `ProjectDashboard` 함수 내부에 상태 및 훅 추가**

`ProjectDashboard` 함수 내 `const wid = ...` 바로 다음에 추가:

```typescript
const router = useRouter();
const [visibilityDialogOpen, setVisibilityDialogOpen] = useState(false);
const [editDialogOpen, setEditDialogOpen] = useState(false);
const [archiveAlertOpen, setArchiveAlertOpen] = useState(false);
const [deleteAlertOpen, setDeleteAlertOpen] = useState(false);
const { canManage } = useWorkspaceRole(wid);
const updateProject = useUpdateProject(wid);
const deleteMutation = useDeleteProject(wid);
const archiveMutation = useArchiveProject(wid);
```

- [ ] **Step 3: `DashboardHeader` 컴포넌트 시그니처 수정**

기존 `DashboardHeader` 컴포넌트는 `{ project }` 만 받는다. 아래로 교체:

```typescript
function DashboardHeader({
  project,
  canManage,
  onVisibilityClick,
  onEditClick,
  onArchiveClick,
  onDeleteClick,
}: {
  project: Project;
  canManage: boolean;
  onVisibilityClick: () => void;
  onEditClick: () => void;
  onArchiveClick: () => void;
  onDeleteClick: () => void;
}) {
```

- [ ] **Step 4: `DashboardHeader` 내부 — VisibilityBadge + 케밥 메뉴 추가**

`DashboardHeader` 내부의 `<div className="flex items-center gap-3 mb-2">` 블록을 다음으로 교체:

```typescript
<div className="flex items-center gap-3 mb-2">
  <h1
    className="text-2xl font-bold"
    style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
  >
    {project.title}
  </h1>
  <span
    className="px-2 py-0.5 rounded-full text-xs font-medium"
    style={{
      background: STATUS_BG[project.status],
      color: STATUS_COLOR[project.status],
    }}
  >
    {STATUS_LABELS[project.status]}
  </span>
  <VisibilityBadge
    visibility={project.visibility}
    onClick={canManage ? onVisibilityClick : undefined}
  />
  {canManage && (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-[var(--surface-hover)] transition-colors"
      >
        <MoreHorizontal className="h-4 w-4" style={{ color: "var(--text-muted)" }} />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={onEditClick}>편집</DropdownMenuItem>
        <DropdownMenuItem onClick={onArchiveClick}>아카이브</DropdownMenuItem>
        <DropdownMenuItem
          className="text-destructive focus:text-destructive"
          onClick={onDeleteClick}
        >
          삭제
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )}
</div>
```

- [ ] **Step 5: `ProjectDashboard` 렌더에서 `DashboardHeader` 호출 업데이트**

`<DashboardHeader project={project} />` 를 모두 찾아 다음으로 교체:

```typescript
<DashboardHeader
  project={project}
  canManage={canManage}
  onVisibilityClick={() => setVisibilityDialogOpen(true)}
  onEditClick={() => setEditDialogOpen(true)}
  onArchiveClick={() => setArchiveAlertOpen(true)}
  onDeleteClick={() => setDeleteAlertOpen(true)}
/>
```

- [ ] **Step 6: 다이얼로그 컴포넌트 추가**

`return (...)` 최상위 `<div>` 닫기 바로 전에 추가:

```typescript
{/* 관리 컨트롤 다이얼로그 */}
<VisibilityChangeDialog
  open={visibilityDialogOpen}
  onOpenChange={setVisibilityDialogOpen}
  currentVisibility={project.visibility}
  isPending={updateProject.isPending}
  onConfirm={(next) => {
    updateProject.mutate(
      { id: projectId, data: { visibility: next } },
      { onSuccess: () => setVisibilityDialogOpen(false) }
    );
  }}
/>

{wid && (
  <EditProjectDialog
    open={editDialogOpen}
    onOpenChange={setEditDialogOpen}
    workspaceId={wid}
    project={project}
  />
)}

<AlertDialog open={archiveAlertOpen} onOpenChange={setArchiveAlertOpen}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>프로젝트를 아카이브하시겠습니까?</AlertDialogTitle>
      <AlertDialogDescription>
        아카이브된 프로젝트는 목록에서 숨겨지며 나중에 복원할 수 있습니다.
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>취소</AlertDialogCancel>
      <AlertDialogAction
        onClick={() => {
          archiveMutation.mutate(projectId, {
            onSuccess: () => setArchiveAlertOpen(false),
          });
        }}
        disabled={archiveMutation.isPending}
      >
        아카이브
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>

<AlertDialog open={deleteAlertOpen} onOpenChange={setDeleteAlertOpen}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>프로젝트를 삭제하시겠습니까?</AlertDialogTitle>
      <AlertDialogDescription>
        삭제된 프로젝트는 복원할 수 없습니다.
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>취소</AlertDialogCancel>
      <AlertDialogAction
        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
        onClick={() => {
          deleteMutation.mutate(projectId, {
            onSuccess: () => {
              setDeleteAlertOpen(false);
              router.push("/dashboard");
            },
          });
        }}
        disabled={deleteMutation.isPending}
      >
        삭제
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

- [ ] **Step 7: TypeScript 컴파일 확인**

```bash
cd /Users/woosung/project/agy-project/kairos/frontend
pnpm tsc --noEmit 2>&1 | head -30
```

Expected: 에러 없음

- [ ] **Step 8: 커밋**

```bash
cd /Users/woosung/project/agy-project/kairos
git add frontend/src/features/projects/components/project-dashboard.tsx
git commit -m "feat(projects): ProjectDashboard 관리 컨트롤 이식 (VisibilityBadge + 편집/아카이브/삭제)"
```

---

## Task 3: ProjectMembersPanel 추가

**Files:**
- Modify: `frontend/src/features/projects/components/project-dashboard.tsx`

- [ ] **Step 1: ProjectMembersPanel import 추가**

```typescript
import { ProjectMembersPanel } from "./project-members-panel";
```

- [ ] **Step 2: 2컬럼 그리드 아래에 ProjectMembersPanel 추가**

`</div> {/* 2컬럼 그리드 */}` 아래, 다이얼로그 블록 시작 전에 추가:

```typescript
{wid && (
  <ProjectMembersPanel
    workspaceId={wid}
    projectId={projectId}
    visibility={project.visibility}
    canManage={canManage}
  />
)}
```

- [ ] **Step 3: TypeScript 컴파일 확인**

```bash
cd /Users/woosung/project/agy-project/kairos/frontend
pnpm tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 4: 커밋**

```bash
cd /Users/woosung/project/agy-project/kairos
git add frontend/src/features/projects/components/project-dashboard.tsx
git commit -m "feat(projects): ProjectDashboard ProjectMembersPanel 추가 (AD-46)"
```

---

## 검증 체크리스트

- [ ] 프로젝트에 연결된 회의만 표시됨 (전체 회의 목록 아님)
- [ ] 노트/액션 탭 실제 데이터 표시
- [ ] owner 로그인 → VisibilityBadge 클릭 가능, 케밥 메뉴 표시
- [ ] member 로그인 → VisibilityBadge 클릭 불가, 케밥 메뉴 없음
- [ ] 편집/아카이브/삭제 동작 확인
- [ ] ProjectMembersPanel canManage 분기 확인
