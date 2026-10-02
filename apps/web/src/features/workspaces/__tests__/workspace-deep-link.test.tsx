/**
 * T-PWA-57 워크스페이스 딥링크 — 판정·호출 (docs/requirements/pwa.md §5.5 딥링크 표).
 *
 * 목은 데이터 경계(useApiClient · useMe 캐시)와 router · toast 에만 건다. 판정 훅 · store ·
 * React Query 캐시는 실물이다. self-heal 경합 회귀(S1~S5, scratchpad eval-spec3/deeplink-selfheal-race.cjs)는
 * 실제 PanelLayout(크롬만 목)을 부모로 함께 렌더해 최종 활성 ws 로 단언한다.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider, type Query } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { PanelLayout } from "@/components/layout/panel-layout";
import type { ApiClient } from "@/lib/api-client";
import { workspaceKeys } from "@/lib/query-keys";
import { useWorkspaceDeepLink } from "../hooks";
import { useWorkspaceStore } from "../store";
import type { Workspace } from "../types";

const ME = "11111111-0000-4000-8000-0000000000aa";
const OTHER_USER = "22222222-0000-4000-8000-0000000000bb";
const MEETING_ID = "9e0a7c1d-2b3c-4d5e-8f60-718293a4b5c6";
const WS_A = "aaaaaaaa-0000-4000-8000-000000000001";
const WS_B = "bbbbbbbb-0000-4000-8000-000000000002";
const WS_NON_MEMBER = "cccccccc-0000-4000-8000-000000000003";
const WS_REMOVED = "dead0000-0000-4000-8000-000000000009";
const ME_KEY = ["auth", "me"] as const;
const MEETING_PATH = `/meetings/${MEETING_ID}`;
const SWITCH_TOAST = "“B팀” 워크스페이스로 전환했습니다";

const { router, toast } = vi.hoisted(() => ({
  router: { replace: vi.fn(), refresh: vi.fn(), push: vi.fn() },
  toast: vi.fn(),
}));

// 목록·me 의 도착 시점은 테스트가 setQueryData 로 정한다 — 네트워크는 끝나지 않는다.
const api: ApiClient = {
  fetch: () => new Promise(() => {}),
  fetchRaw: () => new Promise(() => {}),
  getToken: () => Promise.resolve("token"),
};

vi.mock("@/lib/use-api-client", () => ({ useApiClient: () => api }));
vi.mock("@/features/auth/hooks", async () => {
  const { useQuery } = await import("@tanstack/react-query");
  return {
    useMe: () =>
      useQuery<{ id: string }>({
        queryKey: ["auth", "me"],
        queryFn: () => new Promise(() => {}),
        enabled: false,
      }),
  };
});
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("sonner", () => ({ toast }));

// PanelLayout 크롬 — 판정 대상이 아니다 (panel-layout.test.tsx 와 같은 경계)
vi.mock("@/features/members/hooks", () => ({ useSyncWorkspaceRole: vi.fn() }));
vi.mock("@/hooks/use-media-query", () => ({
  useBreakpoint: () => ({ isMobile: false, isCompact: false }),
}));
vi.mock("@/components/layout/sidebar", () => ({ Sidebar: () => null }));
vi.mock("@/components/layout/header", () => ({ Header: () => null }));
vi.mock("@/components/layout/bottom-nav", () => ({ BottomNav: () => null }));
vi.mock("@/components/layout/cmd-k", () => ({ CmdK: () => null }));
vi.mock("@/components/layout/rag-panel", () => ({ RagPanel: () => null }));
vi.mock("@/features/sources/components/source-viewer", () => ({ SourceViewer: () => null }));

function workspace(id: string, name: string): Workspace {
  return {
    id,
    name,
    ownerId: OTHER_USER,
    createdAt: "2026-10-01T00:00:00.000Z",
    updatedAt: "2026-10-01T00:00:00.000Z",
  };
}

const WORKSPACES = [workspace(WS_A, "A팀"), workspace(WS_B, "B팀")];
const INITIAL_STORE = useWorkspaceStore.getState();

const setActiveWorkspaceId = vi.fn((id: string) => {
  useWorkspaceStore.setState({ activeWorkspaceId: id });
});
const activateWorkspaceForUser = vi.fn((userId: string, workspaceId: string) => {
  useWorkspaceStore.setState({ ownerUserId: userId, activeWorkspaceId: workspaceId });
});

function DeepLinkProbe({ param }: { param: string | null }) {
  const { isSettled } = useWorkspaceDeepLink(MEETING_ID, param);
  return <div data-testid="deep-link-settled">{String(isSettled)}</div>;
}

interface SetupOptions {
  readonly param: string | null;
  readonly active: string | null;
  readonly owner?: string | null;
  readonly workspaces?: Workspace[];
  readonly me?: { id: string };
  readonly withLayout?: boolean;
}

function setup({ param, active, owner = ME, workspaces, me, withLayout = false }: SetupOptions) {
  useWorkspaceStore.setState({
    activeWorkspaceId: active,
    ownerUserId: owner,
    setActiveWorkspaceId,
    activateWorkspaceForUser,
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (workspaces) queryClient.setQueryData(workspaceKeys.list(), workspaces);
  if (me) queryClient.setQueryData(ME_KEY, me);
  const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
  const clearSpy = vi.spyOn(queryClient, "clear");

  const tree = (): ReactNode => {
    const probe = <DeepLinkProbe param={param} />;
    return (
      <QueryClientProvider client={queryClient}>
        {withLayout ? <PanelLayout>{probe}</PanelLayout> : probe}
      </QueryClientProvider>
    );
  };
  const view = render(tree());
  return {
    queryClient,
    invalidateSpy,
    clearSpy,
    rerender: () => view.rerender(tree()),
    arrive: async (patch: { me?: { id: string }; workspaces?: Workspace[] }) => {
      await act(async () => {
        if (patch.me) queryClient.setQueryData(ME_KEY, patch.me);
        if (patch.workspaces) queryClient.setQueryData(workspaceKeys.list(), patch.workspaces);
        // React Query v5 notifyManager 는 observer 알림을 setTimeout(0) 으로 배치한다 — 한 매크로태스크를 기다린다
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    },
  };
}

const settled = () => screen.getByTestId("deep-link-settled").textContent;
const activeWid = () => useWorkspaceStore.getState().activeWorkspaceId;
const switchToasts = () => toast.mock.calls.filter(([message]) => message === SWITCH_TOAST);

function expectNoSwitch() {
  expect(setActiveWorkspaceId).not.toHaveBeenCalled();
  expect(activateWorkspaceForUser).not.toHaveBeenCalled();
  expect(toast).not.toHaveBeenCalled();
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
  useWorkspaceStore.setState(INITIAL_STORE, true);
});

describe("T-PWA-57 딥링크 판정 — §5.5 표 7개 조건", () => {
  it("파라미터 없음 → 전환 0 · replace 0", () => {
    setup({ param: null, active: WS_A, workspaces: WORKSPACES, me: { id: ME } });
    expect(settled()).toBe("true");
    expectNoSwitch();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("비UUID → 전환 0 · replace 1", () => {
    setup({ param: "not-a-uuid", active: WS_A, workspaces: WORKSPACES, me: { id: ME } });
    expectNoSwitch();
    expect(router.replace).toHaveBeenCalledTimes(1);
    expect(router.replace).toHaveBeenCalledWith(MEETING_PATH);
  });

  it("목록 로딩 중 → 대기 (전환·replace 0), 목록 도착 후 판정", async () => {
    const { arrive } = setup({ param: WS_B, active: WS_A, me: { id: ME } });
    expect(settled()).toBe("false");
    expectNoSwitch();
    expect(router.replace).not.toHaveBeenCalled();

    await arrive({ workspaces: WORKSPACES });
    expect(setActiveWorkspaceId).toHaveBeenCalledTimes(1);
    expect(router.replace).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["me 로딩 중", { active: WS_A, me: undefined }],
    ["활성 ws null", { active: null, me: { id: ME } }],
    ["활성 ws 가 목록 밖 (self-heal 대기)", { active: WS_REMOVED, me: { id: ME } }],
  ])("%s → 대기 (전환·replace 0)", (_label, { active, me }) => {
    setup({ param: WS_B, active, workspaces: WORKSPACES, me });
    expect(settled()).toBe("false");
    expectNoSwitch();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("같은 wid → 전환 0 · replace 1", () => {
    setup({ param: WS_A, active: WS_A, workspaces: WORKSPACES, me: { id: ME } });
    expect(settled()).toBe("true");
    expectNoSwitch();
    expect(router.replace).toHaveBeenCalledTimes(1);
    expect(router.replace).toHaveBeenCalledWith(MEETING_PATH);
  });

  it("멤버 + 다른 wid (소유자 == me) → setActiveWorkspaceId 1 · invalidate 1 · toast 1 · replace 1, 재렌더·refetch 에 추가 0", async () => {
    const { invalidateSpy, clearSpy, rerender, arrive } = setup({
      param: WS_B,
      active: WS_A,
      workspaces: WORKSPACES,
      me: { id: ME },
    });

    expect(setActiveWorkspaceId).toHaveBeenCalledTimes(1);
    expect(setActiveWorkspaceId).toHaveBeenCalledWith(WS_B);
    expect(activateWorkspaceForUser).not.toHaveBeenCalled();
    expect(activeWid()).toBe(WS_B);

    expect(invalidateSpy).toHaveBeenCalledTimes(1);
    const filters = invalidateSpy.mock.calls[0][0];
    const predicate = filters?.predicate;
    if (!predicate) throw new Error("predicate 무효화가 아니다");
    const query = (queryKey: readonly unknown[]) => ({ queryKey }) as unknown as Query;
    expect(predicate(query(["workspaces", "list"]))).toBe(false);
    expect(predicate(query(["meetings", WS_B, "detail", MEETING_ID]))).toBe(true);

    expect(toast).toHaveBeenCalledTimes(1);
    expect(toast).toHaveBeenCalledWith(SWITCH_TOAST);
    expect(router.replace).toHaveBeenCalledTimes(1);
    expect(router.replace).toHaveBeenCalledWith(MEETING_PATH);
    expect(settled()).toBe("true");

    rerender();
    rerender();
    await arrive({ workspaces: [...WORKSPACES] });

    expect(setActiveWorkspaceId).toHaveBeenCalledTimes(1);
    expect(invalidateSpy).toHaveBeenCalledTimes(1);
    expect(toast).toHaveBeenCalledTimes(1);
    expect(router.replace).toHaveBeenCalledTimes(1);
    expect(clearSpy).not.toHaveBeenCalled();
    expect(router.refresh).not.toHaveBeenCalled();
    expect(router.push).not.toHaveBeenCalled();
  });

  it.each([
    ["소유자 없음", null],
    ["소유자 다름", OTHER_USER],
  ])("멤버 + 다른 wid (%s) → activateWorkspaceForUser(me.id, wid) 1회", (_label, owner) => {
    setup({ param: WS_B, active: WS_A, owner, workspaces: WORKSPACES, me: { id: ME } });
    expect(activateWorkspaceForUser).toHaveBeenCalledTimes(1);
    expect(activateWorkspaceForUser).toHaveBeenCalledWith(ME, WS_B);
    expect(setActiveWorkspaceId).not.toHaveBeenCalled();
    expect(useWorkspaceStore.getState().ownerUserId).toBe(ME);
    expect(activeWid()).toBe(WS_B);
    expect(switchToasts()).toHaveLength(1);
  });

  it("비멤버 → 전환 0 · toast 0 · replace 1", () => {
    const { invalidateSpy } = setup({
      param: WS_NON_MEMBER,
      active: WS_A,
      workspaces: WORKSPACES,
      me: { id: ME },
    });
    expect(settled()).toBe("true");
    expectNoSwitch();
    expect(invalidateSpy).not.toHaveBeenCalled();
    expect(activeWid()).toBe(WS_A);
    expect(router.replace).toHaveBeenCalledTimes(1);
    expect(router.replace).toHaveBeenCalledWith(MEETING_PATH);
  });
});

describe("T-PWA-57 self-heal 경합 회귀 — 부모 PanelLayout 과 함께 렌더 (eval-spec3 S1~S5)", () => {
  it.each([
    ["S1 active=A(유효), me+목록 동시", { owner: ME, active: WS_A }, "together"],
    ["S2 active=제거된 ws, me+목록 동시", { owner: ME, active: WS_REMOVED }, "together"],
    ["S3 active=null, me 먼저 → 목록", { owner: ME, active: null }, "me-first"],
    ["S4 빈 저장소(소유자 null), me+목록 동시", { owner: null, active: null }, "together"],
    ["S5 active=제거된 ws, 목록 먼저 → me", { owner: ME, active: WS_REMOVED }, "list-first"],
  ] as const)("%s → 최종 활성 = 파라미터 wid · toast 1 · replace 1", async (_label, init, order) => {
    const { arrive } = setup({ param: WS_B, active: init.active, owner: init.owner, withLayout: true });
    expect(router.replace).not.toHaveBeenCalled();

    if (order === "together") {
      await arrive({ me: { id: ME }, workspaces: WORKSPACES });
    } else if (order === "me-first") {
      await arrive({ me: { id: ME } });
      await arrive({ workspaces: WORKSPACES });
    } else {
      await arrive({ workspaces: WORKSPACES });
      await arrive({ me: { id: ME } });
    }

    expect(activeWid()).toBe(WS_B);
    expect(useWorkspaceStore.getState().ownerUserId).toBe(ME);
    expect(switchToasts()).toHaveLength(1);
    expect(router.replace).toHaveBeenCalledTimes(1);
    expect(router.replace).toHaveBeenCalledWith(MEETING_PATH);
    expect(settled()).toBe("true");
  });
});
