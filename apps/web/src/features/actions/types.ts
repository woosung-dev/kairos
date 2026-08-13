import type { UUID, Timestamped, UserBrief } from "@/types";

export type ActionPriority = "high" | "medium" | "low";
export type ActionStatus = "todo" | "in_progress" | "done" | "cancelled";

export interface ActionItem extends Timestamped {
  id: UUID;
  meetingId: UUID | null;
  projectId: UUID | null;
  title: string;
  description: string | null;
  assignee: UserBrief | null;
  dueDate: string | null;
  priority: ActionPriority;
  status: ActionStatus;
}
