// createApiClient seam 단위 테스트 — 토큰 주입 / null 토큰 AuthRequiredError
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  API_BASE_URL,
  ApiError,
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

  it("fetch: 본문 없는 202 Accepted 도 undefined 반환 (reject 하지 않는다)", async () => {
    // B-7/I-EXT-3 의 장기 작업은 202 로 접수만 알린다. 일부 라우트는 본문이 비어
    // 있는데, 204 만 특수 처리하면 res.json() 이 "Unexpected end of JSON input" 으로
    // reject 되어 서버는 접수했는데 FE 의 캐시 무효화가 통째로 건너뛰어진다.
    // (실제 회귀: Drive 문서 "다시 동기화" 버튼이 아무 일도 하지 않았다.)
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("", { status: 202 }),
    );
    const api = createApiClient(async () => "tok-123");

    await expect(
      api.fetch<void>("/workspaces/ws-1/integrations/google-drive/documents/d-1/sync", {
        method: "POST",
      }),
    ).resolves.toBeUndefined();
  });

  it("fetch: 403 응답은 detail과 status를 보존한 ApiError를 던진다", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "워크스페이스 접근 권한이 없습니다" }, 403),
    );
    const api = createApiClient(async () => "tok-123");

    const error = await api.fetch("/workspaces/ws-1/projects").catch((reason: unknown) => reason);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(403);
    expect((error as ApiError).message).toBe("워크스페이스 접근 권한이 없습니다");
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

// C-025 회귀 가드 — FastAPI 422 의 detail 은 객체 배열이다. 예전엔 new Error(배열) 이 되어
// 화면에 "[object Object]" 가 떴다 (/new 텍스트 캡처 실측, probe G2-004).
describe("createApiClient — 422 validation detail 을 읽을 수 있는 한국어로", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  async function errorFor(body: unknown, status: number): Promise<ApiError> {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(body, status));
    const api = createApiClient(async () => "tok-123");
    return (await api.fetch("/workspaces/ws-1/meetings/capture").catch((e: unknown) => e)) as ApiError;
  }

  it("string_too_short → 최소 글자 수 + 필드명, [object Object] 아님", async () => {
    const error = await errorFor(
      {
        detail: [
          {
            type: "string_too_short",
            loc: ["body", "transcriptText"],
            msg: "String should have at least 50 characters",
            input: "😀".repeat(25),
            ctx: { min_length: 50 },
          },
        ],
      },
      422,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(422);
    expect(error.message).toBe("최소 50자 이상 입력해 주세요 (transcriptText)");
    expect(error.message).not.toContain("[object Object]");
  });

  it("string_too_long → 최대 글자 수", async () => {
    const error = await errorFor(
      { detail: [{ type: "string_too_long", loc: ["body", "name"], msg: "x", ctx: { max_length: 60 } }] },
      422,
    );
    expect(error.message).toBe("최대 60자까지 입력할 수 있습니다 (name)");
  });

  it("알 수 없는 validation type 은 일반 문구 + 필드명 (영어 msg 를 노출하지 않는다)", async () => {
    const error = await errorFor(
      { detail: [{ type: "value_error", loc: ["body", "name"], msg: "Value error, blank" }] },
      422,
    );
    expect(error.message).toBe("입력값을 확인해 주세요 (name)");
  });

  it("문자열이 아닌 객체 detail 도 [object Object] 로 새지 않는다", async () => {
    const error = await errorFor({ detail: { code: "SOMETHING" } }, 409);
    expect(error.message).toBe("요청을 처리하지 못했습니다 (HTTP 409)");
  });
});
