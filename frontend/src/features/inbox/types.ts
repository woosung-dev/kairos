import type { UUID, Timestamped } from "@/types";
import type { ParaCategory } from "@/features/para/types";

export type InboxSourceType = "meeting" | "note" | "attachment";

export type InboxStatus = "unprocessed" | "classified" | "dismissed";

export interface InboxItem extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  title: string;
  summary: string | null;
  sourceType: InboxSourceType;
  sourceId: UUID;
  aiSuggestedParaType: ParaCategory | null;
  aiSuggestedParaId: UUID | null;
  aiSuggestedParaTitle: string | null;
  aiConfidence: number | null;
  isProcessed: boolean;
}
