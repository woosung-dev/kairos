/**
 * E2-X01 — 로그인·가입 후 목적지는 same-origin 상대 경로만 허용한다 (open redirect 차단).
 */
import { describe, expect, it } from "vitest";
import { authHrefWithCallback, DEFAULT_CALLBACK_URL, sanitizeCallbackURL } from "../callback-url";

describe("sanitizeCallbackURL", () => {
  it("상대 경로는 쿼리·해시까지 그대로 통과한다", () => {
    expect(sanitizeCallbackURL("/invite/abc123")).toBe("/invite/abc123");
    expect(sanitizeCallbackURL("/projects/p1?tab=notes#top")).toBe("/projects/p1?tab=notes#top");
  });

  it("값이 없으면 기본 목적지", () => {
    expect(sanitizeCallbackURL(null)).toBe(DEFAULT_CALLBACK_URL);
    expect(sanitizeCallbackURL(undefined)).toBe(DEFAULT_CALLBACK_URL);
    expect(sanitizeCallbackURL("")).toBe(DEFAULT_CALLBACK_URL);
  });

  it.each([
    "https://evil.example/phish",
    "//evil.example/phish",
    "/\\evil.example/phish",
    "/\t/evil.example/phish",
    "javascript:alert(1)",
    "invite/abc",
    // dot-segment 정규화가 protocol-relative 를 새로 만드는 경우 (E-FE E-1)
    "/.//evil.example",
    "/..//evil.example",
    "/%2e//evil.example",
    "/.\\/evil.example",
  ])("외부로 나가는 값 %s 은 기본 목적지로 바꾼다", (raw) => {
    expect(sanitizeCallbackURL(raw)).toBe(DEFAULT_CALLBACK_URL);
  });
});

describe("authHrefWithCallback", () => {
  it("초대 경로를 인코딩해 붙인다", () => {
    expect(authHrefWithCallback("/sign-up", "/invite/abc123")).toBe(
      "/sign-up?callbackURL=%2Finvite%2Fabc123",
    );
  });

  it("기본 목적지이거나 안전하지 않으면 쿼리를 붙이지 않는다", () => {
    expect(authHrefWithCallback("/sign-in", DEFAULT_CALLBACK_URL)).toBe("/sign-in");
    expect(authHrefWithCallback("/sign-in", "//evil.example")).toBe("/sign-in");
    expect(authHrefWithCallback("/sign-in", null)).toBe("/sign-in");
  });
});
