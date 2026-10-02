// PWA 설치형 셸 회귀 가드 (docs/requirements/pwa.md §4 · docs/plans/active/2026-10-02-pwa/test-matrix.md PR-1)
//
// public-only project 로 돈다 — 로그인·BE 불요, prod 빌드(`pnpm start`) 대상
// (`mise run fe-security-headers <port>`). SW 는 prod 빌드에서만 등록된다.
//
// - request 그룹: APIRequestContext(Node fetch) — CI chromium 의 ERR_NAME_NOT_RESOLVED 와 무관 (C-7).
// - browser 그룹: 실제 페이지 렌더 + SW. public-only 에서 페이지 렌더는 CI 에서 처음이다 →
//   draft PR CI spike 로 판정하고, 실패하면 `test.skip(!!process.env.CI, '<사유>')` + 로컬 게이트 증거로
//   대체한다 (pwa.md R-1). spike 전이라 아직 skip 하지 않는다.
// ★오프라인 재현 규칙 (pwa.md C-22): `context.setOffline(true)` 는 SW 의 **첫** 내비게이션 fetch 만
//   실패시킨다 → 새 컨텍스트의 첫 reload 1회만 판정한다. 실패를 유지해야 하면 `context.route` abort.
import { createHash } from "node:crypto";
import http from "node:http";
import type { AddressInfo } from "node:net";
import { expect, test, type BrowserContext, type Page, type Route } from "@playwright/test";

const SW_PATH = "/_next/static/service-worker/sw.js";
const BRAND_BACKGROUND = "#0A0A0B";
// create-next-app 기본 favicon (25931 B) — 게이트 ③ 으로 K 로 교체됐는지 판정 (T-PWA-03)
const DEFAULT_FAVICON_SHA256 = "2b8ad2d33455a8f736fc3a8ebf8f0bdea8848ad4c0db48a2833bd0f9cd775932";
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const OFFLINE_TITLE = "오프라인 — Kairos";
// 가로 모드 노치 폭에 가까운 임의 값 (T-PWA-16 CDP override)
const SAFE_AREA_SIDE = 47;

declare global {
  interface Window {
    __swRegisterCalls?: string[];
  }
}

// ---------------------------------------------------------------- helpers

function parsePngHeader(body: Buffer) {
  expect(body.subarray(0, 8).equals(PNG_SIGNATURE), "PNG 시그니처").toBe(true);
  return { width: body.readUInt32BE(16), height: body.readUInt32BE(20), colorType: body[25] };
}

function parseIcoEntries(body: Buffer) {
  expect(body.readUInt16LE(2), "ICO type").toBe(1);
  const count = body.readUInt16LE(4);
  return Array.from({ length: count }, (_, index) => {
    const base = 6 + 16 * index;
    const size = body[base] === 0 ? 256 : body[base];
    const length = body.readUInt32LE(base + 8);
    const offset = body.readUInt32LE(base + 12);
    const isPng = body.subarray(offset, offset + 8).equals(PNG_SIGNATURE);
    // PNG IHDR colortype (항목 시작 +25). Turbopack ICO 디코더는 6(RGBA)만 받는다.
    const colorType = body[offset + 25];
    return { size, length, isPng, colorType };
  });
}

/** `<tag ...>` 를 모두 찾아 속성 맵으로 돌려준다 (SSR HTML 문자열 검사용). */
function findTags(html: string, tag: "meta" | "link") {
  const tags: Record<string, string>[] = [];
  for (const match of html.matchAll(new RegExp(`<${tag}\\b([^>]*)>`, "gi"))) {
    const attributes: Record<string, string> = {};
    for (const attr of match[1].matchAll(/([a-zA-Z:-]+)(?:="([^"]*)")?/g)) {
      attributes[attr[1].toLowerCase()] = attr[2] ?? "";
    }
    tags.push(attributes);
  }
  return tags;
}

interface ConsoleError {
  readonly text: string;
  /** 메시지 발생 위치 — 리소스 로드 실패면 그 리소스 URL (`message.location().url`). */
  readonly url: string;
}

function collectConsoleErrors(page: Page): ConsoleError[] {
  const errors: ConsoleError[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push({ text: message.text(), url: message.location().url });
  });
  page.on("pageerror", (error) => errors.push({ text: `pageerror: ${error.message}`, url: "" }));
  return errors;
}

/** SW 등록·활성을 기다리고 reload 로 제어 상태를 확보한다. prod 빌드 전제. */
async function ensureControlled(page: Page, url: string) {
  await page.goto(url);
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  // reload 직후 아직 진행 중인 `<Link>` prefetch(`/sign-up?_rsc=`)가 이어지는 setOffline·route abort 에
  // 걸리면 "Failed to load resource" error 가 남아 판정이 흔들린다 (EVAL-IMPL-1 D1, 10회 중 4회 실패).
  await page.waitForLoadState("networkidle");
  expect(
    await page.evaluate(() => navigator.serviceWorker.controller !== null),
    "SW 미제어 — 이후 단언이 공허해진다"
  ).toBe(true);
}

interface CountingProxy {
  readonly origin: string;
  hits(pathname: string): number;
  reset(): void;
  close(): Promise<void>;
}

/**
 * prod 서버 앞에 두는 카운팅 리버스 프록시 (T-PWA-11 ②·T-PWA-13).
 * Host 헤더를 그대로 넘겨 리다이렉트 Location 이 프록시 origin 에 머물게 한다.
 */
async function startCountingProxy(upstreamBaseURL: string): Promise<CountingProxy> {
  const upstream = new URL(upstreamBaseURL);
  // Node 는 localhost 를 ::1 로 먼저 풀 수 있다 — next start 는 0.0.0.0(IPv4) 에서 듣는다.
  const upstreamHost = upstream.hostname === "localhost" ? "127.0.0.1" : upstream.hostname;
  const counts = new Map<string, number>();
  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url ?? "/", "http://proxy.invalid").pathname;
    counts.set(pathname, (counts.get(pathname) ?? 0) + 1);
    const upstreamRequest = http.request(
      {
        hostname: upstreamHost,
        port: upstream.port,
        path: req.url,
        method: req.method,
        headers: req.headers,
      },
      (upstreamResponse) => {
        res.writeHead(upstreamResponse.statusCode ?? 502, upstreamResponse.headers);
        upstreamResponse.pipe(res);
      }
    );
    upstreamRequest.on("error", () => {
      res.writeHead(502);
      res.end();
    });
    req.pipe(upstreamRequest);
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as AddressInfo;
  return {
    origin: `http://127.0.0.1:${port}`,
    hits: (pathname) => counts.get(pathname) ?? 0,
    reset: () => counts.clear(),
    close: () =>
      new Promise<void>((resolve) => {
        server.closeAllConnections();
        server.close(() => resolve());
      }),
  };
}

async function abortPath(context: BrowserContext, pathname: string) {
  await context.route(
    (url) => url.pathname === pathname,
    (route) => route.abort("internetdisconnected")
  );
}

// ---------------------------------------------------------------- request 그룹 (CI ✅)

test.describe("PWA request 그룹", () => {
  test("T-PWA-01 비로그인 manifest 200", async ({ request }) => {
    const response = await request.get("/manifest.webmanifest", { maxRedirects: 0 });
    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).toContain("application/manifest+json");
  });

  test("T-PWA-02 manifest 필드값", async ({ request }) => {
    const manifest = await (await request.get("/manifest.webmanifest")).json();
    expect(manifest).toMatchObject({
      id: "/",
      name: "Kairos",
      short_name: "Kairos",
      start_url: "/dashboard",
      scope: "/",
      display: "standalone",
      background_color: BRAND_BACKGROUND,
      theme_color: BRAND_BACKGROUND,
      lang: "ko",
    });
    expect(manifest.icons).toEqual([
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ]);
  });

  test("T-PWA-03 아이콘 실측 + favicon 교체", async ({ request }) => {
    const icons = [
      { path: "/icons/icon-192.png", size: 192 },
      { path: "/icons/icon-512.png", size: 512 },
      { path: "/icons/icon-maskable-512.png", size: 512 },
      { path: "/icons/apple-touch-icon.png", size: 180 },
    ];
    for (const icon of icons) {
      const response = await request.get(icon.path, { maxRedirects: 0 });
      expect(response.status(), icon.path).toBe(200);
      expect(response.headers()["content-type"], icon.path).toContain("image/png");
      const header = parsePngHeader(await response.body());
      expect([header.width, header.height], icon.path).toEqual([icon.size, icon.size]);
      if (icon.path.endsWith("apple-touch-icon.png")) {
        expect(header.colorType, "apple-touch-icon 불투명 (colortype 2)").toBe(2);
      }
    }

    const favicon = await request.get("/favicon.ico", { maxRedirects: 0 });
    expect(favicon.status()).toBe(200);
    const body = await favicon.body();
    expect(createHash("sha256").update(body).digest("hex"), "기본 favicon 그대로").not.toBe(
      DEFAULT_FAVICON_SHA256
    );
    const entries = parseIcoEntries(body);
    for (const size of [16, 32, 48]) {
      const entry = entries.find((candidate) => candidate.size === size);
      expect(entry, `favicon ${size}px 항목`).toBeDefined();
      expect(entry?.isPng, `favicon ${size}px 가 PNG 가 아님`).toBe(true);
      expect(entry?.colorType, `favicon ${size}px colortype (RGBA=6)`).toBe(6);
    }
  });

  test("T-PWA-04 보호 경로 유지 — /dashboard 비로그인 307", async ({ request }) => {
    const response = await request.get("/dashboard", { maxRedirects: 0 });
    expect(response.status()).toBe(307);
    const location = new URL(response.headers()["location"], "http://placeholder.invalid");
    expect(location.pathname).toBe("/sign-in");
    expect(location.searchParams.get("callbackURL")).toBe("/dashboard");
  });

  test("T-PWA-05 matcher 과다 해제 가드 — /x/manifest.webmanifest 307", async ({ request }) => {
    const response = await request.get("/x/manifest.webmanifest", { maxRedirects: 0 });
    expect(response.status()).toBe(307);
    expect(new URL(response.headers()["location"], "http://placeholder.invalid").pathname).toBe(
      "/sign-in"
    );
  });

  test("T-PWA-06 /sign-in SSR 메타", async ({ request }) => {
    const html = await (await request.get("/sign-in")).text();
    const links = findTags(html, "link");
    const metas = findTags(html, "meta");

    const manifestLinks = links.filter((attrs) => attrs.rel === "manifest");
    expect(manifestLinks).toHaveLength(1);
    expect(manifestLinks[0].href).toBe("/manifest.webmanifest");
    expect(manifestLinks[0]).not.toHaveProperty("crossorigin");

    const themeColors = metas.filter((attrs) => attrs.name === "theme-color");
    expect(themeColors).toHaveLength(1);
    expect(themeColors[0].content).toBe(BRAND_BACKGROUND);

    const viewport = metas.find((attrs) => attrs.name === "viewport");
    expect(viewport?.content).toContain("viewport-fit=cover");

    expect(
      links.filter((attrs) => attrs.rel === "apple-touch-icon").map((attrs) => attrs.href)
    ).toEqual(["/icons/apple-touch-icon.png"]);
    expect(metas.find((attrs) => attrs.name === "mobile-web-app-capable")?.content).toBe("yes");
    expect(metas.find((attrs) => attrs.name === "apple-mobile-web-app-title")?.content).toBe(
      "Kairos"
    );
  });

  test("T-PWA-07 SW 스크립트 응답 헤더", async ({ request }) => {
    const response = await request.get(SW_PATH, { maxRedirects: 0 });
    expect(response.status()).toBe(200);
    const headers = response.headers();
    expect(headers["service-worker-allowed"]).toBe("/");
    expect(headers["cache-control"]).toBe("public, max-age=0, must-revalidate");
    expect(headers["content-type"]).toContain("javascript");
  });
});

// ---------------------------------------------------------------- browser 그룹 (CI △ spike)

test.describe("PWA browser 그룹", () => {
  test("T-PWA-08 SW 등록·제어", async ({ page, baseURL }) => {
    await page.goto("/sign-in");
    const registration = await page.evaluate(async () => {
      const ready = await navigator.serviceWorker.ready;
      return { scope: ready.scope, scriptURL: ready.active?.scriptURL ?? "" };
    });
    expect(registration.scope).toBe(`${new URL(baseURL ?? "").origin}/`);
    expect(registration.scriptURL.endsWith(SW_PATH)).toBe(true);

    await page.reload();
    expect(await page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);
  });

  test("T-PWA-09 페이지 로드당 register 정확히 1회 · load 이후 · console.error 0", async ({
    page,
  }) => {
    const errors = collectConsoleErrors(page);
    await page.addInitScript(() => {
      window.__swRegisterCalls = [];
      const container = navigator.serviceWorker;
      const original = container.register.bind(container);
      container.register = (...args: Parameters<ServiceWorkerContainer["register"]>) => {
        window.__swRegisterCalls?.push(document.readyState);
        return original(...args);
      };
    });

    const readCalls = () => page.evaluate(() => window.__swRegisterCalls ?? []);
    const waitForFirstCall = async () => {
      await page.waitForFunction(() => (window.__swRegisterCalls?.length ?? 0) >= 1);
      await page.evaluate(async () => {
        await navigator.serviceWorker.ready;
      });
    };

    await page.goto("/sign-in");
    await waitForFirstCall();
    expect(await readCalls()).toEqual(["complete"]);

    await page.reload();
    await waitForFirstCall();
    expect(await readCalls(), "reload 는 새 로드 — 다시 1회").toEqual(["complete"]);

    await page.getByTestId("auth-switch-link").click();
    await page.waitForURL("**/sign-up");
    expect(await readCalls(), "클라이언트 이동은 추가 등록 0").toEqual(["complete"]);
    expect(errors).toEqual([]);
  });

  test("T-PWA-10 Cache Storage 미사용", async ({ page }) => {
    await ensureControlled(page, "/sign-in");
    await page.goto("/sign-up");
    await page.goto("/sign-in");
    expect(await page.evaluate(() => caches.keys())).toEqual([]);
  });

  test("T-PWA-11 ① 첫 오프라인 reload → SCR-001 (200 · no-store · console.error 0)", async ({
    page,
    context,
    baseURL,
  }) => {
    const errors = collectConsoleErrors(page);
    await ensureControlled(page, "/sign-in");
    const appOrigin = new URL(baseURL ?? "").origin;
    const foreignRequests: string[] = [];
    page.on("request", (request) => {
      if (new URL(request.url()).origin !== appOrigin) foreignRequests.push(request.url());
    });

    await context.setOffline(true);
    // ★첫 reload 1회만 판정한다 — 두 번째부터는 SW fetch 가 서버에 닿는다 (C-22).
    const response = await page.reload();
    expect(response?.status()).toBe(200);
    expect(response?.headers()["cache-control"]).toBe("no-store");
    await expect(page.getByTestId("offline-screen")).toBeVisible();
    expect(await page.title()).toBe(OFFLINE_TITLE);
    expect(foreignRequests).toEqual([]);
    expect(errors).toEqual([]);
  });

  test("T-PWA-11 ② 실패 유지 중 재시도 → 새 내비게이션 1회 · 서버 도달 0", async ({
    page,
    context,
    baseURL,
  }) => {
    const proxy = await startCountingProxy(baseURL ?? "");
    try {
      await ensureControlled(page, `${proxy.origin}/sign-in`);
      await abortPath(context, "/sign-in");
      proxy.reset();

      await page.reload();
      await expect(page.getByTestId("offline-screen")).toBeVisible();

      let navigations = 0;
      page.on("framenavigated", (frame) => {
        if (frame === page.mainFrame()) navigations += 1;
      });
      const [response] = await Promise.all([
        page.waitForResponse((candidate) => candidate.url().startsWith(`${proxy.origin}/sign-in`)),
        page.getByTestId("offline-retry").click(),
      ]);
      await page.waitForLoadState("load");

      expect(response.status()).toBe(200);
      expect(navigations).toBe(1);
      await expect(page.getByTestId("offline-screen")).toBeVisible();
      expect(proxy.hits("/sign-in"), "route abort 중 서버 도달").toBe(0);
    } finally {
      await proxy.close();
    }
  });

  test("T-PWA-11 ③ 온라인 복귀 → 자동 reload", async ({ page, context }) => {
    // setOffline 왕복은 쓰지 않는다 — 브라우저마다 페이지·SW 를 온라인으로 되돌리는 순서가 달라
    // (Chrome 154 는 페이지가 먼저 → online 직후 reload 가 아직 오프라인인 SW 에 걸려 3/14 실패,
    // EVAL-IMPL-2 D1) 결과가 에뮬레이션 순서에 묶인다. 실패는 route abort 로 만들고, 복귀는 abort 를
    // 걷은 뒤 `online` 이벤트를 직접 보내 "이벤트 → 자동 reload" 만 판정한다.
    await ensureControlled(page, "/sign-in");
    const isSignIn = (url: URL) => url.pathname === "/sign-in";
    const abortSignIn = (route: Route) => route.abort("internetdisconnected");
    await context.route(isSignIn, abortSignIn);
    await page.reload();
    await expect(page.getByTestId("offline-screen")).toBeVisible();

    await context.unroute(isSignIn, abortSignIn);
    // 클릭 없이 `online` 이벤트만으로 다시 불러와야 한다.
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    await expect(page.getByTestId("auth-email")).toBeVisible();
    await expect(page.getByTestId("offline-screen")).toHaveCount(0);
  });

  test("T-PWA-13 /api/* 내비게이션 서버 도달 정확히 1회 (navigationPreload 회귀 가드)", async ({
    page,
    baseURL,
  }) => {
    const proxy = await startCountingProxy(baseURL ?? "");
    try {
      await ensureControlled(page, `${proxy.origin}/sign-in`);
      expect(
        await page.evaluate(async () => {
          const registration = await navigator.serviceWorker.getRegistration();
          const state = await registration?.navigationPreload.getState();
          return state?.enabled ?? null;
        })
      ).toBe(false);

      // goto 직전 제어 상태 재확인 — 미제어면 아래 단언이 공허하게 통과한다.
      expect(await page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);
      proxy.reset();
      await page
        .goto(`${proxy.origin}/api/auth/callback/google?code=ONE_TIME&state=s1`)
        .catch(() => undefined);
      expect(proxy.hits("/api/auth/callback/google")).toBe(1);
    } finally {
      await proxy.close();
    }
  });

  test("T-PWA-16 safe-area inset 적용 — body 좌우 padding === inset (CDP override)", async ({
    page,
    context,
  }) => {
    // Chromium 은 실제 inset 이 0 이라 inset 0 단언만으로는 `env()` 를 지워도 통과한다 → 값을 주입한다.
    // CDP 미지원이면 skip 하지 않고 여기서 실패한다 (Chromium 147 지원 확인, EVAL-IMPL-1 probe).
    const cdp = await context.newCDPSession(page);
    await cdp.send("Emulation.setSafeAreaInsetsOverride", {
      insets: { top: 0, left: SAFE_AREA_SIDE, right: SAFE_AREA_SIDE, bottom: 0 },
    });
    await page.goto("/sign-in");
    expect(
      await page.evaluate(() => {
        const style = getComputedStyle(document.body);
        return { left: style.paddingLeft, right: style.paddingRight };
      })
    ).toEqual({ left: `${SAFE_AREA_SIDE}px`, right: `${SAFE_AREA_SIDE}px` });
  });

  test("T-PWA-23 오프라인 <Link> 클라이언트 이동 (측정)", async ({ page, context }) => {
    const errors = collectConsoleErrors(page);
    await ensureControlled(page, "/sign-in");
    // prefetch 된 RSC 로 오프라인에서도 이동해 버리지 않게, 차단을 건 뒤 다시 불러온다.
    await abortPath(context, "/sign-up");
    await page.reload();

    await page.getByTestId("auth-switch-link").click();
    // [가정] Next 가 RSC 실패 후 하드 내비게이션으로 폴백 → SW 가 SCR-001 (pwa.md §4.4)
    await expect(page.getByTestId("offline-screen")).toBeVisible();
    // 이 테스트에서만 허용 (test-matrix 허용 콘솔 목록): Next 의 RSC 실패 error, 그리고 이 테스트가
    // abort 한 RSC fetch 의 리소스 로드 실패 — 후자는 텍스트가 아니라 발생 URL 로 좁힌다.
    const isAllowed = (error: ConsoleError) =>
      error.text.includes("Failed to fetch RSC payload") ||
      (error.text.startsWith("Failed to load resource") && error.url.includes("/sign-up?_rsc="));
    expect(errors.filter((error) => !isAllowed(error))).toEqual([]);
  });
});
