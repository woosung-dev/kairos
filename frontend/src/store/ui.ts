import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  ragOverlayOpen: boolean;
  cmdKOpen: boolean;
  /** Sprint 24 Wave 2 T-CMD-K-FIX: dashboard 추천 질문 클릭 시 palette 에 자동 입력될 query */
  cmdKInitialQuery: string;
  isMobile: boolean;
  toggleSidebar: () => void;
  toggleRagOverlay: () => void;
  toggleCmdK: () => void;
  /** Sprint 24 Wave 2 T-CMD-K-FIX: palette open + query 자동 입력 (RAG 모드) */
  openCmdKWithQuery: (query: string) => void;
  /** palette consumer 가 한번 읽고 reset 하기 위한 setter */
  setCmdKInitialQuery: (query: string) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setIsMobile: (mobile: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  sidebarCollapsed: false,
  ragOverlayOpen: false,
  cmdKOpen: false,
  cmdKInitialQuery: "",
  isMobile: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleRagOverlay: () => set((s) => ({ ragOverlayOpen: !s.ragOverlayOpen })),
  toggleCmdK: () => set((s) => ({ cmdKOpen: !s.cmdKOpen })),
  openCmdKWithQuery: (query: string) =>
    set({ cmdKOpen: true, cmdKInitialQuery: query }),
  setCmdKInitialQuery: (query: string) => set({ cmdKInitialQuery: query }),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setIsMobile: (mobile) => set({ isMobile: mobile }),
}));
