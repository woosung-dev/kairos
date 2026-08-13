// T16: settings Audit 탭 RBAC 가시성 — owner 에게 보임, member 에게 부재(toHaveCount 0), console.error 0
import { test, expect } from "../../fixtures/team";
import { collectConsoleErrors } from "../../team-helpers";

test.describe.serial("T16 settings Audit 탭 RBAC 가시성", () => {
  test.afterEach(async ({ ensureMemberBaseline }) => {
    await ensureMemberBaseline();
  });

  test("owner 에게 Audit 탭 trigger 노출", async ({ ownerPage }) => {
    const errors = collectConsoleErrors(ownerPage);
    await ownerPage.goto("/settings?tab=members");
    await expect(
      ownerPage.getByTestId("audit-tab-trigger"),
      "owner 는 Audit 탭 보임",
    ).toBeVisible();
    expect(errors(), "console.error 0").toEqual([]);
  });

  test("member 에게 Audit 탭 trigger 부재 (toHaveCount 0)", async ({ memberPage, ensureMemberBaseline }) => {
    await ensureMemberBaseline();
    const errors = collectConsoleErrors(memberPage);
    await memberPage.goto("/settings?tab=members");
    await memberPage.waitForLoadState("networkidle");
    // 양성 로커: settings 탭이 실제 렌더됐음을 먼저 확인 → audit 부재가 vacuous(미렌더) 가 아님을 보장.
    await expect(
      memberPage.getByRole("tab").first(),
      "settings 탭 렌더됨 (페이지 로드 보장)",
    ).toBeVisible();
    await expect(
      memberPage.getByTestId("audit-tab-trigger"),
      "member 는 Audit 탭 미노출 (mutation: role-gate 제거 시 노출 → RED)",
    ).toHaveCount(0);
    expect(errors(), "console.error 0").toEqual([]);
  });
});
