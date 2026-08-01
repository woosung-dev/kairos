import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { useActionItems } from "@/features/actions/hooks";
import { useMeetings } from "@/features/meetings/hooks";
import { useNotes } from "@/features/notes/hooks";
import type { Meeting } from "@/features/meetings/types";
import type { Note } from "@/features/notes/types";
import { DashboardContent } from "../dashboard-content";

vi.mock("@/features/actions/hooks", () => ({
  useActionItems: vi.fn(),
}));

vi.mock("@/features/meetings/hooks", () => ({
  useMeetings: vi.fn(),
}));

vi.mock("@/features/notes/hooks", () => ({
  useNotes: vi.fn(),
}));

vi.mock("../actions-section", () => ({
  ActionsSection: () => <div>이번 주 액션</div>,
}));

const NOTE: Note = {
  id: "note-1",
  workspaceId: "workspace-1",
  projectId: "project-1",
  title: "CYAN42 노트",
  content: {},
  plainText: "프로젝트 첫 노트",
  createdById: "user-1",
  createdAt: "2026-08-01T00:00:00.000Z",
  updatedAt: "2026-08-01T00:00:00.000Z",
};

function queryResult<T>(items: T[], isLoading = false) {
  return {
    data: isLoading
      ? undefined
      : { items, total: items.length, page: 1, pageSize: 20, hasNext: false },
    isLoading,
  };
}

function mockContent({ notes = [], isLoading = false }: { notes?: Note[]; isLoading?: boolean }) {
  vi.mocked(useMeetings).mockReturnValue(
    queryResult<Meeting>([], isLoading) as ReturnType<typeof useMeetings>,
  );
  vi.mocked(useNotes).mockReturnValue(
    queryResult(notes, isLoading) as ReturnType<typeof useNotes>,
  );
  vi.mocked(useActionItems).mockReturnValue(
    queryResult([], isLoading) as ReturnType<typeof useActionItems>,
  );
}

beforeEach(() => {
  mockContent({});
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("DashboardContent — 온보딩 게이트", () => {
  it("노트 1건이면 온보딩 대신 노트 카드를 렌더한다", () => {
    mockContent({ notes: [NOTE] });

    render(<DashboardContent wid="workspace-1" projectId="project-1" />);

    expect(screen.queryByRole("heading", { name: "프로젝트를 시작하세요" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: NOTE.title })).toBeInTheDocument();
  });

  it("콘텐츠가 없으면 온보딩 뷰를 렌더한다", () => {
    render(<DashboardContent wid="workspace-1" projectId="project-1" />);

    expect(screen.getByRole("heading", { name: "프로젝트를 시작하세요" })).toBeInTheDocument();
  });

  it("로딩 중이면 온보딩으로 전환하지 않고 스켈레톤을 렌더한다", () => {
    mockContent({ isLoading: true });

    const { container } = render(
      <DashboardContent wid="workspace-1" projectId="project-1" />,
    );

    expect(screen.queryByRole("heading", { name: "프로젝트를 시작하세요" })).not.toBeInTheDocument();
    expect(container.querySelectorAll('[data-slot="skeleton"]')).not.toHaveLength(0);
  });
});
