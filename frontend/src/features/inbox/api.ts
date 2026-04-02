import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type { InboxItem } from "./types";

// --- Query Key Factory ---

export const inboxKeys = {
  all: ["inbox"] as const,
  list: (wid: string) => [...inboxKeys.all, "list", wid] as const,
};

// --- API 함수 ---

export interface FetchInboxParams {
  isProcessed?: boolean;
  page?: number;
  pageSize?: number;
}

export async function fetchInbox(
  token: string,
  wid: string,
  params?: FetchInboxParams
): Promise<PaginatedResponse<InboxItem>> {
  const searchParams = new URLSearchParams();
  if (params?.isProcessed !== undefined)
    searchParams.set("is_processed", String(params.isProcessed));
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.pageSize) searchParams.set("page_size", String(params.pageSize));

  const query = searchParams.toString();
  const path = `/workspaces/${wid}/inbox${query ? `?${query}` : ""}`;

  return apiClient<PaginatedResponse<InboxItem>>(path, { token });
}

/**
 * Inbox 항목을 프로젝트에 분류 확정
 */
export async function classifyInboxItem(
  token: string,
  wid: string,
  id: string,
  projectIds: string[]
): Promise<InboxItem> {
  return apiClient<InboxItem>(`/workspaces/${wid}/inbox/${id}/classify`, {
    token,
    method: "POST",
    body: JSON.stringify({ projectIds }),
  });
}

/**
 * Inbox 항목 무시 (dismiss)
 */
export async function dismissInboxItem(
  token: string,
  wid: string,
  id: string
): Promise<void> {
  return apiClient<void>(`/workspaces/${wid}/inbox/${id}/dismiss`, {
    token,
    method: "POST",
  });
}
