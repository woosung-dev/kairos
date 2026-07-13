import { apiClient, type ApiClient } from "@/lib/api-client";
import type {
  Member,
  Invite,
  InviteInfo,
  CreateInviteRequest,
  UpdateMemberRoleRequest,
  AcceptInviteResponse,
} from "./types";

// --- 멤버 API ---

export async function fetchMembers(
  api: ApiClient,
  wid: string
): Promise<Member[]> {
  return api.fetch<Member[]>(`/workspaces/${wid}/members`);
}

export async function updateMemberRole(
  api: ApiClient,
  wid: string,
  memberId: string,
  data: UpdateMemberRoleRequest
): Promise<Member> {
  return api.fetch<Member>(`/workspaces/${wid}/members/${memberId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function removeMember(
  api: ApiClient,
  wid: string,
  memberId: string
): Promise<void> {
  return api.fetch<void>(`/workspaces/${wid}/members/${memberId}`, {
    method: "DELETE",
  });
}

// --- 초대 API ---

export async function fetchInvites(
  api: ApiClient,
  wid: string
): Promise<Invite[]> {
  return api.fetch<Invite[]>(`/workspaces/${wid}/invites`);
}

export async function createInvite(
  api: ApiClient,
  wid: string,
  data: CreateInviteRequest
): Promise<Invite> {
  return api.fetch<Invite>(`/workspaces/${wid}/invites`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deactivateInvite(
  api: ApiClient,
  wid: string,
  inviteId: string
): Promise<void> {
  return api.fetch<void>(`/workspaces/${wid}/invites/${inviteId}`, {
    method: "DELETE",
  });
}

// --- 공개 초대 API ---

// 공개 엔드포인트 — 비로그인 사용자도 초대 정보를 조회하므로 무토큰 apiClient 유지.
export async function fetchInviteInfo(code: string): Promise<InviteInfo> {
  return apiClient<InviteInfo>(`/invites/${code}`);
}

export async function acceptInvite(
  api: ApiClient,
  code: string
): Promise<AcceptInviteResponse> {
  return api.fetch<AcceptInviteResponse>(`/invites/${code}/accept`, {
    method: "POST",
  });
}
