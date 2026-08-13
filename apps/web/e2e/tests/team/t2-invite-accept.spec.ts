// T2: 초대 수락이 정확한 role 부여 — B 제거 후 member 초대 재수락 → role==member, wsId==team (remove-restore)
import { test, expect } from "../../fixtures/team";

test.describe.serial("T2 초대 수락 role 부여", () => {
  test.afterEach(async ({ ensureMemberBaseline }) => {
    await ensureMemberBaseline();
  });

  test("제거된 B 가 member 초대 수락 → role=member, workspaceId=team", async ({
    ownerPage,
    memberPage,
    api,
    teamWsId,
    getMemberId,
  }) => {
    // B 제거 (재수락이 실 add_member 경로를 타게 — 이미 멤버면 409 단락)
    const id = await getMemberId();
    expect(id).not.toBeNull();
    const del = await api(ownerPage, "DELETE", `/api/v1/workspaces/${teamWsId}/members/${id}`);
    expect(del.status()).toBe(204);

    // owner 가 member role 초대 발급
    const inv = await api(ownerPage, "POST", `/api/v1/workspaces/${teamWsId}/invites`, {
      role: "member",
      maxUses: null,
      expiresInDays: 30,
    });
    expect(inv.status()).toBe(201);
    const code = ((await inv.json()) as { code: string }).code;

    // B 수락 → 정확한 role/ws
    const acc = await api(memberPage, "POST", `/api/v1/invites/${code}/accept`);
    expect([200, 201]).toContain(acc.status());
    const body = (await acc.json()) as { role: string; workspaceId: string };
    expect(body.role, "수락 시 부여 role 은 초대 role(member)").toBe("member");
    expect(body.workspaceId, "수락 workspaceId 는 team ws").toBe(teamWsId);

    // 수락 후 B 가 team ws 접근 가능
    const ws = await api(memberPage, "GET", `/api/v1/workspaces/${teamWsId}`);
    expect(ws.status()).toBe(200);
  });
});
