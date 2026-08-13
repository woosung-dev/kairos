// sources 도메인 전용 — RAG 답변에서 참조한 원본 소스 뷰어의 열림/닫힘 상태
import { create } from "zustand";
import type { SourceDocument, HighlightChunk } from "./types";

interface SourceViewerState {
  source: SourceDocument | null;
  highlights: HighlightChunk[];
  open: (source: SourceDocument, highlights: HighlightChunk[]) => void;
  close: () => void;
}

export const useSourceViewerStore = create<SourceViewerState>((set) => ({
  source: null,
  highlights: [],
  open: (source, highlights) => set({ source, highlights }),
  close: () => set({ source: null, highlights: [] }),
}));
