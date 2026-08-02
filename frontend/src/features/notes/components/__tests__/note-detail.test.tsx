import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { NoteDetail } from "../note-detail";
import { useWorkspaceStore } from "@/features/workspaces/store";

const {
  deleteMutate,
  mockUseDeleteNote,
  mockUseNote,
  mockUseUpdateNote,
  mockUseWorkspaceRole,
  push,
} = vi.hoisted(() => ({
  deleteMutate: vi.fn(),
  mockUseDeleteNote: vi.fn(),
  mockUseNote: vi.fn(),
  mockUseUpdateNote: vi.fn(),
  mockUseWorkspaceRole: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ back: vi.fn(), push }),
}));

vi.mock("@tiptap/react", () => ({
  EditorContent: () => null,
  useEditor: () => ({
    getJSON: vi.fn(),
    setEditable: vi.fn(),
  }),
}));

vi.mock("@tiptap/starter-kit", () => ({ default: {} }));

vi.mock("../../hooks", () => ({
  useDeleteNote: mockUseDeleteNote,
  useNote: mockUseNote,
  useUpdateNote: mockUseUpdateNote,
}));

// 데이터 훅 mock — 판정 대상인 NoteDetail 자체는 실물로 렌더한다.
vi.mock("@/features/members/hooks", () => ({
  useWorkspaceRole: mockUseWorkspaceRole,
}));

vi.mock("@/components/shared/ExportButton", () => ({
  ExportButton: () => null,
}));

vi.mock("@/components/shared/ItemPromoteModal", () => ({
  ItemPromoteModal: () => null,
}));

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

const WORKSPACE_ID = "11111111-1111-1111-1111-111111111111";
const NOTE_ID = "22222222-2222-2222-2222-222222222222";
const AUTHOR_ID = "33333333-3333-3333-3333-333333333333";
const OTHER_USER_ID = "44444444-4444-4444-4444-444444444444";

/** useWorkspaceRole 반환값 — 기본은 "노트 작성자 본인인 member". */
function roleResult(
  overrides: Partial<{
    isAdmin: boolean;
    isLoading: boolean;
    userId: string | null;
  }> = {},
) {
  const isAdmin = overrides.isAdmin ?? false;
  return {
    canManage: isAdmin,
    isAdmin,
    isLoading: overrides.isLoading ?? false,
    isOwner: false,
    role: isAdmin ? "admin" : "member",
    userId: overrides.userId === undefined ? AUTHOR_ID : overrides.userId,
  };
}

const NOTE = {
  content: { content: [], type: "doc" },
  createdAt: "2026-08-01T00:00:00.000Z",
  createdById: AUTHOR_ID,
  id: NOTE_ID,
  plainText: "테스트 노트 본문",
  projectId: null,
  title: "테스트 노트",
  updatedAt: "2026-08-01T00:00:00.000Z",
  workspaceId: WORKSPACE_ID,
};

function renderNoteDetail() {
  return render(<NoteDetail noteId={NOTE_ID} />);
}

beforeEach(() => {
  useWorkspaceStore.setState({
    activeWorkspaceId: WORKSPACE_ID,
    workspaceRole: "member",
  });
  mockUseNote.mockReturnValue({ data: NOTE, error: null, isLoading: false });
  mockUseUpdateNote.mockReturnValue({ isPending: false, mutate: vi.fn() });
  mockUseDeleteNote.mockReturnValue({ isPending: false, mutate: deleteMutate });
  mockUseWorkspaceRole.mockReturnValue(roleResult());
});

afterEach(() => {
  cleanup();
  useWorkspaceStore.setState({ activeWorkspaceId: null, workspaceRole: null });
  vi.clearAllMocks();
});

describe("NoteDetail 삭제", () => {
  it("삭제 버튼 클릭은 확인 다이얼로그만 열고 mutate를 호출하지 않는다", () => {
    renderNoteDetail();

    fireEvent.click(screen.getByTestId("note-detail-delete-button"));

    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    expect(deleteMutate).not.toHaveBeenCalled();
  });

  it("확인 클릭은 해당 noteId로 useDeleteNote mutate를 한 번 호출한다", () => {
    renderNoteDetail();

    fireEvent.click(screen.getByTestId("note-detail-delete-button"));
    fireEvent.click(
      within(screen.getByRole("alertdialog")).getByRole("button", {
        name: "삭제",
      }),
    );

    expect(deleteMutate).toHaveBeenCalledTimes(1);
    expect(deleteMutate).toHaveBeenCalledWith(NOTE_ID, expect.any(Object));
  });

  it("canWrite=false이면 삭제 버튼을 렌더하지 않는다", () => {
    useWorkspaceStore.setState({ workspaceRole: "viewer" });

    renderNoteDetail();

    expect(
      screen.queryByTestId("note-detail-delete-button"),
    ).not.toBeInTheDocument();
  });
});

// BL-NOTE-DELETE-POLICY-1 — 삭제는 작성자 본인 + admin 이상만.
describe("NoteDetail 삭제 권한 (작성자 본인 + admin 이상)", () => {
  it("작성자 본인 member 에게는 삭제 버튼을 렌더한다", () => {
    renderNoteDetail();

    expect(screen.getByLabelText("삭제")).toBeInTheDocument();
  });

  it("작성자가 아닌 member 에게는 삭제 버튼을 렌더하지 않는다 (편집은 유지)", () => {
    mockUseWorkspaceRole.mockReturnValue(roleResult({ userId: OTHER_USER_ID }));

    renderNoteDetail();

    expect(screen.queryByLabelText("삭제")).not.toBeInTheDocument();
    // 정책은 삭제에만 적용된다 — 편집 권한까지 좁히지 않았음을 함께 단언
    expect(screen.getByLabelText("편집")).toBeInTheDocument();
  });

  it("admin 은 남의 노트에도 삭제 버튼을 본다", () => {
    mockUseWorkspaceRole.mockReturnValue(
      roleResult({ isAdmin: true, userId: OTHER_USER_ID }),
    );

    renderNoteDetail();

    expect(screen.getByLabelText("삭제")).toBeInTheDocument();
  });

  it("멤버 정보 로딩 중에는 삭제 버튼을 렌더하지 않는다", () => {
    mockUseWorkspaceRole.mockReturnValue(
      roleResult({ isLoading: true, userId: null }),
    );

    renderNoteDetail();

    expect(screen.queryByLabelText("삭제")).not.toBeInTheDocument();
  });
});
