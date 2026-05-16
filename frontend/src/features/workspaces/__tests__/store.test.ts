// useWorkspaceStore.hasRole RBAC 매트릭스 + persist 동작 단위 테스트
import { beforeEach, describe, expect, it } from "vitest";
import { useWorkspaceStore } from "../store";
import type { WorkspaceRole } from "@/features/members/types";

describe("useWorkspaceStore — hasRole RBAC matrix", () => {
  beforeEach(() => {
    // store 초기화 — workspaceRole + activeWorkspaceId 둘 다 null 로
    useWorkspaceStore.setState({
      activeWorkspaceId: null,
      workspaceRole: null,
    });
  });

  it("role 미설정 (null) 시 항상 false", () => {
    const { hasRole } = useWorkspaceStore.getState();
    expect(hasRole("viewer")).toBe(false);
    expect(hasRole("member")).toBe(false);
    expect(hasRole("admin")).toBe(false);
    expect(hasRole("owner")).toBe(false);
  });

  describe("owner (level 4)", () => {
    beforeEach(() => useWorkspaceStore.setState({ workspaceRole: "owner" }));

    it("모든 요구 권한 통과", () => {
      const { hasRole } = useWorkspaceStore.getState();
      expect(hasRole("viewer")).toBe(true);
      expect(hasRole("member")).toBe(true);
      expect(hasRole("admin")).toBe(true);
      expect(hasRole("owner")).toBe(true);
    });
  });

  describe("admin (level 3)", () => {
    beforeEach(() => useWorkspaceStore.setState({ workspaceRole: "admin" }));

    it("owner 만 거부, 나머지 통과", () => {
      const { hasRole } = useWorkspaceStore.getState();
      expect(hasRole("viewer")).toBe(true);
      expect(hasRole("member")).toBe(true);
      expect(hasRole("admin")).toBe(true);
      expect(hasRole("owner")).toBe(false);
    });
  });

  describe("member (level 2)", () => {
    beforeEach(() => useWorkspaceStore.setState({ workspaceRole: "member" }));

    it("viewer/member 만 통과, admin/owner 거부", () => {
      const { hasRole } = useWorkspaceStore.getState();
      expect(hasRole("viewer")).toBe(true);
      expect(hasRole("member")).toBe(true);
      expect(hasRole("admin")).toBe(false);
      expect(hasRole("owner")).toBe(false);
    });
  });

  describe("viewer (level 1)", () => {
    beforeEach(() => useWorkspaceStore.setState({ workspaceRole: "viewer" }));

    it("viewer 만 통과, member 이상 거부", () => {
      const { hasRole } = useWorkspaceStore.getState();
      expect(hasRole("viewer")).toBe(true);
      expect(hasRole("member")).toBe(false);
      expect(hasRole("admin")).toBe(false);
      expect(hasRole("owner")).toBe(false);
    });
  });

  describe("role 전환", () => {
    it("owner → viewer 전환 시 hasRole 즉시 반영", () => {
      useWorkspaceStore.setState({ workspaceRole: "owner" });
      expect(useWorkspaceStore.getState().hasRole("admin")).toBe(true);

      useWorkspaceStore.setState({ workspaceRole: "viewer" });
      expect(useWorkspaceStore.getState().hasRole("admin")).toBe(false);
      expect(useWorkspaceStore.getState().hasRole("viewer")).toBe(true);
    });

    it("viewer → null (워크스페이스 이탈) 시 모두 false", () => {
      useWorkspaceStore.setState({ workspaceRole: "viewer" });
      expect(useWorkspaceStore.getState().hasRole("viewer")).toBe(true);

      useWorkspaceStore.setState({ workspaceRole: null });
      expect(useWorkspaceStore.getState().hasRole("viewer")).toBe(false);
    });
  });

  describe("ROLE_LEVEL 매트릭스 전수", () => {
    // 4 × 4 = 16 cell 매트릭스 — fence-post 회귀 가드
    const roles: WorkspaceRole[] = ["owner", "admin", "member", "viewer"];
    const expectedMatrix: Record<WorkspaceRole, Record<WorkspaceRole, boolean>> = {
      owner: { owner: true, admin: true, member: true, viewer: true },
      admin: { owner: false, admin: true, member: true, viewer: true },
      member: { owner: false, admin: false, member: true, viewer: true },
      viewer: { owner: false, admin: false, member: false, viewer: true },
    };

    roles.forEach((current) => {
      roles.forEach((required) => {
        it(`current=${current} hasRole(${required}) → ${expectedMatrix[current][required]}`, () => {
          useWorkspaceStore.setState({ workspaceRole: current });
          expect(useWorkspaceStore.getState().hasRole(required)).toBe(
            expectedMatrix[current][required],
          );
        });
      });
    });
  });
});
