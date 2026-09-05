import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import SettingsPage from "@/app/(app)/settings/page";

const { mutate, useWorkspace, useUpdateWorkspaceSettings } = vi.hoisted(() => ({
  mutate: vi.fn(),
  useWorkspace: vi.fn(),
  useUpdateWorkspaceSettings: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams("tab=general"),
}));

vi.mock("@/features/workspaces/store", () => ({
  useWorkspaceStore: () => ({
    activeWorkspaceId: "workspace-1",
    workspaceRole: "owner",
    hasRole: () => true,
  }),
}));

vi.mock("@/features/workspaces/hooks", () => ({
  useWorkspace,
  useUpdateWorkspaceSettings,
}));

vi.mock("@/features/members/hooks", () => ({
  useMembers: () => ({ data: undefined }),
  useInvites: () => ({ data: undefined }),
}));

// 일반 탭의 이름 폼만 검증한다 — 다른 탭의 무거운 자식과 Tabs 원시 컴포넌트는 단순화.
vi.mock("@/features/members/components/member-list", () => ({
  MemberList: () => null,
}));
vi.mock("@/features/members/components/invite-manager", () => ({
  InviteManager: () => null,
}));
vi.mock("@/features/audit/components/audit-list", () => ({
  AuditList: () => null,
}));
vi.mock("@/features/workspaces/components/DangerZone", () => ({
  DangerZone: () => null,
}));
vi.mock("@/features/workspaces/components/google-drive-prototype", () => ({
  GoogleDrivePrototype: () => null,
}));
vi.mock("@/components/ui/tabs", () => ({
  Tabs: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsList: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsTrigger: ({ children }: { children: ReactNode }) => <button>{children}</button>,
  TabsContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

function renderGeneralTab(isPending = false) {
  useUpdateWorkspaceSettings.mockReturnValue({ mutate, isPending });
  render(<SettingsPage />);
  return {
    input: screen.getByTestId("ws-name-input") as HTMLInputElement,
    save: screen.getByTestId("ws-name-save") as HTMLButtonElement,
  };
}

beforeEach(() => {
  mutate.mockReset();
  useWorkspace.mockReturnValue({
    data: { id: "workspace-1", name: "제품팀", inboxThreshold: 0.9, memberCount: 1 },
  });
});

describe("Settings 일반 탭 — 워크스페이스 이름 폼", () => {
  it("서버 이름으로 시드되고, 바뀐 게 없으면 저장이 비활성이다", () => {
    const { input, save } = renderGeneralTab();

    expect(input.value).toBe("제품팀");
    expect(save).toBeDisabled();
  });

  it("새 이름을 입력하면 저장이 활성화되고 trim 된 이름으로 mutate 한다", () => {
    const { input, save } = renderGeneralTab();

    fireEvent.change(input, { target: { value: "  제품팀 v2  " } });

    expect(save).toBeEnabled();
    fireEvent.click(save);
    expect(mutate).toHaveBeenCalledWith({ name: "제품팀 v2" });
  });

  it("공백만 입력하면 저장이 비활성이고 submit 도 막힌다", () => {
    const { input, save } = renderGeneralTab();

    fireEvent.change(input, { target: { value: "   " } });

    expect(save).toBeDisabled();
    fireEvent.submit(input.closest("form")!);
    expect(mutate).not.toHaveBeenCalled();
  });

  it("Enter(form submit) 로도 저장된다", () => {
    const { input } = renderGeneralTab();

    fireEvent.change(input, { target: { value: "운영팀" } });
    fireEvent.submit(input.closest("form")!);

    expect(mutate).toHaveBeenCalledWith({ name: "운영팀" });
  });

  it("저장 중에는 버튼이 '저장 중...' 이고 비활성이다", () => {
    const { input, save } = renderGeneralTab(true);

    fireEvent.change(input, { target: { value: "운영팀" } });

    expect(save).toHaveTextContent("저장 중...");
    expect(save).toBeDisabled();
  });
});
