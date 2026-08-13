import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { WorkspaceSwitcher } from "../components/WorkspaceSwitcher";

const { useCreateWorkspace, useWorkspaces } = vi.hoisted(() => ({
  useCreateWorkspace: vi.fn(),
  useWorkspaces: vi.fn(),
}));

const workspaceState = {
  activeWorkspaceId: "workspace-1" as string | null,
  setActiveWorkspaceId: vi.fn(),
};

vi.mock("../hooks", () => ({
  useCreateWorkspace,
  useWorkspaces,
}));

vi.mock("../store", () => ({
  useWorkspaceStore: (selector: (state: typeof workspaceState) => unknown) =>
    selector(workspaceState),
}));

vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: { children: ReactNode }) => <button>{children}</button>,
  DropdownMenuContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuItem: ({ children }: { children: ReactNode }) => <button>{children}</button>,
  DropdownMenuSeparator: () => <hr />,
}));

vi.mock("../components/WorkspaceTypeBadge", () => ({
  WorkspaceTypeBadge: () => <span>workspace type</span>,
}));

function renderSwitcher() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <WorkspaceSwitcher />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  workspaceState.activeWorkspaceId = "workspace-1";
  workspaceState.setActiveWorkspaceId.mockReset();
  useCreateWorkspace.mockReturnValue({ mutate: vi.fn(), isPending: false });
});

describe("WorkspaceSwitcher", () => {
  it("유효 wid에서는 워크스페이스 이름을 보인다", () => {
    useWorkspaces.mockReturnValue({ data: [{ id: "workspace-1", name: "제품팀" }] });

    renderSwitcher();

    expect(screen.getAllByText("제품팀")).toHaveLength(2);
  });

  it("활성 워크스페이스를 찾지 못하면 Kairos 폴백을 보인다", () => {
    useWorkspaces.mockReturnValue({ data: [{ id: "workspace-2", name: "운영팀" }] });

    renderSwitcher();

    expect(screen.getByText("Kairos")).toBeInTheDocument();
  });
});
