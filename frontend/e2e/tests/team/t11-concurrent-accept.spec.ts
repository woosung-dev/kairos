// T11: 동시 invite-accept (QA-0617-D) — 같은 code 2건 동시 수락 → {200/201, 409}, 절대 500 아님, 최종 membership 1
import { test, expect } from "../../fixtures/team";

interface MemberRow {
  userId: string;
}

test.describe.serial("T11 동시 invite-accept (QA-0617-D)", () => {
  test.afterEach(async ({ ensureMemberBaseline }) => {
    await ensureMemberBaseline();
  });

  test("동시 2 accept → {200/201,409}, no 500, membership=1", async ({
    ownerPage,
    memberPage,
    api,
    teamWsId,
    meta,
    getMemberId,
  }) => {
    // B 제거 (수락이 실 add_member ON CONFLICT 경로를 타게)
    const id = await getMemberId();
    expect(id).not.toBeNull();
    const del = await api(ownerPage, "DELETE", `/api/v1/workspaces/${teamWsId}/members/${id}`);
    expect(del.status()).toBe(204);

    const inv = await api(ownerPage, "POST", `/api/v1/workspaces/${teamWsId}/invites`, {
      role: "member",
      maxUses: null,
      expiresInDays: 30,
    });
    const code = ((await inv.json()) as { code: string }).code;

    // 동시 2건 수락
    const [r1, r2] = await Promise.all([
      api(memberPage, "POST", `/api/v1/invites/${code}/accept`),
      api(memberPage, "POST", `/api/v1/invites/${code}/accept`),
    ]);
    const statuses = [r1.status(), r2.status()];
    expect(statuses, "절대 500 없음 (ON CONFLICT race-safe)").not.toContain(500);
    for (const s of statuses) {
      expect([200, 201, 409], `허용 status {200,201,409}: ${s}`).toContain(s);
    }

    // 최종 membership = B 1행 (중복 가입 없음)
    const members = (await (
      await api(ownerPage, "GET", `/api/v1/workspaces/${teamWsId}/members`)
    ).json()) as MemberRow[];
    const bRows = members.filter((m) => m.userId === meta.memberUserId);
    expect(bRows.length, "B membership 정확히 1").toBe(1);
  });
});
