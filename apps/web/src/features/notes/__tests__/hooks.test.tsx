import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { useDeleteNote, useNote, useNotes } from "../hooks";

const { fetchNote, fetchNotes, deleteNote } = vi.hoisted(() => ({
  fetchNote: vi.fn(),
  fetchNotes: vi.fn(),
  deleteNote: vi.fn(),
}));

/* ── 토큰 주입 seam 목 (ADR-031) ──
   인증 벤더가 아니라 `useApiClient` 를 목한다. 벤더 SDK 를 목하면 전환 때마다 이 파일이
   따라 깨진다 — seam 을 목하면 그 결합이 사라진다. */
vi.mock("@/lib/use-api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api-client")>(
    "@/lib/api-client",
  );
  return {
    useApiClient: () => actual.createApiClient(async () => "test-jwt"),
    clearAuthTokenCache: vi.fn(),
  };
});

vi.mock("../api", () => ({
  fetchNote,
  fetchNotes,
  deleteNote,
  createNote: vi.fn(),
  updateNote: vi.fn(),
}));

const WID = "workspace-1";
const NOTE_ID = "note-1";

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  fetchNote.mockResolvedValue({ id: NOTE_ID, title: "삭제 대상", content: null });
  fetchNotes.mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 20, hasNext: false });
  deleteNote.mockResolvedValue(undefined);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("useDeleteNote — 삭제 후 캐시 무효화 범위", () => {
  // 회귀: noteKeys.all 무효화는 방금 삭제한 노트의 detail 키까지 걸려서, 아직 마운트된
  // 상세 화면의 useNote 가 삭제된 리소스를 재조회해 404 + console.error 를 남겼다.
  it("삭제된 노트의 detail 쿼리를 재조회하지 않는다", async () => {
    const { result } = renderHook(
      () => ({
        note: useNote(WID, NOTE_ID),
        remove: useDeleteNote(WID),
      }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.note.isSuccess).toBe(true));
    expect(fetchNote).toHaveBeenCalledTimes(1);

    result.current.remove.mutate(NOTE_ID);
    await waitFor(() => expect(result.current.remove.isSuccess).toBe(true));

    // 상세 화면이 아직 마운트된 상태 — 여기서 재조회가 일어나면 404 가 난다.
    await waitFor(() => expect(deleteNote).toHaveBeenCalledTimes(1));
    expect(fetchNote).toHaveBeenCalledTimes(1);
  });

  it("노트 목록은 무효화해 재조회한다", async () => {
    const { result } = renderHook(
      () => ({
        list: useNotes(WID),
        remove: useDeleteNote(WID),
      }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.list.isSuccess).toBe(true));
    expect(fetchNotes).toHaveBeenCalledTimes(1);

    result.current.remove.mutate(NOTE_ID);
    await waitFor(() => expect(fetchNotes).toHaveBeenCalledTimes(2));
  });
});
