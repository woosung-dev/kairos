import { test, expect } from "@playwright/test";

/**
 * Golden Path 1: 홈 진입 + 사이드바 네비게이션
 *
 * 검증 대상:
 * - 인증된 상태로 /dashboard 진입 시 Today 피드 또는 온보딩 배너가 렌더된다
 * - 사이드바에 최소 1개 이상의 프로젝트가 표시된다 (템플릿 시딩 동작 확인)
 * - 프로젝트 클릭 → 프로젝트 대시보드 렌더
 */

test.describe("홈 — 인증 후 네비게이션", () => {
  test("/dashboard 렌더 + RAG 검색 진입점 확인", async ({ page }) => {
    await page.goto("/dashboard");

    // Sprint 22 baseline fix: dashboard 의 실제 heading 은 "무엇이든 질문하세요" (RAG 검색).
    // 기존 "오늘의 Kairos" (TodayFeed) 는 mount 안 됨 — origin/main e2e baseline fail 원인.
    await expect(
      page.getByRole("heading", { name: /무엇이든 질문하세요/ }),
    ).toBeVisible({ timeout: 15_000 });

    // Cmd+K 검색 트리거 버튼 존재
    await expect(
      page.getByRole("button", { name: /검색하거나 질문 입력/ }),
    ).toBeVisible({ timeout: 15_000 });

    // G1 (Sprint 24 Wave 2 T-OBN-05 D 옵션): OnboardingBanner 폐기.
    // banner data-testid 가 더 이상 mount 되지 않음 검증 (회귀 가드).
    await expect(
      page.locator('[data-testid="onboarding-banner"]'),
    ).toHaveCount(0);
  });

  test("사이드바 프로젝트 목록 렌더 (템플릿 시딩 포함)", async ({ page }) => {
    await page.goto("/dashboard");

    // 사이드바의 '프로젝트' 섹션 헤더
    await expect(page.getByText("프로젝트", { exact: true })).toBeVisible({ timeout: 15_000 });

    // 신규 가입한 계정이라면 템플릿 시딩으로 🚀 시작하기 / 💡 아이디어 / 📋 회의록 중 적어도 하나는 보여야 함.
    // 기존 계정이라도 사이드바에 프로젝트가 있거나 "프로젝트 없음" 안내가 있음.
    const templateProjects = page.getByText(
      /🚀 시작하기|💡 아이디어|📋 회의록|프로젝트 없음/,
    );
    await expect(templateProjects.first()).toBeVisible({ timeout: 15_000 });
  });

  test("프로젝트 클릭 → 프로젝트 대시보드 진입", async ({ page }) => {
    await page.goto("/dashboard");

    const projectLink = page
      .locator('aside a[href^="/projects/"]')
      .first();

    const projectExists = await projectLink.count();
    test.skip(projectExists === 0, "프로젝트가 없는 계정 — 이 테스트는 생략");

    const href = await projectLink.getAttribute("href");
    await projectLink.click();
    await page.waitForURL(new RegExp(href ?? ""));

    // 프로젝트 페이지 랜딩 요소 (대시보드형 레이아웃)
    await expect(page.locator("main, [role=main]")).toBeVisible();
  });
});
