import type { ApiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type { Note, CreateNoteRequest, UpdateNoteRequest } from "./types";


export async function fetchNotes(
  api: ApiClient,
  wid: string,
  projectId?: string,
  page?: number,
): Promise<PaginatedResponse<Note>> {
  const params = new URLSearchParams();
  if (projectId) params.set("projectId", projectId);
  if (page) params.set("page", String(page));
  const query = params.toString();
  return api.fetch<PaginatedResponse<Note>>(
    `/workspaces/${wid}/notes${query ? `?${query}` : ""}`,
  );
}

export async function fetchNote(
  api: ApiClient,
  wid: string,
  id: string,
): Promise<Note> {
  return api.fetch<Note>(`/workspaces/${wid}/notes/${id}`);
}

export async function createNote(
  api: ApiClient,
  wid: string,
  data: CreateNoteRequest,
): Promise<Note> {
  return api.fetch<Note>(`/workspaces/${wid}/notes`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateNote(
  api: ApiClient,
  wid: string,
  id: string,
  data: UpdateNoteRequest,
): Promise<Note> {
  return api.fetch<Note>(`/workspaces/${wid}/notes/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function exportNote(
  api: ApiClient,
  wid: string,
  id: string,
  format: "md" | "json"
): Promise<Blob> {
  const res = await api.fetchRaw(
    `/workspaces/${wid}/notes/${id}/export?format=${format}`,
  );
  if (!res.ok) throw new Error("내보내기에 실패했습니다");
  return res.blob();
}

export async function deleteNote(
  api: ApiClient,
  wid: string,
  id: string,
): Promise<void> {
  return api.fetch<void>(`/workspaces/${wid}/notes/${id}`, {
    method: "DELETE",
  });
}

// ── Sprint 24 BL-064: embedding-status polling ──

export type EmbeddingStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "n/a";

export interface EmbeddingStatusOut {
  status: EmbeddingStatus;
  chunkCount: number;
}

/**
 * Sprint 24 BL-064 — promoted note 의 embedding 진행 상태 polling.
 *
 * BE 응답은 camelCase (`chunkCount`) — NEW endpoint 이므로 modal snake_case
 * 호환성 제약 무관 (기존 promote 응답만 snake_case 보존).
 */
export async function getEmbeddingStatus(
  api: ApiClient,
  workspaceId: string,
  noteId: string,
): Promise<EmbeddingStatusOut> {
  return api.fetch<EmbeddingStatusOut>(
    `/workspaces/${workspaceId}/notes/${noteId}/embedding-status`,
  );
}
