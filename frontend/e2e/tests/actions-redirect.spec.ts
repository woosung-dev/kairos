import { test, expect } from "@playwright/test";

test.describe("BUG-S27d-2 Actions Redirect Verification", () => {
  test("/actions should redirect to /inbox without console errors", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto("/actions");
    await page.waitForURL(/\/inbox/);

    expect(page.url()).toContain("/inbox");
    // console error가 0건이어야 함 (Base UI PopoverTrigger nativeButton 등도 같이 걸러짐)
    const filteredErrors = consoleErrors.filter(
      (err) => !err.includes("Clerk has been loaded with development keys")
    );
    expect(filteredErrors.length).toBe(0);
  });
});
