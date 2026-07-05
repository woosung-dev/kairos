import { apiClient } from "@/lib/api-client";
import type { Workspace } from "./types";

export const workspaceKeys = {
  all: ["workspaces"] as const,
  list: () => [...workspaceKeys.all, "list"] as const,
  detail: (id: string) => [...workspaceKeys.all, "detail", id] as const,
};

export async function fetchWorkspaces(token: string): Promise<Workspace[]> {
  return apiClient<Workspace[]>("/workspaces", { token });
}

export async function createWorkspace(
  token: string,
  name: string
): Promise<Workspace> {
  return apiClient<Workspace>("/workspaces", {
    token,
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function fetchWorkspace(
  token: string,
  wid: string
): Promise<{
  id: string;
  name: string;
  type?: "personal" | "team";
  inboxThreshold: number;
  memberCount: number;
}> {
  return apiClient(`/workspaces/${wid}`, { token });
}

export async function deleteWorkspace(
  token: string,
  wid: string
): Promise<void> {
  return apiClient<void>(`/workspaces/${wid}`, {
    token,
    method: "DELETE",
  });
}

export async function updateWorkspaceSettings(
  token: string,
  wid: string,
  data: { inbox_threshold: number }
): Promise<{ inboxThreshold: number }> {
  return apiClient(`/workspaces/${wid}/settings`, {
    token,
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
