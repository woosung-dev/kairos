import type { UUID, Timestamped } from "@/types";

export type InboxSourceType = "meeting" | "note" | "attachment";

export interface InboxItem extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  title: string;
  summary: string | null;
  sourceType: InboxSourceType;
  sourceId: UUID;
  aiSuggestedProjectId: UUID | null;
  aiSuggestedProjectTitle: string | null;
  aiSuggestedTags: string[];
  aiConfidence: number | null;
  isProcessed: boolean;
}
