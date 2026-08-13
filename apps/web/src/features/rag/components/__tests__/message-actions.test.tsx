// F3 (2026-06-23 fullsweep) 회귀 가드 — RAG 답변 액션바: 내보내기 wiring + 노트로저장 dead button 제거.
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MessageActions } from "../message-actions";

describe("MessageActions — F3 (RAG 답변 액션바)", () => {
  it("'내보내기' 클릭 시 onExport 콜백을 호출한다 (이전 dead button 회귀)", () => {
    const onExport = vi.fn();
    render(<MessageActions content="답변 본문" onExport={onExport} />);

    fireEvent.click(screen.getByRole("button", { name: /내보내기/ }));
    expect(onExport).toHaveBeenCalledTimes(1);
  });

  it("미구현 '노트로 저장' dead button 은 더 이상 렌더하지 않는다", () => {
    render(<MessageActions content="답변 본문" />);
    expect(
      screen.queryByRole("button", { name: /노트로 저장/ }),
    ).not.toBeInTheDocument();
  });

  it("'복사' 버튼은 유지된다", () => {
    render(<MessageActions content="답변 본문" />);
    expect(
      screen.getByRole("button", { name: /복사/ }),
    ).toBeInTheDocument();
  });
});
