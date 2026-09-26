import type { UUID, Timestamped } from "@/types";
import type { ProjectVisibility } from "@/lib/visibility";

export type ProjectStatus = "active" | "completed" | "archived";
export type { ProjectVisibility };

export interface Project extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  title: string;
  description: string | null;
  status: ProjectStatus;
  visibility: ProjectVisibility;
  tags: string[];
  sortOrder: number;
  /** 작성자 내부 user id (users.id) — 작성자는 member 여도 visibility 를 바꿀 수 있다 (2026-09-27 결정) */
  createdById: UUID;
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
