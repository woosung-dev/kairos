"use client";

import { workspaceKeys } from "@/lib/query-keys";
import { useApiClient } from "@/lib/use-api-client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
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

export function useWorkspaceIdGuard(wid: string | undefined) {
  const {
    data: workspaces,
    error: workspaceListError,
    isPending: isWorkspaceListPending,
  } = useWorkspaces();

  return {
    isValidWorkspaceId: !!wid && !!workspaces?.some((workspace) => workspace.id === wid),
    isWorkspaceListPending,
    // 이미 받은 목록은 wid 가드의 근거로 유효하다. 그 뒤 background refetch 실패는
    // 의존 쿼리를 막지 않으므로 그 쿼리의 오류로 전파하지 않는다.
    workspaceListError: workspaces === undefined ? workspaceListError : null,
  };
}

export function useIsValidWorkspaceId(wid: string | undefined) {
  return useWorkspaceIdGuard(wid).isValidWorkspaceId;
}

export function withWorkspaceGuardLoading<T extends { isLoading: boolean }>(
  query: T,
  isWorkspaceListPending: boolean,
  workspaceListError: Error | null = null,
): T {
  if (!isWorkspaceListPending && !workspaceListError) return query;

  return new Proxy(query, {
    get: (target, key, receiver) => {
      if (workspaceListError) {
        if (key === "error") return workspaceListError;
        if (key === "isError") return true;
        if (key === "status") return "error";
        if (key === "isSuccess" || key === "isPending" || key === "isLoading") return false;
      }
      if (key === "isLoading" && isWorkspaceListPending) return true;
      return Reflect.get(target, key, receiver);
    },
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
