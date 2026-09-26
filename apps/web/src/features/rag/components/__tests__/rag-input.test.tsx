/**
 * G3-018 — 한글 조합 중 Enter 는 조합 확정용이다. 그때 전송하면 마지막 음절이 입력창에 남고
 * 사용자가 다시 Enter 를 누르면 그 한 글자가 두 번째 질문으로 나간다.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { RagInput } from "../rag-input";

afterEach(() => {
  cleanup();
});

describe("RagInput — IME 조합", () => {
  it("조합 중 Enter 는 전송하지 않고, 조합이 끝난 뒤 Enter 한 번에 전문을 보낸다", () => {
    const onSubmit = vi.fn();
    render(<RagInput onSubmit={onSubmit} />);
    const input = screen.getByTestId("rag-input");

    fireEvent.change(input, { target: { value: "블루펭귄 일정" } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter", isComposing: true, keyCode: 229 });
    expect(onSubmit).not.toHaveBeenCalled();

    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith("블루펭귄 일정");
  });

  it("Shift+Enter 는 전송하지 않는다", () => {
    const onSubmit = vi.fn();
    render(<RagInput onSubmit={onSubmit} />);
    const input = screen.getByTestId("rag-input");

    fireEvent.change(input, { target: { value: "질문" } });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });

    expect(onSubmit).not.toHaveBeenCalled();
  });
});
