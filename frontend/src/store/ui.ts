import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  ragPanelOpen: boolean;
  cmdKOpen: boolean;
  toggleSidebar: () => void;
  toggleRagPanel: () => void;
  toggleCmdK: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  ragPanelOpen: true,
  cmdKOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleRagPanel: () => set((s) => ({ ragPanelOpen: !s.ragPanelOpen })),
  toggleCmdK: () => set((s) => ({ cmdKOpen: !s.cmdKOpen })),
}));
