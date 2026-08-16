import type { UUID } from "@/types";
import type { ProjectVisibility } from "@/features/projects/types";

export type WorkspaceRole = "owner" | "admin" | "member" | "viewer";

export interface Member {
  id: UUID;
  /**
   * 내부 사용자 UUID (users.id). 권한/소유권 판정의 유일한 축이다.
   * ADR-031: 외부 인증 공급자 ID(구 `clerkId`)는 응답에서 제거했다 —
   * FE 권한 판정이 벤더 ID 에 문자열 매칭으로 묶여 있던 것이 전환에서 터진 지점이다.
   */
  userId: UUID;
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
