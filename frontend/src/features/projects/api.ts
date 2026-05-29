import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type {
  AddProjectMemberRequest,
  CreateProjectRequest,
  Project,
  ProjectMember,
  UpdateProjectRequest,
} from "./types";

// --- Query Key Factory ---

export const projectKeys = {
  all: ["projects"] as const,
  // S28b RQ-KEY-COLLISION fix: params(status 등) 를 키에 포함 — 안 그러면
  // 사이드바의 active/archived useProjects 두 호출이 같은 키로 충돌(교차오염).
  // invalidate 는 list(wid) prefix 로 모든 param 변형 매칭.
  list: (wid: string, params?: FetchProjectsParams) =>
    params
      ? ([...projectKeys.all, "list", wid, params] as const)
      : ([...projectKeys.all, "list", wid] as const),
  detail: (wid: string, id: string) =>
    [...projectKeys.all, "detail", wid, id] as const,
  members: (wid: string, id: string) =>
    [...projectKeys.all, "members", wid, id] as const,
};

// --- API 함수 ---

export interface FetchProjectsParams {
  status?: string;
  page?: number;
  pageSize?: number;
}

export async function fetchProjects(
  token: string,
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

  return apiClient<PaginatedResponse<Project>>(path, { token });
}

export async function fetchProject(
  token: string,
  wid: string,
  id: string
): Promise<Project> {
  return apiClient<Project>(`/workspaces/${wid}/projects/${id}`, { token });
}

export async function createProject(
  token: string,
  wid: string,
  data: CreateProjectRequest
): Promise<Project> {
  return apiClient<Project>(`/workspaces/${wid}/projects`, {
    token,
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateProject(
  token: string,
  wid: string,
  id: string,
  data: UpdateProjectRequest
): Promise<Project> {
  return apiClient<Project>(`/workspaces/${wid}/projects/${id}`, {
    token,
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteProject(
  token: string,
  wid: string,
  id: string
): Promise<void> {
  return apiClient<void>(`/workspaces/${wid}/projects/${id}`, {
    token,
    method: "DELETE",
  });
}

export async function archiveProject(
  token: string,
  wid: string,
  id: string
): Promise<Project> {
  return apiClient<Project>(`/workspaces/${wid}/projects/${id}/archive`, {
    token,
    method: "POST",
  });
}

export async function addMeetingProject(
  token: string,
  wid: string,
  meetingId: string,
  projectId: string
): Promise<void> {
  return apiClient<void>(
    `/workspaces/${wid}/meetings/${meetingId}/projects/${projectId}`,
    { token, method: "PUT" }
  );
}

export async function removeMeetingProject(
  token: string,
  wid: string,
  meetingId: string,
  projectId: string
): Promise<void> {
  return apiClient<void>(
    `/workspaces/${wid}/meetings/${meetingId}/projects/${projectId}`,
    { token, method: "DELETE" }
  );
}

// --- ProjectMember (Sprint 6 L-6) ---

export async function fetchProjectMembers(
  token: string,
  wid: string,
  projectId: string
): Promise<ProjectMember[]> {
  return apiClient<ProjectMember[]>(
    `/workspaces/${wid}/projects/${projectId}/members`,
    { token }
  );
}

export async function addProjectMember(
  token: string,
  wid: string,
  projectId: string,
  data: AddProjectMemberRequest
): Promise<ProjectMember> {
  return apiClient<ProjectMember>(
    `/workspaces/${wid}/projects/${projectId}/members`,
    {
      token,
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function removeProjectMember(
  token: string,
  wid: string,
  projectId: string,
  userId: string
): Promise<void> {
  return apiClient<void>(
    `/workspaces/${wid}/projects/${projectId}/members/${userId}`,
    { token, method: "DELETE" }
  );
}
