/**
 * C-017 후속 — "보관(archived)" 진입·해제는 admin 이상만 (BE PATCH 403).
 * 편집 다이얼로그는 권한 밖 선택지를 보이지 않고, 이미 보관된 프로젝트를 member(작성자)가 편집할 때는
 * 상태만 잠근 채 다른 필드를 저장할 수 있어야 한다.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { Project } from "../../types";
import { EditProjectDialog } from "../edit-project-dialog";

const { updateMutate } = vi.hoisted(() => ({ updateMutate: vi.fn() }));

vi.mock("../../hooks", () => ({
  useUpdateProject: () => ({ mutate: updateMutate, isPending: false }),
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

function renderDialog(project: Project, canArchive: boolean) {
  render(
    <EditProjectDialog
      open
      onOpenChange={vi.fn()}
      workspaceId="workspace-1"
      project={project}
      canArchive={canArchive}
    />,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("EditProjectDialog — 상태 선택지 권한", () => {
  it("상태 트리거는 raw 값이 아니라 한국어 라벨을 보여준다", () => {
    renderDialog(PROJECT, true);
    expect(screen.getByTestId("edit-project-status")).toHaveTextContent("진행 중");
  });

  it("admin 은 보관 선택지를 본다", async () => {
    renderDialog(PROJECT, true);
    fireEvent.click(screen.getByTestId("edit-project-status"));
    expect(await screen.findByRole("option", { name: "보관" })).toBeInTheDocument();
  });

  it("member 는 보관 선택지를 보지 않는다", async () => {
    renderDialog(PROJECT, false);
    fireEvent.click(screen.getByTestId("edit-project-status"));
    expect(await screen.findByRole("option", { name: "완료" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "보관" })).toBeNull();
  });

  it("member 가 보관된 프로젝트를 편집하면 상태는 잠기고 다른 필드는 저장된다", async () => {
    renderDialog({ ...PROJECT, status: "archived" }, false);

    const trigger = screen.getByTestId("edit-project-status");
    expect(trigger).toHaveTextContent("보관");
    expect(trigger).toBeDisabled();
    expect(screen.getByText(/보관 해제는 관리자만/)).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("프로젝트 이름"), {
      target: { value: "새 이름" },
    });
    fireEvent.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() => expect(updateMutate).toHaveBeenCalledTimes(1));
    const [variables] = updateMutate.mock.calls[0];
    // 상태는 현재 값 그대로 — BE 는 값이 바뀔 때만 archived 권한을 검사한다
    expect(variables).toEqual({
      id: "project-1",
      data: { title: "새 이름", description: null, status: "archived", tags: [] },
    });
  });
});
