"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  meetingKeys,
  fetchMeetings,
  fetchMeetingDetail,
  fetchMeetingStatus,
  createMeeting,
  captureText,
  type CaptureTextRequest,
} from "./api";
import type { CreateMeetingRequest, MeetingStatus } from "./types";

/**
 * 워크스페이스 내 회의 목록 조회 (projectId로 필터 가능)
 */
export function useMeetings(
  wid: string | undefined,
  page = 1,
  projectId?: string,
) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: meetingKeys.list(wid ?? "", projectId),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchMeetings(token, wid!, page, projectId);
    },
    enabled: !!wid,
  });
}

/**
 * 회의 상세 (요약 + 트랜스크립트)
 */
export function useMeetingDetail(wid: string | undefined, id: string) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: meetingKeys.detail(wid ?? "", id),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchMeetingDetail(token, wid!, id);
    },
    enabled: !!wid,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // 완료/실패 상태에서만 중단 — 네트워크 오류 시에도 재시도 유지
      if (status === "completed" || status === "failed") return false;
      if (status && POLLING_STATUSES.includes(status)) return 3000;
      return 3000;
    },
  });
}

// 처리 완료/실패가 아닌 진행 중 상태 (백엔드 status: uploading → transcribing → analyzing → embedding → completed)
const POLLING_STATUSES: MeetingStatus[] = [
  "uploading",
  "transcribing",
  "analyzing",
  "embedding",
];

/**
 * 회의 처리 상태 폴링 (3초 간격, 진행 중일 때만)
 */
export function useMeetingStatus(wid: string | undefined, id: string) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: meetingKeys.status(wid ?? "", id),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchMeetingStatus(token, wid!, id);
    },
    enabled: !!wid,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && POLLING_STATUSES.includes(status)) {
        return 3000;
      }
      return false;
    },
  });
}

/**
 * 회의 생성 (202 Accepted, 비동기 파이프라인)
 */
export function useCreateMeeting(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateMeetingRequest) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return createMeeting(token, wid!, data);
    },
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: meetingKeys.list(wid) });
      }
    },
  });
}

/**
 * 텍스트 캡처 (202 Accepted, 비동기 파이프라인)
 */
export function useCaptureText(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CaptureTextRequest) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return captureText(token, wid!, data);
    },
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: meetingKeys.list(wid) });
      }
    },
  });
}
