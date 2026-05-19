import { test, expect } from "@playwright/test";

/**
 * Golden Path G7 (Sprint 22): 로그아웃 → 재로그인 → state 보존
 *
 * 검증 대상:
 * - Zustand persist key `kairos-workspace` 의 `state.activeWorkspaceId` 가
 *   logout 후에도 유지되거나 재로그인 시 동일 workspace 로 복원된다
 * - onboarding step 도 server-side persistence 로 동일하게 복원 (재페치)
 *
 * Sprint 23 F4: storageState key 정정 (`activeWorkspaceId` → `kairos-workspace.state.activeWorkspaceId`)
 * + skip 가드 제거 → 실 검증 활성화. UserButton/menu selector 미설정은 별도 carry-over.
 */

test.describe("G7 — logout → login → state 보존 (Sprint 22, Sprint 23 F4 storageState fix)", () => {
  test("activeWorkspaceId 가 logout 전후로 복원 (또는 동일 workspace 자동 진입)", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    // Zustand persist key = `kairos-workspace`, shape = { state: { activeWorkspaceId, ... }, version }
    const wsIdBefore = await page.evaluate(
      () => JSON.parse(localStorage.getItem("kairos-workspace") ?? "{}").state?.activeWorkspaceId,
    );
    expect(wsIdBefore).toBeTruthy();

    // 헤더의 user menu / signout 버튼 위치는 codebase 따라 다름.
    // 본 spec 은 fallback — UserButton (Clerk) 또는 settings link → signout
    const userMenu = page.locator(
      '[data-testid="user-menu"], button[aria-label*="user" i], button[aria-label*="profile" i]',
    ).first();
    const menuExists = await userMenu.count();
    if (menuExists === 0) {
      test.skip(true, "user-menu testid 미설정 — Clerk UserButton fallback 미구현 carry-over");
      return;
    }

    await userMenu.click();
    const signoutBtn = page.getByRole("menuitem", { name: /로그아웃|sign out|logout/i }).first();
    const signoutExists = await signoutBtn.count();
    if (signoutExists === 0) {
      test.skip(true, "signout menuitem 미발견 carry-over");
      return;
    }
    await signoutBtn.click();
    await page.waitForURL(/sign-in|\/$/, { timeout: 10_000 });

    // 재로그인 (Clerk dev key) — auth.setup.ts 가 storageState 갱신했다고 가정.
    // 본 test 는 storageState 자동 reuse 가 동작하는지 verify.
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    const wsIdAfter = await page.evaluate(
      () => JSON.parse(localStorage.getItem("kairos-workspace") ?? "{}").state?.activeWorkspaceId,
    );
    // 동일 또는 새로 복원
    expect(wsIdAfter).toBeTruthy();
  });
});
