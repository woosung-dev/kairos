import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  paraKeys,
  fetchParaItems,
  fetchParaItem,
  createParaItem,
  updateParaItem,
  archiveParaItem,
} from "./api";
import type { ParaCategory } from "@/types/para";
import type { UUID } from "@/types";

export function useParaItems(workspaceId: string, category?: ParaCategory) {
  return useQuery({
    queryKey: category
      ? paraKeys.byCategory(workspaceId, category)
      : paraKeys.list(workspaceId),
    queryFn: () => fetchParaItems(workspaceId, category),
  });
}

export function useParaItem(id: UUID) {
  return useQuery({
    queryKey: paraKeys.detail(id),
    queryFn: () => fetchParaItem(id),
    enabled: !!id,
  });
}

export function useCreateParaItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createParaItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paraKeys.all });
    },
  });
}

export function useUpdateParaItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateParaItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paraKeys.all });
    },
  });
}

export function useArchiveParaItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: UUID) => archiveParaItem(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paraKeys.all });
    },
  });
}
