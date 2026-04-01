import type { UUID, Timestamped } from "@/types";

export interface Workspace extends Timestamped {
  id: UUID;
  name: string;
  ownerId: UUID;
  memberCount?: number;
}

export interface CreateWorkspaceRequest {
  name: string;
}
