// G2: 첫 프로젝트 생성 흐름 (Sprint 24 Wave 2 T-OBN-05 D 옵션 적용 후 정리)
// Sprint 22 OBN-02 OnboardingBanner step 갱신 assertion 은 제거됨 — banner 자체 폐기.
// 핵심 흐름 (프로젝트 생성 → /dashboard or /projects 리다이렉트) 만 유지.
import { test, expect } from "@playwright/test";

test.describe("G2 — 첫 프로젝트 생성 흐름 (Sprint 24 Wave 2)", () => {
  test("프로젝트 생성 후 dashboard 또는 projects 진입", async ({ page }) => {
    // /new 진입
    await page.goto("/new");
    await page.waitForLoadState("networkidle");

    const nameInput = page
      .getByRole("textbox", { name: /프로젝트.*이름|name/i })
      .first();
    await nameInput.fill(`Sprint24 G2 Test ${Date.now()}`);

    const submitBtn = page
      .getByRole("button", { name: /생성|create|만들기/i })
      .first();
    await submitBtn.click();

    // 생성 후 /dashboard 또는 /projects/* 진입
    await page.waitForURL(/dashboard|projects/, { timeout: 15_000 });
    await page.waitForLoadState("networkidle");

    // 회귀 가드: OnboardingBanner 더 이상 mount 안 됨 (T-OBN-05 D 옵션)
    await expect(
      page.locator('[data-testid="onboarding-banner"]'),
    ).toHaveCount(0);
  });
});
