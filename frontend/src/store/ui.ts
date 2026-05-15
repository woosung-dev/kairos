import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  ragOverlayOpen: boolean;
  cmdKOpen: boolean;
  isMobile: boolean;
  toggleSidebar: () => void;
  toggleRagOverlay: () => void;
  toggleCmdK: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setIsMobile: (mobile: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  sidebarCollapsed: false,
  ragOverlayOpen: false,
  cmdKOpen: false,
  isMobile: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleRagOverlay: () => set((s) => ({ ragOverlayOpen: !s.ragOverlayOpen })),
  toggleCmdK: () => set((s) => ({ cmdKOpen: !s.cmdKOpen })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setIsMobile: (mobile) => set({ isMobile: mobile }),
}));
