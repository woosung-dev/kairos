import type { UUID, Timestamped, UserBrief } from "@/types";

export type ProjectStatus = "active" | "completed" | "archived";
export type ProjectVisibility = "public" | "draft" | "private";

export interface Project extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  title: string;
  description: string | null;
  status: ProjectStatus;
  visibility: ProjectVisibility;
  tags: string[];
  sortOrder: number;
  createdBy: UserBrief;
  contentCount: number;
  meetingCount: number;
  actionItemCount: number;
}
