import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { workspaceKeys } from "@/lib/query-keys";
import type { Workspace } from "@/features/workspaces/types";
import { useProject, useProjectMembers, useProjectTitleMap, useProjects } from "../hooks";

const {
  fetchProject,
  fetchProjectMembers,
  fetchProjects,
  fetchWorkspaces,
} = vi.hoisted(() => ({
  fetchProject: vi.fn(),
  fetchProjectMembers: vi.fn(),
  fetchProjects: vi.fn(),
  fetchWorkspaces: vi.fn(),
}));

vi.mock("@/lib/use-api-client", () => ({
  useApiClient: () => ({}),
}));

vi.mock("@/features/workspaces/api", () => ({
  fetchWorkspaces,
  createWorkspace: vi.fn(),
  fetchWorkspace: vi.fn(),
  updateWorkspaceSettings: vi.fn(),
  deleteWorkspace: vi.fn(),
}));

vi.mock("../api", () => ({
  fetchProjects,
  fetchProject,
  createProject: vi.fn(),
  updateProject: vi.fn(),
  deleteProject: vi.fn(),
  archiveProject: vi.fn(),
  addMeetingProject: vi.fn(),
  removeMeetingProject: vi.fn(),
  fetchProjectMembers,
  addProjectMember: vi.fn(),
  removeProjectMember: vi.fn(),
}));

const WID = "workspace-1";
const PROJECT_ID = "project-1";
const WORKSPACE: Workspace = {
  id: WID,
  name: "테스트 워크스페이스",
  ownerId: "owner-1",
  createdAt: "2026-08-02T00:00:00Z",
  updatedAt: "2026-08-02T00:00:00Z",
};

function createWrapper(workspaces?: Workspace[]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  if (workspaces !== undefined) {
    queryClient.setQueryData(workspaceKeys.list(), workspaces);
  }

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

const guardedHooks = [
  { name: "useProjects", useHook: () => useProjects(WID), fetch: fetchProjects },
  { name: "useProject", useHook: () => useProject(WID, PROJECT_ID), fetch: fetchProject },
  {
    name: "useProjectMembers",
    useHook: () => useProjectMembers(WID, PROJECT_ID),
    fetch: fetchProjectMembers,
  },
];

afterEach(() => {
  vi.clearAllMocks();
});

describe("프로젝트 데이터 훅의 workspace id 가드", () => {
  it.each(guardedHooks)("$name: 목록에 있는 wid에서는 요청한다", async ({ useHook, fetch }) => {
    fetch.mockResolvedValue({ items: [] });

    renderHook(() => useHook(), { wrapper: createWrapper([WORKSPACE]) });

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  });

  it.each(guardedHooks)("$name: 목록에 없는 wid에서는 요청하지 않는다", async ({ useHook, fetch }) => {
    renderHook(() => useHook(), {
      wrapper: createWrapper([{ ...WORKSPACE, id: "other-workspace" }]),
    });

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fetch).not.toHaveBeenCalled();
  });

  it.each(guardedHooks)("$name: workspace 목록 로딩 중에는 요청하지 않는다", async ({ useHook, fetch }) => {
    fetchWorkspaces.mockImplementation(() => new Promise(() => undefined));

    renderHook(() => useHook(), { wrapper: createWrapper() });

    await waitFor(() => expect(fetchWorkspaces).toHaveBeenCalledTimes(1));
    expect(fetch).not.toHaveBeenCalled();
  });
});

// PR #189 후속 B — 제목 해석 맵은 상태 3종을 각각 pageSize 100 으로 받아 합친다.
// BE ProjectService.list_projects 가 status 미지정을 active 로 기본 처리하므로(BUG-ARCHIVED-PROJECT-LEAK 방어)
// "status 없이 한 번" 으로 바꾸면 완료·보관 프로젝트가 조용히 빠진다 — 2026-09-06 실측으로 잡힌 전제 오류.
describe("useProjectTitleMap", () => {
  it("active/completed/archived 를 각각 pageSize 100 으로 조회해 하나의 제목 맵으로 합친다", async () => {
    fetchProjects.mockImplementation(async (_api: unknown, _wid: string, params?: { status?: string }) => ({
      items: [{ id: `p-${params?.status}`, title: `프로젝트(${params?.status})`, status: params?.status }],
      total: 1,
      page: 1,
      pageSize: 100,
      hasNext: false,
    }));

    const { result } = renderHook(() => useProjectTitleMap(WID), { wrapper: createWrapper([WORKSPACE]) });

    await waitFor(() => expect(result.current.isReady).toBe(true));
    const statuses = fetchProjects.mock.calls.map((c) => c[2]);
    expect(statuses).toEqual(
      expect.arrayContaining([
        { status: "active", pageSize: 100 },
        { status: "completed", pageSize: 100 },
        { status: "archived", pageSize: 100 },
      ]),
    );
    expect(fetchProjects).toHaveBeenCalledTimes(3);
    expect(result.current.projects.map((p) => p.id)).toEqual(["p-active", "p-completed", "p-archived"]);
    expect(result.current.byStatus.completed.map((p) => p.id)).toEqual(["p-completed"]);
    expect(result.current.titleMap.get("p-archived")).toBe("프로젝트(archived)");
  });

  it("한 갈래가 에러면 isReady=false (이전 캐시로 '없음' 오판 방지)", async () => {
    fetchProjects.mockImplementation(async (_api: unknown, _wid: string, params?: { status?: string }) => {
      if (params?.status === "completed") throw new Error("500");
      return { items: [], total: 0, page: 1, pageSize: 100, hasNext: false };
    });

    const { result } = renderHook(() => useProjectTitleMap(WID), { wrapper: createWrapper([WORKSPACE]) });

    await waitFor(() => expect(fetchProjects).toHaveBeenCalledTimes(3));
    await waitFor(() => expect(result.current.isReady).toBe(false));
    expect(result.current.isError).toBe(true);
  });

  it("상태별 total 이 받은 건수보다 크면 isTruncated=true", async () => {
    fetchProjects.mockImplementation(async (_api: unknown, _wid: string, params?: { status?: string }) => ({
      items: [{ id: `p-${params?.status}`, title: "x", status: params?.status }],
      total: params?.status === "completed" ? 150 : 1,
      page: 1,
      pageSize: 100,
      hasNext: params?.status === "completed",
    }));

    const { result } = renderHook(() => useProjectTitleMap(WID), { wrapper: createWrapper([WORKSPACE]) });

    await waitFor(() => expect(result.current.isReady).toBe(true));
    expect(result.current.isTruncated).toBe(true);
    expect(result.current.isSettled).toBe(true);
  });

  it("세 갈래 중 하나라도 미도착이면 isReady=false (없음 오판 방지)", async () => {
    fetchProjects.mockImplementation(async (_api: unknown, _wid: string, params?: { status?: string }) => {
      if (params?.status === "archived") return new Promise(() => undefined);
      return { items: [], total: 0, page: 1, pageSize: 100, hasNext: false };
    });

    const { result } = renderHook(() => useProjectTitleMap(WID), { wrapper: createWrapper([WORKSPACE]) });

    await waitFor(() => expect(fetchProjects).toHaveBeenCalledTimes(3));
    expect(result.current.isReady).toBe(false);
  });
});
