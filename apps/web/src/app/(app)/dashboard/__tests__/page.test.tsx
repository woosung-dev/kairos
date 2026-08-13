import type { ComponentPropsWithoutRef, PropsWithChildren } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { useWorkspaces } from "@/features/workspaces/hooks";
import DashboardPage from "../page";

vi.mock("next/link", () => ({
  default: ({ children, ...props }: ComponentPropsWithoutRef<"a">) => (
    <a {...props} data-next-link="true">
      {children}
    </a>
  ),
}));

vi.mock("@/features/workspaces/hooks", () => ({
  useWorkspaces: vi.fn(),
}));

vi.mock("@/features/workspaces/components/create-workspace-dialog", () => ({
  CreateWorkspaceDialog: () => null,
}));

vi.mock("@/components/empty-state", () => ({
  EmptyState: () => null,
}));

vi.mock("@/store/ui", () => ({
  useUIStore: () => ({ toggleCmdK: vi.fn() }),
}));

vi.mock("@/components/onboarding/onboarding-tooltip", () => ({
  OnboardingTooltip: ({ children }: PropsWithChildren) => <>{children}</>,
}));

vi.mock("@/features/home/components/dashboard-suggestions", () => ({
  DashboardSuggestions: () => null,
}));

beforeEach(() => {
  vi.mocked(useWorkspaces).mockReturnValue({
    data: [{ id: "workspace-1", name: "테스트 워크스페이스" }],
    isLoading: false,
  } as ReturnType<typeof useWorkspaces>);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("DashboardPage 빠른 접근", () => {
  it("각 타일을 기존 href의 Next Link로 렌더한다", () => {
    render(<DashboardPage />);

    expect(screen.getByRole("link", { name: "회의 추가" })).toHaveAttribute("href", "/new");
    expect(screen.getByRole("link", { name: "노트" })).toHaveAttribute("href", "/notes");
    expect(screen.getByRole("link", { name: "Inbox" })).toHaveAttribute("href", "/inbox");
    expect(screen.getByRole("link", { name: "프로젝트" })).toHaveAttribute("href", "/projects");

    for (const label of ["회의 추가", "노트", "Inbox", "프로젝트"]) {
      expect(screen.getByRole("link", { name: label })).toHaveAttribute("data-next-link", "true");
    }
  });
});
