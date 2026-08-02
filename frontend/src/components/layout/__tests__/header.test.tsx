import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Header } from "../header";

interface UIState {
  toggleSidebar: () => void;
  toggleRagOverlay: () => void;
}

const { signOut, setActiveWorkspaceId, useIsValidWorkspaceId, useMembers } = vi.hoisted(() => ({
  signOut: vi.fn(),
  setActiveWorkspaceId: vi.fn(),
  useIsValidWorkspaceId: vi.fn(),
  useMembers: vi.fn(),
}));

const workspaceState = {
  activeWorkspaceId: "workspace-1" as string | null,
  setActiveWorkspaceId,
};

vi.mock("@clerk/nextjs", () => ({
  useClerk: () => ({ signOut }),
  useUser: () => ({
    user: {
      fullName: "테스트 사용자",
      firstName: "테",
      primaryEmailAddress: { emailAddress: "test@example.com" },
    },
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/store/ui", () => {
  const state: UIState = { toggleSidebar: vi.fn(), toggleRagOverlay: vi.fn() };
  return {
    useUIStore: (
      selector?: (state: UIState) => unknown,
    ) => (selector ? selector(state) : state),
  };
});

vi.mock("@/features/workspaces/store", () => ({
  useWorkspaceStore: (selector: (state: typeof workspaceState) => unknown) =>
    selector(workspaceState),
}));

vi.mock("@/features/workspaces/hooks", () => ({
  useIsValidWorkspaceId,
}));

vi.mock("@/features/members/hooks", () => ({
  useMembers,
}));

vi.mock("@/features/workspaces/components/WorkspaceSwitcher", () => ({
  WorkspaceSwitcher: () => <span>워크스페이스 전환</span>,
}));

vi.mock("../theme-toggle", () => ({
  ThemeToggle: () => <span>테마 토글</span>,
}));

vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children, ...props }: { children: ReactNode; "aria-label"?: string }) => (
    <button {...props}>{children}</button>
  ),
  DropdownMenuContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuItem: ({ children, onClick }: { children: ReactNode; onClick?: () => void }) => (
    <button onClick={onClick}>{children}</button>
  ),
  DropdownMenuSeparator: () => <hr />,
}));

beforeEach(() => {
  signOut.mockResolvedValue(undefined);
  setActiveWorkspaceId.mockReset();
  useIsValidWorkspaceId.mockReturnValue(true);
  useMembers.mockReturnValue({ data: [] });
});

describe("Header 로그아웃", () => {
  it("query cache를 비우고 signOut하며 activeWorkspaceId를 직접 초기화하지 않는다", async () => {
    const queryClient = new QueryClient();
    const clear = vi.spyOn(queryClient, "clear");

    render(
      <QueryClientProvider client={queryClient}>
        <Header />
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "로그아웃" }));

    await vi.waitFor(() => expect(signOut).toHaveBeenCalledWith({ redirectUrl: "/" }));
    expect(clear).toHaveBeenCalledTimes(1);
    expect(setActiveWorkspaceId).not.toHaveBeenCalled();
  });
});
