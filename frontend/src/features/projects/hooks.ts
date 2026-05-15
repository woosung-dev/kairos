"use client";

import { useMemo } from "react";
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
  fetchProjectMembers,
  addProjectMember,
  removeProjectMember,
} from "./api";
import type { FetchProjectsParams } from "./api";
import type {
  AddProjectMemberRequest,
  CreateProjectRequest,
  UpdateProjectRequest,
} from "./types";
import { meetingKeys } from "../meetings/api";
import type { Meeting } from "../meetings/types";
import type { Note } from "../notes/types";

/** project-dashboard 의 최근 회의+노트 합본. created/recorded 순. */
export type RecentItem =
  | { kind: "meeting"; data: Meeting }
  | { kind: "note"; data: Note };

/** 회의 + 노트 (최신 5개씩) 를 합쳐 날짜 내림차순으로 정렬한 후 상위 5개 반환. */
export function useRecentItems(
  meetings: Meeting[],
  notes: Note[],
  limit: number = 5,
): RecentItem[] {
  return useMemo(() => {
    const combined: RecentItem[] = [
      ...meetings.map((m): RecentItem => ({ kind: "meeting", data: m })),
      ...notes.slice(0, limit).map((n): RecentItem => ({ kind: "note", data: n })),
    ];
    return combined
      .sort((a, b) => {
        const aDate =
          a.kind === "meeting" ? (a.data.recordedAt ?? a.data.createdAt) : a.data.createdAt;
        const bDate =
          b.kind === "meeting" ? (b.data.recordedAt ?? b.data.createdAt) : b.data.createdAt;
        return new Date(bDate).getTime() - new Date(aDate).getTime();
      })
      .slice(0, limit);
  }, [meetings, notes, limit]);
}

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
      if (wid) {
        queryClient.invalidateQueries({ queryKey: projectKeys.list(wid) });
      }
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
      if (wid) {
        queryClient.invalidateQueries({ queryKey: projectKeys.all });
      }
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
      if (wid) {
        queryClient.invalidateQueries({ queryKey: projectKeys.list(wid) });
      }
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
      if (wid) {
        queryClient.invalidateQueries({ queryKey: projectKeys.all });
      }
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
      if (wid) {
        queryClient.invalidateQueries({
          queryKey: meetingKeys.detail(wid, variables.meetingId),
        });
      }
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
      if (wid) {
        queryClient.invalidateQueries({
          queryKey: meetingKeys.detail(wid, variables.meetingId),
        });
      }
    },
  });
}

// --- Sprint 6 L-6: ProjectMember hooks ---

/** Project 멤버 목록 조회 */
export function useProjectMembers(wid: string | undefined, projectId: string) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: projectKeys.members(wid ?? "", projectId),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return fetchProjectMembers(token, wid!, projectId);
    },
    enabled: !!wid && !!projectId,
  });
}

/** Project 멤버 추가 (admin 이상) */
export function useAddProjectMember(wid: string | undefined, projectId: string) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AddProjectMemberRequest) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return addProjectMember(token, wid!, projectId, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: projectKeys.members(wid ?? "", projectId),
      });
    },
  });
}

/** Project 멤버 제거 (admin 이상) */
export function useRemoveProjectMember(wid: string | undefined, projectId: string) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return removeProjectMember(token, wid!, projectId, userId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: projectKeys.members(wid ?? "", projectId),
      });
    },
  });
}
