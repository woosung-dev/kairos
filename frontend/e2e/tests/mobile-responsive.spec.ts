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
    // Sprint 22 baseline fix: dashboard 의 실제 heading 은 "무엇이든 질문하세요" (RAG 검색).
    // "오늘의 Kairos" (TodayFeed) 는 mount 안 됨 — origin/main e2e baseline fail 원인.
    await expect(
      page.getByRole("heading", { name: "무엇이든 질문하세요" }),
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

  // Sprint 24 Wave 2 T-OBN-05 D 옵션: OnboardingBanner 폐기. mobile flex-wrap 검증 case 제거.
  // 회귀 가드 (banner mount 0) — 375x812 viewport
  test("OnboardingBanner 폐기 회귀 — 375x812 mount 안 됨", async ({ page }) => {
    test.setTimeout(20_000);
    await page.goto("/dashboard");
    await expect(
      page.locator('[data-testid="onboarding-banner"]'),
    ).toHaveCount(0);
  });

  // Sprint 24 Wave 2 T-MOBILE-HEADER (BUG-MOBILE-001): 모바일 헤더 우측 프로필 잘림 fix
  // 3 viewport (375/393/412) 모두 avatar 가 viewport 안에 위치
  for (const vp of [
    { width: 375, height: 667 },
    { width: 393, height: 852 },
    { width: 412, height: 892 },
  ]) {
    test(`헤더 우측 프로필 avatar visible — ${vp.width}x${vp.height}`, async ({
      page,
    }) => {
      test.setTimeout(20_000);
      await page.setViewportSize(vp);
      await page.goto("/dashboard");
      // DropdownMenuTrigger (avatar) — aria-haspopup="menu" 로 식별
      const avatar = page
        .locator('[aria-haspopup="menu"]')
        .first();
      await expect(avatar).toBeVisible({ timeout: 15_000 });
      const box = await avatar.boundingBox();
      expect(box).not.toBeNull();
      if (box) {
        // avatar 의 우측 끝 (x + width) 이 viewport 너비 안에 위치
        expect(box.x + box.width).toBeLessThanOrEqual(vp.width);
        expect(box.x).toBeGreaterThanOrEqual(0);
      }
    });
  }

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
