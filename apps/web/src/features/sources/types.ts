export interface SourceDocument {
  id: string;
  /** CAND-E: source 엔티티(meeting/note/external_document) PK — full-detail fetch 용. 미지정 시 id 폴백. */
  sourceId?: string;
  title: string;
  type: "meeting" | "note" | "file" | "external_document";
  content: string;
  projectId: string;
  createdAt: string;
}

export interface HighlightChunk {
  citationNumber: number;
  startOffset: number;
  endOffset: number;
  text: string;
}
