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
      // 목록만 무효화한다. noteKeys.all 로 무효화하면 방금 삭제한 노트의 detail 키까지 걸려서,
      // 아직 마운트돼 있는 상세 화면의 useNote 가 삭제된 리소스를 재조회해 404 를 낸다.
      if (wid) queryClient.invalidateQueries({ queryKey: [...noteKeys.all, "list"] });
    },
  });
}
