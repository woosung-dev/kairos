// T7: RBAC mutate 경계 — member 는 role 변경(require_owner)·멤버 제거(require_admin) 불가, admin 도 role 변경 불가
import { test, expect } from "../../fixtures/team";

test.describe.serial("T7 RBAC mutate 경계", () => {
  test.afterEach(async ({ ensureMemberBaseline }) => {
    await ensureMemberBaseline();
  });

  test("member 는 role 변경 불가 (require_owner) — self-promotion 차단", async ({
    memberPage,
    api,
    teamWsId,
    getMemberId,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const id = await getMemberId();
    expect(id).not.toBeNull();
    const res = await api(memberPage, "PATCH", `/api/v1/workspaces/${teamWsId}/members/${id}`, {
      role: "admin",
    });
    expect(res.status(), "member self-promote → 403 (require_owner; mutation 시 200)").toBe(403);
  });

  test("member 는 멤버 제거 불가 (require_admin)", async ({
    memberPage,
    api,
    teamWsId,
    getMemberId,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const id = await getMemberId();
    const res = await api(memberPage, "DELETE", `/api/v1/workspaces/${teamWsId}/members/${id}`);
    expect(res.status(), "member DELETE → 403 (require_admin)").toBe(403);
  });

  test("admin 도 role 변경 불가 (require_owner) — admin self-demote 차단", async ({
    memberPage,
    api,
    teamWsId,
    getMemberId,
    setRole,
  }) => {
    await setRole("admin");
    const id = await getMemberId();
    const res = await api(memberPage, "PATCH", `/api/v1/workspaces/${teamWsId}/members/${id}`, {
      role: "viewer",
    });
    expect(res.status(), "admin 도 role 변경은 owner 전용 → 403").toBe(403);
  });
});
