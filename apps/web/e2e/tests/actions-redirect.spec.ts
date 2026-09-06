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

  // PR #189 후속 C — 팔레트에 표시된 "G A" 시퀀스가 실제로 동작하는지 (물리 키 e.code 매칭).
  test("전역 단축키 g → a 로 /actions 에 도달한다", async ({ page }) => {
    // 첫 방문 온보딩 툴팁(role=dialog) 은 열린 동안 단축키를 막는 게 의도라, 전제조건으로 "이미 본 상태" 를 심는다
    // (onboarding-tooltip-first-visit.spec 과 같은 키). 닫힘 애니메이션 타이밍에 기대는 대신 조건을 명시한다.
    await page.addInitScript(() => {
      window.localStorage.setItem("kairos.onboarding.tooltip_shown.dashboard", "1");
    });
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    await page.keyboard.press("g");
    await page.keyboard.press("a");
    await expect(page).toHaveURL(/\/actions$/);
    await expect(page.getByTestId("action-board")).toBeVisible();
  });
});
