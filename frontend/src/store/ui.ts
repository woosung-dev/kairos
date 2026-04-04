import { create } from "zustand";
import type { SourceDocument, HighlightChunk } from "@/features/sources/types";

interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  ragOverlayOpen: boolean;
  cmdKOpen: boolean;
  isMobile: boolean;
  // 소스 뷰어 상태
  sourceViewerSource: SourceDocument | null;
  sourceViewerHighlights: HighlightChunk[];
  toggleSidebar: () => void;
  toggleRagOverlay: () => void;
  toggleCmdK: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setIsMobile: (mobile: boolean) => void;
  openSourceViewer: (source: SourceDocument, highlights: HighlightChunk[]) => void;
  closeSourceViewer: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  sidebarCollapsed: false,
  ragOverlayOpen: false,
  cmdKOpen: false,
  isMobile: false,
  sourceViewerSource: null,
  sourceViewerHighlights: [],
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleRagOverlay: () => set((s) => ({ ragOverlayOpen: !s.ragOverlayOpen })),
  toggleCmdK: () => set((s) => ({ cmdKOpen: !s.cmdKOpen })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setIsMobile: (mobile) => set({ isMobile: mobile }),
  openSourceViewer: (source, highlights) =>
    set({ sourceViewerSource: source, sourceViewerHighlights: highlights }),
  closeSourceViewer: () =>
    set({ sourceViewerSource: null, sourceViewerHighlights: [] }),
}));
