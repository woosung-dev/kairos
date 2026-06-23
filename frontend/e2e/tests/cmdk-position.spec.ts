import { test, expect } from "@playwright/test";

/**
 * 2026-06-24 fullsweep 회귀 가드: Cmd+K command palette 가 화면 중앙 정렬.
 *
 * 버그: OnboardingTooltip 의 PopoverTrigger(block w-full)가 palette 를 감싸
 * 부모 flex 의 justify-center 를 무효화 → palette 가 좌측(사이드바 겹침)에 렌더됐다.
 * fix: palette 에 mx-auto 추가. 본 spec 은 panel 의 bounding box 가 viewport 중앙
 * (사이드바 폭 밖)임을 검증한다.
 */

test.describe("Cmd+K palette 위치 (fullsweep 2026-06-24)", () => {
  test("⌘K palette 는 좌측 사이드바를 가리지 않고 중앙 정렬된다", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    await page.keyboard.press("Meta+k");

    const panel = page.getByTestId("cmdk-panel");
    await expect(panel).toBeVisible();

    const box = await panel.boundingBox();
    expect(box).not.toBeNull();
    if (!box) return;

    // 1) 좌측 사이드바(~208px) 를 가리지 않음 — 버그 시 x≈0.
    expect(box.x).toBeGreaterThan(240);
    // 2) 수평 중앙 정렬 — panel 중심이 viewport 중심(640) 근처(±60px).
    const panelCenter = box.x + box.width / 2;
    expect(Math.abs(panelCenter - 640)).toBeLessThan(60);
  });
});
