"use client";

import { useApiClient } from "@/lib/use-api-client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  actionKeys,
  fetchActionItems,
  createActionItem,
  updateActionItem,
} from "./api";
import type { FetchActionItemsParams, CreateActionItemRequest, UpdateActionItemRequest } from "./api";

/**
 * 워크스페이스 내 액션 아이템 목록 조회
 */
export function useActionItems(wid: string | undefined, params?: FetchActionItemsParams) {
  const api = useApiClient();

  return useQuery({
    queryKey: actionKeys.list(wid ?? ""),
    queryFn: () => fetchActionItems(api, wid!, params),
    enabled: !!wid,
  });
}

/**
 * 액션 아이템 생성
 */
export function useCreateActionItem(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateActionItemRequest) => createActionItem(api, wid!, data),
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: actionKeys.list(wid) });
      }
    },
  });
}

/**
 * 액션 아이템 수정
 */
export function useUpdateActionItem(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateActionItemRequest }) => updateActionItem(api, wid!, id, data),
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: actionKeys.list(wid) });
      }
    },
  });
}
