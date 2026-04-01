import { apiClient } from "@/lib/api-client";
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
  list: (wid: string) => [...meetingKeys.all, "list", wid] as const,
  detail: (wid: string, id: string) =>
    [...meetingKeys.all, "detail", wid, id] as const,
  status: (wid: string, id: string) =>
    [...meetingKeys.all, "status", wid, id] as const,
};

export async function fetchMeetings(
  token: string,
  wid: string,
  page = 1
): Promise<PaginatedResponse<Meeting>> {
  return apiClient<PaginatedResponse<Meeting>>(
    `/workspaces/${wid}/meetings?page=${page}`,
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
