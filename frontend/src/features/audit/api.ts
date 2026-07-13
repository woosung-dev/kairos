// Sprint 24 Wave 2 T-AUDIT-VIEW — ItemPromotionAudit 조회 API client (admin only)
import type { ApiClient } from "@/lib/api-client";
import type { AuditPromotionItem, AuditPromotionPage } from "./types";

export const auditKeys = {
  all: ["audit"] as const,
  promotions: (wid: string, itemType: string | null) =>
    [...auditKeys.all, "promotions", wid, itemType ?? "all"] as const,
};

export async function fetchAuditPromotions(
  api: ApiClient,
  wid: string,
  params: { itemType?: string | null; cursor?: string | null; limit?: number },
): Promise<AuditPromotionPage> {
  const search = new URLSearchParams();
  if (params.itemType) search.set("itemType", params.itemType);
  if (params.cursor) search.set("cursor", params.cursor);
  if (params.limit) search.set("limit", String(params.limit));

  const qs = search.toString();
  const path = `/workspaces/${wid}/audit/promotions${qs ? `?${qs}` : ""}`;
  return api.fetch<AuditPromotionPage>(path);
}

export type { AuditPromotionItem, AuditPromotionPage };
