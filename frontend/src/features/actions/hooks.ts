"use client";

import { useAuth } from "@clerk/nextjs";
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
  const { getToken } = useAuth();

  return useQuery({
    queryKey: actionKeys.list(wid ?? ""),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchActionItems(token, wid!, params);
    },
    enabled: !!wid,
  });
}

/**
 * 액션 아이템 생성
 */
export function useCreateActionItem(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateActionItemRequest) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return createActionItem(token, wid!, data);
    },
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
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateActionItemRequest }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return updateActionItem(token, wid!, id, data);
    },
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: actionKeys.list(wid) });
      }
    },
  });
}
