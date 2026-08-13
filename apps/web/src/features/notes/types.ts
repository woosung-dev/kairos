import type { UUID, Timestamped } from "@/types";

export interface Note extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  projectId: UUID | null;
  title: string;
  content: Record<string, unknown>;
  plainText: string;
  createdById: UUID;
}

export interface CreateNoteRequest {
  title?: string;
  content?: Record<string, unknown>;
  projectId?: string | null;
}

export interface UpdateNoteRequest {
  title?: string;
  content?: Record<string, unknown>;
  projectId?: string | null;
}
