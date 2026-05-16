// 모바일 반응형 — Mobile (< 768px) viewport 에서 핵심 진입점 렌더 가드
import { test, expect } from "@playwright/test";

/**
 * Sprint 17 QA 는 desktop 1280px 만 검증. mobile breakpoint (< 768px)
 * 에서 데드 element / 오버플로우 / overlap 회귀 가드.
 *
 * 본 spec 은 mobile viewport 로만 전환 후 핵심 라우트 4개 (dashboard,
 * inbox, notes, settings) 진입 + 헤딩 가시성 확인.
 */

const MOBILE = { width: 375, height: 812 };

test.describe("Mobile 반응형 (375x812)", () => {
  test.use({ viewport: MOBILE });

  test("/dashboard 진입 + heading 렌더", async ({ page }) => {
    test.setTimeout(20_000);
    await page.goto("/dashboard");
    await expect(
      page.getByRole("heading", { name: "오늘의 Kairos" }),
    ).toBeVisible({ timeout: 15_000 });
  });

  test("/inbox 진입 + heading 렌더", async ({ page }) => {
    test.setTimeout(20_000);
    await page.goto("/inbox");
    await expect(page.getByRole("heading", { name: "Inbox" })).toBeVisible({
      timeout: 15_000,
    });
  });

  test("/notes 진입 + heading 렌더", async ({ page }) => {
    test.setTimeout(20_000);
    await page.goto("/notes");
    await expect(
      page.getByRole("heading", { name: "빠른 메모" }),
    ).toBeVisible({ timeout: 15_000 });
  });

  test("/settings 진입 + tablist 렌더", async ({ page }) => {
    test.setTimeout(20_000);
    await page.goto("/settings");
    await expect(page.getByRole("tab", { name: "멤버" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("tab", { name: "초대" })).toBeVisible();
  });

  test("Cmd+K 검색 버튼 노출 (mobile)", async ({ page }) => {
    test.setTimeout(20_000);
    await page.goto("/dashboard");
    // 모바일에서도 ⌘K 검색 버튼 또는 동등한 진입 노출.
    const cmdK = page.getByRole("button", { name: /지식 검색|⌘K/ });
    await expect(cmdK).toBeVisible({ timeout: 15_000 });
  });
});
