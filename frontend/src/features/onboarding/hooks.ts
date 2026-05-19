// 온보딩 도메인 React Query 훅 — server state (Sprint 22 OBN-02)
"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";

import { useWorkspaceStore } from "@/features/workspaces/store";

import { fetchOnboarding, onboardingKeys } from "./api";

/**
 * 현재 사용자의 온보딩 진행 상태 조회.
 *
 * - workspace 선택 안 됐으면 disabled
 * - polling 없음, 30s staleTime (mutation invalidate 로 갱신)
 * - step === 4 면 isCompleted = true (BE 책임)
 */
export function useOnboarding() {
  const { getToken } = useAuth();
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  return useQuery({
    queryKey: onboardingKeys.status(workspaceId),
    queryFn: async () => {
      const token = await getToken();
      if (!token || !workspaceId) {
        throw new Error("인증이 필요합니다");
      }
      return fetchOnboarding(token, workspaceId);
    },
    enabled: !!workspaceId,
    staleTime: 30_000,
    // Sprint 22 (CI fragility fix): retry/refetch 비활성화 — error 시 banner 만 hidden,
    // page render 영향 0. CI 의 networkidle wait 못 도달 시 home/mobile-responsive heading
    // 검증 timeout fix.
    retry: false,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}
