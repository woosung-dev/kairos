"use client";

import { meetingKeys, onboardingKeys } from "@/lib/query-keys";
import { useApiClient } from "@/lib/use-api-client";
import { useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
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
  const api = useApiClient();

  return useQuery({
    queryKey: meetingKeys.list(wid ?? "", projectId),
    queryFn: () => fetchMeetings(api, wid!, page, projectId),
    enabled: !!wid,
  });
}

/**
 * 회의 상세 (요약 + 트랜스크립트)
 */
export function useMeetingDetail(wid: string | undefined, id: string) {
  const api = useApiClient();

  return useQuery({
    queryKey: meetingKeys.detail(wid ?? "", id),
    queryFn: () => fetchMeetingDetail(api, wid!, id),
    enabled: !!wid,
    // CAND-E: 404(삭제/미존재 source) 등 에러 상태에서 폴링을 멈춘다. 이전엔 에러 시에도
    // 3000ms 폴링을 무한 반복해 SourceViewer 가 죽은 source 를 열면 console 에러가 폭증했다.
    retry: (failureCount) => failureCount < 1,
    refetchInterval: (query) => {
      if (query.state.error) return false; // 에러 지속 시 무한 폴링 중단 (storm 차단)
      const status = query.state.data?.status;
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
 *
 * Sprint 22 OBN-02: 폴링 중 status 가 "completed" 로 전이될 때 onboarding 캐시 무효화.
 * BE pipeline_service 가 distillation 완료 시 step=3 advance.
 */
export function useMeetingStatus(wid: string | undefined, id: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const previousStatusRef = useRef<MeetingStatus | undefined>(undefined);

  const query = useQuery({
    queryKey: meetingKeys.status(wid ?? "", id),
    queryFn: () => fetchMeetingStatus(api, wid!, id),
    enabled: !!wid,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      if (status && POLLING_STATUSES.includes(status)) {
        return 3000;
      }
      return false;
    },
  });

  useEffect(() => {
    const currentStatus = query.data?.status;
    if (
      currentStatus === "completed" &&
      previousStatusRef.current !== "completed"
    ) {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.all });
    }
    previousStatusRef.current = currentStatus;
  }, [query.data?.status, queryClient]);

  return query;
}

/**
 * 회의 생성 (202 Accepted, 비동기 파이프라인)
 */
export function useCreateMeeting(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateMeetingRequest) => createMeeting(api, wid!, data),
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
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CaptureTextRequest) => captureText(api, wid!, data),
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: meetingKeys.list(wid) });
      }
    },
  });
}
