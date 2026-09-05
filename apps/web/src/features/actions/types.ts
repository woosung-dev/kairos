import type { UUID, Timestamped } from "@/types";

export type ActionPriority = "high" | "medium" | "low";
export type ActionStatus = "todo" | "in_progress" | "done" | "cancelled";

export interface ActionItem extends Timestamped {
  id: UUID;
  meetingId: UUID | null;
  projectId: UUID | null;
  title: string;
  description: string | null;
  // BE `_to_dict` 는 `assigneeId` 만 내려준다 — 이전 타입은 `assignee: UserBrief` 객체를 기대해
  // 담당자가 어느 화면에도 렌더되지 않았다. 표시 이름은 워크스페이스 멤버 목록으로 해석한다
  // (`useAssigneeNames`).
  assigneeId: UUID | null;
  dueDate: string | null;
  priority: ActionPriority;
  status: ActionStatus;
}
