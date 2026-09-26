/**
 * BL-FE-WS-HEAL-SCOPE-1 후속 — 초대 수락 시 워크스페이스 목록 캐시 무효화.
 *
 * panel-layout 의 self-heal 은 "activeWorkspaceId 가 워크스페이스 목록에 있는가" 로
 * 판정한다. 그래서 내 멤버십을 바꾸는 mutation 은 목록 캐시를 갱신해야 한다는 불변식이
 * 생긴다 — useCreateWorkspace 는 setQueryData 로 이미 지키고 있었고, useAcceptInvite 만
 * 지키지 않았다. 지키지 않으면 방금 수락한 ws 가 '목록에 없음' 으로 판정돼 덮어써진다.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { workspaceKeys } from "@/lib/query-keys";
import { acceptInvite } from "../api";
import { useAcceptInvite } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";

const { fetchMe } = vi.hoisted(() => ({ fetchMe: vi.fn() }));

vi.mock("@/features/auth/hooks", () => ({
  useMe: () => ({ data: null }),
  meQueryOptions: () => ({ queryKey: ["auth", "me"], queryFn: fetchMe, retry: false }),
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

afterEach(() => {
  useWorkspaceStore.setState({ activeWorkspaceId: null, ownerUserId: null });
  vi.clearAllMocks();
});

function renderAccept() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const invalidate = vi.spyOn(queryClient, "invalidateQueries");
  const { result } = renderHook(() => useAcceptInvite(), {
    wrapper: ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  });
  return { result, invalidate };
}

describe("useAcceptInvite — 워크스페이스 목록 캐시 무효화", () => {
  it("수락에 성공하면 workspaces.list 를 무효화한다", async () => {
    fetchMe.mockResolvedValue({ id: "user-1" });
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

// C-001 회귀 가드 — 빈 브라우저 저장소(ownerUserId=null)에서 초대를 수락하면 panel-layout 의
// ensureOwner(me.id) 가 "다른 계정" 으로 판정해 활성 ws 를 지웠고, self-heal 이 목록 첫 ws 로 덮어썼다.
describe("useAcceptInvite — 수락한 워크스페이스에 착지 (C-001)", () => {
  it("빈 저장소에서도 소유자와 활성 ws 를 함께 확정하고, 이후 ensureOwner 가 지우지 않는다", async () => {
    useWorkspaceStore.setState({ activeWorkspaceId: null, ownerUserId: null });
    fetchMe.mockResolvedValue({ id: "user-1" });
    vi.mocked(acceptInvite).mockResolvedValue({
      workspaceId: "ws-team-2",
    } as Awaited<ReturnType<typeof acceptInvite>>);

    const { result } = renderAccept();
    result.current.mutate("invite-code");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(useWorkspaceStore.getState()).toMatchObject({
      ownerUserId: "user-1",
      activeWorkspaceId: "ws-team-2",
    });

    // panel-layout 이 마운트되며 부르는 소유자 가드 — 같은 user 면 활성 ws 를 유지해야 한다
    useWorkspaceStore.getState().ensureOwner("user-1");
    expect(useWorkspaceStore.getState().activeWorkspaceId).toBe("ws-team-2");
  });

  it("me 조회가 실패해도 수락은 성공으로 두고 활성 ws 만이라도 세팅한다", async () => {
    fetchMe.mockRejectedValue(new Error("network"));
    vi.mocked(acceptInvite).mockResolvedValue({
      workspaceId: "ws-team-2",
    } as Awaited<ReturnType<typeof acceptInvite>>);

    const { result } = renderAccept();
    result.current.mutate("invite-code");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(useWorkspaceStore.getState().activeWorkspaceId).toBe("ws-team-2");
  });
});
