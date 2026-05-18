import { test, expect } from "@playwright/test";

/**
 * Golden Path G2 (Sprint 22 OBN-02): 첫 프로젝트 생성 → onboarding step=2 갱신
 *
 * 검증 대상:
 * - 인증된 사용자가 /new 페이지에서 새 프로젝트 생성 후
 * - OnboardingBanner 의 progress indicator 가 `Step 2/4` 이상으로 갱신된다
 *   (이미 step >= 2 인 기존 user 도 idempotent — banner hidden 또는 동일)
 *
 * Mutation invalidate 검증: E16 의 useCreateProject().onSuccess 에서
 * queryClient.invalidateQueries({ queryKey: ['onboarding'] }) → useOnboarding refetch
 */

test.describe("G2 — 첫 프로젝트 생성 → Step 2/4 갱신 (Sprint 22 OBN-02)", () => {
  test("프로젝트 생성 후 onboarding banner 가 step 갱신 (또는 isCompleted hide)", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    // banner data-testid (Task 4-6 E15 에서 셋업) — visible 또는 hidden (step=4 도달 시)
    const banner = page.getByTestId("onboarding-banner");
    const bannerExists = await banner.count();

    if (bannerExists === 0) {
      // 이미 step=4 도달한 기존 user — banner 자체가 렌더 안 됨. test skip.
      test.skip(true, "이미 isCompleted 인 user — banner 미렌더");
    }

    // 프로젝트 생성 시도
    await page.goto("/new");
    await page.waitForLoadState("networkidle");

    const nameInput = page.getByRole("textbox", { name: /프로젝트.*이름|name/i }).first();
    await nameInput.fill(`Sprint22 G2 Test ${Date.now()}`);

    const submitBtn = page.getByRole("button", { name: /생성|create|만들기/i }).first();
    await submitBtn.click();

    // 생성 후 /dashboard 또는 /projects/* 진입
    await page.waitForURL(/dashboard|projects/, { timeout: 15_000 });
    await page.waitForLoadState("networkidle");

    // banner 가 다시 보이면 step >= 2 텍스트 확인. 안 보이면 isCompleted (step=4).
    const bannerAfter = page.getByTestId("onboarding-banner");
    const stillVisible = await bannerAfter.count();
    if (stillVisible > 0) {
      const stepText = await bannerAfter.textContent({ timeout: 5_000 });
      const match = stepText?.match(/(\d)\s*\/\s*4/);
      const step = match ? parseInt(match[1], 10) : 0;
      expect(step).toBeGreaterThanOrEqual(2);
    }
    // banner hidden = step=4 도달 (E16 invalidate + isCompleted) — PASS
  });
});
