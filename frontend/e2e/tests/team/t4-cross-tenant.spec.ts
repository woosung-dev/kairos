// T4: cross-tenant I-9 — member 가 owner 개인 ws 접근 403 + 타 ws project id 를 team prefix 로 GET/PATCH/DELETE 404 (admin 도 우회 불가)
import { test, expect } from "../../fixtures/team";

test.describe.serial("T4 cross-tenant 격리 (I-9)", () => {
  test.afterEach(async ({ ensureMemberBaseline }) => {
    await ensureMemberBaseline();
  });

  test("member → owner 개인 ws projects 403", async ({
    memberPage,
    api,
    ownerPersonalWsId,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const res = await api(memberPage, "GET", `/api/v1/workspaces/${ownerPersonalWsId}/projects`);
    expect(res.status(), "비멤버 ws 는 403").toBe(403);
  });

  test("member → 타 ws project 를 team prefix 로 GET 404", async ({
    memberPage,
    api,
    teamWsId,
    ownerPersonalProjectId,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const res = await api(
      memberPage,
      "GET",
      `/api/v1/workspaces/${teamWsId}/projects/${ownerPersonalProjectId}`,
    );
    expect(res.status(), "타 ws resource 는 team prefix 로 404").toBe(404);
  });

  test("admin 도 타 ws project GET/PATCH/DELETE 우회 불가 (404)", async ({
    memberPage,
    api,
    teamWsId,
    ownerPersonalProjectId,
    setRole,
  }) => {
    await setRole("admin"); // role 우회를 줘도 ws predicate 로 막혀야 함
    const base = `/api/v1/workspaces/${teamWsId}/projects/${ownerPersonalProjectId}`;
    expect((await api(memberPage, "GET", base)).status(), "admin GET 404").toBe(404);
    expect(
      (await api(memberPage, "PATCH", base, { title: "hijacked" })).status(),
      "admin PATCH 404 (cross-ws write 차단)",
    ).toBe(404);
    expect((await api(memberPage, "DELETE", base)).status(), "admin DELETE 404").toBe(404);
  });
});
