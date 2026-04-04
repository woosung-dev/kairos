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
