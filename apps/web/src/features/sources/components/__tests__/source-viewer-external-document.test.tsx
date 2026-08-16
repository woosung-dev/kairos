import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SourceViewer } from "../source-viewer";
import { useWorkspaceStore } from "@/features/workspaces/store";
import type { SourceDocument } from "../../types";

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

const WORKSPACE_ID = "11111111-1111-1111-1111-111111111111";
const DOCUMENT_ID = "22222222-2222-2222-2222-222222222222";

const EXTERNAL_DOCUMENT_SOURCE: SourceDocument = {
  id: "chunk-id",
  sourceId: DOCUMENT_ID,
  title: "Drive 회의록",
  type: "external_document",
  content: "RAG 스니펫 폴백 본문",
  projectId: "project-id",
  createdAt: "2026-07-31T00:00:00.000Z",
};

function renderSourceViewer() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <SourceViewer source={EXTERNAL_DOCUMENT_SOURCE} onClose={vi.fn()} />
    </QueryClientProvider>,
  );
}

function externalDocumentResponse() {
  return {
    id: DOCUMENT_ID,
    projectId: "project-id",
    driveFileId: "drive-file-id",
    title: "Drive 회의록",
    mimeType: "application/vnd.google-apps.document",
    originUrl: "https://docs.google.com/document/d/drive-file-id",
    revisionId: "revision-id",
    syncStatus: "completed",
    lastSyncedAt: "2026-07-31T00:00:00.000Z",
    plainText: "상세 API 전체 본문",
  };
}

beforeEach(() => {
  useWorkspaceStore.setState({ activeWorkspaceId: WORKSPACE_ID });
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  cleanup();
  useWorkspaceStore.setState({ activeWorkspaceId: null });
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("SourceViewer external_document", () => {
  it("상세 API 본문과 Drive 원본 링크를 렌더한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => externalDocumentResponse(),
    });
    vi.stubGlobal("fetch", fetchMock);

    renderSourceViewer();

    await waitFor(() => {
      expect(screen.getByText("상세 API 전체 본문")).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        `/api/v1/workspaces/${WORKSPACE_ID}/external-documents/${DOCUMENT_ID}`,
      ),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-jwt" }),
      }),
    );
    expect(screen.getByText("📎")).toBeInTheDocument();
    expect(screen.getByText("외부 문서")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Drive 원본/ })).toHaveAttribute(
      "href",
      "https://docs.google.com/document/d/drive-file-id",
    );
  });

  it("상세 API 실패 후 RAG 스니펫을 유지한다", async () => {
    let rejectFirstRequest: (reason?: unknown) => void;
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise((_, reject) => {
            rejectFirstRequest = reject;
          }),
      )
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: "찾을 수 없습니다" }),
      });
    vi.stubGlobal("fetch", fetchMock);

    renderSourceViewer();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(screen.getByText("전체 내용 불러오는 중...")).toBeInTheDocument();
      expect(screen.getByText("Drive 원본 불러오는 중...")).toBeInTheDocument();
    });

    rejectFirstRequest!(new Error("네트워크 실패"));

    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalledTimes(2);
        expect(screen.queryByText("전체 내용 불러오는 중...")).not.toBeInTheDocument();
      },
      { timeout: 3000 },
    );

    expect(screen.getByText("RAG 스니펫 폴백 본문")).toBeInTheDocument();
    expect(screen.getByText("원문을 불러오지 못해 인용 스니펫을 표시합니다.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Drive 원본/ })).not.toBeInTheDocument();
  });
});
