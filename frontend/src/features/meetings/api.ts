import { apiClient, API_BASE_URL } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type {
  Meeting,
  MeetingDetail,
  MeetingStatusResponse,
  CreateMeetingRequest,
  CreateMeetingResponse,
} from "./types";

export const meetingKeys = {
  all: ["meetings"] as const,
  list: (wid: string, projectId?: string) =>
    [...meetingKeys.all, "list", wid, projectId ?? "all"] as const,
  detail: (wid: string, id: string) =>
    [...meetingKeys.all, "detail", wid, id] as const,
  status: (wid: string, id: string) =>
    [...meetingKeys.all, "status", wid, id] as const,
};

export async function fetchMeetings(
  token: string,
  wid: string,
  page = 1,
  projectId?: string,
): Promise<PaginatedResponse<Meeting>> {
  const params = new URLSearchParams();
  params.set("page", String(page));
  if (projectId) params.set("projectId", projectId);
  return apiClient<PaginatedResponse<Meeting>>(
    `/workspaces/${wid}/meetings?${params.toString()}`,
    { token }
  );
}

export async function fetchMeetingDetail(
  token: string,
  wid: string,
  id: string
): Promise<MeetingDetail> {
  return apiClient<MeetingDetail>(`/workspaces/${wid}/meetings/${id}`, {
    token,
  });
}

export async function fetchMeetingStatus(
  token: string,
  wid: string,
  id: string
): Promise<MeetingStatusResponse> {
  return apiClient<MeetingStatusResponse>(
    `/workspaces/${wid}/meetings/${id}/status`,
    { token }
  );
}

export async function exportMeeting(
  token: string,
  wid: string,
  id: string,
  format: "md" | "json"
): Promise<Blob> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/workspaces/${wid}/meetings/${id}/export?format=${format}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) throw new Error("내보내기에 실패했습니다");
  return res.blob();
}

export async function createMeeting(
  token: string,
  wid: string,
  data: CreateMeetingRequest
): Promise<CreateMeetingResponse> {
  return apiClient<CreateMeetingResponse>(`/workspaces/${wid}/meetings`, {
    token,
    method: "POST",
    body: JSON.stringify(data),
  });
}
