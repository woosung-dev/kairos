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

/* ── 토큰 주입 seam 목 (ADR-031) ──
   인증 벤더가 아니라 `useApiClient` 를 목한다. 벤더 SDK 를 목하면 전환 때마다 이 파일이
   따라 깨진다 — seam 을 목하면 그 결합이 사라진다. */
vi.mock("@/lib/use-api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api-client")>(
    "@/lib/api-client",
  );
  return {
    useApiClient: () => actual.createApiClient(async () => "test-jwt"),
    clearAuthTokenCache: vi.fn(),
  };
});

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

// 실물처럼 비공개일 때만 렌더하는 스텁 — `() => null` 이면 패널이 온보딩 게이트 안으로 되돌아가도 잡지 못한다.
vi.mock("../../project-members-panel", () => ({
  ProjectMembersPanel: ({ visibility }: { visibility: string }) =>
    visibility === "private" ? <h2>프로젝트 멤버</h2> : null,
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
  createdById: "user-creator",
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

  // PR #189 P1 #4 회귀 가드: 비공개 + 콘텐츠 0 이어도 멤버 패널은 온보딩 게이트 밖(형제)에서 렌더된다.
  // 이전엔 DashboardContent 의 children 이라 온보딩 뷰에 가려져 owner 가 멤버를 추가할 방법이 없었다.
  it("비공개 프로젝트는 콘텐츠가 없어도 멤버 패널을 온보딩 뷰와 함께 렌더한다", () => {
    vi.mocked(useProject).mockReturnValue({
      data: { ...PROJECT, visibility: "private" },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useProject>);

    renderProjectDashboard();

    expect(screen.getByRole("heading", { name: "프로젝트를 시작하세요" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "프로젝트 멤버" })).toBeInTheDocument();
  });

  it("공개 프로젝트에는 멤버 패널이 없다", () => {
    renderProjectDashboard();

    expect(screen.queryByRole("heading", { name: "프로젝트 멤버" })).not.toBeInTheDocument();
  });
});

// 2026-09-27 결정 — 작성자는 member 여도 visibility 를 바꿀 수 있다. 판정 축은 멤버십의 내부 users.id.
describe("ProjectDashboard — 작성자 visibility 권한", () => {
  function mockRole(userId: string, role: "member" | "viewer" = "member") {
    vi.mocked(useWorkspaceRole).mockReturnValue({
      role,
      userId,
      isLoading: false,
      isOwner: false,
      isAdmin: false,
      canManage: false,
    });
  }

  it("member 작성자는 visibility 배지로 변경 다이얼로그를 연다", () => {
    mockRole(PROJECT.createdById);
    renderProjectDashboard();

    fireEvent.click(screen.getByLabelText("Visibility: 공개"));

    expect(screen.getByText("Visibility 변경")).toBeInTheDocument();
  });

  it("viewer 로 강등된 작성자는 배지가 비활성이다 (BE PATCH 는 member 이상)", () => {
    mockRole(PROJECT.createdById, "viewer");
    renderProjectDashboard();

    expect(screen.getByLabelText("Visibility: 공개")).toBeDisabled();
    expect(screen.queryByLabelText("프로젝트 관리 메뉴")).toBeNull();
  });

  it("작성자가 아닌 member 는 배지가 비활성이고 관리 메뉴도 없다", () => {
    mockRole("user-someone-else");
    renderProjectDashboard();

    expect(screen.getByLabelText("Visibility: 공개")).toBeDisabled();
    expect(screen.queryByLabelText("프로젝트 관리 메뉴")).toBeNull();
  });
});
