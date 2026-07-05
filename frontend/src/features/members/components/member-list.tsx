"use client";

import { useState } from "react";
import { MoreHorizontal, Shield, ShieldCheck, Crown, Eye } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useMembers, useUpdateMemberRole, useRemoveMember } from "../hooks";
import type { Member, WorkspaceRole } from "../types";

// Sprint 23 D2 Variant C: 모든 role badge 가 사각 outline + Geist Mono 11px 통일.
// 색상 강조는 owner=accent, admin=text-primary, default=text-secondary 로 의미만 분리.
type RoleTone = "owner" | "admin" | "default";

const ROLE_CONFIG: Record<
  WorkspaceRole,
  { label: string; icon: typeof Crown; tone: RoleTone }
> = {
  owner: { label: "OWNER", icon: Crown, tone: "owner" },
  admin: { label: "ADMIN", icon: ShieldCheck, tone: "admin" },
  member: { label: "MEMBER", icon: Shield, tone: "default" },
  viewer: { label: "VIEWER", icon: Eye, tone: "default" },
};

const ROLE_TONE_STYLE: Record<RoleTone, React.CSSProperties> = {
  owner: { borderColor: "var(--accent)", color: "var(--accent)" },
  admin: {
    borderColor: "var(--border)",
    color: "var(--text-primary)",
  },
  default: {
    borderColor: "var(--border)",
    color: "var(--text-secondary)",
  },
};

interface MemberListProps {
  workspaceId: string;
  currentUserRole: WorkspaceRole | null;
}

export function MemberList({ workspaceId, currentUserRole }: MemberListProps) {
  const { data: members, isLoading, isError, refetch } = useMembers(workspaceId);
  const updateRole = useUpdateMemberRole(workspaceId);
  const removeMember = useRemoveMember(workspaceId);

  const [confirmRemove, setConfirmRemove] = useState<Member | null>(null);

  const isOwner = currentUserRole === "owner";
  const isAdmin = currentUserRole === "admin" || isOwner;

  const handleRoleChange = (memberId: string, role: Exclude<WorkspaceRole, "owner">) => {
    updateRole.mutate({ memberId, data: { role } });
  };

  const handleRemove = (member: Member) => {
    setConfirmRemove(member);
  };

  const confirmRemoveMember = () => {
    if (confirmRemove) {
      removeMember.mutate(confirmRemove.id);
      setConfirmRemove(null);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
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
          멤버 목록을 불러오지 못했습니다. 네트워크 상태를 확인해주세요.
        </p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          다시 시도
        </Button>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-1">
        {members?.map((member) => {
          const config = ROLE_CONFIG[member.role];
          const RoleIcon = config.icon;
          const isCurrentOwner = member.role === "owner";

          return (
            <div
              key={member.id}
              className="flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors duration-150 hover:bg-[var(--surface-active)]"
            >
              {/* 왼쪽: 아바타 + 이름 + 이메일 */}
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium shrink-0"
                  style={{
                    background: "var(--surface-active)",
                    color: "var(--text-secondary)",
                  }}
                >
                  {(member.displayName ?? member.email ?? "?")
                    .charAt(0)
                    .toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p
                    className="text-sm font-medium truncate"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {member.displayName ?? "이름 없음"}
                  </p>
                  <p
                    className="text-xs truncate"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {member.email}
                  </p>
                </div>
              </div>

              {/* 오른쪽: 역할 뱃지 + 액션 */}
              <div className="flex items-center gap-2 shrink-0">
                <Badge
                  variant="outline"
                  className="gap-1 rounded-sm bg-transparent"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    fontWeight: 500,
                    letterSpacing: "0.04em",
                    paddingInline: 6,
                    paddingBlock: 2,
                    ...ROLE_TONE_STYLE[config.tone],
                  }}
                >
                  <RoleIcon className="w-3 h-3" aria-hidden />
                  {config.label}
                </Badge>

                {/* Owner만 역할 변경, Admin 이상만 제거 가능 */}
                {!isCurrentOwner && (isOwner || isAdmin) && (
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      aria-label={`${member.displayName ?? member.email ?? "멤버"} 관리 메뉴`}
                      className="inline-flex items-center justify-center h-8 w-8 rounded-md cursor-pointer transition-colors duration-150 hover:bg-[var(--surface-active)]"
                    >
                      <MoreHorizontal className="w-4 h-4" style={{ color: "var(--text-secondary)" }} />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-40">
                      {isOwner && (
                        <>
                          <DropdownMenuItem
                            className="cursor-pointer"
                            disabled={member.role === "admin"}
                            onClick={() => handleRoleChange(member.id, "admin")}
                          >
                            <ShieldCheck className="w-4 h-4 mr-2" />
                            Admin으로 변경
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="cursor-pointer"
                            disabled={member.role === "member"}
                            onClick={() => handleRoleChange(member.id, "member")}
                          >
                            <Shield className="w-4 h-4 mr-2" />
                            Member로 변경
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="cursor-pointer"
                            disabled={member.role === "viewer"}
                            onClick={() => handleRoleChange(member.id, "viewer")}
                          >
                            <Eye className="w-4 h-4 mr-2" />
                            Viewer로 변경
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                        </>
                      )}
                      {isAdmin && (
                        <DropdownMenuItem
                          variant="destructive"
                          className="cursor-pointer"
                          onClick={() => handleRemove(member)}
                        >
                          멤버 제거
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 제거 확인 다이얼로그 */}
      <Dialog
        open={!!confirmRemove}
        onOpenChange={() => setConfirmRemove(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>멤버를 제거하시겠습니까?</DialogTitle>
            <DialogDescription>
              {confirmRemove?.displayName ?? confirmRemove?.email}님을
              워크스페이스에서 제거합니다. 이 작업은 되돌릴 수 없습니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setConfirmRemove(null)}
              className="cursor-pointer"
            >
              취소
            </Button>
            <Button
              variant="destructive"
              onClick={confirmRemoveMember}
              className="cursor-pointer"
            >
              제거
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
