// T15: RAG 인라인 citation → SourceViewer UI 흐름 (실 SSE) — 소스 패널 + [1] 배지 클릭 → SourceViewer 열림, console.error 0
// P-FIX-1(프롬프트 [N] 정렬) 후 실 Gemini 가 [1] 인용 → FE markdown-message 가 클릭 배지 렌더.
import { test, expect } from "../../fixtures/team";
import { TOKEN_PUBLIC, collectConsoleErrors } from "../../team-helpers";

test.describe("T15 RAG citation → SourceViewer (실 SSE)", () => {
  test("질문 → 소스 패널 + [1] 배지 클릭 → SourceViewer 열림", async ({ ownerPage, sseAsk }) => {
    test.setTimeout(150_000); // 실 Gemini 스트리밍 (API fresh + UI)

    // (1) LIVE 프롬프트 가드: timeRange 로 캐시 skip → fresh Gemini 답변이 [N] 인용 생성(P-FIX-1).
    //     UI 만으론 캐시된 [1] 답변으로 prompt 회귀를 가릴 수 있어(codex P1), cache=false 로 직접 증명.
    const fresh = await sseAsk(ownerPage, { question: `${TOKEN_PUBLIC} 공개 프로젝트의 핵심 내용 요약` });
    expect(fresh.cached, "timeRange 캐시 skip — fresh 답변").toBe(false);
    expect(/\[\d+\]/.test(fresh.answer), "LIVE 프롬프트가 [N] 번호 인용 생성").toBe(true);

    // (2) UI 배선 가드: 인라인 [N] 배지 → 클릭 → SourceViewer (캐시 여부와 무관하게 wiring 검증).
    const errors = collectConsoleErrors(ownerPage);
    await ownerPage.goto("/search");

    // 유니크 질문 → 시맨틱 캐시 miss → 새 프롬프트([N])로 fresh 답변 생성.
    const q = `${TOKEN_PUBLIC} 공개 프로젝트의 내용을 알려줘 (q${Date.now()})`;
    // Enter 로 제출 (전송 버튼은 피드백 FAB(z-30)와 겹쳐 pointer intercept).
    await ownerPage.getByTestId("rag-input").fill(q);
    await ownerPage.getByTestId("rag-input").press("Enter");

    // 결정적 backstop: search_results → 소스 패널 렌더 (mutation: sources 방출 제거 시 부재).
    await expect(
      ownerPage.getByTestId("rag-sources"),
      "소스 패널(소스 N건) 렌더 — search_results 방출 증명",
    ).toBeVisible({ timeout: 60_000 });

    // 인라인 citation 배지 → 클릭 → SourceViewer 열림 (P-FIX-1 흐름).
    const badge = ownerPage.getByTestId("citation-badge-1").first();
    await expect(badge, "인라인 [1] citation 배지 렌더").toBeVisible({ timeout: 30_000 });
    await badge.click();
    await expect(
      ownerPage.getByTestId("rag-source-viewer"),
      "citation 클릭 → SourceViewer 열림",
    ).toBeVisible({ timeout: 10_000 });

    expect(errors(), "console.error 0").toEqual([]);
  });
});
