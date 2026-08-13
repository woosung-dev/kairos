// T17: owner 보호 — owner 멤버는 강등(PATCH)·제거(DELETE) 불가 (CannotModifyOwnerError 403)
// 주의: baseline 에선 owner 강등이 403 으로 차단돼 시드 무손상. 단 owner-guard 가 깨진(=mutation/회귀)
// 경우엔 owner 가 실제 강등돼 시드 오염 → owner 없는 ws 라 API 로 self-restore 불가.
// 안전망: 다음 team-setup 의 `members==2 + owner role` 가드가 오염을 loud 하게 포착(silent cascade 차단).
import { test, expect } from "../../fixtures/team";

test.describe("T17 owner 보호", () => {
  test("owner role 강등/제거 차단", async ({ ownerPage, api, teamWsId, getOwnerMemberId }) => {
    const ownerId = await getOwnerMemberId();

    const patch = await api(ownerPage, "PATCH", `/api/v1/workspaces/${teamWsId}/members/${ownerId}`, {
      role: "member",
    });
    expect(patch.status(), "owner 강등 차단 403 (mutation 시 200)").toBe(403);

    const del = await api(ownerPage, "DELETE", `/api/v1/workspaces/${teamWsId}/members/${ownerId}`);
    expect(del.status(), "owner 제거 차단 403 (mutation 시 204)").toBe(403);
  });
});
