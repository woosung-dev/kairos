import { describe, expect, it, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../api-client";
import { QueryProvider } from "../query-client";

describe("QueryProvider 기본 재시도 정책", () => {
  function getRetry() {
    let queryClient: ReturnType<typeof useQueryClient> | undefined;

    function Probe() {
      queryClient = useQueryClient();
      return null;
    }

    render(
      <QueryProvider>
        <Probe />
      </QueryProvider>,
    );

    const retry = queryClient?.getDefaultOptions().queries?.retry;
    expect(retry).toBeTypeOf("function");
    return retry as (failureCount: number, error: Error) => boolean;
  }

  it("403 ApiError는 재시도하지 않는다", () => {
    const shouldRetry = getRetry();

    expect(shouldRetry(0, new ApiError("권한 없음", 403))).toBe(false);
  });

  it("500 ApiError는 한 번 재시도한다", () => {
    const shouldRetry = getRetry();

    expect(shouldRetry(0, new ApiError("서버 오류", 500))).toBe(true);
    expect(shouldRetry(1, new ApiError("서버 오류", 500))).toBe(false);
  });

  it("일반 오류는 한 번 재시도한다", () => {
    const shouldRetry = getRetry();

    expect(shouldRetry(0, new Error("네트워크 오류"))).toBe(true);
    expect(shouldRetry(1, new Error("네트워크 오류"))).toBe(false);
  });

  async function expectQueryRetry(error: Error) {
    const queryFn = vi
      .fn()
      .mockRejectedValueOnce(error)
      .mockResolvedValueOnce("재시도 성공");

    function Probe() {
      useQuery({ queryKey: ["retry", error.message], queryFn });
      return null;
    }

    render(
      <QueryProvider>
        <Probe />
      </QueryProvider>,
    );

    await waitFor(() => expect(queryFn).toHaveBeenCalledTimes(2), {
      timeout: 1_500,
    });
  }

  it("500 쿼리는 실제로 한 번 재시도한다", async () => {
    await expectQueryRetry(new ApiError("서버 오류", 500));
  });

  it("일반 오류 쿼리는 실제로 한 번 재시도한다", async () => {
    await expectQueryRetry(new Error("네트워크 오류"));
  });
});
