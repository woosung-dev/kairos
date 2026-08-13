// Sprint 24 Wave 2 T-AUDIT-VIEW — Audit 도메인 타입 (BE schemas.AuditPromotion* 정합)

export type AuditItemType = "meeting" | "note" | "inbox" | "action";

export interface AuditPromotionItem {
  id: string;
  itemType: AuditItemType;
  sourceItemId: string;
  newItemId: string;
  sourceWorkspaceId: string;
  targetWorkspaceId: string;
  promotedByUserId: string;
  embeddingStatus: string;
  createdAt: string;
}

export interface AuditPromotionPage {
  items: AuditPromotionItem[];
  nextCursor: string | null;
}
