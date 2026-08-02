import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { workspaceKeys } from "@/lib/query-keys";
import type { Workspace } from "@/features/workspaces/types";
import { useInbox } from "../hooks";

const { fetchInbox, fetchWorkspaces } = vi.hoisted(() => ({
  fetchInbox: vi.fn(),
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
  fetchInbox,
  classifyInboxItem: vi.fn(),
  dismissInboxItem: vi.fn(),
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

afterEach(() => {
  vi.clearAllMocks();
});

describe("useInbox workspace id 가드", () => {
  it("목록에 있는 wid에서는 요청한다", async () => {
    fetchInbox.mockResolvedValue({ items: [] });

    renderHook(() => useInbox(WID), { wrapper: createWrapper([WORKSPACE]) });

    await waitFor(() => expect(fetchInbox).toHaveBeenCalledTimes(1));
  });

  it("목록에 없는 wid에서는 요청하지 않는다", async () => {
    renderHook(() => useInbox(WID), {
      wrapper: createWrapper([{ ...WORKSPACE, id: "other-workspace" }]),
    });

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fetchInbox).not.toHaveBeenCalled();
  });

  it("workspace 목록 로딩 중에는 요청하지 않는다", async () => {
    fetchWorkspaces.mockImplementation(() => new Promise(() => undefined));

    renderHook(() => useInbox(WID), { wrapper: createWrapper() });

    await waitFor(() => expect(fetchWorkspaces).toHaveBeenCalledTimes(1));
    expect(fetchInbox).not.toHaveBeenCalled();
  });
});
