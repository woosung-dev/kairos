import type { ComponentPropsWithoutRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { ActionItem } from "@/features/actions/types";
import type { Project } from "@/features/projects/types";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { ActionBoard } from "../action-board";

const { mockUseActionItems, mockUseUpdateActionItem, mockUseProjectTitleMap, mutate } = vi.hoisted(
  () => ({
    mockUseActionItems: vi.fn(),
    mockUseUpdateActionItem: vi.fn(),
    mockUseProjectTitleMap: vi.fn(),
    mutate: vi.fn(),
  }),
);

// 데이터 훅 mock — 판정 대상인 ActionBoard 자체는 실물로 렌더한다.
vi.mock("../../hooks", () => ({
  useActionItems: mockUseActionItems,
  useUpdateActionItem: mockUseUpdateActionItem,
  // 담당자 이름 맵 — 실물은 useMembers 로 워크스페이스 멤버를 읽는다
  useAssigneeNames: () =>
    new Map([
      [ME_ID, "나"],
      [OTHER_ID, "다른 사람"],
    ]),
}));

// 전 상태 프로젝트 제목 맵 — 실물은 useProjects(wid, { pageSize: 100 }) 위에 얹힌다.
vi.mock("@/features/projects/hooks", () => ({
  useProjectTitleMap: mockUseProjectTitleMap,
}));

const ME_ID = "00000000-0000-0000-0000-0000000000aa";
const OTHER_ID = "00000000-0000-0000-0000-0000000000bb";

vi.mock("@/features/auth/hooks", () => ({
  useMe: () => ({
    data: { id: ME_ID, displayName: "나", email: "me@example.com" },
  }),
}));

vi.mock("next/link", () => ({
  default: ({ children, ...props }: ComponentPropsWithoutRef<"a">) => (
    <a {...props}>{children}</a>
  ),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

const WORKSPACE_ID = "11111111-1111-1111-1111-111111111111";

const PROJECT_A: Project = {
  id: "project-a",
  workspaceId: WORKSPACE_ID,
  title: "프로젝트 A",
  description: null,
  status: "active",
  visibility: "public",
  tags: [],
  sortOrder: 0,
  createdAt: "2026-08-01T00:00:00.000Z",
  updatedAt: "2026-08-01T00:00:00.000Z",
};

const PROJECT_B: Project = { ...PROJECT_A, id: "project-b", title: "프로젝트 B", sortOrder: 1 };
// 완료·보관 프로젝트 — 이전엔 active 20건만 조회해 이들의 액션 칩이 "프로젝트" 로 퇴화했다.
const PROJECT_C: Project = { ...PROJECT_A, id: "project-c", title: "프로젝트 C", status: "completed", sortOrder: 2 };
const PROJECT_D: Project = { ...PROJECT_A, id: "project-d", title: "프로젝트 D", status: "archived", sortOrder: 3 };
const ALL_PROJECTS = [PROJECT_A, PROJECT_B, PROJECT_C, PROJECT_D];

function action(overrides: Partial<ActionItem> & Pick<ActionItem, "id" | "title">): ActionItem {
  return {
    meetingId: null,
    projectId: null,
    description: null,
    assigneeId: null,
    dueDate: null,
    priority: "medium",
    status: "todo",
    createdAt: "2026-09-01T00:00:00.000Z",
    updatedAt: "2026-09-01T00:00:00.000Z",
    ...overrides,
  };
}

/** 4건: 완료 1 / 지연·높음 1 / 프로젝트 미배정 1 / 내 담당(진행 중, 회의 출처) 1 */
const ACTIONS: ActionItem[] = [
  action({
    id: "a-done",
    title: "완료된 액션",
    status: "done",
    projectId: PROJECT_A.id,
    updatedAt: "2026-09-03T00:00:00.000Z",
  }),
  action({
    id: "a-overdue",
    title: "지연된 액션",
    priority: "high",
    dueDate: "2020-01-01",
    projectId: PROJECT_A.id,
    assigneeId: OTHER_ID,
  }),
  action({
    id: "a-unassigned",
    title: "미배정 액션",
    projectId: null,
  }),
  action({
    id: "a-mine",
    title: "내 액션",
    status: "in_progress",
    projectId: PROJECT_B.id,
    meetingId: "meeting-1",
    assigneeId: ME_ID,
  }),
];

function visibleTitles(): string[] {
  return screen
    .getAllByTestId("action-row")
    .map((row) => within(row).getByRole("checkbox").getAttribute("aria-label") ?? "")
    .map((label) => label.replace(" 완료 토글", ""));
}

beforeEach(() => {
  useWorkspaceStore.setState({ activeWorkspaceId: WORKSPACE_ID, workspaceRole: "member" });
  mockUseActionItems.mockReturnValue({
    data: { items: ACTIONS, total: ACTIONS.length, page: 1, pageSize: 100, hasNext: false },
    isLoading: false,
    error: null,
  });
  mockUseProjectTitleMap.mockReturnValue({
    projects: ALL_PROJECTS,
    byStatus: { active: [PROJECT_A, PROJECT_B], completed: [PROJECT_C], archived: [PROJECT_D] },
    titleMap: new Map(ALL_PROJECTS.map((p) => [p.id, p.title])),
    isReady: true,
    isError: false,
    isSettled: true,
    isTruncated: false,
  });
  mockUseUpdateActionItem.mockReturnValue({ mutate, isPending: false, variables: undefined });
});

afterEach(() => {
  cleanup();
  useWorkspaceStore.setState({ activeWorkspaceId: null, workspaceRole: null });
  vi.clearAllMocks();
});

describe("ActionBoard", () => {
  it("상태별 카운트 요약을 렌더한다", () => {
    render(<ActionBoard />);

    expect(screen.getByTestId("action-board")).toBeInTheDocument();
    expect(screen.getByText("할 일 2 · 진행 중 1 · 완료 1")).toBeInTheDocument();
    expect(screen.getAllByTestId("action-row")).toHaveLength(4);
  });

  it("미완료 우선 · 지연 우선 · 완료는 맨 아래로 정렬한다", () => {
    render(<ActionBoard />);

    const titles = visibleTitles();
    expect(titles[0]).toBe("지연된 액션");
    expect(titles[titles.length - 1]).toBe("완료된 액션");
  });

  it("할 일 필터를 누르면 완료·진행 중 행이 사라진다", () => {
    render(<ActionBoard />);

    fireEvent.click(screen.getByTestId("action-status-filter-todo"));

    expect(screen.queryByText("완료된 액션")).not.toBeInTheDocument();
    expect(screen.queryByText("내 액션")).not.toBeInTheDocument();
    expect(visibleTitles()).toEqual(["지연된 액션", "미배정 액션"]);
  });

  it("프로젝트 select 로 특정 프로젝트 / 미배정 액션만 남긴다", () => {
    render(<ActionBoard />);
    const select = screen.getByRole("combobox", { name: "프로젝트 필터" });

    fireEvent.change(select, { target: { value: PROJECT_B.id } });
    expect(visibleTitles()).toEqual(["내 액션"]);

    fireEvent.change(select, { target: { value: "__unassigned__" } });
    expect(visibleTitles()).toEqual(["미배정 액션"]);
  });

  it("내 액션만 토글은 assignee 가 나인 액션만 남긴다", () => {
    render(<ActionBoard />);

    fireEvent.click(screen.getByTestId("action-mine-filter"));

    expect(visibleTitles()).toEqual(["내 액션"]);
  });

  it("체크박스 클릭 시 status=done 으로 update mutation 을 호출한다", () => {
    render(<ActionBoard />);

    fireEvent.click(screen.getByLabelText("미배정 액션 완료 토글"));

    expect(mutate).toHaveBeenCalledTimes(1);
    expect(mutate).toHaveBeenCalledWith(
      { id: "a-unassigned", data: { status: "done" } },
      expect.objectContaining({ onError: expect.any(Function) }),
    );
  });

  it("완료된 액션의 체크박스는 status=todo 로 되돌린다", () => {
    render(<ActionBoard />);

    fireEvent.click(screen.getByLabelText("완료된 액션 완료 토글"));

    expect(mutate).toHaveBeenCalledWith(
      { id: "a-done", data: { status: "todo" } },
      expect.anything(),
    );
  });

  it("viewer 는 체크박스가 비활성이고 안내 title 이 붙는다", () => {
    useWorkspaceStore.setState({ workspaceRole: "viewer" });
    render(<ActionBoard />);

    const checkbox = screen.getByLabelText("미배정 액션 완료 토글");
    expect(checkbox).toBeDisabled();
    expect(checkbox).toHaveAttribute("title", "Member 이상만 변경할 수 있습니다");
  });

  it("프로젝트 칩과 원본 회의 링크를 Next Link 로 렌더한다", () => {
    render(<ActionBoard />);

    expect(screen.getByRole("link", { name: "프로젝트 B" })).toHaveAttribute(
      "href",
      `/projects/${PROJECT_B.id}`,
    );
    expect(screen.getByRole("link", { name: "원본 회의 보기" })).toHaveAttribute(
      "href",
      "/meetings/meeting-1",
    );
  });

  it("액션이 하나도 없으면 회의 추가 CTA 가 있는 빈 상태를 렌더한다", () => {
    mockUseActionItems.mockReturnValue({
      data: { items: [], total: 0, page: 1, pageSize: 100, hasNext: false },
      isLoading: false,
      error: null,
    });
    render(<ActionBoard />);

    expect(screen.getByText("액션 아이템이 없습니다")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "회의 추가" })).toHaveAttribute("href", "/new");
  });

  it("필터 결과만 비어 있으면 CTA 없이 필터 안내를 렌더한다", () => {
    render(<ActionBoard />);

    fireEvent.click(screen.getByTestId("action-status-filter-done"));
    fireEvent.click(screen.getByTestId("action-mine-filter"));

    expect(screen.getByText(/필터를 바꿔보세요/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "회의 추가" })).not.toBeInTheDocument();
  });

  it("완료·보관 프로젝트의 액션도 실제 제목 칩으로 렌더하고 select 에 그룹으로 나온다", () => {
    mockUseActionItems.mockReturnValue({
      data: {
        items: [
          action({ id: "a-c", title: "완료 프로젝트 액션", projectId: PROJECT_C.id }),
          action({ id: "a-d", title: "보관 프로젝트 액션", projectId: PROJECT_D.id }),
        ],
        total: 2,
        page: 1,
        pageSize: 100,
        hasNext: false,
      },
      isLoading: false,
      error: null,
    });
    render(<ActionBoard />);

    expect(screen.getByRole("link", { name: "프로젝트 C" })).toHaveAttribute("href", `/projects/${PROJECT_C.id}`);
    expect(screen.getByRole("link", { name: "프로젝트 D" })).toHaveAttribute("href", `/projects/${PROJECT_D.id}`);
    expect(screen.queryByRole("link", { name: "프로젝트" })).not.toBeInTheDocument();

    const done = screen.getByRole("group", { name: "완료" });
    expect(within(done).getByRole("option", { name: "프로젝트 C" })).toBeInTheDocument();
    const archived = screen.getByRole("group", { name: "보관" });
    expect(within(archived).getByRole("option", { name: "프로젝트 D" })).toBeInTheDocument();
    // 진행 중은 그룹 없이 평면
    expect(screen.getByRole("option", { name: "프로젝트 A" }).closest("optgroup")).toBeNull();
  });

  it("상태 pill 은 tablist/tab + aria-selected 로 선택 상태를 노출한다 (/projects 와 동일 패턴)", () => {
    render(<ActionBoard />);

    const tablist = screen.getByRole("tablist", { name: "액션 상태 필터" });
    expect(within(tablist).getAllByRole("tab")).toHaveLength(4);
    expect(screen.getByRole("tab", { name: "전체" })).toHaveAttribute("aria-selected", "true");

    fireEvent.click(screen.getByRole("tab", { name: "할 일" }));

    expect(screen.getByRole("tab", { name: "할 일" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "전체" })).toHaveAttribute("aria-selected", "false");
    // '내 액션만' 은 토글 — aria-pressed 유지, tab 아님
    expect(screen.getByTestId("action-mine-filter")).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTestId("action-mine-filter")).not.toHaveAttribute("role", "tab");
  });

  it("total 이 받은 건수보다 크면 잘림 안내를, 아니면 안내 없이 렌더한다", () => {
    render(<ActionBoard />);
    expect(screen.queryByText(/더 있음/)).not.toBeInTheDocument();
    cleanup();

    mockUseActionItems.mockReturnValue({
      data: { items: ACTIONS, total: 150, page: 1, pageSize: 100, hasNext: true },
      isLoading: false,
      error: null,
    });
    render(<ActionBoard />);
    expect(screen.getByText(/최근 4건만 표시 · 146건 더 있음/)).toBeInTheDocument();
  });

  it("부제는 실제 기능(회의 추출)만 말한다 — 직접 추가 UI 는 없다", () => {
    render(<ActionBoard />);
    expect(screen.getByText("회의에서 추출된 액션을 한곳에서 관리합니다")).toBeInTheDocument();
    expect(screen.queryByText(/직접 추가한/)).not.toBeInTheDocument();
  });

  it("워크스페이스 미선택 시 안내 문구를 렌더한다", () => {
    useWorkspaceStore.setState({ activeWorkspaceId: null });
    mockUseActionItems.mockReturnValue({ data: undefined, isLoading: false, error: null });
    render(<ActionBoard />);

    expect(screen.getByText("워크스페이스를 선택해주세요")).toBeInTheDocument();
  });
});
