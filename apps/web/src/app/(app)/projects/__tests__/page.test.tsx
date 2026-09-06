import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { workspaceKeys } from "@/lib/query-keys";
import type { Workspace } from "@/features/workspaces/types";
import ProjectsPage from "../page";

const { fetchProjects, fetchWorkspaces } = vi.hoisted(() => ({
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

vi.mock("@/features/projects/api", () => ({
  fetchProjects,
  fetchProject: vi.fn(),
  createProject: vi.fn(),
  updateProject: vi.fn(),
  deleteProject: vi.fn(),
  archiveProject: vi.fn(),
  addMeetingProject: vi.fn(),
  removeMeetingProject: vi.fn(),
  fetchProjectMembers: vi.fn(),
  addProjectMember: vi.fn(),
  removeProjectMember: vi.fn(),
}));

vi.mock("@/features/workspaces/store", () => ({
  useWorkspaceStore: (selector: (state: {
    activeWorkspaceId: string;
    hasRole: (role: string) => boolean;
  }) => unknown) => selector({
    activeWorkspaceId: "workspace-1",
    hasRole: () => true,
  }),
}));

vi.mock("@/features/projects/components/project-card", () => ({
  ProjectCard: ({ project }: { project: { title: string } }) => <div>{project.title}</div>,
}));

vi.mock("@/features/projects/components/create-project-dialog", () => ({
  CreateProjectDialog: () => null,
}));

vi.mock("@/components/onboarding/onboarding-tooltip", () => ({
  OnboardingTooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

const WORKSPACE: Workspace = {
  id: "workspace-1",
  name: "테스트 워크스페이스",
  ownerId: "owner-1",
  createdAt: "2026-08-02T00:00:00Z",
  updatedAt: "2026-08-02T00:00:00Z",
};

function createWrapper(workspaces?: Workspace[], staleTime: number = Infinity) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime } },
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

describe("ProjectsPage workspace id 가드", () => {
  it("workspace 목록 미해소 중에는 빈 상태 대신 로딩을 렌더한다", async () => {
    fetchWorkspaces.mockImplementation(() => new Promise(() => undefined));

    render(<ProjectsPage />, { wrapper: createWrapper() });

    await waitFor(() => expect(fetchWorkspaces).toHaveBeenCalledTimes(1));
    expect(screen.getByText("프로젝트 불러오는 중...")).toBeInTheDocument();
    expect(screen.queryByTestId("projects-empty-state")).not.toBeInTheDocument();
    expect(fetchProjects).not.toHaveBeenCalled();
  });

  it("workspace 목록 조회 오류 시 빈 상태 대신 에러를 렌더한다", async () => {
    fetchWorkspaces.mockRejectedValue(new Error("workspace 목록 조회 실패"));

    render(<ProjectsPage />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByText("프로젝트를 불러오지 못했습니다")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("projects-empty-state")).not.toBeInTheDocument();
    expect(fetchProjects).not.toHaveBeenCalled();
  });

  it("유효한 workspace 목록의 background refetch 오류에도 그리드를 유지한다", async () => {
    fetchWorkspaces.mockRejectedValue(new Error("workspace 목록 재조회 실패"));
    fetchProjects.mockResolvedValue({
      items: [{ id: "project-1", title: "프로젝트 A" }],
    });

    render(<ProjectsPage />, { wrapper: createWrapper([WORKSPACE], 0) });

    await waitFor(() => expect(fetchWorkspaces).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByTestId("projects-grid")).toBeInTheDocument());
    expect(screen.queryByText("프로젝트를 불러오지 못했습니다")).not.toBeInTheDocument();
    expect(screen.queryByTestId("projects-empty-state")).not.toBeInTheDocument();
  });

  it("접근 가능한 workspace가 없으면 로딩을 끝내고 빈 상태를 렌더한다", async () => {
    render(<ProjectsPage />, { wrapper: createWrapper([]) });

    await waitFor(() => expect(screen.getByTestId("projects-empty-state")).toBeInTheDocument());
    expect(screen.queryByText("프로젝트 불러오는 중...")).not.toBeInTheDocument();
    expect(fetchProjects).not.toHaveBeenCalled();
  });

  it("프로젝트가 있으면 그리드를 렌더한다", async () => {
    fetchProjects.mockResolvedValue({
      items: [{ id: "project-1", title: "프로젝트 A" }],
    });

    render(<ProjectsPage />, { wrapper: createWrapper([WORKSPACE]) });

    await waitFor(() => expect(screen.getByTestId("projects-grid")).toBeInTheDocument());
    expect(screen.getByText("프로젝트 A")).toBeInTheDocument();
    expect(screen.queryByTestId("projects-empty-state")).not.toBeInTheDocument();
  });

  it("프로젝트가 실제로 없으면 빈 상태를 렌더한다", async () => {
    fetchProjects.mockResolvedValue({ items: [] });

    render(<ProjectsPage />, { wrapper: createWrapper([WORKSPACE]) });

    await waitFor(() => expect(screen.getByTestId("projects-empty-state")).toBeInTheDocument());
    expect(screen.queryByTestId("projects-grid")).not.toBeInTheDocument();
  });
});

// PR #189 후속 E — 상태 필터 pill 은 이전에 테스트 0건이었다 (완료 프로젝트 소실 fix 가 무가드).
describe("ProjectsPage 상태 필터", () => {
  it("완료 탭을 누르면 status=completed 로 재조회하고 빈 상태에 생성 CTA 를 숨긴다", async () => {
    fetchProjects.mockResolvedValue({ items: [] });

    render(<ProjectsPage />, { wrapper: createWrapper([WORKSPACE]) });
    await waitFor(() => expect(screen.getByTestId("projects-empty-state")).toBeInTheDocument());
    expect(fetchProjects).toHaveBeenLastCalledWith(expect.anything(), "workspace-1", { status: "active" });
    // 진행 중 빈 상태에는 생성 CTA 가 있다
    expect(within(screen.getByTestId("projects-empty-state")).getByText("새 프로젝트")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("projects-status-completed"));

    await waitFor(() =>
      expect(fetchProjects).toHaveBeenLastCalledWith(expect.anything(), "workspace-1", {
        status: "completed",
      }),
    );
    expect(screen.getByRole("tab", { name: "완료" })).toHaveAttribute("aria-selected", "true");
    await waitFor(() => expect(screen.getByText("완료된 프로젝트가 없습니다")).toBeInTheDocument());
    // 완료 탭의 빈 상태에는 생성 CTA 가 없다 (헤더의 "새 프로젝트" 버튼과는 별개)
    expect(within(screen.getByTestId("projects-empty-state")).queryByText("새 프로젝트")).not.toBeInTheDocument();
  });
});
