export interface SourceDocument {
  id: string;
  title: string;
  type: "meeting" | "note" | "file";
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
