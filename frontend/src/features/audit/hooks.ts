"use client";

// Sprint 24 Wave 2 T-AUDIT-VIEW — Audit 무한 스크롤 훅 (useInfiniteQuery)
import { useAuth } from "@clerk/nextjs";
import { useInfiniteQuery } from "@tanstack/react-query";
import { auditKeys, fetchAuditPromotions } from "./api";
import type { AuditPromotionPage } from "./types";

interface UseAuditPromotionsOptions {
  enabled?: boolean;
}

export function useAuditPromotions(
  workspaceId: string | undefined,
  itemType: string | null,
  options?: UseAuditPromotionsOptions,
) {
  const { getToken } = useAuth();

  return useInfiniteQuery({
    queryKey: auditKeys.promotions(workspaceId ?? "", itemType),
    initialPageParam: null as string | null,
    queryFn: async ({
      pageParam,
    }: {
      pageParam: string | null;
    }): Promise<AuditPromotionPage> => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      if (!workspaceId) throw new Error("workspaceId 필요");
      return fetchAuditPromotions(token, workspaceId, {
        itemType: itemType ?? undefined,
        cursor: pageParam ?? undefined,
        limit: 20,
      });
    },
    getNextPageParam: (lastPage: AuditPromotionPage) => lastPage.nextCursor,
    enabled: !!workspaceId && (options?.enabled ?? true),
  });
}
