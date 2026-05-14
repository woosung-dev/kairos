// Sprint 15 Recall-first wedge — Memory 도메인 타입
export type MemoryStatus =
  | "processing"
  | "transcription_pending"
  | "embedding_pending"
  | "embedding_failed"
  | "active"
  | "archived";

export interface MemoryDistilled {
  title: string;
  atomic_notes: string[];
  suggested_visibility: "personal" | "team";
}

export interface MemoryDetail {
  memory_id: string;
  workspace_id: string;
  type: "text" | "voice";
  raw_content: string;
  distilled_json: MemoryDistilled | null;
  status: MemoryStatus;
  embedding_chunk_id: string | null;
  r2_audio_key: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryCreateResponse {
  memory_id: string;
  status: MemoryStatus;
  distilled_json: MemoryDistilled | null;
  created_at: string;
}

export type MemoryMatchType = "vector" | "keyword";

export interface MemoryRecallSource {
  memory_id: string;
  title: string;
  atomic_notes_excerpt: string;
  score: number;
  match_type: MemoryMatchType;
  created_at: string;
}

export interface MemoryRecallResult {
  query: string;
  sources: MemoryRecallSource[];
  fallback_used: boolean;
}
