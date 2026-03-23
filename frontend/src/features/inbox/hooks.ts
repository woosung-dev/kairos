import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { inboxKeys, fetchInboxItems, classifyInboxItem, dismissInboxItem } from "./api";
import type { UUID } from "@/types";

export function useInboxItems(workspaceId: string) {
  return useQuery({
    queryKey: inboxKeys.list(workspaceId),
    queryFn: () => fetchInboxItems(workspaceId),
  });
}

export function useClassifyInboxItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: classifyInboxItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inboxKeys.all });
    },
  });
}

export function useDismissInboxItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (inboxItemId: UUID) => dismissInboxItem(inboxItemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inboxKeys.all });
    },
  });
}
