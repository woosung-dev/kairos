import type { UUID } from "@/types";

export type SourceFreshness = "recent" | "normal" | "stale";

export interface RagMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: RagSource[];
  isStreaming?: boolean;
  createdAt: string;
}

export interface RagSource {
  id: string;
  /** CAND-E: source 엔티티(meeting/note) PK. SourceViewer full-detail fetch 용. id 는 chunk PK. */
  sourceId: string;
  text: string;
  source: string;
  sourceType: "meeting" | "note";
  date: string;
  speaker?: string;
  score: number;
  freshness: SourceFreshness;
}

export interface SearchFilter {
  projectId?: UUID;
  timeRange?: "1m" | "3m" | "6m" | null;
  sourceType?: "meeting" | "note" | null;
}

export interface RagAskRequest {
  question: string;
  projectId?: string | null;
  timeRange?: string | null;
  sourceType?: string | null;
}

export interface SSESearchResultsEvent {
  chunks: RagSource[];
}

export interface SSEAnswerEvent {
  token: string;
}

export interface SSEDoneEvent {
  cached: boolean;
  sourceCount: number;
}
