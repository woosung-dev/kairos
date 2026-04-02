import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type { Project, CreateProjectRequest, UpdateProjectRequest } from "./types";

// --- Query Key Factory ---

export const projectKeys = {
  all: ["projects"] as const,
  list: (wid: string) => [...projectKeys.all, "list", wid] as const,
  detail: (wid: string, id: string) =>
    [...projectKeys.all, "detail", wid, id] as const,
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
  if (params?.pageSize) searchParams.set("page_size", String(params.pageSize));

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
