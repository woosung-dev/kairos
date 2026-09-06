import { describe, expect, it, vi } from "vitest";
import type { ApiClient } from "@/lib/api-client";
import { fetchActionItems } from "../api";

// PR #189 P1 회귀 가드 — BE 는 camelCase alias(`projectId`/`pageSize`)만 받고 snake_case 는 400 없이
// 조용히 무시한다. typecheck·contracts-check 는 쿼리 파라미터 이름을 보지 못하므로, 이 테스트가
// "프로젝트 대시보드 이번 주 액션이 워크스페이스 전체를 보여주던" 회귀를 잡는 유일한 게이트다.

const WID = "11111111-1111-1111-1111-111111111111";

function mockApi() {
  const fetch = vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 20, hasNext: false });
  return { api: { fetch } as unknown as ApiClient, fetch };
}

function calledPath(fetch: ReturnType<typeof vi.fn>): string {
  expect(fetch).toHaveBeenCalledTimes(1);
  return String(fetch.mock.calls[0]?.[0]);
}

describe("fetchActionItems 쿼리 파라미터", () => {
  it("projectId / pageSize 를 BE alias 와 같은 camelCase 로 보낸다", async () => {
    const { api, fetch } = mockApi();

    await fetchActionItems(api, WID, {
      projectId: "project-1",
      pageSize: 100,
      page: 2,
      status: "todo",
      priority: "high",
    });

    const url = new URL(calledPath(fetch), "http://localhost");
    expect(url.pathname).toBe(`/workspaces/${WID}/action-items`);
    expect(url.searchParams.get("projectId")).toBe("project-1");
    expect(url.searchParams.get("pageSize")).toBe("100");
    expect(url.searchParams.get("page")).toBe("2");
    expect(url.searchParams.get("status")).toBe("todo");
    expect(url.searchParams.get("priority")).toBe("high");
    // snake_case 는 BE 가 무시한다 — 절대 나가면 안 된다.
    expect(url.searchParams.has("project_id")).toBe(false);
    expect(url.searchParams.has("page_size")).toBe(false);
  });

  it("파라미터가 없으면 쿼리 문자열을 붙이지 않는다", async () => {
    const { api, fetch } = mockApi();

    await fetchActionItems(api, WID);

    expect(calledPath(fetch)).toBe(`/workspaces/${WID}/action-items`);
  });
});
