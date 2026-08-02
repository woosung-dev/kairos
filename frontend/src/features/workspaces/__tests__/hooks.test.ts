import { describe, expect, it } from "vitest";
import { withWorkspaceGuardLoading } from "../hooks";

function createTrackedQuery(isLoading: boolean) {
  const reads = {
    error: 0,
    isError: 0,
    isLoading: 0,
    isPending: 0,
    isSuccess: 0,
    isFetching: 0,
    status: 0,
    dataUpdatedAt: 0,
  };
  const query = Object.defineProperties(
    {},
    {
      isLoading: {
        enumerable: true,
        get: () => {
          reads.isLoading += 1;
          return isLoading;
        },
      },
      error: {
        enumerable: true,
        get: () => {
          reads.error += 1;
          return null;
        },
      },
      isError: {
        enumerable: true,
        get: () => {
          reads.isError += 1;
          return false;
        },
      },
      isPending: {
        enumerable: true,
        get: () => {
          reads.isPending += 1;
          return true;
        },
      },
      isSuccess: {
        enumerable: true,
        get: () => {
          reads.isSuccess += 1;
          return false;
        },
      },
      status: {
        enumerable: true,
        get: () => {
          reads.status += 1;
          return "pending";
        },
      },
      isFetching: {
        enumerable: true,
        get: () => {
          reads.isFetching += 1;
          return false;
        },
      },
      dataUpdatedAt: {
        enumerable: true,
        get: () => {
          reads.dataUpdatedAt += 1;
          return 0;
        },
      },
    },
  ) as {
    error: Error | null;
    isError: boolean;
    isLoading: boolean;
    isPending: boolean;
    isSuccess: boolean;
    isFetching: boolean;
    status: "pending" | "error" | "success";
    dataUpdatedAt: number;
  };

  return { query, reads };
}

describe("withWorkspaceGuardLoading", () => {
  it("workspace 목록 미해소 중에는 원본 isLoading과 무관하게 true를 반환한다", () => {
    const { query } = createTrackedQuery(false);

    expect(withWorkspaceGuardLoading(query, true).isLoading).toBe(true);
  });

  it("workspace 목록 해소 후에는 원본 query와 isLoading 값을 그대로 반환한다", () => {
    const { query } = createTrackedQuery(false);

    const guardedQuery = withWorkspaceGuardLoading(query, false);

    expect(guardedQuery).toBe(query);
    expect(guardedQuery.isLoading).toBe(false);
  });

  it("isLoading만 읽으면 다른 query 속성에 접근하지 않는다", () => {
    const { query, reads } = createTrackedQuery(false);

    const guardedQuery = withWorkspaceGuardLoading(query, true);

    expect(guardedQuery.isLoading).toBe(true);
    expect(reads.isFetching).toBe(0);
    expect(reads.dataUpdatedAt).toBe(0);
  });

  it("목록 오류를 합성하면 error 상태 키를 함께 맞춘다", () => {
    const { query } = createTrackedQuery(false);
    const workspaceListError = new Error("workspace 목록 조회 실패");
    const guardedQuery = withWorkspaceGuardLoading(query, false, workspaceListError);

    expect(guardedQuery.error).toBe(workspaceListError);
    expect(guardedQuery.isError).toBe(true);
    expect(guardedQuery.status).toBe("error");
    expect(guardedQuery.isSuccess).toBe(false);
    expect(guardedQuery.isPending).toBe(false);
  });
});
