import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { WorkspaceRole } from "@/features/members/types";

interface WorkspaceState {
  /** 현재 선택된 워크스페이스 ID (localStorage에 저장) */
  activeWorkspaceId: string | null;
  setActiveWorkspaceId: (id: string) => void;

  /** 현재 워크스페이스에서의 사용자 역할 (메모리만, persist 안 함) */
  workspaceRole: WorkspaceRole | null;
  setWorkspaceRole: (role: WorkspaceRole | null) => void;

  /** 역할 기반 권한 헬퍼 */
  hasRole: (minRole: WorkspaceRole) => boolean;
}

const ROLE_LEVEL: Record<WorkspaceRole, number> = {
  viewer: 1,
  member: 2,
  admin: 3,
  owner: 4,
};

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      activeWorkspaceId: null,
      setActiveWorkspaceId: (id: string) => set({ activeWorkspaceId: id }),

      workspaceRole: null,
      setWorkspaceRole: (role: WorkspaceRole | null) =>
        set({ workspaceRole: role }),

      hasRole: (minRole: WorkspaceRole) => {
        const current = get().workspaceRole;
        if (!current) return false;
        return ROLE_LEVEL[current] >= ROLE_LEVEL[minRole];
      },
    }),
    {
      name: "kairos-workspace",
      // workspaceRole은 persist 제외 (매 세션마다 API에서 가져옴)
      partialize: (state) => ({
        activeWorkspaceId: state.activeWorkspaceId,
      }),
    }
  )
);
