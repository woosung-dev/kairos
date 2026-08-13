"use client";

import { useState } from "react";
import { Copy, Check, Link2, Trash2, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { VISIBILITY_LABELS } from "@/lib/visibility";
import type { ProjectVisibility } from "@/lib/visibility";

import { formatExpiry } from "@/lib/format-expiry";

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
  const { data: invites, isLoading, isError, refetch } = useInvites(workspaceId);
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

  // BL-039: non-admin 진입 시 빈 헤더 대신 명시적 권한 부족 메시지.
  // BE 가 403 반환하므로 fetch 가 실패하지만 사용자 입장에서 침묵은 혼란.
  if (!isAdmin) {
    return (
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
        <p className="text-sm">초대 링크 관리 권한이 필요합니다</p>
        <p className="text-xs mt-1">admin 이상 역할의 멤버에게 문의하세요</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-14 rounded-lg" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div
        className="flex flex-col items-start gap-2 rounded-lg border p-4"
        style={{ borderColor: "var(--border)" }}
        role="alert"
      >
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          초대 링크 목록을 불러오지 못했습니다. 네트워크 상태를 확인해주세요.
        </p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          다시 시도
        </Button>
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
              {/* select 의미론 (listbox) — DropdownMenu(menu) 는 스크린리더에
                  선택 컨트롤로 노출되지 않아 Select 로 교체 */}
              <Select
                value={newInviteRole}
                onValueChange={(v) =>
                  setNewInviteRole(v as Exclude<WorkspaceRole, "owner">)
                }
              >
                <SelectTrigger
                  className="w-full"
                  aria-label="초대할 역할 선택"
                >
                  <SelectValue>
                    {newInviteRole === "admin"
                      ? "Admin"
                      : newInviteRole === "member"
                        ? "Member"
                        : "Viewer"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">
                    Admin — 멤버 초대/제거, 모든 콘텐츠 관리
                  </SelectItem>
                  <SelectItem value="member">
                    Member — 콘텐츠 생성/편집, AI 검색
                  </SelectItem>
                  <SelectItem value="viewer">
                    Viewer — 읽기 전용, AI 검색만
                  </SelectItem>
                </SelectContent>
              </Select>

              {/* Sprint 6 FE-T5: default project visibility (시안 3A Two-Stack Radio) */}
              <label
                className="text-sm font-medium pt-2"
                style={{ color: "var(--text-primary)" }}
              >
                기본 Project Visibility
              </label>
              <Select
                value={newDefaultVisibility}
                onValueChange={(v) =>
                  setNewDefaultVisibility(v as ProjectVisibility)
                }
              >
                <SelectTrigger
                  className="w-full"
                  aria-label="기본 Project Visibility 선택"
                >
                  <SelectValue>
                    {VISIBILITY_LABELS[newDefaultVisibility]}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="public">
                    공개 — 워크스페이스 모든 멤버 접근
                  </SelectItem>
                  <SelectItem value="draft">
                    작업 중 — 작성자 + admin/owner만 접근
                  </SelectItem>
                  <SelectItem value="private">
                    비공개 — 명시 멤버 + admin/owner만 접근
                  </SelectItem>
                </SelectContent>
              </Select>
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
                {/* member-list 역할 뱃지와 동일 스타일 (대문자 + mono) */}
                <Badge
                  variant="outline"
                  className="rounded-sm bg-transparent"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    fontWeight: 500,
                    letterSpacing: "0.04em",
                    color: "var(--text-secondary)",
                  }}
                >
                  {invite.role.toUpperCase()}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 cursor-pointer"
                  aria-label="초대 링크 복사"
                  onClick={() => handleCopy(invite.inviteUrl, invite.id)}
                >
                  {copiedId === invite.id ? (
                    <Check
                      className="w-4 h-4"
                      style={{ color: "var(--success)" }}
                    />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 cursor-pointer text-destructive hover:text-destructive"
                  aria-label="초대 링크 비활성화"
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
