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

  // Sprint 22 OBN-04: OnboardingBanner mobile flex-wrap + bottom-nav FAB 충돌 가드
  test("OnboardingBanner — 375x812 진행률 노출 + 오버플로우 없음", async ({
    page,
  }) => {
    test.setTimeout(20_000);
    await page.goto("/dashboard");

    // step < 4 인 경우에만 banner 가 보임. 미인증/skip 환경에서는 가드.
    const banner = page.getByTestId("onboarding-banner");
    const isBannerVisible = await banner
      .isVisible({ timeout: 5_000 })
      .catch(() => false);

    if (isBannerVisible) {
      // "온보딩 N/4 단계" heading 가시성
      await expect(page.getByText(/온보딩 \d\/4 단계/)).toBeVisible({
        timeout: 5_000,
      });

      // 가로 오버플로우 없음 (banner.clientWidth ≤ viewport.width)
      const bannerWidth = await banner.evaluate(
        (el) => (el as HTMLElement).getBoundingClientRect().width,
      );
      expect(bannerWidth).toBeLessThanOrEqual(MOBILE.width);
    }
  });

  // Sprint 22 BL-017: /memory FAB 가 bottom-nav 와 겹치지 않음
  test("/memory FAB — mobile bottom-nav 위로 띄움 (BL-017)", async ({
    page,
  }) => {
    test.setTimeout(20_000);
    await page.goto("/memory");

    const fab = page.getByRole("button", { name: "새 메모 추가" });
    const fabVisible = await fab.isVisible({ timeout: 5_000 }).catch(() => false);

    if (fabVisible) {
      const fabBox = await fab.boundingBox();
      // bottom-nav-height = 56px → FAB top 이 viewport 하단 - 56px 이상으로 위치해야 함
      // FAB top + FAB height < viewport height - bottom-nav-height 면 무겹침
      const bottomNavHeight = 56;
      if (fabBox) {
        const fabBottom = fabBox.y + fabBox.height;
        const safeBottom = MOBILE.height - bottomNavHeight;
        expect(fabBottom).toBeLessThanOrEqual(safeBottom);
      }
    }
  });
});
