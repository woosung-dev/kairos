// T13: 워크스페이스 전환 UI (BUG-WS-SWITCH 회귀 가드) — switcher 클릭 → 2번째 ws 선택 → active ws 갱신, console.error 0
import { test, expect } from "../../fixtures/team";
import { collectConsoleErrors } from "../../team-helpers";

interface WsRow {
  id: string;
}

test.describe("T13 워크스페이스 전환 UI", () => {
  test("switcher 클릭 → 다른 ws 선택 → activeWorkspaceId 즉시 갱신", async ({
    memberPage,
    api,
    teamWsId,
  }) => {
    const errors = collectConsoleErrors(memberPage);
    await memberPage.goto("/dashboard");

    // B 는 personal + team ≥2 ws. active 는 team(시드 주입). 다른 ws(personal)로 전환.
    const wsList = (await (await api(memberPage, "GET", "/api/v1/workspaces")).json()) as WsRow[];
    expect(wsList.length, "B 는 personal+team 2개 이상 ws").toBeGreaterThanOrEqual(2);
    const other = wsList.find((w) => w.id !== teamWsId);
    expect(other, "전환 대상(다른 ws) 존재").toBeDefined();

    await memberPage.getByTestId("workspace-switcher").click();
    await memberPage.getByTestId(`workspace-switcher-item-${other!.id}`).click();

    // localStorage.activeWorkspaceId 가 선택한 ws 로 갱신 (mutation: onClick no-op → 불변)
    await expect
      .poll(async () =>
        memberPage.evaluate(() => {
          const raw = localStorage.getItem("kairos-workspace");
          return raw ? (JSON.parse(raw) as { state: { activeWorkspaceId: string } }).state.activeWorkspaceId : null;
        }),
      )
      .toBe(other!.id);

    expect(errors(), "전환 중 console.error 0").toEqual([]);
  });
});
