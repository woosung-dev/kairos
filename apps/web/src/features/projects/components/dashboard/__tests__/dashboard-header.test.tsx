/**
 * BL-FE-A11Y-DROPDOWN-1 — 관리 드롭다운 트리거의 접근성 이름 회귀 가드.
 *
 * 이름이 없으면 스크린리더가 용도를 알 수 없고, 테스트도 base-ui 자동생성 id 에
 * 의존하게 되어 셀렉터가 불안정해진다. 태그를 가정하지 않고 getByLabel 로만 찾는다
 * (같은 배지가 화면에 따라 button/span 으로 갈리는 전례가 있다).
 */
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { Project } from "../../../types";
import { DashboardHeader } from "../dashboard-header";

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

function renderHeader(canManage: boolean) {
  const onEditClick = vi.fn();
  render(
    <DashboardHeader
      project={PROJECT}
      canManage={canManage}
      isRoleLoading={false}
      onVisibilityClick={vi.fn()}
      onEditClick={onEditClick}
      onArchiveClick={vi.fn()}
      onDeleteClick={vi.fn()}
    />,
  );
  return { onEditClick };
}

describe("DashboardHeader — 관리 드롭다운 접근성 이름", () => {
  it("접근성 이름으로 트리거를 찾아 열면 관리 항목이 보인다", async () => {
    const { onEditClick } = renderHeader(true);

    fireEvent.click(screen.getByLabelText("프로젝트 관리 메뉴"));

    expect(await screen.findByText("편집")).toBeTruthy();
    expect(screen.getByText("아카이브")).toBeTruthy();
    expect(screen.getByText("삭제")).toBeTruthy();

    fireEvent.click(screen.getByText("편집"));
    expect(onEditClick).toHaveBeenCalledTimes(1);
  });

  it("canManage 가 false 면 트리거 자체가 없다", () => {
    renderHeader(false);
    expect(screen.queryByLabelText("프로젝트 관리 메뉴")).toBeNull();
  });
});
