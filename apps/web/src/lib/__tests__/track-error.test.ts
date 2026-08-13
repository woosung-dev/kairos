// trackError 통합 entry point 단위 테스트
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { trackError } from "../track-error";

describe("trackError", () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it("Error 객체 + scope/digest 메타를 console.error 로 로깅", () => {
    const err = new Error("boom");
    err.stack = "stack-line-1";
    trackError(err, { scope: "test-scope", digest: "abc123" });

    expect(consoleErrorSpy).toHaveBeenCalledTimes(1);
    const [tag, payload] = consoleErrorSpy.mock.calls[0];
    expect(tag).toBe("[track-error] test-scope");
    expect(payload).toMatchObject({
      scope: "test-scope",
      digest: "abc123",
      error: { name: "Error", message: "boom", stack: "stack-line-1" },
    });
    expect(payload.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it("non-Error throw 도 그대로 직렬화", () => {
    trackError({ weird: "obj" }, { scope: "x" });
    const [, payload] = consoleErrorSpy.mock.calls[0];
    expect(payload.error).toEqual({ weird: "obj" });
  });

  it("extra 메타 그대로 포함", () => {
    trackError(new Error("x"), {
      scope: "memory",
      extra: { workspaceId: "ws-1", role: "viewer" },
    });
    const [, payload] = consoleErrorSpy.mock.calls[0];
    expect(payload.extra).toEqual({ workspaceId: "ws-1", role: "viewer" });
  });

  it("digest 없으면 undefined 로 유지", () => {
    trackError(new Error("x"), { scope: "no-digest" });
    const [, payload] = consoleErrorSpy.mock.calls[0];
    expect(payload.digest).toBeUndefined();
  });
});
