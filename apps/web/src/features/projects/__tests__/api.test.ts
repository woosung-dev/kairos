import { describe, expect, it, vi } from "vitest";
import type { ApiClient } from "@/lib/api-client";
import { addMeetingProject, fetchProjects, removeMeetingProject } from "../api";

// S28b FE-PAGESIZE-MISMATCH 회귀 가드 — BE `pageSize` alias 는 camelCase 만 받는다 (actions/api.test 와 같은 버그 클래스).

const WID = "11111111-1111-1111-1111-111111111111";

function mockApi() {
  const fetch = vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 20, hasNext: false });
  return { api: { fetch } as unknown as ApiClient, fetch };
}

function calledPath(fetch: ReturnType<typeof vi.fn>): string {
  expect(fetch).toHaveBeenCalledTimes(1);
  return String(fetch.mock.calls[0]?.[0]);
}

describe("fetchProjects 쿼리 파라미터", () => {
  it("pageSize 를 BE alias 와 같은 camelCase 로 보낸다", async () => {
    const { api, fetch } = mockApi();

    await fetchProjects(api, WID, { status: "completed", page: 3, pageSize: 100 });

    const url = new URL(calledPath(fetch), "http://localhost");
    expect(url.pathname).toBe(`/workspaces/${WID}/projects`);
    expect(url.searchParams.get("status")).toBe("completed");
    expect(url.searchParams.get("page")).toBe("3");
    expect(url.searchParams.get("pageSize")).toBe("100");
    expect(url.searchParams.has("page_size")).toBe(false);
  });

  it("파라미터가 없으면 쿼리 문자열을 붙이지 않는다", async () => {
    const { api, fetch } = mockApi();

    await fetchProjects(api, WID);

    expect(calledPath(fetch)).toBe(`/workspaces/${WID}/projects`);
  });
});

// C-002 회귀 가드 — BE 는 POST /meetings/{mid}/projects + body {projectId} 만 받는다.
// 예전 FE 는 PUT /meetings/{mid}/projects/{pid} 를 보내 405 였고, 그래서 UI 에 링크 경로가 없었다.
describe("회의↔프로젝트 링크 API", () => {
  const MID = "22222222-2222-2222-2222-222222222222";
  const PID = "33333333-3333-3333-3333-333333333333";

  it("addMeetingProject: POST + body { projectId }", async () => {
    const fetch = vi.fn().mockResolvedValue({ id: "link-1", meetingId: MID, projectId: PID });
    const api = { fetch } as unknown as ApiClient;

    await addMeetingProject(api, WID, MID, PID);

    expect(fetch).toHaveBeenCalledWith(`/workspaces/${WID}/meetings/${MID}/projects`, {
      method: "POST",
      body: JSON.stringify({ projectId: PID }),
    });
  });

  it("removeMeetingProject: DELETE /meetings/{mid}/projects/{pid}", async () => {
    const fetch = vi.fn().mockResolvedValue(undefined);
    const api = { fetch } as unknown as ApiClient;

    await removeMeetingProject(api, WID, MID, PID);

    expect(fetch).toHaveBeenCalledWith(`/workspaces/${WID}/meetings/${MID}/projects/${PID}`, {
      method: "DELETE",
    });
  });
});
