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
    // dashboard tooltip 이 발화하지 않도록 미리 mark 처리 (잡음 제거 + dismiss race 회피)
    await page.evaluate(() =>
      window.localStorage.setItem(
        "kairos.onboarding.tooltip_shown.dashboard",
        "1",
      ),
    );
    await page.reload();

    // CI fix v3: page snapshot 분석 결과 — 헤더 "팀 지식 검색... ⌘K" 는 toggleRagOverlay (RAG 패널) 호출.
    // 진짜 cmd-k trigger = dashboard 본문의 "검색하거나 질문 입력... ⌘K" button (toggleCmdK).
    // 정확한 selector = OnboardingTooltip(page="dashboard") 안의 button (dashboard tooltip 이 wrap).
    // dashboard tooltip 이 mark 처리되어 mount 안 되므로 우리 click 은 직접 button 도달.
    const cmdKTrigger = page.getByRole("button", {
      name: /검색하거나 질문 입력/,
    });
    await cmdKTrigger.click();

    await expect(
      page.getByTestId("onboarding-tooltip-search"),
    ).toBeVisible({ timeout: 10_000 });
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
