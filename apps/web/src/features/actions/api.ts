import type { ApiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type { ActionItem } from "./types";

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
  api: ApiClient,
  wid: string,
  params?: FetchActionItemsParams
): Promise<PaginatedResponse<ActionItem>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.priority) searchParams.set("priority", params.priority);
  // BE 는 camelCase alias(`projectId`/`pageSize`)만 받는다 — snake_case 는 무시돼 필터가 통째로 빠졌다
  // (프로젝트 대시보드 "이번 주 액션" 이 워크스페이스 전체 액션을 보여주던 원인).
  if (params?.projectId) searchParams.set("projectId", params.projectId);
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.pageSize) searchParams.set("pageSize", String(params.pageSize));

  const query = searchParams.toString();
  const path = `/workspaces/${wid}/action-items${query ? `?${query}` : ""}`;

  return api.fetch<PaginatedResponse<ActionItem>>(path);
}

export async function createActionItem(
  api: ApiClient,
  wid: string,
  data: CreateActionItemRequest
): Promise<ActionItem> {
  return api.fetch<ActionItem>(`/workspaces/${wid}/action-items`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateActionItem(
  api: ApiClient,
  wid: string,
  id: string,
  data: UpdateActionItemRequest
): Promise<ActionItem> {
  return api.fetch<ActionItem>(`/workspaces/${wid}/action-items/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
