# AD-34 — FE RBAC 정밀 분기 설계

## Context

백엔드는 이미 `admin` 이상만 visibility 변경·멤버 관리·프로젝트 삭제/아카이브를 허용한다 (`require_admin` Depends).
그러나 프론트엔드는 role 무관하게 모든 버튼을 노출하고 있어, 권한 없는 사용자가 눌렀을 때 403이 발생하는 UX 문제가 있다.
AD-34는 FE에서 role에 따라 버튼 자체를 숨겨 UI 일관성을 확보한다.

---

## 역할 권한 매트릭스

| 작업 | owner | admin | member | viewer |
|------|:-----:|:-----:|:------:|:------:|
| visibility 변경 | ✅ | ✅ | ❌ | ❌ |
| 프로젝트 멤버 추가/제거 | ✅ | ✅ | ❌ | ❌ |
| 프로젝트 편집 (제목/설명/태그/상태) | ✅ | ✅ | ❌ | ❌ |
| 프로젝트 아카이브 | ✅ | ✅ | ❌ | ❌ |
| 프로젝트 삭제 | ✅ | ✅ | ❌ | ❌ |
| 읽기 | ✅ | ✅ | ✅ | ✅ |

`canManage = role === "admin" || role === "owner"`

---

## 구현 방식 — A안 채택

`useWorkspaceRole(workspaceId)` 훅을 신설하여 `project-detail.tsx`에서 한 번 호출하고,
`canManage` prop을 하위 컴포넌트에 전달한다. React Query가 `memberKeys.list(wid)` 쿼리를
dedup하므로 중복 네트워크 요청 없음.

---

## 컴포넌트 트리

```
project-detail.tsx
  ├── useWorkspaceRole(workspaceId) → { canManage }
  │
  ├── [Header 영역]
  │   ├── VisibilityBadge  (onClick=handleVisibilityClick if canManage, else undefined)
  │   └── DropdownMenu (케밥 메뉴, canManage일 때만 렌더)
  │       ├── "편집"     → editDialogOpen = true
  │       ├── "아카이브" → archiveAlertOpen = true
  │       └── "삭제"     → deleteAlertOpen = true
  │
  ├── EditProjectDialog (open=editDialogOpen, project=project)
  ├── AlertDialog (Archive 확인)
  ├── AlertDialog (Delete 확인 → 완료 시 /workspace/[wid] 이동)
  │
  ├── [탭 / 본문 — 변경 없음]
  │
  └── ProjectMembersPanel (canManage=canManage)
```

---

## 파일별 변경 계획

### 1. `frontend/src/features/members/hooks.ts` — `useWorkspaceRole` 신설

```typescript
export function useWorkspaceRole(workspaceId: string | undefined) {
  const { user } = useUser();
  const { data: members } = useMembers(workspaceId);

  const role = members?.find((m) => m.userId === user?.id)?.role ?? null;
  return {
    role,
    isOwner: role === "owner",
    isAdmin: role === "admin" || role === "owner",
    canManage: role === "admin" || role === "owner",
  };
}
```

반환 타입은 `{ role: WorkspaceRole | null; isOwner: boolean; isAdmin: boolean; canManage: boolean }`.

---

### 2. `frontend/src/features/projects/components/edit-project-dialog.tsx` — 신규

- `Dialog` + `form` (react-hook-form + zod)
- 필드: `title` (required), `description` (optional textarea), `status` (select: active/completed/archived), `tags` (콤마 구분 텍스트 → string[] 변환)
- 제출 시 `useUpdateProject(workspaceId, projectId)` 호출
- 성공 시 다이얼로그 닫기 + 쿼리 자동 무효화 (기존 훅이 처리)

```typescript
interface EditProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  project: Project;
}
```

스키마:
```typescript
const editProjectSchema = z.object({
  title: z.string().min(1, "프로젝트 이름을 입력하세요"),
  description: z.string().optional(),
  status: z.enum(["active", "completed", "archived"]),
  tags: z.string(), // 콤마 구분 문자열, submit 시 split(",").map(trim).filter(Boolean)
});
```

---

### 3. `frontend/src/features/projects/components/project-detail.tsx` — 수정

추가 import:
```typescript
import { useWorkspaceRole } from "@/features/members/hooks";
import { EditProjectDialog } from "./edit-project-dialog";
import { useDeleteProject, useArchiveProject } from "../hooks";
import { MoreHorizontal } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
```

추가 상태:
```typescript
const [editDialogOpen, setEditDialogOpen] = useState(false);
const [archiveAlertOpen, setArchiveAlertOpen] = useState(false);
const [deleteAlertOpen, setDeleteAlertOpen] = useState(false);
```

추가 훅:
```typescript
const { canManage } = useWorkspaceRole(workspaceId);
const deleteMutation = useDeleteProject(workspaceId);
const archiveMutation = useArchiveProject(workspaceId);
```

헤더 변경:
- `VisibilityBadge`에 `onClick={canManage ? handleVisibilityClick : undefined}` 전달
- 헤더 우측에 `canManage && <DropdownMenu>` 추가

프로젝트 삭제 후 라우팅:
```typescript
deleteMutation.mutate(project.id, {
  onSuccess: () => router.push(`/workspace/${workspaceId}`),
});
```

---

### 4. `frontend/src/features/projects/components/project-members-panel.tsx` — 수정

Props에 `canManage: boolean` 추가:
```typescript
interface ProjectMembersPanelProps {
  workspaceId: string;
  projectId: string;
  visibility: ProjectVisibility;
  canManage: boolean;
}
```

멤버 추가 영역 (`canManage && <...>`), Trash 아이콘 (`canManage && <Button ...>`) 조건부 렌더링.

---

## 검증 계획

1. **owner 로그인** → 케밥 메뉴 렌더 확인, 편집 다이얼로그 동작, 아카이브/삭제 확인
2. **member 로그인** → 케밥 메뉴 없음, VisibilityBadge 클릭 불가(cursor 변화 없음), ProjectMembersPanel에 추가/제거 버튼 없음
3. **편집 저장** → title/description/status 반영, 쿼리 자동 갱신
4. **삭제** → 워크스페이스 프로젝트 목록으로 리다이렉트

---

## 파일 경로 요약

| 작업 | 경로 |
|------|------|
| 신규 | `frontend/src/features/projects/components/edit-project-dialog.tsx` |
| 수정 | `frontend/src/features/members/hooks.ts` |
| 수정 | `frontend/src/features/projects/components/project-detail.tsx` |
| 수정 | `frontend/src/features/projects/components/project-members-panel.tsx` |
