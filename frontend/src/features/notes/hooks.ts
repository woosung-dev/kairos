"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  noteKeys,
  fetchNotes,
  fetchNote,
  createNote,
  updateNote,
  deleteNote,
} from "./api";
import type { CreateNoteRequest, UpdateNoteRequest } from "./types";

export function useNotes(wid: string | undefined, projectId?: string) {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: noteKeys.list(wid ?? "", projectId),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchNotes(token, wid!, projectId);
    },
    enabled: !!wid,
  });
}

export function useNote(wid: string | undefined, id: string) {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: noteKeys.detail(wid ?? "", id),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchNote(token, wid!, id);
    },
    enabled: !!wid && !!id,
  });
}

export function useCreateNote(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateNoteRequest) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return createNote(token, wid!, data);
    },
    onSuccess: () => {
      if (wid) queryClient.invalidateQueries({ queryKey: noteKeys.all });
    },
  });
}

export function useUpdateNote(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateNoteRequest }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return updateNote(token, wid!, id, data);
    },
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
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return deleteNote(token, wid!, id);
    },
    onSuccess: () => {
      if (wid) queryClient.invalidateQueries({ queryKey: noteKeys.all });
    },
  });
}
