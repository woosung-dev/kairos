"use client";

import { memberKeys, inviteKeys, workspaceKeys } from "@/lib/query-keys";
import { useApiClient } from "@/lib/use-api-client";
import {
  useWorkspaceIdGuard,
  withWorkspaceGuardLoading,
} from "@/features/workspaces/hooks";
import { useEffect } from "react";
import { useUser } from "@clerk/nextjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useWorkspaceStore } from "@/features/workspaces/store";
import {
  fetchMembers,
  updateMemberRole,
  removeMember,
  fetchInvites,
  createInvite,
  deactivateInvite,
  fetchInviteInfo,
  acceptInvite,
} from "./api";
import { toast } from "sonner";
import type {
  CreateInviteRequest,
  Invite,
  UpdateMemberRoleRequest,
} from "./types";

// --- 역할 동기화 훅 (앱 초기화 시 호출) ---

export function useSyncWorkspaceRole(wid: string | undefined) {
  const { user } = useUser();
  const { data: members, isLoading: isMembersLoading } = useMembers(wid);
  const setWorkspaceRole = useWorkspaceStore((s) => s.setWorkspaceRole);

  useEffect(() => {
    if (isMembersLoading) {
      return;
    }

    if (!members || !user) {
      setWorkspaceRole(null);
      return;
    }
    // Clerk user.id로 직접 매칭 (email은 JWT claims에 미포함)
    const me = members.find((m) => m.clerkId === user.id);
    setWorkspaceRole(me?.role ?? null);
  }, [members, isMembersLoading, user, setWorkspaceRole]);
}

// --- 멤버 훅 ---

export function useMembers(wid: string | undefined) {
  const api = useApiClient();
  const { isValidWorkspaceId, isWorkspaceListPending, workspaceListError } =
    useWorkspaceIdGuard(wid);

  const query = useQuery({
    queryKey: memberKeys.list(wid ?? ""),
    queryFn: () => fetchMembers(api, wid!),
    enabled: !!wid && isValidWorkspaceId,
    // 권한 표면 — 전역 focus refetch off 에서 예외 (role 변경/제거 반영 지연 방지)
    refetchOnWindowFocus: true,
  });

  return withWorkspaceGuardLoading(query, isWorkspaceListPending, workspaceListError);
}

export function useWorkspaceRole(workspaceId: string | undefined) {
  const { user } = useUser();
  const { data: members, isLoading } = useMembers(workspaceId);

  // clerkId 기반 매칭 (email은 JWT claims에 미포함)
  const me = members?.find((m) => m.clerkId === user?.id) ?? null;
  const role = me?.role ?? null;

  // workspaceId 가 비어있으면 fetch 자체가 enabled=false → isLoading=false 로 간주.
  // members 미로딩 상태에서는 권한 분기 컴포넌트가 placeholder/spinner 를 띄울 수 있도록 노출.
  return {
    role,
    // BL-NOTE-DELETE-POLICY-1: 작성자 판정용 **내부** user id (Clerk id 아님).
    // 리소스의 createdById 와 대조하는 용도 — 별도 API 없이 members 응답에서 얻는다.
    userId: me?.userId ?? null,
    isLoading: !!workspaceId && isLoading,
    isOwner: role === "owner",
    isAdmin: role === "admin" || role === "owner",
    canManage: role === "admin" || role === "owner",
  };
}

export function useUpdateMemberRole(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      memberId,
      data,
    }: {
      memberId: string;
      data: UpdateMemberRoleRequest;
    }) => updateMemberRole(api, wid!, memberId, data),
    onSuccess: (_data, variables) => {
      toast.success(`역할이 ${variables.data.role}로 변경되었습니다`);
      if (wid) {
        queryClient.invalidateQueries({ queryKey: memberKeys.list(wid) });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "역할 변경에 실패했습니다");
    },
  });
}

export function useRemoveMember(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (memberId: string) => removeMember(api, wid!, memberId),
    onSuccess: () => {
      toast.success("멤버가 제거되었습니다");
      if (wid) {
        queryClient.invalidateQueries({ queryKey: memberKeys.list(wid) });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "멤버 제거에 실패했습니다");
    },
  });
}

// --- 초대 훅 ---

// Sprint 23 Codex 7차 P2 fix: enabled override 옵션 — admin/owner 만 호출 가능한
// GET /workspaces/{id}/invites 가 member/viewer 에게 403 unauthorized 발생하지 않도록.
// 기존 호출자 (admin manager UI 내부 InviteManager) 는 항상 admin context 라 enabled
// 미지정 가능 (default true → !!wid).
export function useInvites(
  wid: string | undefined,
  options?: { enabled?: boolean },
) {
  const api = useApiClient();
  const { isValidWorkspaceId, isWorkspaceListPending, workspaceListError } =
    useWorkspaceIdGuard(wid);
  const isInvitesEnabled = options?.enabled ?? true;

  const query = useQuery({
    queryKey: inviteKeys.list(wid ?? ""),
    queryFn: () => fetchInvites(api, wid!),
    enabled: !!wid && isValidWorkspaceId && isInvitesEnabled,
    // 권한 표면 — 전역 focus refetch off 에서 예외 (초대 비활성화 반영 지연 방지)
    refetchOnWindowFocus: true,
  });

  return withWorkspaceGuardLoading(
    query,
    isWorkspaceListPending && isInvitesEnabled,
    isInvitesEnabled ? workspaceListError : null,
  );
}

export function useCreateInvite(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateInviteRequest) => createInvite(api, wid!, data),
    onSuccess: (newInvite) => {
      toast.success("초대 링크가 생성되었습니다");
      if (wid) {
        // BL-038: optimistic update — invalidate 만 하면 refetch 완료까지 race
        // 동안 사용자가 빈 목록 봄. mutation 응답으로 받은 새 invite 를 즉시
        // 캐시 맨 위에 prepend, 그 후 background refetch 로 정합성 확인.
        queryClient.setQueryData<Invite[]>(inviteKeys.list(wid), (old) =>
          old ? [newInvite, ...old] : [newInvite],
        );
        queryClient.invalidateQueries({ queryKey: inviteKeys.list(wid) });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "초대 링크 생성에 실패했습니다");
    },
  });
}

export function useDeactivateInvite(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (inviteId: string) => {
      await deactivateInvite(api, wid!, inviteId);
      return inviteId;
    },
    onSuccess: (deactivatedId) => {
      toast.success("초대 링크가 비활성화되었습니다");
      if (wid) {
        // BL-038: optimistic update — 캐시에서 즉시 제거 후 background refetch.
        queryClient.setQueryData<Invite[]>(inviteKeys.list(wid), (old) =>
          old ? old.filter((inv) => inv.id !== deactivatedId) : old,
        );
        queryClient.invalidateQueries({ queryKey: inviteKeys.list(wid) });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "초대 링크 비활성화에 실패했습니다");
    },
  });
}

// --- 공개 초대 훅 ---

export function useInviteInfo(code: string) {
  return useQuery({
    queryKey: inviteKeys.info(code),
    queryFn: () => fetchInviteInfo(code),
    enabled: !!code,
  });
}

export function useAcceptInvite() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (code: string) => acceptInvite(api, code),
    // 수락하면 내 워크스페이스 목록이 바뀐다. 목록을 갱신하지 않으면 새 ws 가
    // switcher 에 안 보이고, panel-layout self-heal 이 '목록에 없음' 으로 보고
    // 방금 고른 ws 를 덮어쓴다 (BL-FE-WS-HEAL-SCOPE-1 의 목록 대조 전제).
    // useCreateWorkspace 는 setQueryData 로 같은 불변식을 지키고 있었다.
    // ⚠ 현재 앱 안에 /invite 로 가는 링크가 없어 초대는 항상 전체 로드(빈 캐시)로
    // 열리므로 이 경로는 아직 도달 불가다. 불변식을 균일하게 하는 방어다.
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workspaceKeys.list() });
    },
  });
}
