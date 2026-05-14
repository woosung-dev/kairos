// Sprint 15 R6 Promote modal — C1 dropdown variant (DESIGN.md §Promote Modal)
"use client";

import { useState } from "react";
import { ArrowUpRight, Users } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useWorkspaces } from "@/features/workspaces/hooks";
import { usePromote } from "../hooks";

interface PromoteModalProps {
  memoryId: string;
  sourceWorkspaceId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PromoteModal({
  memoryId,
  sourceWorkspaceId,
  open,
  onOpenChange,
}: PromoteModalProps) {
  const { data: workspaces } = useWorkspaces();
  // 신규 생성된 워크스페이스는 응답에 type 필드가 누락될 수 있음 (useCreateWorkspace가
  // cache에 추가하는 row). type이 명시적으로 'personal'이 아니면 team으로 본다.
  const teamOptions = (workspaces ?? []).filter(
    (w) => w.type !== "personal" && w.id !== sourceWorkspaceId
  );
  const [targetId, setTargetId] = useState<string>("");
  const promote = usePromote(sourceWorkspaceId);

  const selectedTarget = targetId || teamOptions[0]?.id || "";
  const isDisabled =
    !selectedTarget || promote.isPending || teamOptions.length === 0;

  async function handleConfirm() {
    if (!selectedTarget) return;
    await promote.mutateAsync({
      memoryId,
      targetWorkspaceId: selectedTarget,
    });
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-lg">팀으로 올리기</DialogTitle>
          <DialogDescription>
            어느 팀 워크스페이스로 보낼까요? 원본은 그대로 유지됩니다.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-2">
          <label
            htmlFor="promote-target"
            className="mb-2 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground"
          >
            Target workspace
          </label>
          <div className="relative">
            <Users className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <select
              id="promote-target"
              value={selectedTarget}
              onChange={(event) => setTargetId(event.target.value)}
              disabled={teamOptions.length === 0 || promote.isPending}
              className="h-11 w-full appearance-none rounded-md border border-input bg-background pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
            >
              {teamOptions.length === 0 && (
                <option value="">팀 워크스페이스가 없어요</option>
              )}
              {teamOptions.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={promote.isPending}
          >
            취소
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={isDisabled}>
            <ArrowUpRight className="mr-2 h-4 w-4" />
            {promote.isPending ? "복사 중…" : "팀으로 올리기"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
