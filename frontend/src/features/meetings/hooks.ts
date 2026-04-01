"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  meetingKeys,
  fetchMeetings,
  fetchMeetingDetail,
  fetchMeetingStatus,
  createMeeting,
} from "./api";
import type { CreateMeetingRequest, MeetingStatus } from "./types";

/**
 * 워크스페이스 내 회의 목록 조회
 */
export function useMeetings(wid: string | undefined, page = 1) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: meetingKeys.list(wid ?? ""),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchMeetings(token, wid!, page);
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
  });
}

// 처리 완료/실패가 아닌 진행 중 상태
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
