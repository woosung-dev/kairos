"use client";

import { useApiClient } from "@/lib/use-api-client";
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
  const api = useApiClient();

  return useQuery({
    queryKey: workspaceKeys.list(),
    queryFn: () => fetchWorkspaces(api),
    // 권한 표면 — 전역 focus refetch off 에서 예외 (ws 삭제/가입 반영 지연 방지)
    refetchOnWindowFocus: true,
  });
}

export function useCreateWorkspace() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => createWorkspace(api, name),
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
  const api = useApiClient();

  return useQuery({
    queryKey: workspaceKeys.detail(wid ?? ""),
    queryFn: () => fetchWorkspace(api, wid!),
    enabled: !!wid,
  });
}

export function useDeleteWorkspace() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (wid: string) => {
      await deleteWorkspace(api, wid);
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
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { inbox_threshold: number }) => updateWorkspaceSettings(api, wid!, data),
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
