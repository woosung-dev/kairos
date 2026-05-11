import type { UUID, Timestamped } from "@/types";

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
}

export interface CreateProjectRequest {
  title: string;
  description?: string | null;
  visibility?: ProjectVisibility;
  tags?: string[];
}

export interface UpdateProjectRequest {
  title?: string;
  description?: string | null;
  status?: ProjectStatus;
  visibility?: ProjectVisibility;
  tags?: string[];
}

// Sprint 6 L-6: ProjectMember (visibility=Private 시 명시적 매핑)

export interface ProjectMember {
  id: UUID;
  projectId: UUID;
  userId: UUID;
  role: string; // Sprint 6: "member" 단일 (AD-27)
  createdAt: string;
}

export interface AddProjectMemberRequest {
  userId: UUID;
  role?: string;
}
