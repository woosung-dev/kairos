// 프로젝트 관리 다이얼로그 묶음 — visibility/편집/아카이브/삭제 + mutations 소유 (BL-AV-1 분해)
"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
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
import type { Project } from "../../types";
import {
  useArchiveProject,
  useDeleteProject,
  useUpdateProject,
} from "../../hooks";
import { EditProjectDialog } from "../edit-project-dialog";
import { VisibilityChangeDialog } from "../visibility-change-dialog";

export function ProjectAdminDialogs({
  wid,
  projectId,
  project,
  visibilityDialogOpen,
  onVisibilityDialogOpenChange,
  editDialogOpen,
  onEditDialogOpenChange,
  archiveAlertOpen,
  onArchiveAlertOpenChange,
  deleteAlertOpen,
  onDeleteAlertOpenChange,
}: {
  wid: string | undefined;
  projectId: string;
  project: Project;
  visibilityDialogOpen: boolean;
  onVisibilityDialogOpenChange: (open: boolean) => void;
  editDialogOpen: boolean;
  onEditDialogOpenChange: (open: boolean) => void;
  archiveAlertOpen: boolean;
  onArchiveAlertOpenChange: (open: boolean) => void;
  deleteAlertOpen: boolean;
  onDeleteAlertOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const updateProject = useUpdateProject(wid);
  const deleteMutation = useDeleteProject(wid);
  const archiveMutation = useArchiveProject(wid);

  return (
    <>
      <VisibilityChangeDialog
        open={visibilityDialogOpen}
        onOpenChange={onVisibilityDialogOpenChange}
        currentVisibility={project.visibility}
        isPending={updateProject.isPending}
        onConfirm={(next) => {
          updateProject.mutate(
            { id: projectId, data: { visibility: next } },
            { onSuccess: () => onVisibilityDialogOpenChange(false) }
          );
        }}
      />

      {wid && (
        <EditProjectDialog
          open={editDialogOpen}
          onOpenChange={onEditDialogOpenChange}
          workspaceId={wid}
          project={project}
        />
      )}

      <AlertDialog open={archiveAlertOpen} onOpenChange={onArchiveAlertOpenChange}>
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
                  onSuccess: () => onArchiveAlertOpenChange(false),
                });
              }}
              disabled={archiveMutation.isPending}
            >
              아카이브
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={deleteAlertOpen} onOpenChange={onDeleteAlertOpenChange}>
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
                    onDeleteAlertOpenChange(false);
                    router.push("/dashboard");
                  },
                  onError: (err) => {
                    // BL-S27e-5: 콘텐츠 연결 프로젝트는 409 → 사유 토스트, 다이얼로그 유지.
                    toast.error(err instanceof Error ? err.message : "삭제 실패");
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
    </>
  );
}
