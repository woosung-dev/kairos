// C-025 — FE 글자 수는 BE(Python len = 코드 포인트)와 같은 기준으로 센다
import { describe, expect, it } from "vitest";
import { codePointLength } from "../text-length";

describe("codePointLength", () => {
  it("BMP 밖 이모지는 1글자 (String.length 는 2)", () => {
    const emoji25 = "😀".repeat(25);
    expect(emoji25.length).toBe(50);
    expect(codePointLength(emoji25)).toBe(25);
  });

  it("한글·영문은 String.length 와 같다", () => {
    expect(codePointLength("회의록 abc")).toBe(7);
    expect(codePointLength("")).toBe(0);
  });
});
