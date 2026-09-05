"use client";

import { actionKeys } from "@/lib/query-keys";
import { useApiClient } from "@/lib/use-api-client";
import { useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMembers } from "@/features/members/hooks";
import {
  fetchActionItems,
  createActionItem,
  updateActionItem,
} from "./api";
import type { FetchActionItemsParams, CreateActionItemRequest, UpdateActionItemRequest } from "./api";

/**
 * 워크스페이스 내 액션 아이템 목록 조회
 */
export function useActionItems(wid: string | undefined, params?: FetchActionItemsParams) {
  const api = useApiClient();

  return useQuery({
    // params 를 키에 포함 — 프로젝트 필터 목록과 전체 목록이 같은 키를 쓰면 마지막 호출자의
    // params 가 다른 callsite 의 데이터를 덮어쓴다 (projectKeys 의 RQ-KEY-COLLISION 과 동일).
    queryKey: actionKeys.list(wid ?? "", params),
    queryFn: () => fetchActionItems(api, wid!, params),
    enabled: !!wid,
  });
}

/**
 * 담당자 표시 이름 맵 (users.id → displayName).
 * 액션 응답은 `assigneeId` 만 실어오므로 이미 캐시된 워크스페이스 멤버 목록으로 이름을 푼다.
 * 탈퇴한 멤버 등 목록에 없는 id 는 맵에 없다 → 호출부가 "알 수 없음" 대신 미표시로 처리한다.
 */
export function useAssigneeNames(wid: string | undefined): Map<string, string> {
  const { data: members } = useMembers(wid);
  return useMemo(() => {
    const map = new Map<string, string>();
    for (const member of members ?? []) {
      map.set(member.userId, member.displayName ?? member.email ?? "");
    }
    return map;
  }, [members]);
}

/**
 * 액션 아이템 생성
 */
export function useCreateActionItem(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateActionItemRequest) => createActionItem(api, wid!, data),
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: actionKeys.byWorkspace(wid) });
      }
    },
  });
}

/**
 * 액션 아이템 수정
 */
export function useUpdateActionItem(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateActionItemRequest }) => updateActionItem(api, wid!, id, data),
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: actionKeys.byWorkspace(wid) });
      }
    },
  });
}
