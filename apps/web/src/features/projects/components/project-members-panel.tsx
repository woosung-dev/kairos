// Project 멤버 관리 패널 (Sprint 6 FE-T4, 시안 2A 단순화 — inline 섹션)
"use client";

import { Trash2, UserPlus } from "lucide-react";
import { useState } from "react";
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
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useMembers } from "@/features/members/hooks";

import {
  useAddProjectMember,
  useProjectMembers,
  useRemoveProjectMember,
} from "../hooks";
import type { ProjectVisibility } from "../types";

interface ProjectMembersPanelProps {
  workspaceId: string;
  projectId: string;
  visibility: ProjectVisibility;
  canManage: boolean;
}

export function ProjectMembersPanel({
  workspaceId,
  projectId,
  visibility,
  canManage,
}: ProjectMembersPanelProps) {
  if (visibility !== "private") {
    return null;
  }

  return (
    <PrivateProjectMembersPanel
      workspaceId={workspaceId}
      projectId={projectId}
      visibility={visibility}
      canManage={canManage}
    />
  );
}

function PrivateProjectMembersPanel({
  workspaceId,
  projectId,
  visibility,
  canManage,
}: ProjectMembersPanelProps) {
  const { data: projectMembers, isLoading } = useProjectMembers(
    workspaceId,
    projectId
  );
  const { data: workspaceMembers } = useMembers(workspaceId);
  const addMember = useAddProjectMember(workspaceId, projectId);
  const removeMember = useRemoveProjectMember(workspaceId, projectId);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  // 제거 확인 대상 — native confirm() 대신 앱 공용 AlertDialog (다른 삭제 흐름과 동일한 패턴)
  const [removeTargetUserId, setRemoveTargetUserId] = useState<string | null>(null);

  const isPrivate = visibility === "private";

  // 이미 추가된 user_id 제외
  const projectMemberIds = new Set(projectMembers?.map((m) => m.userId) ?? []);
  const candidates = (workspaceMembers ?? []).filter(
    (m) => !projectMemberIds.has(m.userId) && m.role !== "viewer"
  );

  const handleAdd = () => {
    if (!selectedUserId) return;
    addMember.mutate(
      { userId: selectedUserId, role: "member" },
      {
        onSuccess: () => {
          setSelectedUserId(null);
          toast.success("프로젝트 멤버를 추가했습니다");
        },
        onError: (err) => {
          toast.error(err instanceof Error ? err.message : "멤버 추가에 실패했습니다");
        },
      }
    );
  };

  const handleConfirmRemove = () => {
    if (!removeTargetUserId) return;
    removeMember.mutate(removeTargetUserId, {
      onSuccess: () => toast.success("프로젝트 멤버를 제거했습니다"),
      onError: (err) => {
        toast.error(err instanceof Error ? err.message : "멤버 제거에 실패했습니다");
      },
    });
    setRemoveTargetUserId(null);
  };

  const removeTarget = projectMembers?.find((pm) => pm.userId === removeTargetUserId);
  const removeTargetName =
    workspaceMembers?.find((m) => m.userId === removeTarget?.userId)?.displayName ??
    "이 멤버";

  return (
    <div
      className="mt-6 p-4 rounded border"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-md)",
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3
          className="text-sm font-semibold"
          style={{
            color: "var(--text-primary)",
            fontFamily: "var(--font-display)",
          }}
        >
          프로젝트 멤버
          {projectMembers && (
            <span
              className="ml-2 text-xs"
              style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
            >
              {projectMembers.length}
            </span>
          )}
        </h3>
        {isPrivate && (
          <span className="text-caption" style={{ color: "var(--text-muted)" }}>
            비공개 프로젝트는 여기 있는 멤버와 admin/owner 만 볼 수 있습니다
          </span>
        )}
      </div>

      {/* 멤버 추가 (admin 이상만, BE-T7이 검증) */}
      {canManage && (
        <div className="flex items-center gap-2 mb-3">
          <DropdownMenu>
            <DropdownMenuTrigger
              className="flex-1 inline-flex items-center justify-between px-3 py-2 text-sm rounded-md border cursor-pointer"
              style={{
                borderColor: "var(--border-subtle)",
                color: selectedUserId
                  ? "var(--text-primary)"
                  : "var(--text-muted)",
              }}
            >
              {selectedUserId
                ? candidates.find((c) => c.userId === selectedUserId)?.displayName ??
                  "멤버 선택됨"
                : candidates.length === 0
                  ? "추가 가능한 멤버 없음"
                  : "워크스페이스 멤버 선택..."}
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              {candidates.map((m) => (
                <DropdownMenuItem
                  key={m.userId}
                  onClick={() => setSelectedUserId(m.userId)}
                  className="cursor-pointer"
                >
                  {m.displayName ?? m.email ?? m.userId}{" "}
                  <span
                    className="ml-2 text-xs"
                    style={{ color: "var(--text-muted)" }}
                  >
                    ({m.role})
                  </span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <Button
            size="sm"
            onClick={handleAdd}
            disabled={!selectedUserId || addMember.isPending}
          >
            <UserPlus className="w-4 h-4 mr-1" />
            추가
          </Button>
        </div>
      )}

      {/* 멤버 리스트 */}
      {isLoading ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          멤버 불러오는 중...
        </p>
      ) : projectMembers && projectMembers.length > 0 ? (
        <ul className="space-y-1">
          {projectMembers.map((pm) => {
            const ws = workspaceMembers?.find((m) => m.userId === pm.userId);
            return (
              <li
                key={pm.id}
                className="flex items-center justify-between px-2 py-1.5 rounded transition-colors hover:bg-[var(--surface-hover)]"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center text-xs"
                    style={{
                      background: "var(--surface-active)",
                      color: "var(--text-secondary)",
                    }}
                  >
                    {(ws?.displayName ?? "?").slice(0, 1).toUpperCase()}
                  </div>
                  <span
                    className="text-sm truncate"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {ws?.displayName ?? ws?.email ?? pm.userId}
                  </span>
                  <span
                    className="text-xs"
                    style={{
                      color: "var(--text-muted)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    {pm.role}
                  </span>
                </div>
                {canManage && (
                  // 이전 `opacity-0 group-hover:opacity-100` 은 부모에 `group` 이 없어 항상 투명 →
                  // 제거 버튼이 존재하는데 보이지 않았다. 항상 노출 + aria-label.
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 cursor-pointer"
                    aria-label={`${ws?.displayName ?? "멤버"} 프로젝트에서 제거`}
                    onClick={() => setRemoveTargetUserId(pm.userId)}
                    disabled={removeMember.isPending}
                  >
                    <Trash2
                      className="w-3.5 h-3.5"
                      style={{ color: "var(--text-muted)" }}
                    />
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          아직 추가된 멤버가 없습니다
          {isPrivate && canManage && ". 위에서 워크스페이스 멤버를 선택해 추가하세요"}
        </p>
      )}

      <AlertDialog
        open={removeTargetUserId !== null}
        onOpenChange={(open) => {
          if (!open) setRemoveTargetUserId(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>프로젝트에서 제거하시겠습니까?</AlertDialogTitle>
            <AlertDialogDescription>
              {removeTargetName}님은 이 비공개 프로젝트의 회의·노트를 더 이상 볼 수 없게 됩니다.
              워크스페이스 멤버십은 유지됩니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleConfirmRemove}
            >
              제거
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
