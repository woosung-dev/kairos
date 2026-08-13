import type { UUID } from "@/types";
import type { ProjectVisibility } from "@/features/projects/types";

export type WorkspaceRole = "owner" | "admin" | "member" | "viewer";

export interface Member {
  id: UUID;
  userId: UUID;
  clerkId: string | null;
  email: string | null;
  displayName: string | null;
  role: WorkspaceRole;
}

export interface UpdateMemberRoleRequest {
  role: Exclude<WorkspaceRole, "owner">;
}

// --- 초대 링크 ---

export interface Invite {
  id: UUID;
  workspaceId: UUID;
  code: string;
  role: Exclude<WorkspaceRole, "owner">;
  defaultProjectVisibility: ProjectVisibility;
  inviteUrl: string;
  maxUses: number | null;
  useCount: number;
  expiresAt: string | null;
  isActive: boolean;
  createdAt: string;
}

export interface CreateInviteRequest {
  role?: Exclude<WorkspaceRole, "owner">;
  defaultProjectVisibility?: ProjectVisibility;
  maxUses?: number | null;
  expiresInDays?: number | null;
}

export interface InviteInfo {
  workspaceName: string;
  inviterName: string | null;
  role: string;
  isValid: boolean;
  reason: string | null;
}

export interface AcceptInviteResponse {
  workspaceId: UUID;
  memberId: UUID;
  role: WorkspaceRole;
}
