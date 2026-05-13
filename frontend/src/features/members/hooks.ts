"use client";

import { useEffect } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useWorkspaceStore } from "@/features/workspaces/store";
import {
  memberKeys,
  inviteKeys,
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
  UpdateMemberRoleRequest,
} from "./types";

// --- 역할 동기화 훅 (앱 초기화 시 호출) ---

export function useSyncWorkspaceRole(wid: string | undefined) {
  const { user } = useUser();
  const { data: members } = useMembers(wid);
  const setWorkspaceRole = useWorkspaceStore((s) => s.setWorkspaceRole);

  useEffect(() => {
    if (!members || !user) {
      setWorkspaceRole(null);
      return;
    }
    // Clerk user.id로 직접 매칭 (email은 JWT claims에 미포함)
    const me = members.find((m) => m.clerkId === user.id);
    setWorkspaceRole(me?.role ?? null);
  }, [members, user, setWorkspaceRole]);
}

// --- 멤버 훅 ---

export function useMembers(wid: string | undefined) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: memberKeys.list(wid ?? ""),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchMembers(token, wid!);
    },
    enabled: !!wid,
  });
}

export function useWorkspaceRole(workspaceId: string | undefined) {
  const { user } = useUser();
  const { data: members, isLoading } = useMembers(workspaceId);

  // clerkId 기반 매칭 (email은 JWT claims에 미포함)
  const role =
    members?.find((m) => m.clerkId === user?.id)?.role ?? null;

  // workspaceId 가 비어있으면 fetch 자체가 enabled=false → isLoading=false 로 간주.
  // members 미로딩 상태에서는 권한 분기 컴포넌트가 placeholder/spinner 를 띄울 수 있도록 노출.
  return {
    role,
    isLoading: !!workspaceId && isLoading,
    isOwner: role === "owner",
    isAdmin: role === "admin" || role === "owner",
    canManage: role === "admin" || role === "owner",
  };
}

export function useUpdateMemberRole(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      memberId,
      data,
    }: {
      memberId: string;
      data: UpdateMemberRoleRequest;
    }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return updateMemberRole(token, wid!, memberId, data);
    },
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
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (memberId: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return removeMember(token, wid!, memberId);
    },
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

export function useInvites(wid: string | undefined) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: inviteKeys.list(wid ?? ""),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchInvites(token, wid!);
    },
    enabled: !!wid,
  });
}

export function useCreateInvite(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateInviteRequest) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return createInvite(token, wid!, data);
    },
    onSuccess: () => {
      toast.success("초대 링크가 생성되었습니다");
      if (wid) {
        queryClient.invalidateQueries({ queryKey: inviteKeys.list(wid) });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "초대 링크 생성에 실패했습니다");
    },
  });
}

export function useDeactivateInvite(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (inviteId: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return deactivateInvite(token, wid!, inviteId);
    },
    onSuccess: () => {
      toast.success("초대 링크가 비활성화되었습니다");
      if (wid) {
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
  const { getToken } = useAuth();

  return useMutation({
    mutationFn: async (code: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return acceptInvite(token, code);
    },
  });
}
