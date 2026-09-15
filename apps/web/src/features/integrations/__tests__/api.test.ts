import { describe, expect, it, vi } from "vitest";

import {
  disconnectGoogleDrive,
  importGoogleDriveDocuments,
  fetchGoogleDriveDocuments,
} from "../api";
import type { ApiClient } from "@/lib/api-client";

function createApiStub(response: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  return { api: { fetch: fetchMock } as unknown as ApiClient, fetchMock };
}

describe("integrations api", () => {
  it("가져오기 본문에 fileIds 와 projectId 만 넣는다 (ADR-026 D5)", async () => {
    // ★브라우저 access token 이 본문에 섞여 백엔드로 넘어가면 2-토큰 모델이 깨진다.
    const { api, fetchMock } = createApiStub({ syncRunId: "sync-run-1" });

    const syncRunId = await importGoogleDriveDocuments(api, "ws-1", {
      fileIds: ["file-a", "file-b"],
      projectId: "project-1",
    });

    expect(syncRunId).toBe("sync-run-1");
    const [path, init] = fetchMock.mock.calls[0];
    expect(path).toBe("/workspaces/ws-1/integrations/google-drive/documents");
    expect(JSON.parse(init.body as string)).toEqual({
      fileIds: ["file-a", "file-b"],
      projectId: "project-1",
    });
    expect(init.body as string).not.toMatch(/token/i);
  });

  it("프로젝트 미선택은 null 로 보낸다 — 빈 문자열이 아니다", async () => {
    const { api, fetchMock } = createApiStub({ syncRunId: "sync-run-2" });

    await importGoogleDriveDocuments(api, "ws-1", {
      fileIds: ["file-a"],
      projectId: null,
    });

    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string).projectId).toBeNull();
  });

  it("연결 해제는 DELETE 로 연결 경로를 친다 (문서 경로가 아니다)", async () => {
    const { api, fetchMock } = createApiStub({
      unpublishedDocuments: 2,
      revoked: false,
    });

    const result = await disconnectGoogleDrive(api, "ws-1");

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/workspaces/ws-1/integrations/google-drive",
    );
    expect(fetchMock.mock.calls[0][1]).toEqual({ method: "DELETE" });
    expect(result).toEqual({ unpublishedDocuments: 2, revoked: false });
  });

  it("문서 목록은 workspace 경로로만 조회한다 (I-9)", async () => {
    const { api, fetchMock } = createApiStub([]);

    await fetchGoogleDriveDocuments(api, "ws-1");

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/workspaces/ws-1/integrations/google-drive/documents",
    );
  });
});
