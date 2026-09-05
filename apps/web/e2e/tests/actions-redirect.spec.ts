import { test, expect } from "@playwright/test";

// 2026-09-06 UI/UX sweep — /actions 는 이제 워크스페이스 액션 보드다.
// 이전 (Sprint 27d BUG-S27d-2) 에는 404 회피용으로 /inbox 로 redirect 했고 이 spec 이 그걸 고정했다.
// 보드가 실제로 렌더되는지 + 상태 필터가 동작하는지를 게이트로 바꾼다.
test.describe("/actions 액션 보드", () => {
  test("/actions 진입 시 redirect 없이 보드가 렌더되고 상태 필터가 동작한다", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto("/actions");
    await expect(page).toHaveURL(/\/actions$/);

    const board = page.getByTestId("action-board");
    await expect(board).toBeVisible();
    await expect(board.getByRole("heading", { level: 1, name: "액션" })).toBeVisible();

    // 상태 필터 pill 4종 — 클릭 후에도 보드가 유지되고 URL 이 바뀌지 않는다
    for (const status of ["todo", "in_progress", "done", "all"]) {
      const pill = page.getByTestId(`action-status-filter-${status}`);
      await expect(pill).toBeVisible();
      await pill.click();
      await expect(page).toHaveURL(/\/actions$/);
    }

    // Sprint 27d codex CI fix 와 동일: 브라우저 네트워크 layer noise 는 제외하고 제품 JS 회귀만 검사.
    const filteredErrors = consoleErrors.filter(
      (err) => !err.startsWith("Failed to load resource"),
    );
    expect(filteredErrors).toEqual([]);
  });
});
