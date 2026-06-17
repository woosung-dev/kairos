// T18: 초대 유효성 — 비활성화(deactivate)된 초대는 수락 불가 (_validate_invite is_active 가드)
import { test, expect } from "../../fixtures/team";

test.describe.serial("T18 비활성 초대 수락 차단", () => {
  test.afterEach(async ({ ensureMemberBaseline }) => {
    await ensureMemberBaseline();
  });

  test("제거된 B 가 비활성 초대 수락 시도 → 4xx", async ({
    ownerPage,
    memberPage,
    api,
    teamWsId,
    getMemberId,
  }) => {
    // B 제거 (수락이 is_active 가드 경로를 타게 — 이미 멤버면 409 로 단락).
    // 제거 성공(204)을 단언해야 이후 4xx 가 already-member(409) 가 아닌 inactive 가드(410)임이 보장됨.
    const id = await getMemberId();
    expect(id).not.toBeNull();
    const del = await api(ownerPage, "DELETE", `/api/v1/workspaces/${teamWsId}/members/${id}`);
    expect(del.status(), "B 제거 성공 (이후 409 already-member 차단)").toBe(204);

    // 초대 발급 후 즉시 비활성화
    const inv = await api(ownerPage, "POST", `/api/v1/workspaces/${teamWsId}/invites`, {
      role: "member",
      maxUses: null,
      expiresInDays: 30,
    });
    const body = (await inv.json()) as { id: string; code: string };
    const deact = await api(ownerPage, "DELETE", `/api/v1/workspaces/${teamWsId}/invites/${body.id}`);
    expect([200, 204], "초대 비활성화 성공").toContain(deact.status());

    // B(비멤버) 가 비활성 초대 수락 → 410(InviteExpiredError). 409(already-member) 아님.
    // mutation: is_active 가드 제거 시 비멤버라 200/201 → RED.
    const acc = await api(memberPage, "POST", `/api/v1/invites/${body.code}/accept`);
    expect(acc.status(), "비활성 초대 수락 → 410 (inactive 가드)").toBe(410);
  });
});
