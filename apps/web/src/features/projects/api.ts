import type { ApiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type { components } from "@/types/api.gen";
import type {
  AddProjectMemberRequest,
  CreateProjectRequest,
  Project,
  ProjectMember,
  UpdateProjectRequest,
} from "./types";

type AddMeetingProjectRequest = components["schemas"]["AddMeetingProjectRequest"];

// --- API 함수 ---

export interface FetchProjectsParams {
  status?: string;
  page?: number;
  pageSize?: number;
}

export async function fetchProjects(
  api: ApiClient,
  wid: string,
  params?: FetchProjectsParams
): Promise<PaginatedResponse<Project>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.page) searchParams.set("page", String(params.page));
  // S28b FE-PAGESIZE-MISMATCH fix: BE Query alias 는 "pageSize"(camel) — snake 는 무시됨.
  if (params?.pageSize) searchParams.set("pageSize", String(params.pageSize));

  const query = searchParams.toString();
  const path = `/workspaces/${wid}/projects${query ? `?${query}` : ""}`;

  return api.fetch<PaginatedResponse<Project>>(path);
}

export async function fetchProject(
  api: ApiClient,
  wid: string,
  id: string
): Promise<Project> {
  return api.fetch<Project>(`/workspaces/${wid}/projects/${id}`);
}

export async function createProject(
  api: ApiClient,
  wid: string,
  data: CreateProjectRequest
): Promise<Project> {
  return api.fetch<Project>(`/workspaces/${wid}/projects`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateProject(
  api: ApiClient,
  wid: string,
  id: string,
  data: UpdateProjectRequest
): Promise<Project> {
  return api.fetch<Project>(`/workspaces/${wid}/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteProject(
  api: ApiClient,
  wid: string,
  id: string
): Promise<void> {
  return api.fetch<void>(`/workspaces/${wid}/projects/${id}`, {
    method: "DELETE",
  });
}

export async function archiveProject(
  api: ApiClient,
  wid: string,
  id: string
): Promise<Project> {
  return api.fetch<Project>(`/workspaces/${wid}/projects/${id}/archive`, {
    method: "POST",
  });
}

// BE: POST /meetings/{mid}/projects  body {projectId} → 201 {id, meetingId, projectId}.
// 예전 FE 는 PUT /meetings/{mid}/projects/{pid} 를 보냈는데 BE 에 그 라우트가 없어 405 였다 (C-002).
// 응답 본문은 OpenAPI 에 스키마가 없어(201 content = unknown) 수기 wire 타입을 만들지 않는다 — 호출부도 쓰지 않는다.
export async function addMeetingProject(
  api: ApiClient,
  wid: string,
  meetingId: string,
  projectId: string
): Promise<unknown> {
  return api.fetch<unknown>(
    `/workspaces/${wid}/meetings/${meetingId}/projects`,
    {
      method: "POST",
      body: JSON.stringify({ projectId } satisfies AddMeetingProjectRequest),
    }
  );
}

export async function removeMeetingProject(
  api: ApiClient,
  wid: string,
  meetingId: string,
  projectId: string
): Promise<void> {
  return api.fetch<void>(
    `/workspaces/${wid}/meetings/${meetingId}/projects/${projectId}`,
    { method: "DELETE" }
  );
}

// --- ProjectMember (Sprint 6 L-6) ---

export async function fetchProjectMembers(
  api: ApiClient,
  wid: string,
  projectId: string
): Promise<ProjectMember[]> {
  return api.fetch<ProjectMember[]>(
    `/workspaces/${wid}/projects/${projectId}/members`);
}

export async function addProjectMember(
  api: ApiClient,
  wid: string,
  projectId: string,
  data: AddProjectMemberRequest
): Promise<ProjectMember> {
  return api.fetch<ProjectMember>(
    `/workspaces/${wid}/projects/${projectId}/members`,
    { method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function removeProjectMember(
  api: ApiClient,
  wid: string,
  projectId: string,
  userId: string
): Promise<void> {
  return api.fetch<void>(
    `/workspaces/${wid}/projects/${projectId}/members/${userId}`,
    { method: "DELETE" }
  );
}
