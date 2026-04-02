import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type { ActionItem } from "./types";

// --- Query Key Factory ---

export const actionKeys = {
  all: ["actions"] as const,
  list: (wid: string) => [...actionKeys.all, "list", wid] as const,
};

// --- API 함수 ---

export interface FetchActionItemsParams {
  status?: string;
  priority?: string;
  projectId?: string;
  page?: number;
  pageSize?: number;
}

export interface CreateActionItemRequest {
  title: string;
  description?: string | null;
  priority?: "high" | "medium" | "low";
  status?: "todo" | "in_progress" | "done" | "cancelled";
  dueDate?: string | null;
  assigneeId?: string | null;
  meetingId?: string | null;
  projectId?: string | null;
}

export interface UpdateActionItemRequest {
  title?: string;
  description?: string | null;
  priority?: "high" | "medium" | "low";
  status?: "todo" | "in_progress" | "done" | "cancelled";
  dueDate?: string | null;
  assigneeId?: string | null;
  projectId?: string | null;
}

export async function fetchActionItems(
  token: string,
  wid: string,
  params?: FetchActionItemsParams
): Promise<PaginatedResponse<ActionItem>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.priority) searchParams.set("priority", params.priority);
  if (params?.projectId) searchParams.set("project_id", params.projectId);
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.pageSize) searchParams.set("page_size", String(params.pageSize));

  const query = searchParams.toString();
  const path = `/workspaces/${wid}/action-items${query ? `?${query}` : ""}`;

  return apiClient<PaginatedResponse<ActionItem>>(path, { token });
}

export async function createActionItem(
  token: string,
  wid: string,
  data: CreateActionItemRequest
): Promise<ActionItem> {
  return apiClient<ActionItem>(`/workspaces/${wid}/action-items`, {
    token,
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateActionItem(
  token: string,
  wid: string,
  id: string,
  data: UpdateActionItemRequest
): Promise<ActionItem> {
  return apiClient<ActionItem>(`/workspaces/${wid}/action-items/${id}`, {
    token,
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
