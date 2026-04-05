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
import { toast } from "sonner";
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
      toast.success("노트가 생성되었습니다");
      if (wid) queryClient.invalidateQueries({ queryKey: noteKeys.all });
    },
    onError: (error: Error) => {
      toast.error(error.message || "노트 생성에 실패했습니다");
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
    onError: (error: Error) => {
      toast.error(error.message || "노트 수정에 실패했습니다");
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
      toast.success("노트가 삭제되었습니다");
      if (wid) queryClient.invalidateQueries({ queryKey: noteKeys.all });
    },
    onError: (error: Error) => {
      toast.error(error.message || "노트 삭제에 실패했습니다");
    },
  });
}
