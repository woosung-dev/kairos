import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useActionItems } from "@/features/actions/hooks";
import { useWorkspaceRole } from "@/features/members/hooks";
import { useMeetings } from "@/features/meetings/hooks";
import { useNotes } from "@/features/notes/hooks";
import { useProject } from "@/features/projects/hooks";
import type { Project } from "@/features/projects/types";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { ProjectDashboard } from "../project-dashboard";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({
    getToken: vi.fn().mockResolvedValue("test-jwt"),
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/features/actions/hooks", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/actions/hooks")>()),
  useActionItems: vi.fn(),
}));

vi.mock("@/features/members/hooks", () => ({
  useWorkspaceRole: vi.fn(),
}));

vi.mock("@/features/meetings/hooks", () => ({
  useMeetings: vi.fn(),
}));

vi.mock("@/features/notes/hooks", () => ({
  useNotes: vi.fn(),
}));

vi.mock("@/features/projects/hooks", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/projects/hooks")>()),
  useProject: vi.fn(),
}));

vi.mock("../../project-members-panel", () => ({
  ProjectMembersPanel: () => null,
}));

const PROJECT: Project = {
  id: "project-1",
  workspaceId: "workspace-1",
  title: "테스트 프로젝트",
  description: null,
  status: "active",
  visibility: "public",
  tags: [],
  sortOrder: 0,
  createdAt: "2026-08-01T00:00:00.000Z",
  updatedAt: "2026-08-01T00:00:00.000Z",
};

function mockEmptyContent() {
  const emptyData = { items: [], total: 0, page: 1, pageSize: 20, hasNext: false };

  vi.mocked(useMeetings).mockReturnValue({
    data: emptyData,
    isLoading: false,
  } as unknown as ReturnType<typeof useMeetings>);
  vi.mocked(useNotes).mockReturnValue({
    data: emptyData,
    isLoading: false,
  } as unknown as ReturnType<typeof useNotes>);
  vi.mocked(useActionItems).mockReturnValue({
    data: emptyData,
    isLoading: false,
  } as unknown as ReturnType<typeof useActionItems>);
}

function renderProjectDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ProjectDashboard projectId={PROJECT.id} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useWorkspaceStore.setState({ activeWorkspaceId: "workspace-1" });
  vi.mocked(useWorkspaceRole).mockReturnValue({
    role: "owner",
    userId: "user-owner",
    isLoading: false,
    isOwner: true,
    isAdmin: true,
    canManage: true,
  });
  vi.mocked(useProject).mockReturnValue({
    data: PROJECT,
    isLoading: false,
    error: null,
  } as ReturnType<typeof useProject>);
  mockEmptyContent();
});

afterEach(() => {
  cleanup();
  useWorkspaceStore.setState({ activeWorkspaceId: null });
  vi.clearAllMocks();
});

describe("ProjectDashboard — 온보딩 게이트", () => {
  it("콘텐츠가 없는 온보딩 상태에서 visibility 배지를 클릭하면 VisibilityChangeDialog가 열린다", () => {
    renderProjectDashboard();

    expect(screen.getByRole("heading", { name: "프로젝트를 시작하세요" })).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Visibility: 공개"));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Visibility 변경")).toBeInTheDocument();
  });
});
