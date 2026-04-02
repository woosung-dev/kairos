"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  inboxKeys,
  fetchInbox,
  classifyInboxItem,
  dismissInboxItem,
} from "./api";
import type { FetchInboxParams } from "./api";

/**
 * 워크스페이스 내 Inbox 목록 조회
 */
export function useInbox(wid: string | undefined, params?: FetchInboxParams) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: inboxKeys.list(wid ?? ""),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchInbox(token, wid!, params);
    },
    enabled: !!wid,
  });
}

/**
 * Inbox 항목 분류 확정
 */
export function useClassifyInbox(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      projectIds,
    }: {
      id: string;
      projectIds: string[];
    }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return classifyInboxItem(token, wid!, id, projectIds);
    },
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: inboxKeys.list(wid) });
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
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return dismissInboxItem(token, wid!, id);
    },
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: inboxKeys.list(wid) });
      }
      toast("항목을 무시했습니다");
    },
    onError: (error: Error) => {
      toast.error(error.message || "처리에 실패했습니다");
    },
  });
}
