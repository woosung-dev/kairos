"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  projectKeys,
  fetchProjects,
  fetchProject,
  createProject,
  updateProject,
  deleteProject,
  archiveProject,
  addMeetingProject,
  removeMeetingProject,
} from "./api";
import type { FetchProjectsParams } from "./api";
import type { CreateProjectRequest, UpdateProjectRequest } from "./types";
import { meetingKeys } from "../meetings/api";
import { toast } from "sonner";

/**
 * 워크스페이스 내 프로젝트 목록 조회
 */
export function useProjects(wid: string | undefined, params?: FetchProjectsParams) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: projectKeys.list(wid ?? ""),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchProjects(token, wid!, params);
    },
    enabled: !!wid,
  });
}

/**
 * 프로젝트 상세 조회
 */
export function useProject(wid: string | undefined, id: string) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: projectKeys.detail(wid ?? "", id),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchProject(token, wid!, id);
    },
    enabled: !!wid,
  });
}

/**
 * 프로젝트 생성
 */
export function useCreateProject(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateProjectRequest) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return createProject(token, wid!, data);
    },
    onSuccess: () => {
      toast.success("프로젝트가 생성되었습니다");
      if (wid) {
        queryClient.invalidateQueries({ queryKey: projectKeys.list(wid) });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "프로젝트 생성에 실패했습니다");
    },
  });
}

/**
 * 프로젝트 수정
 */
export function useUpdateProject(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateProjectRequest }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return updateProject(token, wid!, id, data);
    },
    onSuccess: () => {
      toast.success("프로젝트가 수정되었습니다");
      if (wid) {
        queryClient.invalidateQueries({ queryKey: projectKeys.all });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "프로젝트 수정에 실패했습니다");
    },
  });
}

/**
 * 프로젝트 삭제
 */
export function useDeleteProject(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return deleteProject(token, wid!, id);
    },
    onSuccess: () => {
      toast.success("프로젝트가 삭제되었습니다");
      if (wid) {
        queryClient.invalidateQueries({ queryKey: projectKeys.list(wid) });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "프로젝트 삭제에 실패했습니다");
    },
  });
}

/**
 * 프로젝트 아카이브
 */
export function useArchiveProject(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return archiveProject(token, wid!, id);
    },
    onSuccess: () => {
      toast.success("프로젝트가 아카이브되었습니다");
      if (wid) {
        queryClient.invalidateQueries({ queryKey: projectKeys.all });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "프로젝트 아카이브에 실패했습니다");
    },
  });
}

/**
 * 회의에 프로젝트 연결
 */
export function useAddMeetingProject(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      meetingId,
      projectId,
    }: {
      meetingId: string;
      projectId: string;
    }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return addMeetingProject(token, wid!, meetingId, projectId);
    },
    onSuccess: (_data, variables) => {
      toast.success("프로젝트가 연결되었습니다");
      if (wid) {
        queryClient.invalidateQueries({
          queryKey: meetingKeys.detail(wid, variables.meetingId),
        });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "프로젝트 연결에 실패했습니다");
    },
  });
}

/**
 * 회의에서 프로젝트 연결 해제
 */
export function useRemoveMeetingProject(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      meetingId,
      projectId,
    }: {
      meetingId: string;
      projectId: string;
    }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return removeMeetingProject(token, wid!, meetingId, projectId);
    },
    onSuccess: (_data, variables) => {
      toast.success("프로젝트 연결이 해제되었습니다");
      if (wid) {
        queryClient.invalidateQueries({
          queryKey: meetingKeys.detail(wid, variables.meetingId),
        });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "프로젝트 연결 해제에 실패했습니다");
    },
  });
}
