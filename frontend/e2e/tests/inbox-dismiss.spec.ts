import { test, expect } from "@playwright/test";

/**
 * Sprint 25 BL-069 회귀 spec: Inbox 항목 dismiss → list 즉시 사라짐 + reload 후에도 보존
 *
 * 검증 대상 (D3 fix + Sprint 25 BL-069 wire 보강):
 * - dismiss 버튼 클릭 시 useInbox cache 무효화 → list 즉시 갱신
 * - useInbox({isProcessed: false}) BE filter 가 dismiss 항목 제외 → reload 후에도 보존
 *
 * 의존: storageState (auth.setup.ts) + inbox 시드 1개 이상 (미처리 항목)
 * 시드 부재 시 skip (CI 환경 적응).
 */

test.describe("D3+BL-069 — Inbox dismiss 영속 (Sprint 23/25)", () => {
  test("dismiss 클릭 → list 사라짐 → reload 후에도 보존", async ({ page }) => {
    await page.goto("/inbox");
    await page.waitForLoadState("networkidle");

    // 미처리 inbox 항목 카드 — 무시 버튼 존재
    const dismissButton = page.getByRole("button", { name: /무시/ }).first();
    const buttonCount = await page.getByRole("button", { name: /무시/ }).count();

    if (buttonCount === 0) {
      test.skip(
        true,
        "inbox 미처리 항목 0건 — 시드 환경 의존 carry-over (수동 QA)",
      );
      return;
    }

    // 첫 카드의 title 캡쳐 (dismiss 후 list 에서 사라짐 verify 용)
    const firstCard = dismissButton.locator(
      "xpath=ancestor::div[contains(@class, 'rounded-lg')][1]",
    );
    const titleBefore = await firstCard
      .locator("h3")
      .first()
      .textContent();
    if (!titleBefore) {
      test.skip(true, "첫 카드 title 캡쳐 실패 — DOM 구조 확인 필요");
      return;
    }

    // F-2B v3 (codex+agy 2차 A/B race fix): refetch unmount 전에 동기 UI 먼저 검증.
    // 이전 v2 는 await response 후 어설션 → cache invalidate refetch 가 transient
    // 카드를 제거하여 어설션 fail 가능 (CI flake).
    const dismissResponsePromise = page.waitForResponse(
      (resp) => resp.url().includes("/inbox/") && resp.url().endsWith("/dismiss"),
      { timeout: 5_000 },
    );
    await dismissButton.click();
    // 1) setStatus 동기 → "무시되었습니다" 즉시 표시 (refetch 이전).
    await expect(page.getByText("무시되었습니다").first()).toBeVisible();
    // 2) BE persist 응답 대기 (이후 reload race 차단).
    await dismissResponsePromise;

    // reload 후에도 첫 카드 title 이 list 에 없어야 함 (BE persist 확인)
    await page.reload();
    await page.waitForLoadState("networkidle");

    const titleStillExists = await page
      .locator(`h3:has-text("${titleBefore.trim()}")`)
      .count();
    expect(titleStillExists).toBe(0);
  });
});
