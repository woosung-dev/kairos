"use client";

import { noteKeys } from "@/lib/query-keys";
import { useApiClient } from "@/lib/use-api-client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchNotes,
  fetchNote,
  createNote,
  updateNote,
  deleteNote,
} from "./api";
import type { CreateNoteRequest, UpdateNoteRequest } from "./types";

export function useNotes(wid: string | undefined, projectId?: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: noteKeys.list(wid ?? "", projectId),
    queryFn: () => fetchNotes(api, wid!, projectId),
    enabled: !!wid,
  });
}

export function useNote(wid: string | undefined, id: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: noteKeys.detail(wid ?? "", id),
    queryFn: () => fetchNote(api, wid!, id),
    enabled: !!wid && !!id,
  });
}

export function useCreateNote(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateNoteRequest) => createNote(api, wid!, data),
    onSuccess: () => {
      if (wid) queryClient.invalidateQueries({ queryKey: noteKeys.all });
    },
  });
}

export function useUpdateNote(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateNoteRequest }) => updateNote(api, wid!, id, data),
    onSuccess: (_data, variables) => {
      if (wid) {
        queryClient.invalidateQueries({
          queryKey: noteKeys.detail(wid, variables.id),
        });
        queryClient.invalidateQueries({ queryKey: noteKeys.all });
      }
    },
  });
}

export function useDeleteNote(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteNote(api, wid!, id),
    onSuccess: () => {
      if (wid) queryClient.invalidateQueries({ queryKey: noteKeys.all });
    },
  });
}
