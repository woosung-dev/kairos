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
