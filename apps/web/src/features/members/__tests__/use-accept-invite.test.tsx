/**
 * BL-FE-WS-HEAL-SCOPE-1 후속 — 초대 수락 시 워크스페이스 목록 캐시 무효화.
 *
 * panel-layout 의 self-heal 은 "activeWorkspaceId 가 워크스페이스 목록에 있는가" 로
 * 판정한다. 그래서 내 멤버십을 바꾸는 mutation 은 목록 캐시를 갱신해야 한다는 불변식이
 * 생긴다 — useCreateWorkspace 는 setQueryData 로 이미 지키고 있었고, useAcceptInvite 만
 * 지키지 않았다. 지키지 않으면 방금 수락한 ws 가 '목록에 없음' 으로 판정돼 덮어써진다.
 */
import { describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { workspaceKeys } from "@/lib/query-keys";
import { acceptInvite } from "../api";
import { useAcceptInvite } from "../hooks";

vi.mock("@/features/auth/hooks", () => ({
  useMe: () => ({ data: null }),
}));

vi.mock("@/lib/use-api-client", () => ({
  useApiClient: () => ({}),
}));

vi.mock("../api", () => ({
  acceptInvite: vi.fn(),
  fetchMembers: vi.fn(),
  updateMemberRole: vi.fn(),
  removeMember: vi.fn(),
  fetchInvites: vi.fn(),
  createInvite: vi.fn(),
  deactivateInvite: vi.fn(),
  fetchInviteInfo: vi.fn(),
}));

describe("useAcceptInvite — 워크스페이스 목록 캐시 무효화", () => {
  it("수락에 성공하면 workspaces.list 를 무효화한다", async () => {
    vi.mocked(acceptInvite).mockResolvedValue({
      workspaceId: "ws-new",
    } as Awaited<ReturnType<typeof acceptInvite>>);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useAcceptInvite(), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    });

    result.current.mutate("invite-code");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: workspaceKeys.list() });
  });
});
