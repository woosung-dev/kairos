import { apiClient, API_BASE_URL } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type { Note, CreateNoteRequest, UpdateNoteRequest } from "./types";

export const noteKeys = {
  all: ["notes"] as const,
  list: (wid: string, projectId?: string) =>
    [...noteKeys.all, "list", wid, projectId ?? "all"] as const,
  detail: (wid: string, id: string) =>
    [...noteKeys.all, "detail", wid, id] as const,
};

export async function fetchNotes(
  token: string,
  wid: string,
  projectId?: string,
  page?: number,
): Promise<PaginatedResponse<Note>> {
  const params = new URLSearchParams();
  if (projectId) params.set("projectId", projectId);
  if (page) params.set("page", String(page));
  const query = params.toString();
  return apiClient<PaginatedResponse<Note>>(
    `/workspaces/${wid}/notes${query ? `?${query}` : ""}`,
    { token },
  );
}

export async function fetchNote(
  token: string,
  wid: string,
  id: string,
): Promise<Note> {
  return apiClient<Note>(`/workspaces/${wid}/notes/${id}`, { token });
}

export async function createNote(
  token: string,
  wid: string,
  data: CreateNoteRequest,
): Promise<Note> {
  return apiClient<Note>(`/workspaces/${wid}/notes`, {
    token,
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateNote(
  token: string,
  wid: string,
  id: string,
  data: UpdateNoteRequest,
): Promise<Note> {
  return apiClient<Note>(`/workspaces/${wid}/notes/${id}`, {
    token,
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function exportNote(
  token: string,
  wid: string,
  id: string,
  format: "md" | "json"
): Promise<Blob> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/workspaces/${wid}/notes/${id}/export?format=${format}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) throw new Error("내보내기에 실패했습니다");
  return res.blob();
}

export async function deleteNote(
  token: string,
  wid: string,
  id: string,
): Promise<void> {
  return apiClient<void>(`/workspaces/${wid}/notes/${id}`, {
    token,
    method: "DELETE",
  });
}
