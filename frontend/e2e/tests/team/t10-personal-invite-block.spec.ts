// T10: I-19 personal workspace 초대 금지 + QA-0617-E 조사 플레이스홀더(을(를)) 미노출
import { test, expect } from "../../fixtures/team";

test.describe("T10 personal ws 초대 금지 (I-19)", () => {
  test("owner 가 personal ws 초대 발급 → 403 + 메시지에 리터럴 을(를) 없음", async ({
    ownerPage,
    api,
    ownerPersonalWsId,
  }) => {
    const res = await api(ownerPage, "POST", `/api/v1/workspaces/${ownerPersonalWsId}/invites`, {
      role: "member",
    });
    expect(res.status(), "personal ws 초대 → 403 (PersonalWorkspaceProtected)").toBe(403);

    const body = await res.text();
    expect(body.includes("을(를)"), "QA-0617-E: 조사 플레이스홀더 리터럴 노출 없음").toBe(false);
    // 정상 조사 적용 확인 ("초대" 받침 없음 → "초대를")
    expect(body.includes("초대를"), "조사 정상 적용(초대를)").toBe(true);
  });
});
