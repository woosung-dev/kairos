import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { workspaceKeys } from "@/lib/query-keys";
import type { Workspace } from "@/features/workspaces/types";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { useInvites, useMembers, useSyncWorkspaceRole } from "../hooks";

const { fetchInvites, fetchMembers, fetchWorkspaces, userState } = vi.hoisted(() => ({
  fetchInvites: vi.fn(),
  fetchMembers: vi.fn(),
  fetchWorkspaces: vi.fn(),
  userState: { current: { id: "clerk-user-1" } },
}));

vi.mock("@clerk/nextjs", () => ({
  useUser: () => ({ user: userState.current }),
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
  fetchMembers,
  updateMemberRole: vi.fn(),
  removeMember: vi.fn(),
  fetchInvites,
  createInvite: vi.fn(),
  deactivateInvite: vi.fn(),
  fetchInviteInfo: vi.fn(),
  acceptInvite: vi.fn(),
}));

const WID = "workspace-1";
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
  { name: "useMembers", useHook: () => useMembers(WID), fetch: fetchMembers },
  { name: "useInvites", useHook: () => useInvites(WID), fetch: fetchInvites },
];

afterEach(() => {
  vi.clearAllMocks();
  useWorkspaceStore.setState({ workspaceRole: null });
});

describe("멤버 데이터 훅의 workspace id 가드", () => {
  it.each(guardedHooks)("$name: 목록에 있는 wid에서는 요청한다", async ({ useHook, fetch }) => {
    fetch.mockResolvedValue([]);

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

  it.each(guardedHooks)("$name: workspace 목록 오류를 error 상태로 합성한다", async ({ useHook, fetch }) => {
    const workspaceListError = new Error("workspace 목록 조회 실패");
    fetchWorkspaces.mockRejectedValue(workspaceListError);

    const { result } = renderHook(() => useHook(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(workspaceListError);
    expect(result.current.status).toBe("error");
    expect(fetch).not.toHaveBeenCalled();
  });
});

describe("useSyncWorkspaceRole", () => {
  it("workspace 목록 미해소 중에는 기존 role을 null로 덮어쓰지 않는다", async () => {
    useWorkspaceStore.setState({ workspaceRole: "member" });
    fetchWorkspaces.mockImplementation(() => new Promise(() => undefined));

    renderHook(() => useSyncWorkspaceRole(WID), { wrapper: createWrapper() });

    await waitFor(() => expect(fetchWorkspaces).toHaveBeenCalledTimes(1));
    expect(useWorkspaceStore.getState().workspaceRole).toBe("member");
  });

  it("목록 해소 후 현재 사용자가 멤버가 아니면 role을 null로 설정한다", async () => {
    useWorkspaceStore.setState({ workspaceRole: "member" });
    fetchMembers.mockResolvedValue([]);

    renderHook(() => useSyncWorkspaceRole(WID), {
      wrapper: createWrapper([WORKSPACE]),
    });

    await waitFor(() => expect(fetchMembers).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(useWorkspaceStore.getState().workspaceRole).toBeNull());
  });
});
