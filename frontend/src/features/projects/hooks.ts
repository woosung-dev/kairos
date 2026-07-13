"use client";

import { useApiClient } from "@/lib/use-api-client";
import { useMemo } from "react";
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
import { onboardingKeys } from "@/features/onboarding/api";
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
  const api = useApiClient();

  return useQuery({
    queryKey: projectKeys.list(wid ?? "", params),
    queryFn: () => fetchProjects(api, wid!, params),
    enabled: !!wid,
  });
}

/**
 * 프로젝트 상세 조회
 */
export function useProject(wid: string | undefined, id: string) {
  const api = useApiClient();

  return useQuery({
    queryKey: projectKeys.detail(wid ?? "", id),
    queryFn: () => fetchProject(api, wid!, id),
    enabled: !!wid,
  });
}

/**
 * 프로젝트 생성
 */
export function useCreateProject(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateProjectRequest) => createProject(api, wid!, data),
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: projectKeys.list(wid) });
      }
      // Sprint 22 OBN-02: 프로젝트 생성 시 BE 가 onboarding step=2 advance → 재조회
      queryClient.invalidateQueries({ queryKey: onboardingKeys.all });
    },
  });
}

/**
 * 프로젝트 수정
 */
export function useUpdateProject(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateProjectRequest }) => updateProject(api, wid!, id, data),
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
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteProject(api, wid!, id),
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
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => archiveProject(api, wid!, id),
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
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      meetingId,
      projectId,
    }: {
      meetingId: string;
      projectId: string;
    }) => addMeetingProject(api, wid!, meetingId, projectId),
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
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      meetingId,
      projectId,
    }: {
      meetingId: string;
      projectId: string;
    }) => removeMeetingProject(api, wid!, meetingId, projectId),
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
  const api = useApiClient();

  return useQuery({
    queryKey: projectKeys.members(wid ?? "", projectId),
    queryFn: () => fetchProjectMembers(api, wid!, projectId),
    enabled: !!wid && !!projectId,
  });
}

/** Project 멤버 추가 (admin 이상) */
export function useAddProjectMember(wid: string | undefined, projectId: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AddProjectMemberRequest) => addProjectMember(api, wid!, projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: projectKeys.members(wid ?? "", projectId),
      });
    },
  });
}

/** Project 멤버 제거 (admin 이상) */
export function useRemoveProjectMember(wid: string | undefined, projectId: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => removeProjectMember(api, wid!, projectId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: projectKeys.members(wid ?? "", projectId),
      });
    },
  });
}
