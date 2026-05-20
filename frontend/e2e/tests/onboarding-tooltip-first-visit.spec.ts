// T-OBN-05 D 옵션 (Sprint 24 Wave 2): 첫 방문 inline tooltip 발화 + dismiss + 재방문 + banner 폐기 회귀 가드
// 결정 anchor: docs/superpowers/specs/2026-05-20-sprint24-wave2-trusty-heron-design.md §T-OBN-05
import { test, expect } from "@playwright/test";

test.describe("Onboarding Tooltip (T-OBN-05 D 옵션, Sprint 24 Wave 2)", () => {
  test.beforeEach(async ({ page }) => {
    // 신규 사용자 시뮬레이션: localStorage 초기화
    await page.goto("/dashboard");
    await page.evaluate(() => window.localStorage.clear());
  });

  test("dashboard 첫 방문 시 ⌘K tooltip 발화", async ({ page }) => {
    await page.reload();
    await expect(
      page.getByTestId("onboarding-tooltip-dashboard"),
    ).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/AI 검색은 ⌘K/)).toBeVisible();
  });

  test("dashboard 재방문 시 tooltip 미발화", async ({ page }) => {
    // 발화 마크 직접 set
    await page.evaluate(() =>
      window.localStorage.setItem(
        "kairos.onboarding.tooltip_shown.dashboard",
        "1",
      ),
    );
    await page.reload();
    // tooltip popover 가 mount 되지 않음
    const tooltip = page.getByTestId("onboarding-tooltip-dashboard");
    await expect(tooltip).toHaveCount(0);
  });

  test("dismiss(X) 클릭 시 tooltip 닫힘 + 재방문 미발화", async ({ page }) => {
    await page.reload();
    const tooltip = page.getByTestId("onboarding-tooltip-dashboard");
    await expect(tooltip).toBeVisible({ timeout: 5_000 });

    const dismissBtn = tooltip.getByRole("button", { name: "닫기" });
    await dismissBtn.click();
    await expect(tooltip).toHaveCount(0);

    // localStorage 에 마크 기록 검증
    const mark = await page.evaluate(() =>
      window.localStorage.getItem(
        "kairos.onboarding.tooltip_shown.dashboard",
      ),
    );
    expect(mark).toBe("1");

    // 새로고침 후에도 재발화 X
    await page.reload();
    await expect(tooltip).toHaveCount(0);
  });

  test("⌘K 첫 열기 시 search tooltip 발화", async ({ page }) => {
    await page.reload();
    // dashboard tooltip 발화 후 dismiss (잡음 제거)
    const dashTip = page.getByTestId("onboarding-tooltip-dashboard");
    const dashVisible = await dashTip
      .isVisible({ timeout: 5_000 })
      .catch(() => false);
    if (dashVisible) {
      await dashTip.getByRole("button", { name: "닫기" }).click();
    }

    await page.keyboard.press("Meta+K");
    await expect(
      page.getByTestId("onboarding-tooltip-search"),
    ).toBeVisible({ timeout: 5_000 });
    await expect(
      page.getByText(/검색 범위는 현재 워크스페이스 전체/),
    ).toBeVisible();
  });

  test("회귀 가드 — OnboardingBanner data-testid 더 이상 mount 안 됨", async ({
    page,
  }) => {
    await page.reload();
    await expect(
      page.locator('[data-testid="onboarding-banner"]'),
    ).toHaveCount(0);
  });
});
