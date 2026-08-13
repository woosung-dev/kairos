// CAND-D 회귀 — /search 의 피드백 FAB 가 RAG 전송 버튼을 가려 클릭을 가로채는 overlap 가드
import { test, expect } from "@playwright/test";

/**
 * CAND-D (P2): /search 페이지의 floating 피드백 FAB (fixed right-4 z-30, 데스크톱
 * bottom-6) 가 RAG composer 의 전송 버튼(data-testid="rag-submit")과 기하학적으로
 * 겹쳐 pointer 이벤트를 가로챈다. 결과적으로 마우스로 보이는 전송 버튼을 클릭할 수
 * 없고 Enter fallback 만 동작한다 (discoverability + a11y 회귀).
 *
 * 본 spec 은 layout 엔진을 실제로 거치는 라이브 /search 를 띄워:
 *   1) 질문을 입력해 rag-submit 을 enabled/visible 상태로 만들고
 *   2) 전송 버튼 중심점에서 document.elementFromPoint 가 전송 버튼 자신이어야 함을
 *      검증한다 (FAB 가 위에 있으면 elementFromPoint === FAB → RED).
 *   3) boundingBox 교차로 FAB 가 전송 버튼 위에 겹치지 않음을 함께 가드한다.
 *
 * Enter fallback 만 검증하던 T15 가 잡지 못한 빈틈을 메운다.
 * 어떤 bug 위치(FAB/composer 의 CSS/위치)도 mock 하지 않고 실제 seam 만 검증.
 */
test.describe("CAND-D: /search FAB 가 RAG 전송 버튼을 가리지 않음", () => {
  test("rag-submit 중심점이 전송 버튼 자신으로 hit-test 됨 (FAB 미차단)", async ({
    page,
  }) => {
    test.setTimeout(45_000);

    await page.goto("/search", { waitUntil: "domcontentloaded" });

    // RAG 입력 영역 렌더 대기 후 질문 입력 → 전송 버튼 활성화.
    const input = page.getByTestId("rag-input");
    await expect(input).toBeVisible({ timeout: 15_000 });
    await input.fill("FAB overlap 회귀 검증 질문");

    const submit = page.getByTestId("rag-submit");
    await expect(submit).toBeVisible();
    await expect(submit).toBeEnabled();

    // 피드백 FAB 가 마운트되어 있는지 확인 (overlap 의 전제).
    const fab = page.getByRole("button", { name: "피드백 보내기" });
    await expect(fab).toBeVisible({ timeout: 5_000 });

    // 핵심: 전송 버튼 중심점에서의 hit-test 결과가 전송 버튼이어야 함.
    // FAB 가 겹쳐 pointer 이벤트를 가로채면 elementFromPoint === FAB → false.
    const hitsSubmit = await submit.evaluate((el) => {
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const top = document.elementFromPoint(cx, cy);
      return el === top || el.contains(top);
    });
    expect(
      hitsSubmit,
      "전송 버튼 중심점에서 다른 요소(FAB)가 hit-test 됨 — FAB 가 전송 버튼을 가림",
    ).toBe(true);

    // 보조 가드: FAB 와 전송 버튼의 bounding box 가 교차하지 않음.
    const submitBox = await submit.boundingBox();
    const fabBox = await fab.boundingBox();
    expect(submitBox).not.toBeNull();
    expect(fabBox).not.toBeNull();
    if (submitBox && fabBox) {
      const overlapX =
        Math.min(submitBox.x + submitBox.width, fabBox.x + fabBox.width) >
        Math.max(submitBox.x, fabBox.x);
      const overlapY =
        Math.min(submitBox.y + submitBox.height, fabBox.y + fabBox.height) >
        Math.max(submitBox.y, fabBox.y);
      expect(
        overlapX && overlapY,
        "FAB 와 전송 버튼 bounding box 가 교차함 (overlap)",
      ).toBe(false);
    }

    // 회귀 핵심: 실제 마우스 클릭이 전송 버튼에 도달해야 함 (FAB 차단 시 timeout).
    await submit.click({ timeout: 5_000 });
  });
});
