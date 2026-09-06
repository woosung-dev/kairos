import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { InboxItem } from "@/features/inbox/types";
import type { Project } from "@/features/projects/types";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { SmartInboxItemCard } from "../inbox-item-card";

// PR #189 P1 잔여 분기 회귀 가드 — AI 추천 라벨은 (a) 실제 제목 / (b) 새 프로젝트 제안 / (c) 프로젝트 없음
// 세 갈래이고, AI 가 지어낸 `aiSuggestedProjectTitle` 은 (b) 에서만 노출된다.

const { mockUseProjectTitleMap, classifyMutate, dismissMutate } = vi.hoisted(() => ({
  mockUseProjectTitleMap: vi.fn(),
  classifyMutate: vi.fn(),
  dismissMutate: vi.fn(),
}));

vi.mock("../../hooks", () => ({
  useDismissInbox: () => ({ mutate: dismissMutate, isPending: false }),
  useClassifyInbox: () => ({ mutate: classifyMutate, isPending: false }),
}));

vi.mock("@/features/projects/hooks", () => ({
  useProjectTitleMap: mockUseProjectTitleMap,
}));

vi.mock("@/components/shared/ItemPromoteModal", () => ({
  ItemPromoteModal: () => null,
}));

const WORKSPACE_ID = "11111111-1111-1111-1111-111111111111";

const PROJECT_ACTIVE: Project = {
  id: "project-active",
  workspaceId: WORKSPACE_ID,
  title: "모바일 앱 v2 출시",
  description: null,
  status: "active",
  visibility: "public",
  tags: [],
  sortOrder: 0,
  createdAt: "2026-08-01T00:00:00.000Z",
  updatedAt: "2026-08-01T00:00:00.000Z",
};
const PROJECT_DONE: Project = {
  ...PROJECT_ACTIVE,
  id: "project-done",
  title: "💡 아이디어",
  status: "completed",
  sortOrder: 1,
};
const ALL_PROJECTS = [PROJECT_ACTIVE, PROJECT_DONE];

function item(overrides: Partial<InboxItem>): InboxItem {
  return {
    id: "inbox-1",
    workspaceId: WORKSPACE_ID,
    title: "투자 IR 덱 리뷰 요약",
    summary: null,
    sourceType: "meeting",
    sourceId: "meeting-1",
    aiSuggestedProjectId: null,
    aiSuggestedProjectTitle: null,
    aiSuggestedTags: [],
    aiConfidence: 0.82,
    isProcessed: false,
    createdAt: "2026-09-01T00:00:00.000Z",
    updatedAt: "2026-09-01T00:00:00.000Z",
    ...overrides,
  };
}

function mockTitleMap(
  projects: Project[],
  isReady = true,
  extra: Partial<{ isError: boolean; isSettled: boolean; isTruncated: boolean }> = {},
) {
  mockUseProjectTitleMap.mockReturnValue({
    projects,
    byStatus: {
      active: projects.filter((p) => p.status === "active"),
      completed: projects.filter((p) => p.status === "completed"),
      archived: projects.filter((p) => p.status === "archived"),
    },
    titleMap: new Map(projects.map((p) => [p.id, p.title])),
    isReady,
    isError: false,
    isSettled: true,
    isTruncated: false,
    ...extra,
  });
}

beforeEach(() => {
  useWorkspaceStore.setState({ activeWorkspaceId: WORKSPACE_ID, workspaceRole: "member" });
  mockTitleMap(ALL_PROJECTS);
});

afterEach(() => {
  cleanup();
  useWorkspaceStore.setState({ activeWorkspaceId: null, workspaceRole: null });
  vi.clearAllMocks();
});

describe("SmartInboxItemCard AI 추천 라벨", () => {
  it("(a) 추천 id 가 완료 프로젝트여도 실제 제목을 쓰고 AI 제목은 노출하지 않는다", () => {
    render(
      <SmartInboxItemCard
        item={item({ aiSuggestedProjectId: PROJECT_DONE.id, aiSuggestedProjectTitle: "IR 투자 유치 전략" })}
      />,
    );

    expect(screen.getByText("AI 추천:")).toBeInTheDocument();
    expect(screen.getByText("💡 아이디어")).toBeInTheDocument();
    expect(screen.queryByText("IR 투자 유치 전략")).not.toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();
  });

  it("(b) id 없이 제목만 있으면 새 프로젝트 제안으로 AI 제목을 보여준다", () => {
    render(<SmartInboxItemCard item={item({ aiSuggestedProjectTitle: "IR 투자 유치 전략" })} />);

    expect(screen.getByText("새 프로젝트 제안:")).toBeInTheDocument();
    expect(screen.getByText("IR 투자 유치 전략")).toBeInTheDocument();
  });

  it("(c) id 가 목록에 없으면 '(프로젝트 없음)' 을 보여주고 확정은 picker 를 연다", () => {
    render(
      <SmartInboxItemCard
        item={item({ aiSuggestedProjectId: "project-deleted", aiSuggestedProjectTitle: "IR 투자 유치 전략" })}
      />,
    );

    expect(screen.getByText("AI 추천:")).toBeInTheDocument();
    expect(screen.getByText("(프로젝트 없음)")).toBeInTheDocument();
    expect(screen.queryByText("IR 투자 유치 전략")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /확정/ }));

    expect(classifyMutate).not.toHaveBeenCalled();
    expect(screen.getByText("프로젝트를 선택하세요")).toBeInTheDocument();
    // 보이지 않는 추천 id 가 숨은 채 제출되지 않는다 — select 는 빈 값, 이동 버튼은 비활성 (codex P1)
    expect(screen.getByRole("combobox", { name: "프로젝트 선택" })).toHaveValue("");
    const move = screen.getByRole("button", { name: "이 프로젝트로 이동" });
    expect(move).toBeDisabled();
    fireEvent.click(move);
    expect(classifyMutate).not.toHaveBeenCalled();
  });

  it("완료 프로젝트 추천에서 '다른 프로젝트' 를 열어도 숨은 id 로 이동할 수 없다", () => {
    render(<SmartInboxItemCard item={item({ aiSuggestedProjectId: PROJECT_DONE.id })} />);

    fireEvent.click(screen.getByRole("button", { name: /다른 프로젝트/ }));

    expect(screen.getByRole("combobox", { name: "프로젝트 선택" })).toHaveValue("");
    expect(screen.getByRole("button", { name: "이 프로젝트로 이동" })).toBeDisabled();
  });

  it("프로젝트 맵 로딩 전에는 추천 블록을 그리지 않는다 (없음으로 오판 방지)", () => {
    mockTitleMap([], false);
    render(
      <SmartInboxItemCard
        item={item({ aiSuggestedProjectId: PROJECT_DONE.id, aiSuggestedProjectTitle: "IR 투자 유치 전략" })}
      />,
    );

    expect(screen.queryByText("AI 추천:")).not.toBeInTheDocument();
    expect(screen.queryByText("(프로젝트 없음)")).not.toBeInTheDocument();
    expect(screen.queryByText("IR 투자 유치 전략")).not.toBeInTheDocument();
    // 검증 전 id 로 classify 하지 않는다 — 확정 비활성 (codex P1)
    const confirm = screen.getByRole("button", { name: /확정/ });
    expect(confirm).toBeDisabled();
    fireEvent.click(confirm);
    expect(classifyMutate).not.toHaveBeenCalled();
  });

  it("프로젝트 목록 조회가 실패하면 확정은 '불러올 수 없음' 으로 막히고 picker 는 실패를 말한다", () => {
    mockTitleMap([], false, { isError: true });
    render(<SmartInboxItemCard item={item({ aiSuggestedProjectId: PROJECT_DONE.id })} />);

    const confirm = screen.getByRole("button", { name: /확정/ });
    expect(confirm).toBeDisabled();
    expect(confirm).toHaveAttribute("title", expect.stringContaining("불러올 수 없습니다"));

    fireEvent.click(screen.getByRole("button", { name: /다른 프로젝트/ }));
    expect(screen.getByText("프로젝트 목록을 불러올 수 없습니다.")).toBeInTheDocument();
    expect(screen.queryByText(/먼저 프로젝트를 만들어주세요/)).not.toBeInTheDocument();
  });

  it("재조회가 진행 중(isSettled=false)이거나 목록이 잘렸으면(isTruncated) '없음' 을 확정하지 않는다", () => {
    mockTitleMap([PROJECT_ACTIVE], true, { isSettled: false });
    const { unmount } = render(
      <SmartInboxItemCard item={item({ aiSuggestedProjectId: "project-moving" })} />,
    );
    expect(screen.queryByText("(프로젝트 없음)")).not.toBeInTheDocument();
    unmount();

    mockTitleMap([PROJECT_ACTIVE], true, { isTruncated: true });
    render(<SmartInboxItemCard item={item({ aiSuggestedProjectId: "project-101st" })} />);
    expect(screen.queryByText("(프로젝트 없음)")).not.toBeInTheDocument();
  });

  it("추천 id 가 없는 항목은 맵 로딩 중에도 확정(=picker 열기)이 가능하다", () => {
    mockTitleMap([], false);
    render(<SmartInboxItemCard item={item({ aiSuggestedProjectTitle: "IR 투자 유치 전략" })} />);

    const confirm = screen.getByRole("button", { name: /확정/ });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);
    expect(screen.getByText("프로젝트를 선택하세요")).toBeInTheDocument();
  });

  it("확정은 추천 id 로 classify 하고 확정 카드에 실제 제목을 쓴다", () => {
    render(<SmartInboxItemCard item={item({ aiSuggestedProjectId: PROJECT_DONE.id })} />);

    fireEvent.click(screen.getByRole("button", { name: /확정/ }));

    expect(classifyMutate).toHaveBeenCalledWith(
      { id: "inbox-1", projectIds: [PROJECT_DONE.id] },
      expect.objectContaining({ onError: expect.any(Function) }),
    );
    expect(screen.getByText("💡 아이디어")).toBeInTheDocument();
  });

  it("'다른 프로젝트' picker 는 진행 중 프로젝트만 나열한다", () => {
    render(<SmartInboxItemCard item={item({ aiSuggestedProjectId: PROJECT_DONE.id })} />);

    fireEvent.click(screen.getByRole("button", { name: /다른 프로젝트/ }));

    const picker = screen.getByRole("combobox", { name: "프로젝트 선택" });
    expect(within(picker).getByRole("option", { name: "모바일 앱 v2 출시" })).toBeInTheDocument();
    expect(within(picker).queryByRole("option", { name: "💡 아이디어" })).not.toBeInTheDocument();
  });
});
