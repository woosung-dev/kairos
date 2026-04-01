"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { workspaceKeys, fetchWorkspaces, createWorkspace } from "./api";
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
