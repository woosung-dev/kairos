import { apiClient } from "@/lib/api-client";
import type {
  Member,
  Invite,
  InviteInfo,
  CreateInviteRequest,
  UpdateMemberRoleRequest,
  AcceptInviteResponse,
} from "./types";

// --- Query Key Factory ---

export const memberKeys = {
  all: ["members"] as const,
  list: (wid: string) => [...memberKeys.all, "list", wid] as const,
};

export const inviteKeys = {
  all: ["invites"] as const,
  list: (wid: string) => [...inviteKeys.all, "list", wid] as const,
  info: (code: string) => [...inviteKeys.all, "info", code] as const,
};

// --- 멤버 API ---

export async function fetchMembers(
  token: string,
  wid: string
): Promise<Member[]> {
  return apiClient<Member[]>(`/workspaces/${wid}/members`, { token });
}

export async function updateMemberRole(
  token: string,
  wid: string,
  memberId: string,
  data: UpdateMemberRoleRequest
): Promise<Member> {
  return apiClient<Member>(`/workspaces/${wid}/members/${memberId}`, {
    token,
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function removeMember(
  token: string,
  wid: string,
  memberId: string
): Promise<void> {
  return apiClient<void>(`/workspaces/${wid}/members/${memberId}`, {
    token,
    method: "DELETE",
  });
}

// --- 초대 API ---

export async function fetchInvites(
  token: string,
  wid: string
): Promise<Invite[]> {
  return apiClient<Invite[]>(`/workspaces/${wid}/invites`, { token });
}

export async function createInvite(
  token: string,
  wid: string,
  data: CreateInviteRequest
): Promise<Invite> {
  return apiClient<Invite>(`/workspaces/${wid}/invites`, {
    token,
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deactivateInvite(
  token: string,
  wid: string,
  inviteId: string
): Promise<void> {
  return apiClient<void>(`/workspaces/${wid}/invites/${inviteId}`, {
    token,
    method: "DELETE",
  });
}

// --- 공개 초대 API ---

export async function fetchInviteInfo(code: string): Promise<InviteInfo> {
  return apiClient<InviteInfo>(`/invites/${code}`);
}

export async function acceptInvite(
  token: string,
  code: string
): Promise<AcceptInviteResponse> {
  return apiClient<AcceptInviteResponse>(`/invites/${code}/accept`, {
    token,
    method: "POST",
  });
}
