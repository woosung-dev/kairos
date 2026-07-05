"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  workspaceKeys,
  fetchWorkspaces,
  createWorkspace,
  fetchWorkspace,
  updateWorkspaceSettings,
  deleteWorkspace,
} from "./api";
import type { Workspace } from "./types";

export function useWorkspaces() {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: workspaceKeys.list(),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchWorkspaces(token);
    },
    // 권한 표면 — 전역 focus refetch off 에서 예외 (ws 삭제/가입 반영 지연 방지)
    refetchOnWindowFocus: true,
  });
}

export function useCreateWorkspace() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (name: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return createWorkspace(token, name);
    },
    onSuccess: (newWorkspace: Workspace) => {
      queryClient.setQueryData<Workspace[]>(
        workspaceKeys.list(),
        (old) => (old ? [...old, newWorkspace] : [newWorkspace])
      );
    },
    onError: (error: Error) => {
      toast.error(error.message || "워크스페이스 생성에 실패했습니다");
    },
  });
}

export function useWorkspace(wid: string | undefined) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: workspaceKeys.detail(wid ?? ""),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchWorkspace(token, wid!);
    },
    enabled: !!wid,
  });
}

export function useDeleteWorkspace() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (wid: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      await deleteWorkspace(token, wid);
      return wid;
    },
    onSuccess: (wid: string) => {
      queryClient.setQueryData<Workspace[]>(workspaceKeys.list(), (old) =>
        old ? old.filter((ws) => ws.id !== wid) : old
      );
      queryClient.removeQueries({ queryKey: workspaceKeys.detail(wid) });
      toast.success("워크스페이스가 삭제되었습니다");
    },
    onError: (error: Error) => {
      toast.error(error.message || "워크스페이스 삭제에 실패했습니다");
    },
  });
}

export function useUpdateWorkspaceSettings(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { inbox_threshold: number }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return updateWorkspaceSettings(token, wid!, data);
    },
    onSuccess: (result) => {
      toast.success(
        `임계값이 ${Math.round(result.inboxThreshold * 100)}%로 변경되었습니다`
      );
      if (wid) {
        queryClient.invalidateQueries({ queryKey: workspaceKeys.detail(wid) });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "설정 변경에 실패했습니다");
    },
  });
}
