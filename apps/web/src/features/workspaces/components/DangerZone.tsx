"use client";

// 워크스페이스 위험 구역 — owner 전용 영구 삭제 (이름 재입력 확인 다이얼로그)
import { useState } from "react";
import { useRouter } from "next/navigation";
import { TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useWorkspaces, useDeleteWorkspace } from "../hooks";
import { useWorkspaceStore } from "../store";
import { inferWorkspaceType } from "../utils";

interface DangerZoneProps {
  workspaceId: string;
  workspaceName: string;
}

export function DangerZone({ workspaceId, workspaceName }: DangerZoneProps) {
  const router = useRouter();
  const { data: workspaces } = useWorkspaces();
  const { setActiveWorkspaceId } = useWorkspaceStore();
  const deleteWorkspace = useDeleteWorkspace();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  const isNameConfirmed = confirmText === workspaceName;

  const handleDelete = () => {
    if (!isNameConfirmed || deleteWorkspace.isPending) return;
    deleteWorkspace.mutate(workspaceId, {
      onSuccess: () => {
        setIsDialogOpen(false);
        // 삭제된 ws 에 머물 수 없음 — personal 로 폴백 (lazy seed 로 항상 존재)
        const fallback =
          workspaces?.find(
            (ws) =>
              ws.id !== workspaceId && inferWorkspaceType(ws) === "personal"
          ) ?? workspaces?.find((ws) => ws.id !== workspaceId);
        if (fallback) {
          setActiveWorkspaceId(fallback.id);
        }
        router.push("/");
      },
    });
  };

  return (
    <div
      className="rounded-lg border p-4 space-y-3"
      style={{ borderColor: "var(--error, #dc2626)" }}
      data-testid="ws-danger-zone"
    >
      <h2
        className="flex items-center gap-1.5 text-sm font-medium"
        style={{ color: "var(--error, #dc2626)" }}
      >
        <TriangleAlert className="w-4 h-4" aria-hidden />
        위험 구역
      </h2>
      <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
        워크스페이스를 삭제하면 프로젝트·회의·노트·액션·메모리·검색 인덱스가 모두
        영구적으로 삭제됩니다. 이 작업은 되돌릴 수 없습니다.
      </p>
      <Button
        type="button"
        variant="destructive"
        size="sm"
        onClick={() => {
          setConfirmText("");
          setIsDialogOpen(true);
        }}
        data-testid="ws-delete-button"
      >
        워크스페이스 삭제
      </Button>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>워크스페이스 영구 삭제</DialogTitle>
            <DialogDescription>
              모든 데이터가 즉시 삭제되며 복구할 수 없습니다. 계속하려면 아래
              입력란에 워크스페이스 이름{" "}
              <span
                className="font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                {workspaceName}
              </span>{" "}
              그대로 입력하세요.
            </DialogDescription>
          </DialogHeader>
          <Input
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder={workspaceName}
            aria-label="삭제 확인용 워크스페이스 이름 입력"
            data-testid="ws-delete-confirm-input"
          />
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsDialogOpen(false)}
              disabled={deleteWorkspace.isPending}
            >
              취소
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDelete}
              disabled={!isNameConfirmed || deleteWorkspace.isPending}
              data-testid="ws-delete-confirm-button"
            >
              {deleteWorkspace.isPending ? "삭제 중..." : "영구 삭제"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
