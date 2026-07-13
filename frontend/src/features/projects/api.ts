import type { ApiClient } from "@/lib/api-client";
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

export async function addMeetingProject(
  api: ApiClient,
  wid: string,
  meetingId: string,
  projectId: string
): Promise<void> {
  return api.fetch<void>(
    `/workspaces/${wid}/meetings/${meetingId}/projects/${projectId}`,
    { method: "PUT" }
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
