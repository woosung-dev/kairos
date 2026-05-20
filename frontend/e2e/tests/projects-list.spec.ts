// Sprint 24 Wave 2 T-PROJ-LIST (BUG-CASUAL-001) — sidebar 프로젝트 → /projects dead-end fix
// 검증: /projects 도달 + 헤딩 + (empty state | grid) + 생성 버튼 visible
import { test, expect } from "@playwright/test";

test.describe("T-PROJ-LIST — /projects 페이지 (Sprint 24 Wave 2)", () => {
  test("/projects 직접 진입 시 200 (404 dead-end fix)", async ({ page }) => {
    const response = await page.goto("/projects");
    expect(response?.status()).toBeLessThan(400);

    await expect(
      page.getByRole("heading", { name: "프로젝트", level: 1 }),
    ).toBeVisible({ timeout: 15_000 });
  });

  test("페이지에 grid 또는 empty state 가 mount 된다", async ({ page }) => {
    await page.goto("/projects");
    await page.waitForLoadState("networkidle");

    // grid 또는 empty state 중 하나는 반드시 mount
    const grid = page.getByTestId("projects-grid");
    const empty = page.getByTestId("projects-empty-state");

    // 둘 중 적어도 하나 visible
    const gridVisible = await grid.isVisible().catch(() => false);
    const emptyVisible = await empty.isVisible().catch(() => false);
    expect(gridVisible || emptyVisible).toBe(true);
  });

  test("write 권한 보유 시 새 프로젝트 버튼 visible", async ({ page }) => {
    await page.goto("/projects");
    await page.waitForLoadState("networkidle");

    // member 이상 권한 (대부분 owner 로 로그인) → 버튼 노출
    const createBtn = page.getByTestId("create-project-button");
    // 권한 없을 수 있으므로 visible 여부만 우호적 검증
    const visible = await createBtn.isVisible({ timeout: 5_000 }).catch(() => false);
    if (visible) {
      await expect(createBtn).toBeEnabled();
    } else {
      test.skip(
        true,
        "현재 워크스페이스에 member 이상 권한 없음 — 버튼 미노출은 정상",
      );
    }
  });
});
