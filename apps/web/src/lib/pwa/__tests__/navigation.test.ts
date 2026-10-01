// T-PWA-12 — SW 가로채기 조건 + 서버 응답 마스킹 금지 + 오프라인 응답 형식
// (docs/plans/active/2026-10-02-pwa/test-matrix.md, docs/requirements/pwa.md §4.4)
import { describe, expect, it, vi } from "vitest";
import {
  createOfflineResponse,
  respondToNavigation,
  shouldHandleNavigation,
} from "../navigation";
import { OFFLINE_HTML, OFFLINE_TITLE } from "../offline-page";

const ORIGIN = "https://kairos.woosung.dev";

function navRequest(url: string, overrides: { mode?: string; method?: string } = {}) {
  return { mode: overrides.mode ?? "navigate", method: overrides.method ?? "GET", url };
}

describe("shouldHandleNavigation", () => {
  it("같은 origin GET navigate 만 처리한다", () => {
    expect(shouldHandleNavigation(navRequest(`${ORIGIN}/dashboard`), ORIGIN)).toBe(true);
    expect(shouldHandleNavigation(navRequest(`${ORIGIN}/sign-in?callbackURL=%2F`), ORIGIN)).toBe(
      true
    );
  });

  it("navigate 가 아닌 요청은 건드리지 않는다 (RSC·자산·fetch)", () => {
    for (const mode of ["cors", "no-cors", "same-origin"]) {
      expect(shouldHandleNavigation(navRequest(`${ORIGIN}/dashboard`, { mode }), ORIGIN)).toBe(
        false
      );
    }
  });

  it("다른 origin 내비게이션은 건드리지 않는다", () => {
    expect(
      shouldHandleNavigation(navRequest("https://kairos-api.woosung.dev/docs"), ORIGIN)
    ).toBe(false);
  });

  it("/api/* 내비게이션(OAuth 콜백 포함)은 건드리지 않는다", () => {
    expect(
      shouldHandleNavigation(
        navRequest(`${ORIGIN}/api/auth/callback/google?code=ONE_TIME&state=s1`),
        ORIGIN
      )
    ).toBe(false);
    expect(shouldHandleNavigation(navRequest(`${ORIGIN}/api/v1/anything`), ORIGIN)).toBe(false);
  });

  it("POST 내비게이션(form submit)은 건드리지 않는다", () => {
    expect(
      shouldHandleNavigation(navRequest(`${ORIGIN}/sign-in`, { method: "POST" }), ORIGIN)
    ).toBe(false);
  });
});

describe("respondToNavigation", () => {
  const request = new Request(`${ORIGIN}/dashboard`);

  it("주입한 fetch 를 정확히 1회 부른다", async () => {
    const fetchFn = vi.fn(async () => new Response("ok", { status: 200 }));
    await respondToNavigation(request, fetchFn);
    expect(fetchFn).toHaveBeenCalledTimes(1);
    expect(fetchFn).toHaveBeenCalledWith(request);
  });

  it.each([500, 503, 307, 404])("서버 응답 %i 은 그 객체 그대로 돌려준다", async (status) => {
    const serverResponse = new Response(null, { status });
    const result = await respondToNavigation(request, async () => serverResponse);
    expect(result).toBe(serverResponse);
  });

  it("fetch reject(네트워크 실패)일 때만 오프라인 화면 — 200 + no-store", async () => {
    const result = await respondToNavigation(request, async () => {
      throw new TypeError("Failed to fetch");
    });
    expect(result.status).toBe(200);
    expect(result.headers.get("content-type")).toBe("text/html; charset=utf-8");
    expect(result.headers.get("cache-control")).toBe("no-store");
    const body = await result.text();
    expect(body).toContain('data-testid="offline-screen"');
    expect(body).toContain('data-testid="offline-retry"');
  });
});

describe("SCR-001 오프라인 HTML", () => {
  it("문서 메타 — lang·title·viewport·theme-color", () => {
    expect(OFFLINE_HTML).toContain('<html lang="ko">');
    expect(OFFLINE_HTML).toContain(`<title>${OFFLINE_TITLE}</title>`);
    expect(OFFLINE_TITLE).toBe("오프라인 — Kairos");
    expect(OFFLINE_HTML).toContain('name="viewport"');
    expect(OFFLINE_HTML).toContain('<meta name="theme-color" content="#0A0A0B">');
  });

  it("외부 리소스를 참조하지 않는다 (오프라인이라 받을 수 없다) — `data:` 만 허용", () => {
    expect(OFFLINE_HTML).not.toMatch(/\b(?:src|href)\s*=\s*(?!"data:)/i);
    expect(OFFLINE_HTML).not.toMatch(/@import|url\(/i);
    expect(OFFLINE_HTML).not.toMatch(/https?:\/\//i);
  });

  it("아이콘 선언이 `data:` 로 정확히 1개 — headed Chrome 의 /favicon.ico 요청 차단 (EVAL-IMPL-1 D2)", () => {
    expect(OFFLINE_HTML.match(/rel="icon"/g)).toHaveLength(1);
    expect(OFFLINE_HTML.match(/href="data:/g)).toHaveLength(1);
    const icon = OFFLINE_HTML.match(/<link rel="icon" href="(data:image\/svg\+xml,[^"]+)">/);
    expect(icon).not.toBeNull();
    // href 값 안에 이스케이프되지 않은 따옴표·꺾쇠·# 가 없다 → 디코드하면 K 모노그램 SVG
    expect(icon?.[1]).not.toMatch(/[<>#"]/);
    const svg = decodeURIComponent(icon?.[1].slice("data:image/svg+xml,".length) ?? "");
    expect(svg).toContain('xmlns="http://www.w3.org/2000/svg"');
    expect(svg).toContain('fill="#3ECFB4">K</text>');
    expect(svg).toContain('fill="#0A0A0B"');
  });

  it("다시 시도 버튼 + online 자동 reload 를 담는다", () => {
    expect(OFFLINE_HTML).toContain("location.reload()");
    expect(OFFLINE_HTML).toContain('addEventListener("online"');
  });

  it("createOfflineResponse 는 호출마다 새 Response 를 만든다 (본문 재사용 불가 회피)", async () => {
    const first = createOfflineResponse();
    const second = createOfflineResponse();
    expect(first).not.toBe(second);
    await first.text();
    await expect(second.text()).resolves.toBe(OFFLINE_HTML);
  });
});
