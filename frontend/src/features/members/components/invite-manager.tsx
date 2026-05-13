"use client";

import { useState } from "react";
import { Copy, Check, Link2, Trash2, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  VISIBILITY_LABELS,
} from "@/features/projects/components/visibility-badge";
import type { ProjectVisibility } from "@/features/projects/types";

import { useInvites, useCreateInvite, useDeactivateInvite } from "../hooks";
import type { WorkspaceRole } from "../types";

interface InviteManagerProps {
  workspaceId: string;
  currentUserRole: WorkspaceRole | null;
}

export function InviteManager({
  workspaceId,
  currentUserRole,
}: InviteManagerProps) {
  const { data: invites, isLoading } = useInvites(workspaceId);
  const createInvite = useCreateInvite(workspaceId);
  const deactivateInvite = useDeactivateInvite(workspaceId);

  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [confirmDeactivateId, setConfirmDeactivateId] = useState<string | null>(null);
  const [newInviteRole, setNewInviteRole] =
    useState<Exclude<WorkspaceRole, "owner">>("member");
  const [newDefaultVisibility, setNewDefaultVisibility] =
    useState<ProjectVisibility>("public");

  const isAdmin =
    currentUserRole === "admin" || currentUserRole === "owner";

  const handleCopy = async (url: string, id: string) => {
    await navigator.clipboard.writeText(url);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCreate = () => {
    createInvite.mutate(
      {
        role: newInviteRole,
        defaultProjectVisibility: newDefaultVisibility,
        expiresInDays: 7,
      },
      {
        onSuccess: () => {
          setIsCreateOpen(false);
          setNewInviteRole("member");
          setNewDefaultVisibility("public");
        },
      }
    );
  };

  const handleDeactivate = () => {
    if (confirmDeactivateId) {
      deactivateInvite.mutate(confirmDeactivateId);
      setConfirmDeactivateId(null);
    }
  };

  const formatExpiry = (expiresAt: string | null) => {
    if (!expiresAt) return "만료 없음";
    const date = new Date(expiresAt);
    const now = new Date();
    const diffDays = Math.ceil(
      (date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
    );
    if (diffDays <= 0) return "만료됨";
    if (diffDays === 1) return "1일 남음";
    return `${diffDays}일 남음`;
  };

  if (!isAdmin) return null;

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <div
            key={i}
            className="h-14 rounded-lg animate-pulse"
            style={{ background: "var(--surface-active)" }}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 헤더 + 생성 버튼 */}
      <div className="flex items-center justify-between">
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          초대 링크를 생성하여 팀원을 워크스페이스에 초대합니다.
        </p>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger
            render={
              <Button size="sm" className="gap-1.5 cursor-pointer" />
            }
          >
            <Plus className="w-4 h-4" />
            초대 링크 생성
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>초대 링크 생성</DialogTitle>
              <DialogDescription>
                새 초대 링크를 생성합니다. 링크는 7일 후 만료됩니다.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3 py-2">
              <label
                className="text-sm font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                초대할 역할
              </label>
              <DropdownMenu>
                <DropdownMenuTrigger
                  className="inline-flex items-center justify-between w-full px-3 py-2 text-sm rounded-md border cursor-pointer"
                  style={{
                    borderColor: "var(--border-subtle)",
                    color: "var(--text-primary)",
                  }}
                >
                  {newInviteRole === "admin"
                    ? "Admin"
                    : newInviteRole === "member"
                      ? "Member"
                      : "Viewer"}
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem
                    className="cursor-pointer"
                    onClick={() => setNewInviteRole("admin")}
                  >
                    Admin — 멤버 초대/제거, 모든 콘텐츠 관리
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="cursor-pointer"
                    onClick={() => setNewInviteRole("member")}
                  >
                    Member — 콘텐츠 생성/편집, AI 검색
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="cursor-pointer"
                    onClick={() => setNewInviteRole("viewer")}
                  >
                    Viewer — 읽기 전용, AI 검색만
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Sprint 6 FE-T5: default project visibility (시안 3A Two-Stack Radio) */}
              <label
                className="text-sm font-medium pt-2"
                style={{ color: "var(--text-primary)" }}
              >
                기본 Project Visibility
              </label>
              <DropdownMenu>
                <DropdownMenuTrigger
                  className="inline-flex items-center justify-between w-full px-3 py-2 text-sm rounded-md border cursor-pointer"
                  style={{
                    borderColor: "var(--border-subtle)",
                    color: "var(--text-primary)",
                  }}
                >
                  {VISIBILITY_LABELS[newDefaultVisibility]}
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem
                    className="cursor-pointer"
                    onClick={() => setNewDefaultVisibility("public")}
                  >
                    공개 — 워크스페이스 모든 멤버 접근
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="cursor-pointer"
                    onClick={() => setNewDefaultVisibility("draft")}
                  >
                    작업 중 — 작성자 + admin/owner만 접근
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="cursor-pointer"
                    onClick={() => setNewDefaultVisibility("private")}
                  >
                    비공개 — 명시 멤버 + admin/owner만 접근
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <DialogFooter>
              <Button
                variant="ghost"
                onClick={() => setIsCreateOpen(false)}
                className="cursor-pointer"
              >
                취소
              </Button>
              <Button
                onClick={handleCreate}
                disabled={createInvite.isPending}
                className="cursor-pointer"
              >
                {createInvite.isPending ? "생성 중..." : "생성"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* 초대 링크 목록 */}
      {invites && invites.length > 0 ? (
        <div className="space-y-1">
          {invites.map((invite) => (
            <div
              key={invite.id}
              className="flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors duration-150 hover:bg-[var(--surface-active)]"
            >
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
                  style={{
                    background: "var(--surface-active)",
                    color: "var(--text-secondary)",
                  }}
                >
                  <Link2 className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <p
                    className="text-sm font-mono truncate"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {invite.code}
                  </p>
                  <div className="flex items-center gap-2">
                    <span
                      className="text-xs"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {formatExpiry(invite.expiresAt)}
                    </span>
                    {invite.maxUses && (
                      <span
                        className="text-xs"
                        style={{ color: "var(--text-muted)" }}
                      >
                        · {invite.useCount}/{invite.maxUses} 사용
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Badge variant="outline" className="text-xs">
                  {invite.role}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 cursor-pointer"
                  onClick={() => handleCopy(invite.inviteUrl, invite.id)}
                >
                  {copiedId === invite.id ? (
                    <Check className="w-4 h-4 text-green-400" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 cursor-pointer text-red-400 hover:text-red-300"
                  onClick={() => setConfirmDeactivateId(invite.id)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div
          className="text-center py-8 rounded-lg"
          style={{
            background: "var(--surface)",
            color: "var(--text-muted)",
          }}
        >
          <Link2
            className="w-8 h-8 mx-auto mb-2"
            style={{ color: "var(--text-muted)" }}
          />
          <p className="text-sm">아직 초대 링크가 없습니다</p>
          <p className="text-xs mt-1">위의 버튼으로 새 링크를 생성하세요</p>
        </div>
      )}

      {/* 비활성화 확인 다이얼로그 */}
      <Dialog
        open={!!confirmDeactivateId}
        onOpenChange={() => setConfirmDeactivateId(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>초대 링크를 비활성화하시겠습니까?</DialogTitle>
            <DialogDescription>
              비활성화된 링크로는 더 이상 워크스페이스에 참여할 수 없습니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setConfirmDeactivateId(null)}
              className="cursor-pointer"
            >
              취소
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeactivate}
              className="cursor-pointer"
            >
              비활성화
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
