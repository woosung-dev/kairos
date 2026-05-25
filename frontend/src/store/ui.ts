import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  ragOverlayOpen: boolean;
  cmdKOpen: boolean;
  /** Sprint 24 Wave 2 T-CMD-K-FIX: dashboard 추천 질문 클릭 시 palette 에 자동 입력될 query */
  cmdKInitialQuery: string;
  /** Sprint 27e Post-Merge BUG-QA-3: 추천 질문 click 시 prefill 후 자동 submit (Enter 명시 회피) */
  cmdKAutoSubmit: boolean;
  isMobile: boolean;
  toggleSidebar: () => void;
  toggleRagOverlay: () => void;
  toggleCmdK: () => void;
  /** Sprint 24 Wave 2 T-CMD-K-FIX: palette open + query 자동 입력 (RAG 모드).
   *  Sprint 27e Post-Merge: autoSubmit=true 시 cmd-k.tsx 가 prefill 직후 RAG 호출. */
  openCmdKWithQuery: (query: string, autoSubmit?: boolean) => void;
  /** palette consumer 가 한번 읽고 reset 하기 위한 setter */
  setCmdKInitialQuery: (query: string) => void;
  setCmdKAutoSubmit: (v: boolean) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setIsMobile: (mobile: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  sidebarCollapsed: false,
  ragOverlayOpen: false,
  cmdKOpen: false,
  cmdKInitialQuery: "",
  cmdKAutoSubmit: false,
  isMobile: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleRagOverlay: () => set((s) => ({ ragOverlayOpen: !s.ragOverlayOpen })),
  toggleCmdK: () => set((s) => ({ cmdKOpen: !s.cmdKOpen })),
  openCmdKWithQuery: (query: string, autoSubmit: boolean = false) =>
    set({ cmdKOpen: true, cmdKInitialQuery: query, cmdKAutoSubmit: autoSubmit }),
  setCmdKInitialQuery: (query: string) => set({ cmdKInitialQuery: query }),
  setCmdKAutoSubmit: (v: boolean) => set({ cmdKAutoSubmit: v }),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setIsMobile: (mobile) => set({ isMobile: mobile }),
}));
