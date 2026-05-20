// G2: 첫 프로젝트 생성 흐름 (Sprint 24 Wave 2 T-OBN-05 D 옵션 + T-PROJ-LIST 적용 후 정리)
// Sprint 22 OBN-02 OnboardingBanner step 갱신 assertion 은 제거됨 — banner 자체 폐기.
// Sprint 22 의 `/new` 가정도 무효 — /new 는 회의/노트/자료 3 type 선택 페이지 (프로젝트 생성 form 없음).
// Sprint 24 Wave 2 T-PROJ-LIST 가 신설한 /projects + CreateProjectDialog 흐름 사용.
import { test, expect } from "@playwright/test";

test.describe("G2 — 첫 프로젝트 생성 흐름 (Sprint 24 Wave 2)", () => {
  test("/projects 진입 → CreateProjectDialog → 프로젝트 생성", async ({ page }) => {
    // T-PROJ-LIST 신설 /projects 페이지 진입
    await page.goto("/projects");
    await page.waitForLoadState("networkidle");

    // "+ 새 프로젝트" 또는 "새 프로젝트" 버튼 click → CreateProjectDialog open
    const newProjectBtn = page
      .getByRole("button", { name: /새 프로젝트|create.*project/i })
      .first();
    await newProjectBtn.click();

    // CreateProjectDialog 의 FormLabel "프로젝트 이름" input
    const nameInput = page.getByLabel(/프로젝트.*이름/);
    await nameInput.fill(`Sprint24 G2 Test ${Date.now()}`);

    // 제출 (Form submit button)
    const submitBtn = page
      .getByRole("button", { name: /^(생성|만들기|create)$/i })
      .last();
    await submitBtn.click();

    // 생성 후 URL = /projects 또는 /projects/[id] (CreateProjectDialog 의 redirect 정책)
    await page.waitForURL(/\/projects/, { timeout: 15_000 });
    await page.waitForLoadState("networkidle");

    // 회귀 가드: OnboardingBanner 더 이상 mount 안 됨 (T-OBN-05 D 옵션)
    await expect(
      page.locator('[data-testid="onboarding-banner"]'),
    ).toHaveCount(0);
  });
});
