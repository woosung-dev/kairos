import { create } from "zustand";

interface UIStore {
  // 사이드바 상태
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;

  // RAG 채팅 패널 상태
  isRAGPanelOpen: boolean;
  toggleRAGPanel: () => void;
  setRAGPanelOpen: (open: boolean) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSidebarOpen: (open) => set({ isSidebarOpen: open }),

  isRAGPanelOpen: false,
  toggleRAGPanel: () =>
    set((state) => ({ isRAGPanelOpen: !state.isRAGPanelOpen })),
  setRAGPanelOpen: (open) => set({ isRAGPanelOpen: open }),
}));
