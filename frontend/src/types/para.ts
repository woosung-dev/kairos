import type { UUID, Timestamped, UserBrief } from ".";

export type ParaCategory = "project" | "area" | "resource" | "archive";

export type ParaStatus = "active" | "completed" | "archived";

export interface ParaItem extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  category: ParaCategory;
  title: string;
  description: string | null;
  status: ParaStatus;
  paraOrder: number;
  createdBy: UserBrief;
  contentCount: number;
  meetingCount: number;
  actionItemCount: number;
}

// PARA 카테고리 메타데이터 (사이드바 네비 등에서 사용)
export interface ParaCategoryMeta {
  category: ParaCategory;
  label: string;
  icon: string;
  href: string;
}
