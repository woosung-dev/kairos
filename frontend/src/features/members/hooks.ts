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
    // Clerk user.id와 매칭되는 멤버를 이메일로 찾음
    const me = members.find(
      (m) => m.email === user.primaryEmailAddress?.emailAddress
    );
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
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: memberKeys.list(wid) });
      }
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
      if (wid) {
        queryClient.invalidateQueries({ queryKey: memberKeys.list(wid) });
      }
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
      if (wid) {
        queryClient.invalidateQueries({ queryKey: inviteKeys.list(wid) });
      }
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
      if (wid) {
        queryClient.invalidateQueries({ queryKey: inviteKeys.list(wid) });
      }
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
