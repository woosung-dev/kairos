import type { UUID, Timestamped } from "@/types";

export interface Workspace extends Timestamped {
  id: UUID;
  name: string;
  ownerId: UUID;
  // Sprint 15 R6: 'personal' | 'team' — promote modal에서 team만 필터.
  // BE가 응답에 type을 포함하지 않는 구버전 호환을 위해 optional.
  type?: "personal" | "team";
  memberCount?: number;
}

export interface CreateWorkspaceRequest {
  name: string;
}
