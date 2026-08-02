import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { workspaceKeys } from "@/lib/query-keys";
import type { Workspace } from "@/features/workspaces/types";
import { useProject, useProjectMembers, useProjects } from "../hooks";

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
