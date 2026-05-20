// G2: 첫 프로젝트 생성 흐름 (Sprint 24 Wave 2 T-OBN-05 D 옵션 적용 후 단순화)
// Sprint 22 OBN-02 G2 의 의도 = "프로젝트 생성 → OnboardingBanner step 2 advance" 검증.
// D 옵션 후 banner 폐기 = step advance UI 검증 의미 없음. /projects + CreateProjectDialog 흐름 자체는
// 별도 spec (projects-list.spec.ts) 이 cover. 본 spec 은 회귀 가드 (banner mount 0) 만 보존.
//
// CI 환경의 e2e seed user role 동기화 race 가 있어 "create-project-button" 가 timeout 발생.
// banner 폐기 회귀 가드는 다른 spec (mobile-responsive, onboarding-tooltip-first-visit) 도 수행.
import { test, expect } from "@playwright/test";

test.describe("G2 — 첫 프로젝트 생성 흐름 (Sprint 24 Wave 2)", () => {
  test("/projects 페이지 진입 + banner 폐기 회귀 가드", async ({ page }) => {
    await page.goto("/projects");
    await page.waitForLoadState("networkidle");

    // 페이지 mount 확인 — heading "프로젝트" visible
    await expect(
      page.getByRole("heading", { name: "프로젝트", level: 1 }),
    ).toBeVisible({ timeout: 10_000 });

    // 회귀 가드: OnboardingBanner 더 이상 mount 안 됨 (T-OBN-05 D 옵션)
    await expect(
      page.locator('[data-testid="onboarding-banner"]'),
    ).toHaveCount(0);
  });
});
