import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { useMembers } from "@/features/members/hooks";
import {
  useAddProjectMember,
  useProjectMembers,
  useRemoveProjectMember,
} from "@/features/projects/hooks";
import { ProjectMembersPanel } from "../project-members-panel";

vi.mock("@/features/members/hooks", () => ({
  useMembers: vi.fn(),
}));

vi.mock("@/features/projects/hooks", () => ({
  useAddProjectMember: vi.fn(),
  useProjectMembers: vi.fn(),
  useRemoveProjectMember: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(useProjectMembers).mockReturnValue({
    data: [],
    isLoading: false,
  } as unknown as ReturnType<typeof useProjectMembers>);
  vi.mocked(useMembers).mockReturnValue({
    data: [{ userId: "member-1", displayName: "멤버", email: null, role: "member" }],
  } as ReturnType<typeof useMembers>);
  vi.mocked(useAddProjectMember).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useAddProjectMember>);
  vi.mocked(useRemoveProjectMember).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useRemoveProjectMember>);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ProjectMembersPanel visibility 게이트", () => {
  it("private 프로젝트에서는 owner의 멤버 추가 UI와 멤버 쿼리를 렌더한다", () => {
    render(
      <ProjectMembersPanel
        workspaceId="workspace-1"
        projectId="project-1"
        visibility="private"
        canManage
      />,
    );

    expect(screen.getByRole("heading", { name: /프로젝트 멤버/ })).toBeInTheDocument();
    expect(screen.getByText("워크스페이스 멤버 선택...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "추가" })).toBeInTheDocument();
    expect(useProjectMembers).toHaveBeenCalledWith("workspace-1", "project-1");
    expect(useMembers).toHaveBeenCalledWith("workspace-1");
  });

  it("public 프로젝트에서는 섹션과 멤버 쿼리를 렌더하지 않는다", () => {
    render(
      <ProjectMembersPanel
        workspaceId="workspace-1"
        projectId="project-1"
        visibility="public"
        canManage
      />,
    );

    expect(screen.queryByRole("heading", { name: /프로젝트 멤버/ })).not.toBeInTheDocument();
    expect(useProjectMembers).not.toHaveBeenCalled();
    expect(useMembers).not.toHaveBeenCalled();
  });

  it("draft 프로젝트에서도 섹션과 멤버 쿼리를 렌더하지 않는다", () => {
    render(
      <ProjectMembersPanel
        workspaceId="workspace-1"
        projectId="project-1"
        visibility="draft"
        canManage
      />,
    );

    expect(screen.queryByRole("heading", { name: /프로젝트 멤버/ })).not.toBeInTheDocument();
    expect(useProjectMembers).not.toHaveBeenCalled();
    expect(useMembers).not.toHaveBeenCalled();
  });
});
