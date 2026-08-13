// T23: 접근 불가 wid 로 /projects 직접 진입 → 자동 복구 회귀 가드
// (BL-FE-WS-HEAL-SCOPE-1 자동 교정 + BL-FE-WID-GUARD-PREFETCH-1 잔여 403 감소)
//
// 시나리오: member 의 localStorage 에 owner 개인 ws(멤버가 아닌 ws) id 를 주입하고 /projects 로 직접 진입.
// 기대: self-heal 이 접근 가능한 ws 로 교정하고 화면이 정상 렌더된다. 교정이 끝난 뒤에는 403 이 더 나오지 않는다.
import { test, expect } from "../../fixtures/team";
import { collectConsoleErrors, getMe, injectActiveWorkspace } from "../../team-helpers";

interface WsRow {
  id: string;
}

const readActiveWid = (page: import("@playwright/test").Page) =>
  page.evaluate(() => {
    const raw = localStorage.getItem("kairos-workspace");
    return raw
      ? (JSON.parse(raw) as { state?: { activeWorkspaceId?: string } }).state?.activeWorkspaceId ?? null
      : null;
  });

test.describe("T23 접근 불가 wid 자동 복구", () => {
  test("접근 불가 wid 주입 → /projects 직접 진입 → 접근 가능한 ws 로 교정 + 정상 렌더", async ({
    memberPage,
    api,
    ownerPersonalWsId,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const memberMe = await getMe(memberPage);

    // member 가 실제로 접근 가능한 ws 목록 — 교정 목적지의 정답 집합
    const accessible = (await (await api(memberPage, "GET", "/api/v1/workspaces")).json()) as WsRow[];
    const accessibleIds = accessible.map((w) => w.id);
    expect(accessibleIds, "member 는 접근 가능한 ws 를 최소 1개 갖는다").not.toHaveLength(0);
    expect(
      accessibleIds,
      "owner 개인 ws 는 member 에게 접근 불가여야 이 시나리오가 성립한다",
    ).not.toContain(ownerPersonalWsId);

    const errors = collectConsoleErrors(memberPage);

    await memberPage.goto("/");
    await injectActiveWorkspace(memberPage, ownerPersonalWsId, memberMe.clerkId ?? "");
    await memberPage.goto("/projects");

    // 1) 자동 교정 — activeWorkspaceId 가 접근 가능한 ws 로 바뀐다
    await expect
      .poll(() => readActiveWid(memberPage), {
        message: "self-heal 이 접근 불가 wid 를 접근 가능한 ws 로 교정해야 한다",
      })
      .not.toBe(ownerPersonalWsId);
    const healed = await readActiveWid(memberPage);
    expect(accessibleIds, "교정 목적지는 member 가 접근 가능한 ws 여야 한다").toContain(healed);

    // 2) 화면이 고착되지 않고 정상 렌더 — 목록 또는 빈 상태 중 하나가 반드시 보인다
    await expect(
      memberPage.getByTestId("projects-grid").or(memberPage.getByTestId("projects-empty-state")),
      "교정 후 /projects 가 목록 또는 빈 상태를 렌더해야 한다 (고착 금지)",
    ).toBeVisible();

    // 3) 교정 완료 후에는 403 이 더 나오지 않는다.
    //    (교정 *전* 첫 렌더의 잔여 403 은 BL-FE-WID-GUARD-PREFETCH-1 의 감소 대상이지 0 이 목표가 아니다.
    //     여기서는 고정 개수를 단언하지 않고 "교정 이후 추가 발생 0" 만 본다.)
    await memberPage.waitForLoadState("networkidle");
    const afterHeal = errors().length;
    await memberPage.waitForTimeout(1500);
    expect(
      errors().length,
      "교정이 끝난 뒤에는 403 이 추가로 발사되지 않아야 한다 (재시도·재구독 루프 부재)",
    ).toBe(afterHeal);

    // 4) uncaught 예외와 서버 오류는 어느 시점에도 허용하지 않는다
    const fatal = errors().filter((e) => e.startsWith("pageerror:") || /HTTP 5\d\d/.test(e));
    expect(fatal, "pageerror 와 5xx 는 0건이어야 한다").toEqual([]);
  });
});
