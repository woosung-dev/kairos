/**
 * C-002 — 회의 상세에서 프로젝트를 연결·해제한다 (이전엔 UI 경로가 0개였다).
 * member 이상만 편집, viewer 는 읽기 전용 칩. 공개 범위를 넓히는 두 조작만 확인을 거친다 (E-FE E-2):
 * 비공개 링크뿐인 회의에 공개 프로젝트 연결 · 마지막 링크 해제.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { Project } from "@/features/projects/types";
import { MeetingProjectLinks } from "../meeting-project-links";

const { addMutate, removeMutate, mockUseProjects } = vi.hoisted(() => ({
  addMutate: vi.fn(),
  removeMutate: vi.fn(),
  mockUseProjects: vi.fn(),
}));

vi.mock("@/features/projects/hooks", () => ({
  useProjects: mockUseProjects,
  useAddMeetingProject: () => ({ mutate: addMutate, isPending: false }),
  useRemoveMeetingProject: () => ({ mutate: removeMutate, isPending: false }),
}));

const WID = "workspace-1";
const MEETING_ID = "meeting-1";

function project(id: string, title: string, visibility: Project["visibility"] = "public"): Project {
  return {
    id,
    workspaceId: WID,
    title,
    description: null,
    status: "active",
    visibility,
    tags: [],
    sortOrder: 0,
    createdById: "user-1",
    createdAt: "2026-08-01T00:00:00.000Z",
    updatedAt: "2026-08-01T00:00:00.000Z",
  };
}

const LINKED_PUBLIC = { id: "p-linked", title: "연결된 공개", status: "active", visibility: "public" };
const LINKED_PRIVATE = { id: "p-private", title: "비밀 프로젝트", status: "active", visibility: "private" };
const LINKED_DRAFT = { id: "p-draft", title: "작업 중", status: "active", visibility: "draft" };

beforeEach(() => {
  mockUseProjects.mockReturnValue({
    data: {
      items: [
        project("p-linked", "연결된 공개"),
        project("p-new", "새 후보"),
        project("p-new-private", "새 비공개 후보", "private"),
      ],
      total: 3,
      page: 1,
      pageSize: 100,
      hasNext: false,
    },
    isLoading: false,
    isError: false,
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("MeetingProjectLinks — viewer 읽기 전용", () => {
  it("연결 칩은 보이고 연결·해제 버튼은 없다", () => {
    render(
      <MeetingProjectLinks
        workspaceId={WID}
        meetingId={MEETING_ID}
        linkedProjects={[LINKED_PUBLIC]}
        canEdit={false}
      />,
    );

    expect(screen.getByRole("link", { name: /연결된 공개/ })).toHaveAttribute("href", "/projects/p-linked");
    expect(screen.queryByTestId("meeting-project-unlink")).toBeNull();
    expect(screen.queryByTestId("meeting-project-link-open")).toBeNull();
  });

  it("연결된 프로젝트가 없으면 아무것도 그리지 않는다", () => {
    render(
      <MeetingProjectLinks workspaceId={WID} meetingId={MEETING_ID} linkedProjects={[]} canEdit={false} />,
    );
    expect(screen.queryByTestId("meeting-linked-projects")).toBeNull();
  });
});

describe("MeetingProjectLinks — member 편집", () => {
  it("picker 는 이미 연결된 프로젝트를 빼고, 고른 프로젝트로 연결한다", () => {
    render(
      <MeetingProjectLinks
        workspaceId={WID}
        meetingId={MEETING_ID}
        linkedProjects={[LINKED_PUBLIC]}
        canEdit
      />,
    );

    fireEvent.click(screen.getByTestId("meeting-project-link-open"));

    const select = screen.getByTestId("meeting-project-select");
    expect(screen.queryByRole("option", { name: "연결된 공개" })).toBeNull();
    expect(screen.getByTestId("meeting-project-link-submit")).toBeDisabled();

    fireEvent.change(select, { target: { value: "p-new" } });
    fireEvent.click(screen.getByTestId("meeting-project-link-submit"));

    expect(addMutate).toHaveBeenCalledWith(
      { meetingId: MEETING_ID, projectId: "p-new" },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it("후보 조회는 picker 를 열 때만 한다 (닫혀 있으면 wid 를 넘기지 않는다)", () => {
    render(
      <MeetingProjectLinks workspaceId={WID} meetingId={MEETING_ID} linkedProjects={[]} canEdit />,
    );
    expect(mockUseProjects).toHaveBeenLastCalledWith(undefined, { status: "active", pageSize: 100 });

    fireEvent.click(screen.getByTestId("meeting-project-link-open"));
    expect(mockUseProjects).toHaveBeenLastCalledWith(WID, { status: "active", pageSize: 100 });
  });

  it("링크가 여럿이면 해제는 바로 요청한다 (공개 범위가 좁아지기만 함)", () => {
    render(
      <MeetingProjectLinks
        workspaceId={WID}
        meetingId={MEETING_ID}
        linkedProjects={[LINKED_PRIVATE, LINKED_DRAFT]}
        canEdit
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "비밀 프로젝트 연결 해제" }));

    expect(removeMutate).toHaveBeenCalledWith({ meetingId: MEETING_ID, projectId: "p-private" });
    expect(screen.queryByText("마지막 연결을 해제할까요?")).toBeNull();
  });

  it.each([
    ["공개", LINKED_PUBLIC],
    ["비공개", LINKED_PRIVATE],
  ])("마지막 링크(%s) 해제는 확인 후에만 요청한다 (링크 0개 = 워크스페이스 전체 공개)", async (_label, linked) => {
    render(
      <MeetingProjectLinks workspaceId={WID} meetingId={MEETING_ID} linkedProjects={[linked]} canEdit />,
    );

    fireEvent.click(screen.getByRole("button", { name: `${linked.title} 연결 해제` }));
    expect(removeMutate).not.toHaveBeenCalled();
    expect(await screen.findByText("마지막 연결을 해제할까요?")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("meeting-project-unlink-confirm"));

    expect(removeMutate).toHaveBeenCalledWith(
      { meetingId: MEETING_ID, projectId: linked.id },
      expect.objectContaining({ onSettled: expect.any(Function) }),
    );
  });

  it("비공개 링크뿐인 회의에 공개 프로젝트를 연결하면 확인 후에만 요청한다", async () => {
    render(
      <MeetingProjectLinks
        workspaceId={WID}
        meetingId={MEETING_ID}
        linkedProjects={[LINKED_PRIVATE]}
        canEdit
      />,
    );

    fireEvent.click(screen.getByTestId("meeting-project-link-open"));
    fireEvent.change(screen.getByTestId("meeting-project-select"), { target: { value: "p-new" } });
    fireEvent.click(screen.getByTestId("meeting-project-link-submit"));

    expect(addMutate).not.toHaveBeenCalled();
    expect(await screen.findByText("공개 프로젝트에 연결할까요?")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("meeting-project-link-confirm"));

    expect(addMutate).toHaveBeenCalledWith(
      { meetingId: MEETING_ID, projectId: "p-new" },
      expect.objectContaining({ onSuccess: expect.any(Function), onSettled: expect.any(Function) }),
    );
  });

  it.each([
    ["이미 공개 링크가 있는 회의", [LINKED_PUBLIC], "p-new"],
    ["링크가 없는 회의(이미 전체 공개)", [], "p-new"],
    ["비공개 프로젝트 연결", [LINKED_PRIVATE], "p-new-private"],
  ])("%s 는 확인 없이 바로 연결한다", (_label, linked, targetId) => {
    render(
      <MeetingProjectLinks workspaceId={WID} meetingId={MEETING_ID} linkedProjects={linked} canEdit />,
    );

    fireEvent.click(screen.getByTestId("meeting-project-link-open"));
    fireEvent.change(screen.getByTestId("meeting-project-select"), { target: { value: targetId } });
    fireEvent.click(screen.getByTestId("meeting-project-link-submit"));

    expect(addMutate).toHaveBeenCalledWith(
      { meetingId: MEETING_ID, projectId: targetId },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(screen.queryByText("공개 프로젝트에 연결할까요?")).toBeNull();
  });
});
