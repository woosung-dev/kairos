// Sprint 24 Wave 2 T-NOTE-DETAIL (BUG-POW-003) — /notes/[id] 페이지 신설
// 검증: /notes 에서 노트 선택 → /notes/[id] 도달 + Tiptap editor + Export/Promote 버튼 visible
import { test, expect } from "@playwright/test";

test.describe("T-NOTE-DETAIL — /notes/[id] 페이지 (Sprint 24 Wave 2)", () => {
  test("/notes 진입 후 첫 노트 선택 → /notes/[id] 도달", async ({ page }) => {
    await page.goto("/notes");
    await page.waitForLoadState("networkidle");

    // 노트 카드/링크 패턴 — quick-memo 에서는 list 가 직접 노출
    const firstNoteLink = page
      .locator('a[href^="/notes/"]:not([href$="/new"])')
      .first();
    const noteExists = await firstNoteLink.count();

    if (noteExists === 0) {
      // 직접 /notes/[id] 도달은 dummy id 로 검증 — 404 가 아닌 page 자체는 render
      // (해당 노트 없으면 "노트를 불러오지 못했습니다" 라도 page 자체는 200)
      const dummyId = "00000000-0000-0000-0000-000000000000";
      const response = await page.goto(`/notes/${dummyId}`);
      expect(response?.status()).toBeLessThan(500);
      // 페이지 자체는 render — 404 dead-end 가 아님이 핵심
      await expect(page.locator("main, [role=main]")).toBeVisible();
      test.skip(
        true,
        "노트 0건 — empty seed 환경에서는 detail 검증 skip (page 자체 200 만 확인)",
      );
      return;
    }

    await firstNoteLink.click();
    await page.waitForURL(/\/notes\/[0-9a-f-]+/, { timeout: 10_000 });
    await page.waitForLoadState("networkidle");

    // Tiptap editor mount
    await expect(page.getByTestId("note-detail-editor")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("Note detail 진입 시 Export + Promote 버튼 둘 다 visible", async ({
    page,
  }) => {
    await page.goto("/notes");
    await page.waitForLoadState("networkidle");

    const firstNoteLink = page
      .locator('a[href^="/notes/"]:not([href$="/new"])')
      .first();
    const noteExists = await firstNoteLink.count();
    if (noteExists === 0) {
      test.skip(true, "노트 0건 — fixture seeding 필요 carry-over");
      return;
    }

    await firstNoteLink.click();
    await page.waitForURL(/\/notes\/[0-9a-f-]+/, { timeout: 10_000 });
    await page.waitForLoadState("networkidle");

    // Export button (NoteExportButton) — Sprint 22 BUG-C04 패턴 정렬
    await expect(
      page.getByRole("button", { name: /내보내기/ }).first(),
    ).toBeVisible({ timeout: 10_000 });

    // Promote button (BL-064 carry-over reuse)
    await expect(
      page.getByTestId("note-detail-promote-button"),
    ).toBeVisible({ timeout: 10_000 });

    // 뒤로 가기 link
    await expect(
      page.getByTestId("note-detail-back-button"),
    ).toBeVisible();
  });
});
