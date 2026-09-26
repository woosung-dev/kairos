/**
 * C-002 — 회의↔프로젝트 링크 mutation 은 그 링크로 파생되는 화면(회의 상세·회의 목록·프로젝트별 회의·
 * 인박스·액션)을 모두 무효화하고, 404(권한 밖·사라짐)는 읽을 수 있는 한국어로 알린다.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ApiError } from "@/lib/api-client";
import { actionKeys, inboxKeys, meetingKeys } from "@/lib/query-keys";
import { addMeetingProject, removeMeetingProject } from "../api";
import { useAddMeetingProject, useRemoveMeetingProject } from "../hooks";

const { toastSuccess, toastError } = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: { success: toastSuccess, error: toastError } }));

vi.mock("@/lib/use-api-client", () => ({
  useApiClient: () => ({}),
}));

vi.mock("../api", () => ({
  fetchProjects: vi.fn(),
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

const WID = "workspace-1";
const MEETING_ID = "meeting-1";
const PROJECT_ID = "project-1";

function setup() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const invalidate = vi.spyOn(queryClient, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { invalidate, wrapper };
}

function expectLinkViewsInvalidated(invalidate: ReturnType<typeof vi.spyOn>) {
  expect(invalidate).toHaveBeenCalledWith({ queryKey: meetingKeys.detail(WID, MEETING_ID) });
  // byWorkspace prefix — 워크스페이스 목록(list(wid)) 과 프로젝트별 목록(list(wid, pid)) 을 함께 덮는다
  expect(invalidate).toHaveBeenCalledWith({ queryKey: meetingKeys.byWorkspace(WID) });
  expect(invalidate).toHaveBeenCalledWith({ queryKey: inboxKeys.byWorkspace(WID) });
  expect(invalidate).toHaveBeenCalledWith({ queryKey: actionKeys.byWorkspace(WID) });
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("useAddMeetingProject / useRemoveMeetingProject", () => {
  it("연결 성공 시 링크 파생 화면을 모두 무효화한다", async () => {
    vi.mocked(addMeetingProject).mockResolvedValue({ id: "link-1" });
    const { invalidate, wrapper } = setup();
    const { result } = renderHook(() => useAddMeetingProject(WID), { wrapper });

    result.current.mutate({ meetingId: MEETING_ID, projectId: PROJECT_ID });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(addMeetingProject).toHaveBeenCalledWith({}, WID, MEETING_ID, PROJECT_ID);
    expectLinkViewsInvalidated(invalidate);
    expect(toastSuccess).toHaveBeenCalledWith("프로젝트에 연결했습니다");
  });

  it("해제 성공 시에도 같은 화면을 무효화한다", async () => {
    vi.mocked(removeMeetingProject).mockResolvedValue(undefined);
    const { invalidate, wrapper } = setup();
    const { result } = renderHook(() => useRemoveMeetingProject(WID), { wrapper });

    result.current.mutate({ meetingId: MEETING_ID, projectId: PROJECT_ID });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expectLinkViewsInvalidated(invalidate);
  });

  it("404 는 권한 밖/사라짐을 한국어로 알린다 (BE 영어 원문·상태 코드 노출 없음)", async () => {
    vi.mocked(addMeetingProject).mockRejectedValue(new ApiError("프로젝트를 찾을 수 없습니다", 404));
    const { invalidate, wrapper } = setup();
    const { result } = renderHook(() => useAddMeetingProject(WID), { wrapper });

    result.current.mutate({ meetingId: MEETING_ID, projectId: PROJECT_ID });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toastError).toHaveBeenCalledWith(
      "회의나 프로젝트에 접근할 수 없습니다. 삭제되었거나 권한이 없을 수 있어요.",
    );
    expect(invalidate).not.toHaveBeenCalled();
  });
});
