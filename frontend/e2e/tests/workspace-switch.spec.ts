import { test, expect } from "@playwright/test";

/**
 * Sprint 23 D1 회귀 spec: 워크스페이스 스위처 클릭 → 컨텍스트 즉시 전환
 *
 * 검증 대상 (D1 fix):
 * - WorkspaceSwitcher dropdown 클릭 시 localStorage 의
 *   `kairos-workspace.state.activeWorkspaceId` 가 새 wid 로 갱신
 * - queryClient.invalidateQueries 가 wid-scoped 쿼리만 invalidate
 *   (workspaces.list 보존 → ws list dropdown 계속 표시)
 * - router.refresh() 제거 → invalidateQueries 만으로 사이드바/Today/Inbox 새 데이터
 *
 * 의존: storageState (auth.setup.ts) + 2개 이상 workspace 시드
 * 시드 부재 시 skip (CI 환경 적응).
 */

test.describe("D1 — 워크스페이스 스위처 즉시 전환 (Sprint 23)", () => {
  test("워크스페이스 스위처 클릭 → localStorage activeWorkspaceId 즉시 갱신", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    // 현재 wid 확인 (Zustand persist key `kairos-workspace`)
    const wsIdBefore = await page.evaluate(
      () =>
        JSON.parse(localStorage.getItem("kairos-workspace") ?? "{}").state
          ?.activeWorkspaceId,
    );
    if (!wsIdBefore) {
      test.skip(true, "storageState 미주입 — auth setup 의존 carry-over");
      return;
    }

    // WorkspaceSwitcher trigger (aria-label 강제)
    const trigger = page.getByRole("button", { name: /워크스페이스 전환/ });
    await expect(trigger).toBeVisible({ timeout: 10_000 });
    await trigger.click();

    // dropdown 내 다른 workspace option 검색
    const dropdownItems = page.getByRole("menuitem");
    const itemCount = await dropdownItems.count();
    if (itemCount < 2) {
      test.skip(
        true,
        "2개 이상의 워크스페이스 시드 없음 — local/CI dev 환경 가드",
      );
      return;
    }

    // 현재 active 가 아닌 option 클릭
    let clicked = false;
    for (let i = 0; i < itemCount; i++) {
      const item = dropdownItems.nth(i);
      const check = item.locator('svg[class*="text-accent"]');
      const isActive = (await check.count()) > 0;
      if (!isActive) {
        const text = await item.textContent();
        if (!text?.includes("새 워크스페이스")) {
          await item.click();
          clicked = true;
          break;
        }
      }
    }
    if (!clicked) {
      test.skip(true, "non-active workspace option 미발견 carry-over");
      return;
    }

    // localStorage activeWorkspaceId 가 새 wid 로 갱신
    await page.waitForFunction(
      (oldWid) => {
        const state = JSON.parse(
          localStorage.getItem("kairos-workspace") ?? "{}",
        ).state;
        return (
          state?.activeWorkspaceId && state.activeWorkspaceId !== oldWid
        );
      },
      wsIdBefore,
      { timeout: 5_000 },
    );

    const wsIdAfter = await page.evaluate(
      () =>
        JSON.parse(localStorage.getItem("kairos-workspace") ?? "{}").state
          ?.activeWorkspaceId,
    );
    expect(wsIdAfter).toBeTruthy();
    expect(wsIdAfter).not.toBe(wsIdBefore);
  });
});
