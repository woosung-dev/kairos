import type { ApiClient } from "@/lib/api-client";
import type { Workspace } from "./types";


export async function fetchWorkspaces(api: ApiClient): Promise<Workspace[]> {
  return api.fetch<Workspace[]>("/workspaces");
}

export async function createWorkspace(
  api: ApiClient,
  name: string
): Promise<Workspace> {
  return api.fetch<Workspace>("/workspaces", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function fetchWorkspace(
  api: ApiClient,
  wid: string
): Promise<{
  id: string;
  name: string;
  type?: "personal" | "team";
  inboxThreshold: number;
  memberCount: number;
}> {
  return api.fetch(`/workspaces/${wid}`);
}

export async function deleteWorkspace(
  api: ApiClient,
  wid: string
): Promise<void> {
  return api.fetch<void>(`/workspaces/${wid}`, {
    method: "DELETE",
  });
}

// PATCH settings 는 부분 갱신 — 바꾸려는 필드만 보낸다 (BE alias 가 camelCase).
export interface UpdateWorkspaceSettingsInput {
  inboxThreshold?: number;
  name?: string;
}

export async function updateWorkspaceSettings(
  api: ApiClient,
  wid: string,
  data: UpdateWorkspaceSettingsInput
): Promise<{ inboxThreshold: number; name: string }> {
  return api.fetch(`/workspaces/${wid}/settings`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
