import { create } from "zustand";
import { persist } from "zustand/middleware";

interface WorkspaceState {
  /** 현재 선택된 워크스페이스 ID (localStorage에 저장) */
  activeWorkspaceId: string | null;
  setActiveWorkspaceId: (id: string) => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      activeWorkspaceId: null,
      setActiveWorkspaceId: (id: string) => set({ activeWorkspaceId: id }),
    }),
    { name: "kairos-workspace" }
  )
);
