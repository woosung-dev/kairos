// T1: 초대 발급 RBAC — member/viewer→403, owner/admin→201 (실 2-토큰, RoleChecker 관통, mock 금지)
import { test, expect } from "../../fixtures/team";

test.describe.serial("T1 초대 발급 RBAC (require_admin)", () => {
  test.afterEach(async ({ ensureMemberBaseline }) => {
    await ensureMemberBaseline();
  });

  test("owner → 201 (body code+inviteUrl)", async ({ ownerPage, api, teamWsId }) => {
    const res = await api(ownerPage, "POST", `/api/v1/workspaces/${teamWsId}/invites`, {
      role: "member",
      maxUses: null,
      expiresInDays: 30,
    });
    expect(res.status()).toBe(201);
    const body = (await res.json()) as { code?: string; invite_url?: string; inviteUrl?: string };
    expect(body.code, "초대 code 발급").toBeTruthy();
    expect(body.invite_url ?? body.inviteUrl, "inviteUrl 포함").toBeTruthy();
  });

  test("member → 403", async ({ memberPage, api, teamWsId, ensureMemberBaseline }) => {
    await ensureMemberBaseline();
    const res = await api(memberPage, "POST", `/api/v1/workspaces/${teamWsId}/invites`, {
      role: "member",
    });
    expect(res.status(), "member 는 초대 발급 불가").toBe(403);
  });

  test("viewer → 403", async ({ memberPage, api, teamWsId, setRole }) => {
    await setRole("viewer");
    const res = await api(memberPage, "POST", `/api/v1/workspaces/${teamWsId}/invites`, {
      role: "member",
    });
    expect(res.status(), "viewer 는 초대 발급 불가").toBe(403);
  });

  test("admin → 201 (require_admin 통과)", async ({ memberPage, api, teamWsId, setRole }) => {
    await setRole("admin");
    const res = await api(memberPage, "POST", `/api/v1/workspaces/${teamWsId}/invites`, {
      role: "member",
      maxUses: null,
      expiresInDays: 30,
    });
    expect(res.status(), "admin 은 초대 발급 가능").toBe(201);
  });
});
