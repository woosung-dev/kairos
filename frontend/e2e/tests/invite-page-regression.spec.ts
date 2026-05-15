// /invite/[code] regression e2e — ISSUE-008 (QueryProvider root 이동) + 잘못된 코드 처리
import { test, expect } from "@playwright/test";

/**
 * Sprint 17 ISSUE-008 regression — /invite/[code] 페이지가 500 → 200 으로 fix 된
 * 후 회귀 방지용 e2e. (app) 그룹 외부 라우트가 QueryClientProvider 를 잃지
 * 않는지 검증.
 *
 * 시나리오:
 * 1. 잘못된 (존재하지 않는) invite code → 페이지 200 + "찾을 수 없" 류 안내 텍스트 노출
 * 2. 미인증 상태로 진입 → 페이지 200 + 로그인 유도 또는 invite 정보 노출 (사용자 흐름)
 *
 * 핵심: HTTP status 200 + React 트리 정상 마운트 ("This page couldn't load" 류
 * Next.js 기본 에러 페이지 미노출).
 */

test.describe("/invite/[code] regression (ISSUE-008)", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("존재하지 않는 invite code 도 페이지 200 + 안내 텍스트 (Next.js error page 아님)", async ({
    page,
  }) => {
    test.setTimeout(30_000);

    const response = await page.goto(
      "/invite/invalid-code-no-such-thing-zzzz",
    );

    // 1. HTTP 200 — 이전 회귀에서는 500 응답이었음 (ISSUE-008).
    expect(response?.status()).toBe(200);

    // 2. Next.js 의 기본 "This page couldn't load" 에러 페이지 미노출.
    //    React 트리가 정상 마운트되면 본 메시지는 절대 안 보임.
    const nextErrorHeading = page.getByRole("heading", {
      name: /This page couldn't load|페이지를 불러올 수 없습니다/,
    });
    await expect(nextErrorHeading).toHaveCount(0);

    // 3. invite info 가 없으니 어떤 형태로든 사용자 안내 노출.
    //    "찾을 수 없", "유효하지 않", "Invalid", "expired" 등 키워드 중 하나.
    const fallback = page.locator(
      "text=/찾을 수 없|유효하지 않|만료|invalid|expired/i",
    ).first();
    await expect(fallback).toBeVisible({ timeout: 15_000 });
  });

  test("/invite/[code] 라우트가 QueryClientProvider 안에서 마운트된다 (No QueryClient set 회귀 없음)", async ({
    page,
  }) => {
    test.setTimeout(30_000);

    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto("/invite/regression-check-zzz");

    // 페이지 안정 대기 (React Query 마운트 + 첫 fetch).
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

    // 핵심 검증: "No QueryClient set" 에러 없음.
    //   ISSUE-008 의 표면 증상이었음. QueryProvider 가 root layout 으로
    //   이동한 33c9f1c 가 정착되었는지 확인.
    const queryClientErrors = consoleErrors.filter((m) =>
      /No QueryClient set/i.test(m),
    );
    expect(queryClientErrors).toEqual([]);
  });
});
