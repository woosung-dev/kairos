"use client";

import { inboxKeys } from "@/lib/query-keys";
import { useApiClient } from "@/lib/use-api-client";
import {
  useWorkspaceIdGuard,
  withWorkspaceGuardLoading,
} from "@/features/workspaces/hooks";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  fetchInbox,
  classifyInboxItem,
  dismissInboxItem,
} from "./api";
import type { FetchInboxParams } from "./api";

/**
 * 워크스페이스 내 Inbox 목록 조회
 */
export function useInbox(wid: string | undefined, params?: FetchInboxParams) {
  const api = useApiClient();
  const { isValidWorkspaceId, isWorkspaceListPending, workspaceListError } =
    useWorkspaceIdGuard(wid);

  const query = useQuery({
    // Sprint 23 D3 fix: queryKey 에 params 포함 → 각 callsite 의 의도 분리.
    queryKey: inboxKeys.list(wid ?? "", params),
    queryFn: () => fetchInbox(api, wid!, params),
    enabled: !!wid && isValidWorkspaceId,
  });

  return withWorkspaceGuardLoading(query, isWorkspaceListPending, workspaceListError);
}

/**
 * Inbox 항목 분류 확정
 */
export function useClassifyInbox(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      projectIds,
    }: {
      id: string;
      projectIds: string[];
    }) => classifyInboxItem(api, wid!, id, projectIds),
    onSuccess: () => {
      if (wid) {
        // Sprint 23 D3 fix: byWorkspace prefix 로 모든 params 의 cache 일괄 무효화.
        queryClient.invalidateQueries({ queryKey: inboxKeys.byWorkspace(wid) });
      }
      toast.success("프로젝트에 연결되었습니다");
    },
    onError: (error: Error) => {
      toast.error(error.message || "분류에 실패했습니다");
    },
  });
}

/**
 * Inbox 항목 무시 (dismiss)
 */
export function useDismissInbox(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => dismissInboxItem(api, wid!, id),
    onSuccess: () => {
      if (wid) {
        // Sprint 23 D3 fix: byWorkspace prefix 로 모든 params 의 cache 일괄 무효화.
        queryClient.invalidateQueries({ queryKey: inboxKeys.byWorkspace(wid) });
      }
      toast("항목을 무시했습니다");
    },
    onError: (error: Error) => {
      toast.error(error.message || "처리에 실패했습니다");
    },
  });
}
