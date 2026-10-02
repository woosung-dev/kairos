"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useMe } from "@/features/auth/hooks";
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
  type UpdateWorkspaceSettingsInput,
} from "./api";
import { useWorkspaceStore } from "./store";
import type { Workspace } from "./types";
import { invalidateWorkspaceScopedQueries, resolveWorkspaceDeepLink } from "./utils";

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
    mutationFn: (data: UpdateWorkspaceSettingsInput) =>
      updateWorkspaceSettings(api, wid!, data),
    onSuccess: (result, variables) => {
      if (variables.name !== undefined) {
        toast.success("워크스페이스 이름이 변경되었습니다");
      } else {
        toast.success(
          `임계값이 ${Math.round(result.inboxThreshold * 100)}%로 변경되었습니다`
        );
      }
      if (wid) {
        queryClient.invalidateQueries({ queryKey: workspaceKeys.detail(wid) });
      }
      // 헤더 WorkspaceSwitcher 는 목록 쿼리를 읽는다 — 이름 변경이 거기에도 바로 보여야 한다.
      queryClient.invalidateQueries({ queryKey: workspaceKeys.list() });
    },
    onError: (error: Error) => {
      toast.error(error.message || "설정 변경에 실패했습니다");
    },
  });
}

/**
 * 알림 딥링크 워크스페이스 전환 (docs/requirements/pwa.md §5.5, 게이트 ⑥) — 회의 상세가 마운트한다.
 * `?workspace=<wid>` 를 1회 처리하고 `router.replace("/meetings/<mid>")` 로 파라미터를 지운다.
 *
 * - 전환 = store 소유자가 me 면 `setActiveWorkspaceId`, 아니면 `activateWorkspaceForUser` (C-001)
 *   → WorkspaceSwitcher 와 같은 predicate 로 무효화 → toast 1회. ref 가드로 재렌더·목록 refetch 에도 1회.
 * - `queryClient.clear()`·`router.refresh()` 를 쓰지 않는다 (Sprint 23 D1). `replace` 라 히스토리 추가 0.
 * - `isSettled=false` 동안 상세 쿼리를 보내지 않는다 — 옛 활성 ws 로 오류 블록이 한 번 그려지는 깜빡임 방지.
 */
export function useWorkspaceDeepLink(
  meetingId: string,
  workspaceParam: string | null,
): { isSettled: boolean } {
  const { data: workspaces, isPending: isWorkspaceListPending } = useWorkspaces();
  const { data: me } = useMe();
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const ownerUserId = useWorkspaceStore((s) => s.ownerUserId);
  const setActiveWorkspaceId = useWorkspaceStore((s) => s.setActiveWorkspaceId);
  const activateWorkspaceForUser = useWorkspaceStore((s) => s.activateWorkspaceForUser);
  const queryClient = useQueryClient();
  const router = useRouter();
  const handledParamRef = useRef<string | null>(null);
  const meId = me?.id;

  const decision = resolveWorkspaceDeepLink({
    workspaceParam,
    workspaces,
    isWorkspaceListPending,
    meId,
    activeWorkspaceId,
  });
  const decisionType = decision.type;
  const targetWorkspaceId = decision.type === "switch" ? decision.workspaceId : null;
  const targetWorkspaceName = decision.type === "switch" ? decision.workspaceName : null;

  useEffect(() => {
    if (workspaceParam === null || decisionType === "none" || decisionType === "wait") return;
    if (handledParamRef.current === workspaceParam) return;
    handledParamRef.current = workspaceParam;

    if (decisionType === "switch" && targetWorkspaceId && meId) {
      if (ownerUserId === meId) {
        setActiveWorkspaceId(targetWorkspaceId);
      } else {
        activateWorkspaceForUser(meId, targetWorkspaceId);
      }
      invalidateWorkspaceScopedQueries(queryClient);
      toast(`“${targetWorkspaceName}” 워크스페이스로 전환했습니다`);
    }
    router.replace(`/meetings/${meetingId}`);
  }, [
    workspaceParam,
    decisionType,
    targetWorkspaceId,
    targetWorkspaceName,
    meId,
    ownerUserId,
    meetingId,
    setActiveWorkspaceId,
    activateWorkspaceForUser,
    queryClient,
    router,
  ]);

  return { isSettled: decisionType === "none" || decisionType === "strip" };
}
