import type { ApiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types";
import type {
  Meeting,
  MeetingDetail,
  MeetingStatusResponse,
  CreateMeetingRequest,
  CreateMeetingResponse,
} from "./types";


export async function fetchMeetings(
  api: ApiClient,
  wid: string,
  page = 1,
  projectId?: string,
): Promise<PaginatedResponse<Meeting>> {
  const params = new URLSearchParams();
  params.set("page", String(page));
  if (projectId) params.set("projectId", projectId);
  return api.fetch<PaginatedResponse<Meeting>>(
    `/workspaces/${wid}/meetings?${params.toString()}`);
}

export async function fetchMeetingDetail(
  api: ApiClient,
  wid: string,
  id: string
): Promise<MeetingDetail> {
  return api.fetch<MeetingDetail>(`/workspaces/${wid}/meetings/${id}`);
}

export async function fetchMeetingStatus(
  api: ApiClient,
  wid: string,
  id: string
): Promise<MeetingStatusResponse> {
  return api.fetch<MeetingStatusResponse>(
    `/workspaces/${wid}/meetings/${id}/status`);
}

export async function exportMeeting(
  api: ApiClient,
  wid: string,
  id: string,
  format: "md" | "json"
): Promise<Blob> {
  const res = await api.fetchRaw(
    `/workspaces/${wid}/meetings/${id}/export?format=${format}`,
  );
  if (!res.ok) throw new Error("내보내기에 실패했습니다");
  return res.blob();
}

export async function createMeeting(
  api: ApiClient,
  wid: string,
  data: CreateMeetingRequest
): Promise<CreateMeetingResponse> {
  return api.fetch<CreateMeetingResponse>(`/workspaces/${wid}/meetings`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export interface CaptureTextRequest {
  title: string;
  transcriptText: string;
}

export async function captureText(
  api: ApiClient,
  wid: string,
  data: CaptureTextRequest
): Promise<{ id: string; status: string; message: string }> {
  return api.fetch(`/workspaces/${wid}/meetings/capture`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
