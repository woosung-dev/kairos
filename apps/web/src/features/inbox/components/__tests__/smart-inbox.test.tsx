import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { workspaceKeys } from "@/lib/query-keys";
import type { Workspace } from "@/features/workspaces/types";
import { SmartInbox } from "../smart-inbox";

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

vi.mock("@/features/inbox/api", () => ({
  fetchInbox,
  classifyInboxItem: vi.fn(),
  dismissInboxItem: vi.fn(),
}));

vi.mock("@/features/workspaces/store", () => ({
  useWorkspaceStore: (selector: (state: { activeWorkspaceId: string }) => unknown) =>
    selector({ activeWorkspaceId: "workspace-1" }),
}));

vi.mock("../inbox-item-card", () => ({
  SmartInboxItemCard: ({ item }: { item: { title: string } }) => <div>{item.title}</div>,
}));

const WORKSPACE: Workspace = {
  id: "workspace-1",
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

describe("SmartInbox workspace id 가드", () => {
  it("workspace 목록 미해소 중에는 빈 상태 대신 로딩을 렌더한다", async () => {
    fetchWorkspaces.mockImplementation(() => new Promise(() => undefined));

    render(<SmartInbox />, { wrapper: createWrapper() });

    await waitFor(() => expect(fetchWorkspaces).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Inbox")).toBeInTheDocument();
    expect(screen.queryByText("처리할 항목이 없습니다")).not.toBeInTheDocument();
    expect(fetchInbox).not.toHaveBeenCalled();
  });

  it("workspace 목록 조회 오류 시 빈 상태 대신 에러를 렌더한다", async () => {
    fetchWorkspaces.mockRejectedValue(new Error("workspace 목록 조회 실패"));

    render(<SmartInbox />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(
        screen.getByText("데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요."),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText("처리할 항목이 없습니다")).not.toBeInTheDocument();
    expect(fetchInbox).not.toHaveBeenCalled();
  });

  it("접근 가능한 workspace가 없으면 로딩을 끝내고 빈 상태를 렌더한다", async () => {
    render(<SmartInbox />, { wrapper: createWrapper([]) });

    await waitFor(() => expect(screen.getByText("처리할 항목이 없습니다")).toBeInTheDocument());
    expect(fetchInbox).not.toHaveBeenCalled();
  });

  it("Inbox 항목이 있으면 목록을 렌더한다", async () => {
    fetchInbox.mockResolvedValue({
      items: [{ id: "inbox-1", title: "Inbox A" }],
    });

    render(<SmartInbox />, { wrapper: createWrapper([WORKSPACE]) });

    await waitFor(() => expect(screen.getByText("Inbox A")).toBeInTheDocument());
    expect(screen.queryByText("처리할 항목이 없습니다")).not.toBeInTheDocument();
  });

  it("Inbox 항목이 실제로 없으면 빈 상태를 렌더한다", async () => {
    fetchInbox.mockResolvedValue({ items: [] });

    render(<SmartInbox />, { wrapper: createWrapper([WORKSPACE]) });

    await waitFor(() => expect(screen.getByText("처리할 항목이 없습니다")).toBeInTheDocument());
  });
});
