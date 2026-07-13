import type { ApiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type { InboxItem } from "./types";

// --- Query Key Factory ---

// Sprint 23 D3 fix: queryKey 에 params 포함 → cache 격리.
// 이전: useInbox(wid) 와 useInbox(wid, { isProcessed: false }) 가 같은 cache 사용 → 마지막 호출자의 params 가 실 fetch 결정 → 다른 callsite 의 의도 손상.
// 이후: 각 (wid, params) 조합이 별도 cache entry. invalidate 시 inboxKeys.byWorkspace(wid) prefix 로 일괄 무효화.
export const inboxKeys = {
  all: ["inbox"] as const,
  byWorkspace: (wid: string) => [...inboxKeys.all, "list", wid] as const,
  list: (wid: string, params?: FetchInboxParams) =>
    [...inboxKeys.byWorkspace(wid), params ?? {}] as const,
};

// --- API 함수 ---

export interface FetchInboxParams {
  isProcessed?: boolean;
  page?: number;
  pageSize?: number;
}

export async function fetchInbox(
  api: ApiClient,
  wid: string,
  params?: FetchInboxParams
): Promise<PaginatedResponse<InboxItem>> {
  const searchParams = new URLSearchParams();
  // Sprint 23 Codex 2.5차 P2 fix: BE router.py L22 가 alias="isProcessed" 강제 — snake_case
  // query param 무시 → all items 반환 → smart-inbox UX regression. FE camelCase 전송으로
  // 정합 (헌법 I-16 API camelCase). page_size 도 alias="pageSize" 정합 (BE router L24).
  if (params?.isProcessed !== undefined)
    searchParams.set("isProcessed", String(params.isProcessed));
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.pageSize) searchParams.set("pageSize", String(params.pageSize));

  const query = searchParams.toString();
  const path = `/workspaces/${wid}/inbox${query ? `?${query}` : ""}`;

  return api.fetch<PaginatedResponse<InboxItem>>(path);
}

/**
 * Inbox 항목을 프로젝트에 분류 확정
 */
export async function classifyInboxItem(
  api: ApiClient,
  wid: string,
  id: string,
  projectIds: string[]
): Promise<InboxItem> {
  return api.fetch<InboxItem>(`/workspaces/${wid}/inbox/${id}/classify`, {
    method: "POST",
    body: JSON.stringify({ projectIds }),
  });
}

/**
 * Inbox 항목 무시 (dismiss)
 */
export async function dismissInboxItem(
  api: ApiClient,
  wid: string,
  id: string
): Promise<void> {
  return api.fetch<void>(`/workspaces/${wid}/inbox/${id}/dismiss`, {
    method: "POST",
  });
}
