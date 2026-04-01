import type { UUID } from "@/types";

export type SourceFreshness = "recent" | "normal" | "stale";

export interface RagMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: RagSource[];
  createdAt: string;
}

export interface RagSource {
  title: string;
  type: "meeting" | "note" | "attachment";
  date: string;
  speaker?: string;
  freshness: SourceFreshness;
}

export interface SearchScope {
  projectId?: UUID;
  timeRange?: "all" | "1m" | "3m" | "6m";
  sourceType?: "all" | "meeting" | "note" | "attachment";
}
