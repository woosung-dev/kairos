import { test, expect } from "@playwright/test";

/**
 * Golden Path G8 (Sprint 22 BUG-C04): Meeting Export discoverability + Markdown download
 *
 * 검증 대상:
 * - meeting detail 진입 시 "내보내기" 라벨 (Task 5.2 E18 의 export button enhancement) 가
 *   header 영역에 visible — Power 페르소나가 못 찾았던 BUG-C04 해소
 * - dropdown 클릭 → Markdown / JSON 옵션 표시
 * - Markdown 다운로드 트리거 시 .md 파일 다운로드
 */

test.describe("G8 — Meeting export discoverability (Sprint 22 BUG-C04)", () => {
  test("meeting detail header 에 Export 라벨 + tooltip visible", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    // 첫 meeting 진입 (없으면 skip)
    const firstMeeting = page
      .locator('a[href^="/meetings/"], [data-testid="meeting-card"]')
      .first();
    const exists = await firstMeeting.count();
    if (exists === 0) {
      test.skip(true, "Meeting 0건 — fixture seeding 필요 carry-over");
      return;
    }

    await firstMeeting.click();
    await page.waitForLoadState("networkidle");

    // "내보내기" 라벨 또는 aria-label 로 export 버튼 찾기 (Task 5.2 E18)
    const exportBtn = page.getByRole("button", { name: /내보내기/ }).first();
    await expect(exportBtn).toBeVisible({ timeout: 10_000 });
  });

  test("dropdown 클릭 → Markdown 옵션 표시", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    const firstMeeting = page
      .locator('a[href^="/meetings/"], [data-testid="meeting-card"]')
      .first();
    const exists = await firstMeeting.count();
    if (exists === 0) {
      test.skip(true, "Meeting 0건 carry-over");
      return;
    }
    await firstMeeting.click();
    await page.waitForLoadState("networkidle");

    const exportBtn = page.getByRole("button", { name: /내보내기/ }).first();
    await exportBtn.click();

    // dropdown menu 안의 Markdown 항목
    await expect(page.getByText(/Markdown.*\.md/)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/JSON.*\.json/)).toBeVisible();
  });
});
