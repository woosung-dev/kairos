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

    // local BE 환경 (CI) 에서는 sidebar 가 비어있을 수 있으므로 API 로
    // 직접 project 1개 생성한 뒤 /projects/{id} 진입.
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "오늘의 Kairos" })).toBeVisible({
      timeout: 15_000,
    });

    // 1. Clerk 토큰 + activeWorkspaceId 확보 (페이지 안에서 fetch)
    const ctx = await page.evaluate(async () => {
      // @ts-ignore — Clerk SDK 가 window 에 주입
      const token = await window.Clerk?.session?.getToken();
      const stored = window.localStorage.getItem("kairos-workspace");
      const parsed = stored ? JSON.parse(stored) : null;
      const wid = parsed?.state?.activeWorkspaceId;
      return { token, wid };
    });
    expect(ctx.token).toBeTruthy();
    expect(ctx.wid).toBeTruthy();

    // 2. project 1개 생성 (API 직접) — 환경 의존성 제거
    const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000";
    const createRes = await page.request.post(
      `${apiUrl}/api/v1/workspaces/${ctx.wid}/projects`,
      {
        headers: { Authorization: `Bearer ${ctx.token}`, "Content-Type": "application/json" },
        data: { title: "ISSUE-009 e2e", description: "regression test" },
      },
    );
    expect(createRes.ok()).toBeTruthy();
    const project = await createRes.json();
    expect(project.id).toBeTruthy();

    // 3. /projects/{id} 직접 진입 — sidebar 의존 없음
    await page.goto(`/projects/${project.id}`);

    // ErrorBoundary 의 "문제가 발생했습니다" 텍스트 미노출.
    await expect(page.getByText("문제가 발생했습니다")).toHaveCount(0);

    // 페이지 안정 대기 (React Query mount + 첫 fetch)
    await page
      .waitForLoadState("networkidle", { timeout: 15_000 })
      .catch(() => {});

    // 핵심: hooks order 위반 에러 부재.
    const hooksOrderErrors = consoleErrors.filter((m) =>
      /Rendered more hooks than during the previous render/i.test(m),
    );
    expect(hooksOrderErrors).toEqual([]);
  });

  test("ISSUE-005: /notes 페이지에 BE 데이터 반영 (mock 데이터 제거 검증)", async ({
    page,
  }) => {
    test.setTimeout(45_000);

    // 1. dashboard 우선 진입 — useSyncWorkspaceRole 가 panel-layout 에서 fire,
    //    workspaceRole 이 설정될 때까지 members API 응답 대기 (CI flake 회피).
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "오늘의 Kairos" })).toBeVisible({
      timeout: 15_000,
    });

    // 2. members API 가 완료될 때까지 polling — workspaceRole 가 store 에 들어왔는지
    //    Zustand persist 외부의 in-memory 값이므로 evaluate 로 직접 조회.
    await page.waitForFunction(
      () => {
        const stored = window.localStorage.getItem("kairos-workspace");
        // workspaceRole 은 persist 제외 (매 세션 fetch) — 따로 hasRole 확인 불가.
        // 대신 dashboard 의 워크스페이스 이름이 표시되면 members API 완료된 것.
        return !!stored && stored.includes("activeWorkspaceId");
      },
      { timeout: 15_000 },
    );

    // 3. /notes 진입 (role 이미 설정됨)
    await page.goto("/notes");
    await expect(page.getByRole("heading", { name: "빠른 메모" })).toBeVisible({
      timeout: 10_000,
    });

    // mock 데이터 흔적 ("AI 검색 성능 개선 아이디어" / "사용자 피드백 요약")
    // 가 fix 이후로 영구 사라져야 함. 단, 사용자가 실제로 같은 제목 노트를
    // 만들 수 있어서 0건이 아닐 수 있음. 대신 "Q2 제품 로드맵" / "사용자
    // 리서치" 라는 MOCK_PROJECTS 의 태그 명이 노출되는지로 회귀 검출.
    const mockProjectTags = page.locator(
      "text=/Q2 제품 로드맵|사용자 리서치/",
    );
    await expect(mockProjectTags).toHaveCount(0);

    // 새 메모 버튼 존재 확인 (canWrite=true 가정 — owner 계정).
    // 20s timeout — workspaceRole 동기화 race 회피.
    const newMemoBtn = page.getByRole("button", { name: /\+ 새 메모/ });
    await expect(newMemoBtn).toBeVisible({ timeout: 20_000 });
  });
});
