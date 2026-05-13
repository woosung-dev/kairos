// 미팅 업로드 E2E — 오디오 업로드 → STT → AI 분석 → 완료 골든패스 검증
import { test, expect } from "@playwright/test";
import path from "path";

const FIXTURE = path.join(__dirname, "../fixtures/test.m4a");

// serial: 향후 테스트 추가 대비 (단일 테스트 구조 유지)
test.describe.serial("미팅 업로드 파이프라인", () => {
  test("오디오 파일 업로드 후 STT 처리 완료 및 요약이 렌더링된다", async ({
    page,
  }) => {
    // STT 처리 최대 3분 소요 — 테스트 타임아웃 5분으로 설정
    test.setTimeout(300_000);

    // 1. /new 페이지 이동 (기본: 회의 녹음 + 오디오 업로드 탭 선택됨)
    await page.goto("/new");

    // 2. 제목 입력 (업로드 버튼 활성화 조건)
    await page.getByPlaceholder("회의 제목을 입력하세요").fill("E2E 테스트 회의");

    // 3. 파일 업로드 (hidden input에 직접 setInputFiles)
    await page.getByTestId("meeting-file-input").setInputFiles(FIXTURE);

    // 4. 업로드 버튼 클릭
    await page.getByRole("button", { name: "업로드 시작" }).click();

    // 5. 미팅 상세 페이지 이동 대기 (202 Accepted → redirect)
    await expect(page).toHaveURL(/\/meetings\//, { timeout: 30_000 });

    // 6. status=failed이면 즉시 실패 (낭비 방지)
    await page.waitForFunction(
      () => {
        const el = document.querySelector('[data-testid="meeting-status"]');
        return (
          el?.textContent !== "업로드 중" &&
          el?.textContent !== "STT 처리 중" &&
          el?.textContent !== "AI 분석 중" &&
          el?.textContent !== "임베딩 중"
        );
      },
      { timeout: 180_000, polling: 3000 }
    );
    await expect(page.getByTestId("meeting-status")).not.toHaveText("실패");
    await expect(page.getByTestId("meeting-status")).toHaveText("완료");

    // 7. 요약 섹션 렌더링 확인
    await expect(page.getByTestId("meeting-summary")).toBeVisible();
  });
});
