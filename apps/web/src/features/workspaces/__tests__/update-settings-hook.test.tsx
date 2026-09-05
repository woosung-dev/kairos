import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { workspaceKeys } from "@/lib/query-keys";
import { useUpdateWorkspaceSettings } from "../hooks";

const { updateWorkspaceSettings, toastSuccess, toastError } = vi.hoisted(() => ({
  updateWorkspaceSettings: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock("@/lib/use-api-client", () => ({
  useApiClient: () => ({}),
}));

vi.mock("sonner", () => ({
  toast: { success: toastSuccess, error: toastError },
}));

vi.mock("../api", () => ({
  fetchWorkspaces: vi.fn(),
  createWorkspace: vi.fn(),
  fetchWorkspace: vi.fn(),
  updateWorkspaceSettings,
  deleteWorkspace: vi.fn(),
}));

const WID = "workspace-1";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { Wrapper, invalidateSpy };
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("useUpdateWorkspaceSettings", () => {
  it("이름 변경은 이름 토스트를 띄우고 상세·목록 쿼리를 모두 무효화한다", async () => {
    updateWorkspaceSettings.mockResolvedValue({ inboxThreshold: 0.9, name: "제품팀" });
    const { Wrapper, invalidateSpy } = createWrapper();
    const { result } = renderHook(() => useUpdateWorkspaceSettings(WID), {
      wrapper: Wrapper,
    });

    result.current.mutate({ name: "제품팀" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(updateWorkspaceSettings).toHaveBeenCalledWith({}, WID, { name: "제품팀" });
    expect(toastSuccess).toHaveBeenCalledWith("워크스페이스 이름이 변경되었습니다");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: workspaceKeys.detail(WID) });
    // 헤더 WorkspaceSwitcher 가 읽는 목록도 갱신되어야 새 이름이 보인다.
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: workspaceKeys.list() });
  });

  it("임계값 변경은 기존 임계값 토스트를 유지한다", async () => {
    updateWorkspaceSettings.mockResolvedValue({ inboxThreshold: 0.8, name: "제품팀" });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useUpdateWorkspaceSettings(WID), {
      wrapper: Wrapper,
    });

    result.current.mutate({ inboxThreshold: 0.8 });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(updateWorkspaceSettings).toHaveBeenCalledWith({}, WID, { inboxThreshold: 0.8 });
    expect(toastSuccess).toHaveBeenCalledWith("임계값이 80%로 변경되었습니다");
  });

  it("실패 시 에러 토스트를 띄운다", async () => {
    updateWorkspaceSettings.mockRejectedValue(new Error("권한이 없습니다"));
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useUpdateWorkspaceSettings(WID), {
      wrapper: Wrapper,
    });

    result.current.mutate({ name: "제품팀" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toastError).toHaveBeenCalledWith("권한이 없습니다");
    expect(toastSuccess).not.toHaveBeenCalled();
  });
});
