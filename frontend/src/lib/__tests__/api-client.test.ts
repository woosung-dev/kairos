// createApiClient seam 단위 테스트 — 토큰 주입 / null 토큰 AuthRequiredError
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  API_BASE_URL,
  AuthRequiredError,
  createApiClient,
} from "../api-client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("createApiClient", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetch: getToken 토큰을 Authorization 헤더로 주입하고 JSON 을 반환", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ id: "ws-1" }));
    const api = createApiClient(async () => "tok-123");

    const result = await api.fetch<{ id: string }>("/workspaces");

    expect(result).toEqual({ id: "ws-1" });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/v1/workspaces`);
    expect(
      (init?.headers as Record<string, string>)["Authorization"],
    ).toBe("Bearer tok-123");
  });

  it("fetch: 204 No Content 는 undefined 반환", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 }),
    );
    const api = createApiClient(async () => "tok-123");

    await expect(api.fetch<void>("/notes/1", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("fetch: 토큰 null 이면 AuthRequiredError (message '인증이 필요합니다')", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const api = createApiClient(async () => null);

    const err = await api.fetch("/workspaces").catch((e: unknown) => e);

    expect(err).toBeInstanceOf(AuthRequiredError);
    expect((err as Error).message).toBe("인증이 필요합니다");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("fetchRaw: raw Response 를 반환하고 기존 헤더를 보존", async () => {
    const raw = new Response("blob-body", { status: 200 });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(raw);
    const api = createApiClient(async () => "tok-raw");

    const res = await api.fetchRaw("/export", {
      headers: { Accept: "text/csv" },
    });

    expect(res).toBe(raw);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/v1/export`);
    const headers = init?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer tok-raw");
    expect(headers.get("Accept")).toBe("text/csv");
  });

  it("fetchRaw: 토큰 null 이면 AuthRequiredError", async () => {
    const api = createApiClient(async () => null);
    await expect(api.fetchRaw("/export")).rejects.toBeInstanceOf(
      AuthRequiredError,
    );
  });

  it("getToken: 토큰 반환 / null 이면 AuthRequiredError", async () => {
    const api = createApiClient(async () => "tok-sse");
    await expect(api.getToken()).resolves.toBe("tok-sse");

    const apiNull = createApiClient(async () => null);
    await expect(apiNull.getToken()).rejects.toBeInstanceOf(AuthRequiredError);
  });
});
