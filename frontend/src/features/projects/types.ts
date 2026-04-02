import type { UUID, Timestamped } from "@/types";

export type ProjectStatus = "active" | "completed" | "archived";

export interface Project extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  title: string;
  description: string | null;
  status: ProjectStatus;
  tags: string[];
  sortOrder: number;
}

export interface CreateProjectRequest {
  title: string;
  description?: string | null;
  tags?: string[];
}

export interface UpdateProjectRequest {
  title?: string;
  description?: string | null;
  status?: ProjectStatus;
  tags?: string[];
}
