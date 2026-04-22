import { test, expect } from "@playwright/test";

/**
 * Golden Path 2: RAG 질문 → citation 클릭 → Source Viewer
 *
 * 전략: 실제 RAG SSE 응답을 네트워크 인터셉트로 페이크한다.
 * - 이유: E2E에서 실제 LLM을 치면 (1) 느리고 (2) 답변에 citation이 포함될지 확률적
 * - UI 플로우(스트리밍 수신 → citation-badge 렌더 → 클릭 → SourceViewer open)가 검증 초점
 */

const FAKE_SOURCE = {
  id: "test-src-1",
  source: "테스트 회의",
  sourceType: "meeting",
  text: "이번 주 회의에서는 DevEx 강화에 집중하기로 결정했다.",
  date: "2026-04-23T00:00:00Z",
  score: 0.9,
  freshness: "recent",
};

/** hooks.ts 의 SSE 파서가 기대하는 형식: `event: <name>\ndata: <json>\n\n` */
function buildSseStream(): string {
  const events: string[] = [];
  events.push(
    `event: search_results\ndata: ${JSON.stringify({ chunks: [FAKE_SOURCE] })}`,
  );
  events.push(
    `event: answer\ndata: ${JSON.stringify({ token: "테스트 답변 " })}`,
  );
  events.push(
    `event: answer\ndata: ${JSON.stringify({ token: "[1]" })}`,
  );
  events.push(
    `event: done\ndata: ${JSON.stringify({ cached: false, sourceCount: 1 })}`,
  );
  return events.join("\n\n") + "\n\n";
}

test.describe("RAG citation → Source Viewer", () => {
  test("질문 제출 → [1] 클릭 → SourceViewer 열림", async ({ page }) => {
    // SSE 인터셉트
    await page.route("**/rag/ask", async (route) => {
      await route.fulfill({
        status: 200,
        headers: { "content-type": "text/event-stream" },
        body: buildSseStream(),
      });
    });

    await page.goto("/dashboard");

    // Cmd+K 열기 (버튼 클릭)
    await page.getByRole("button", { name: /검색하거나 질문 입력/ }).click();

    // 질문 입력 (Cmd+K 모달 내부 input)
    const input = page.locator('input[placeholder*="질문"], textarea[placeholder*="질문"]').first();
    await input.waitFor({ state: "visible", timeout: 5_000 });
    await input.fill("이번 주 회의 요약해줘");
    await input.press("Enter");

    // 응답 도착 + citation 배지 렌더
    const citation = page.getByRole("button", { name: /\[?1\]?/ }).first();
    await expect(citation).toBeVisible({ timeout: 10_000 });

    // citation 클릭 → SourceViewer 열림
    await citation.click();

    // SourceViewer 헤더에 소스 타이틀 노출
    await expect(page.getByText(FAKE_SOURCE.source)).toBeVisible();
  });
});
