"use client";

import { projectKeys, meetingKeys, onboardingKeys } from "@/lib/query-keys";
import { API_PAGE_SIZE_MAX } from "@/lib/api-client";
import { useApiClient } from "@/lib/use-api-client";
import {
  useWorkspaceIdGuard,
  withWorkspaceGuardLoading,
} from "@/features/workspaces/hooks";
import { useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
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
  const { isValidWorkspaceId, isWorkspaceListPending, workspaceListError } =
    useWorkspaceIdGuard(wid);

  const query = useQuery({
    queryKey: projectKeys.list(wid ?? "", params),
    queryFn: () => fetchProjects(api, wid!, params),
    enabled: !!wid && isValidWorkspaceId,
  });

  return withWorkspaceGuardLoading(query, isWorkspaceListPending, workspaceListError);
}

/**
 * 제목 해석·필터 옵션용 전 상태 프로젝트 목록 (액션 보드 · Inbox 카드 공유).
 *
 * `useProjects(wid, { status: "active" })` 는 active 만 + BE 기본 pageSize 20 이라, 완료·보관 프로젝트나
 * 21번째 이후 프로젝트를 가리키는 액션 칩이 "프로젝트" 로 퇴화하고 Inbox 는 AI 가 지어낸 제목을 다시
 * 노출했다 (PR #189 P1 의 잔여 분기).
 *
 * ★BE `ProjectService.list_projects` 는 status 미지정을 **active 로 기본 처리**한다 (BUG-ARCHIVED-PROJECT-LEAK
 *   방어 — repository 만 보면 "미지정=전체" 로 읽혀 2026-09-06 실측에서 완료 프로젝트가 빠졌다).
 *   그래서 상태 3종을 각각 `API_PAGE_SIZE_MAX`(BE 상한 `le=100`) 로 받아 합친다. 쿼리 키에 params 가 들어가
 *   사이드바의 active/archived 목록과 캐시가 섞이지 않는다.
 */
export function useProjectTitleMap(wid: string | undefined) {
  const active = useProjects(wid, { status: "active", pageSize: API_PAGE_SIZE_MAX });
  const completed = useProjects(wid, { status: "completed", pageSize: API_PAGE_SIZE_MAX });
  const archived = useProjects(wid, { status: "archived", pageSize: API_PAGE_SIZE_MAX });
  const byStatus = useMemo(
    () => ({
      active: active.data?.items ?? [],
      completed: completed.data?.items ?? [],
      archived: archived.data?.items ?? [],
    }),
    [active.data, completed.data, archived.data],
  );
  const projects = useMemo(
    () => [...byStatus.active, ...byStatus.completed, ...byStatus.archived],
    [byStatus],
  );
  const titleMap = useMemo(
    () => new Map<string, string>(projects.map((p) => [p.id, p.title])),
    [projects],
  );
  const queries = [active, completed, archived];
  return {
    projects,
    byStatus,
    titleMap,
    // 셋 다 도착했고 에러가 없을 때만 "목록에 없음" 을 판정한다 — 미도착이거나 재조회가 실패해 이전 캐시만
    // 남은 갈래가 있으면 오판 대신 미표시.
    isReady: queries.every((q) => q.data !== undefined && !q.isError),
    // 한 갈래라도 실패 — 소비처가 "불러오는 중" 과 "불러올 수 없음" 을 구분해 말할 수 있게 한다.
    isError: queries.some((q) => q.isError),
    // 상태 전이(완료/보관) 직후 3갈래 refetch 가 엇갈리는 한 RTT 동안은 "없음" 을 확정하지 않는다.
    isSettled: queries.every((q) => !q.isFetching),
    // 상태별 100건 상한을 넘는 워크스페이스 — 맵에 없다고 "없음" 이라 말할 수 없다.
    isTruncated: queries.some((q) => (q.data?.total ?? 0) > (q.data?.items.length ?? 0)),
  };
}

/**
 * 프로젝트 상세 조회
 */
export function useProject(wid: string | undefined, id: string) {
  const api = useApiClient();
  const { isValidWorkspaceId, isWorkspaceListPending, workspaceListError } =
    useWorkspaceIdGuard(wid);

  const query = useQuery({
    queryKey: projectKeys.detail(wid ?? "", id),
    queryFn: () => fetchProject(api, wid!, id),
    enabled: !!wid && isValidWorkspaceId,
  });

  return withWorkspaceGuardLoading(query, isWorkspaceListPending, workspaceListError);
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
  const { isValidWorkspaceId, isWorkspaceListPending, workspaceListError } =
    useWorkspaceIdGuard(wid);

  const query = useQuery({
    queryKey: projectKeys.members(wid ?? "", projectId),
    queryFn: () => fetchProjectMembers(api, wid!, projectId),
    enabled: !!wid && !!projectId && isValidWorkspaceId,
  });

  return withWorkspaceGuardLoading(query, isWorkspaceListPending, workspaceListError);
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
