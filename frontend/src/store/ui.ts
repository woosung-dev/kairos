import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  ragPanelOpen: boolean;
  cmdKOpen: boolean;
  isMobile: boolean;
  toggleSidebar: () => void;
  toggleRagPanel: () => void;
  toggleCmdK: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setIsMobile: (mobile: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  sidebarCollapsed: false,
  ragPanelOpen: true,
  cmdKOpen: false,
  isMobile: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleRagPanel: () => set((s) => ({ ragPanelOpen: !s.ragPanelOpen })),
  toggleCmdK: () => set((s) => ({ cmdKOpen: !s.cmdKOpen })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setIsMobile: (mobile) => set({ isMobile: mobile }),
}));
