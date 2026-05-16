// Sprint 17 QA regression e2e — ISSUE-005 + ISSUE-009 회귀 가드
import { test, expect } from "@playwright/test";

/**
 * Sprint 17 fix 회귀 방지 e2e 모음.
 *
 * 본 spec 은 auth.setup.ts 의 storageState 를 재사용 (인증 상태 + 워크스페이스
 * 보장). 각 시나리오는 단일 fix 의 표면 증상 (콘솔 에러 / HTTP 상태 / UI
 * 텍스트) 만 검증해 시간 비용 최소화.
 */

test.describe("Sprint 17 QA regression 모음", () => {
  test("ISSUE-009: /projects/[id] 렌더링 (useRecentItems hooks order)", async ({
    page,
  }) => {
    test.setTimeout(60_000);

    // 콘솔 에러 수집 — "Rendered more hooks than during the previous render"
    // 가 다시 나타나면 회귀.
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    // 사이드바에서 첫 프로젝트 링크 진입 (link href 기반).
    // 대시보드에서 시작 — 사이드바 프로젝트 list 로드 대기.
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "오늘의 Kairos" })).toBeVisible({
      timeout: 15_000,
    });

    // 사이드바의 프로젝트 링크 한 개 클릭 (첫번째).
    const firstProjectLink = page
      .getByRole("link")
      .filter({ hasText: /^[🚀💡📋]/ })
      .first();
    await firstProjectLink.waitFor({ timeout: 10_000 });
    await firstProjectLink.click();

    // 프로젝트 detail 페이지 URL 패턴.
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]+/, { timeout: 10_000 });

    // ErrorBoundary 의 "문제가 발생했습니다" 텍스트 미노출.
    const errorBoundary = page.getByText("문제가 발생했습니다");
    await expect(errorBoundary).toHaveCount(0);

    // 핵심: hooks order 위반 에러 부재.
    const hooksOrderErrors = consoleErrors.filter((m) =>
      /Rendered more hooks than during the previous render/i.test(m),
    );
    expect(hooksOrderErrors).toEqual([]);
  });

  test("ISSUE-005: /notes 페이지에 BE 데이터 반영 (mock 데이터 제거 검증)", async ({
    page,
  }) => {
    test.setTimeout(30_000);

    await page.goto("/notes");
    await expect(page.getByRole("heading", { name: "빠른 메모" })).toBeVisible({
      timeout: 10_000,
    });

    // mock 데이터 흔적 ("AI 검색 성능 개선 아이디어" / "사용자 피드백 요약")
    // 가 fix 이후로 영구 사라져야 함. 단, 사용자가 실제로 같은 제목 노트를
    // 만들 수 있어서 0건이 아닐 수 있음. 대신 "Q2 제품 로드맵" / "사용자
    // 리서치" 라는 MOCK_PROJECTS 의 태그 명이 노출되는지로 회귀 검출.
    // 이 두 태그는 quick-memo.tsx 가 mock 일 때만 노출 가능. real API 사용 시
    // useProjects 결과 (시작하기/아이디어/회의록) 만 노출.
    const mockProjectTags = page.locator(
      "text=/Q2 제품 로드맵|사용자 리서치/",
    );
    await expect(mockProjectTags).toHaveCount(0);

    // 새 메모 버튼 존재 확인 (canWrite=true 가정 — owner 계정).
    const newMemoBtn = page.getByRole("button", { name: /\+ 새 메모/ });
    await expect(newMemoBtn).toBeVisible({ timeout: 10_000 });
  });
});
