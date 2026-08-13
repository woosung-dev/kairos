/**
 * BL-FE-WS-HEAL-SCOPE-1 — 접근 불가 activeWorkspaceId 자가 교정 회귀 가드.
 *
 * 브라우저 실측(2026-08-01): 접근 불가 wid 를 가진 채 /projects·/inbox·/projects/<id> 로
 * 직접 진입하면 21초 뒤에도 403 이 계속 나가고 화면이 죽었다. 같은 보정이
 * dashboard/page.tsx 에만 있어 /dashboard 를 거쳐야만 복구됐다.
 *
 * 목은 **데이터 훅과 레이아웃 크롬에만** 건다. 판정 대상인 self-heal effect 와
 * useWorkspaceStore 는 실물을 쓰고 실제 렌더 후 store 상태로 단언한다.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, waitFor } from "@testing-library/react";
import { useIsValidWorkspaceId, useWorkspaces } from "@/features/workspaces/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import type { Workspace } from "@/features/workspaces/types";
import { PanelLayout } from "../panel-layout";

const CURRENT_USER = "user_A";
const { toast } = vi.hoisted(() => ({ toast: vi.fn() }));

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ userId: CURRENT_USER }),
}));

vi.mock("sonner", () => ({ toast }));

vi.mock("@/features/workspaces/hooks", () => ({
  useWorkspaces: vi.fn(),
  useIsValidWorkspaceId: vi.fn(),
}));

vi.mock("@/features/members/hooks", () => ({
  useSyncWorkspaceRole: vi.fn(),
}));

vi.mock("@/hooks/use-media-query", () => ({
  useBreakpoint: () => ({ isMobile: false, isCompact: false }),
}));

// 레이아웃 크롬 — 판정 대상이 아니고 각자 Clerk/router/데이터에 의존한다.
vi.mock("../sidebar", () => ({ Sidebar: () => null }));
vi.mock("../header", () => ({ Header: () => null }));
vi.mock("../bottom-nav", () => ({ BottomNav: () => null }));
vi.mock("../cmd-k", () => ({ CmdK: () => null }));
vi.mock("../rag-panel", () => ({ RagPanel: () => null }));
vi.mock("@/features/sources/components/source-viewer", () => ({
  SourceViewer: () => null,
}));

function workspace(id: string, name: string): Workspace {
  return {
    id,
    name,
    ownerId: "owner-1",
    createdAt: "2026-08-01T00:00:00.000Z",
    updatedAt: "2026-08-01T00:00:00.000Z",
  };
}

const WS_LIST = [workspace("ws-1", "첫 워크스페이스"), workspace("ws-2", "두 번째")];

function mockWorkspaces(data: Workspace[] | undefined) {
  vi.mocked(useWorkspaces).mockReturnValue({
    data,
  } as unknown as ReturnType<typeof useWorkspaces>);
  vi.mocked(useIsValidWorkspaceId).mockImplementation(
    (wid) => !!wid && !!data?.some((workspace) => workspace.id === wid),
  );
}

function renderLayout() {
  return render(
    <PanelLayout>
      <div>본문</div>
    </PanelLayout>,
  );
}

function activeWid() {
  return useWorkspaceStore.getState().activeWorkspaceId;
}

describe("PanelLayout — activeWorkspaceId self-heal", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    // ownerUserId 를 현재 사용자로 맞춰 둔다 — 불일치면 ensureOwner 가 먼저 초기화해
    // '목록에 있는 wid 는 유지' 를 검증할 수 없다.
    useWorkspaceStore.setState({
      activeWorkspaceId: null,
      ownerUserId: CURRENT_USER,
    });
  });

  it("접근 불가 wid(목록에 없음)는 목록 첫 워크스페이스로 교정하고 한 번 알린다", async () => {
    useWorkspaceStore.setState({ activeWorkspaceId: "ws-foreign" });
    mockWorkspaces(WS_LIST);

    const { rerender } = renderLayout();

    await waitFor(() => expect(activeWid()).toBe("ws-1"));
    expect(toast).toHaveBeenCalledTimes(1);
    expect(toast).toHaveBeenCalledWith(
      "접근할 수 없어 “첫 워크스페이스” 워크스페이스로 전환했습니다",
    );

    rerender(
      <PanelLayout>
        <div>본문</div>
      </PanelLayout>,
    );
    expect(toast).toHaveBeenCalledTimes(1);
  });

  it("목록에 있는 wid 는 덮어쓰지 않는다", async () => {
    useWorkspaceStore.setState({ activeWorkspaceId: "ws-2" });
    mockWorkspaces(WS_LIST);

    renderLayout();

    await waitFor(() => expect(useWorkspaces).toHaveBeenCalled());
    expect(activeWid()).toBe("ws-2");
    expect(toast).not.toHaveBeenCalled();
  });

  it("wid 가 비어있으면 목록 첫 워크스페이스로 채운다", async () => {
    useWorkspaceStore.setState({ activeWorkspaceId: null });
    mockWorkspaces(WS_LIST);

    renderLayout();

    await waitFor(() => expect(activeWid()).toBe("ws-1"));
    expect(toast).not.toHaveBeenCalled();
  });

  it("목록 로딩 중(undefined)에는 접근 불가 wid 라도 건드리지 않는다", async () => {
    useWorkspaceStore.setState({ activeWorkspaceId: "ws-foreign" });
    mockWorkspaces(undefined);

    renderLayout();

    await waitFor(() => expect(useWorkspaces).toHaveBeenCalled());
    expect(activeWid()).toBe("ws-foreign");
    expect(toast).not.toHaveBeenCalled();
  });
});
