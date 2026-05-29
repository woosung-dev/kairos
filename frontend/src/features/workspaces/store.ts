import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { WorkspaceRole } from "@/features/members/types";

interface WorkspaceState {
  /** 현재 선택된 워크스페이스 ID (localStorage에 저장) */
  activeWorkspaceId: string | null;
  setActiveWorkspaceId: (id: string) => void;

  /** 이 persist 를 소유한 Clerk user id — 계정 전환 시 stale workspace 정리용 (BL-S27c-12) */
  ownerUserId: string | null;
  /**
   * 현재 로그인 user 와 persist 소유자 불일치 시 activeWorkspaceId 를 초기화한다.
   * 워크스페이스 목록과 무관하게 user id 만 비교 → 워크스페이스 생성/전환 race 없음.
   * 계정 전환(드롭다운 외 세션만료 포함)으로 이전 user 의 wid 가 잔존해 cross-tenant
   * 403 이 나던 문제 방어.
   */
  ensureOwner: (userId: string) => void;

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

      ownerUserId: null,
      ensureOwner: (userId: string) =>
        set((state) =>
          state.ownerUserId === userId
            ? state
            : { ownerUserId: userId, activeWorkspaceId: null }
        ),

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
        ownerUserId: state.ownerUserId,
      }),
    }
  )
);
