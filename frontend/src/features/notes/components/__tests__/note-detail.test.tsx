import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { NoteDetail } from "../note-detail";
import { useWorkspaceStore } from "@/features/workspaces/store";

const {
  deleteMutate,
  mockUseDeleteNote,
  mockUseNote,
  mockUseUpdateNote,
  push,
} = vi.hoisted(() => ({
  deleteMutate: vi.fn(),
  mockUseDeleteNote: vi.fn(),
  mockUseNote: vi.fn(),
  mockUseUpdateNote: vi.fn(),
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

const NOTE = {
  content: { content: [], type: "doc" },
  createdAt: "2026-08-01T00:00:00.000Z",
  createdById: "33333333-3333-3333-3333-333333333333",
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
