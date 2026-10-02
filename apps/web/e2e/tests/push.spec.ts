// 웹 푸시 FE 회귀 (docs/requirements/pwa.md §5.5 · §5.6 · test-matrix.md T-PWA-48 · 49 · 59) — chromium project.
//
// - 전제 (T-48·49): prod 빌드(`pnpm start`) + SW 등록 상태. CI e2e 잡은 prod 빌드라 반드시 등록돼 있어야 한다.
//   로컬 `pnpm dev` 는 SW 를 등록하지 않으므로(pwa.md §4.5) 그때만 skip 한다 — CI 에서는 공허 통과 대신 실패.
// - CI 백엔드에는 VAPID 가 없다 → API-001~003 은 `page.route` 로 고정한다 (FE 흐름만 판정).
// - 헤드리스 구독은 실제 푸시 서비스(FCM)에 닿는다 → `PushManager`·`Notification.requestPermission` 은
//   `addInitScript` stub. 호출 수·구독 상태는 sessionStorage 에 둬 리로드·전체 내비게이션을 넘는다.
import { expect, test, type Page, type Route } from "@playwright/test";

import { collectConsoleErrors, api, getMe, injectActiveWorkspace } from "../team-helpers";

declare global {
  interface Window {
    __meetingDetailErrorSeen?: boolean;
  }
}

const PUSH_MARKER_KEY = "kairos:push:v1";
const STUB_STATE_KEY = "__e2ePushStub";
const PUSH_CONFIG_PATH = "/api/v1/users/me/push-config";
const PUSH_SUBSCRIPTIONS_PATH = "/api/v1/users/me/push-subscriptions";
const SIGN_OUT_PATH = "/api/auth/sign-out";
// 테스트 전용 P-256 공개키 (비밀키 없음 — stub 이라 서명하지 않는다)
const VAPID_PUBLIC_KEY =
  "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U";
const STUB_SUBSCRIPTION_ID = "5d1c9a4e-7b2f-4c3d-9e8a-0f1b2c3d4e5f";
const STUB_ENDPOINT = "https://push.e2e.invalid/kairos/device-1";
const STUB_KEYS = { p256dh: "e2e-p256dh", auth: "e2e-auth" };
const CLICK_LOGOUT = "CLICK 로그아웃";
// 3초 상한 (flows.ts PUSH_CLEANUP_TIMEOUT_MS) + CI 러너 여유
const LOGOUT_DELAY_BUDGET_MS = 4_500;

const DEEPLINK_WORKSPACE_NAME = "[E2E] Push Deeplink B";
const DEEPLINK_MEETING_TITLE = "[E2E] push deeplink meeting";
const DEEPLINK_TRANSCRIPT =
  "웹 푸시 딥링크 e2e 고정 회의다. 알림을 누르면 이 회의가 속한 워크스페이스로 한 번 전환돼야 한다.";
// 비멤버 워크스페이스 — 목록 대조로만 판정하므로 존재하지 않는 UUID 와 같다 [가정, T-PWA-59]
const NON_MEMBER_WORKSPACE_ID = "c0ffee00-0000-4000-8000-00000000c0de";

interface PushStubState {
  requestPermission: number;
  subscribe: number;
  unsubscribe: number;
  subscribedKey: number[] | null;
}

// ---------------------------------------------------------------- helpers

/** PushManager · Notification stub — 모든 문서에서 프로토타입을 덮는다 (SW 의 push 핸들러는 건드리지 않는다). */
async function installPushStub(page: Page, permission: NotificationPermission) {
  await page.addInitScript(
    ({ permission, stateKey, endpoint, keys }) => {
      try {
        const initial: PushStubState = {
          requestPermission: 0,
          subscribe: 0,
          unsubscribe: 0,
          subscribedKey: null,
        };
        const read = (): PushStubState =>
          JSON.parse(sessionStorage.getItem(stateKey) ?? "null") ?? initial;
        const write = (state: PushStubState) => sessionStorage.setItem(stateKey, JSON.stringify(state));

        Object.defineProperty(Notification, "permission", { configurable: true, get: () => permission });
        Notification.requestPermission = () => {
          const state = read();
          state.requestPermission += 1;
          write(state);
          return Promise.resolve(permission);
        };

        const makeSubscription = (keyBytes: number[]) => ({
          endpoint,
          expirationTime: null,
          options: { applicationServerKey: Uint8Array.from(keyBytes).buffer, userVisibleOnly: true },
          toJSON: () => ({ endpoint, expirationTime: null, keys }),
          unsubscribe: () => {
            const state = read();
            state.unsubscribe += 1;
            state.subscribedKey = null;
            write(state);
            return Promise.resolve(true);
          },
        });
        PushManager.prototype.getSubscription = function getSubscription() {
          const key = read().subscribedKey;
          return Promise.resolve(key ? (makeSubscription(key) as unknown as PushSubscription) : null);
        };
        PushManager.prototype.subscribe = function subscribe(options?: PushSubscriptionOptionsInit) {
          const source = options?.applicationServerKey;
          const keyBytes =
            source instanceof ArrayBuffer
              ? Array.from(new Uint8Array(source))
              : ArrayBuffer.isView(source)
                ? Array.from(new Uint8Array(source.buffer, source.byteOffset, source.byteLength))
                : [];
          const state = read();
          state.subscribe += 1;
          state.subscribedKey = keyBytes;
          write(state);
          return Promise.resolve(makeSubscription(keyBytes) as unknown as PushSubscription);
        };
      } catch {
        // about:blank 등 sessionStorage·PushManager 가 없는 문서
      }
    },
    { permission, stateKey: STUB_STATE_KEY, endpoint: STUB_ENDPOINT, keys: STUB_KEYS },
  );
}

async function readStubState(page: Page): Promise<PushStubState> {
  return page.evaluate(
    (stateKey) =>
      JSON.parse(sessionStorage.getItem(stateKey) ?? "null") ?? {
        requestPermission: 0,
        subscribe: 0,
        unsubscribe: 0,
        subscribedKey: null,
      },
    STUB_STATE_KEY,
  );
}

async function readMarker(page: Page): Promise<unknown> {
  return page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? "null"), PUSH_MARKER_KEY);
}

/** 표식 + (선택) 이 기기의 구독을 심는다 — 켜기 흐름은 T-PWA-48 이 따로 판정한다. */
async function seedPushOwner(page: Page, userId: string, options: { withSubscription: boolean }) {
  const keyBytes = Array.from(Buffer.from(VAPID_PUBLIC_KEY, "base64url"));
  await page.evaluate(
    ({ markerKey, marker, stateKey, keyBytes, withSubscription }) => {
      localStorage.setItem(markerKey, JSON.stringify(marker));
      if (!withSubscription) return;
      const state = JSON.parse(sessionStorage.getItem(stateKey) ?? "null") ?? {
        requestPermission: 0,
        subscribe: 0,
        unsubscribe: 0,
        subscribedKey: null,
      };
      state.subscribedKey = keyBytes;
      sessionStorage.setItem(stateKey, JSON.stringify(state));
    },
    {
      markerKey: PUSH_MARKER_KEY,
      marker: { userId, subscriptionId: STUB_SUBSCRIPTION_ID },
      stateKey: STUB_STATE_KEY,
      keyBytes,
      withSubscription: options.withSubscription,
    },
  );
}

type DeleteMode = "ok" | "hang";

interface PushApiStub {
  readonly putBodies: unknown[];
}

const CORS_HEADERS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "*",
  "access-control-allow-methods": "GET, PUT, DELETE, OPTIONS",
};

/** API-001~003 고정 — CI 백엔드에는 VAPID 가 없어 실제 값으로는 탭이 숨겨진다. */
async function stubPushApi(
  page: Page,
  options: { isEnabled: boolean; deleteMode?: DeleteMode },
): Promise<PushApiStub> {
  const putBodies: unknown[] = [];
  const preflight = (route: Route) =>
    route.request().method() === "OPTIONS"
      ? route.fulfill({ status: 204, headers: CORS_HEADERS }).then(() => true)
      : Promise.resolve(false);

  await page.route(
    (url) => url.pathname === PUSH_CONFIG_PATH,
    async (route) => {
      if (await preflight(route)) return;
      await route.fulfill({
        headers: CORS_HEADERS,
        json: { isEnabled: options.isEnabled, vapidPublicKey: options.isEnabled ? VAPID_PUBLIC_KEY : null },
      });
    },
  );
  await page.route(
    (url) => url.pathname === PUSH_SUBSCRIPTIONS_PATH,
    async (route) => {
      if (await preflight(route)) return;
      putBodies.push(route.request().postDataJSON());
      await route.fulfill({ headers: CORS_HEADERS, json: { id: STUB_SUBSCRIPTION_ID } });
    },
  );
  await page.route(
    (url) => url.pathname.startsWith(`${PUSH_SUBSCRIPTIONS_PATH}/`),
    async (route) => {
      if (await preflight(route)) return;
      // hang — 응답하지 않는다 (요청은 테스트 종료 때 컨텍스트와 함께 정리된다).
      if (options.deleteMode === "hang") return;
      await route.fulfill({ status: 204, headers: CORS_HEADERS });
    },
  );
  return { putBodies };
}

async function hasRegistration(page: Page): Promise<boolean> {
  return page.evaluate(async () => (await navigator.serviceWorker.getRegistration()) !== undefined);
}

/** SW 등록 대기 (registrar 는 load 뒤 등록한다). CI(prod 빌드)에선 없으면 실패 — 공허 통과 금지. */
async function requireServiceWorkerRegistration(page: Page) {
  const deadline = Date.now() + 15_000;
  let isRegistered = await hasRegistration(page);
  while (!isRegistered && Date.now() < deadline) {
    await page.waitForTimeout(250);
    isRegistered = await hasRegistration(page);
  }
  test.skip(
    !isRegistered && !process.env.CI,
    "SW 미등록 — 로컬 dev 서버. prod 빌드(pnpm build && pnpm start -p 3003)에서 실행",
  );
  expect(isRegistered, "SW 미등록 — 이후 단언이 공허해진다").toBe(true);
}

interface RequestLog {
  readonly events: { readonly label: string; readonly at: number }[];
  mark(label: string): void;
}

function recordRequests(page: Page): RequestLog {
  const events: { label: string; at: number }[] = [];
  page.on("request", (request) => {
    events.push({ label: `${request.method()} ${new URL(request.url()).pathname}`, at: Date.now() });
  });
  return { events, mark: (label) => events.push({ label, at: Date.now() }) };
}

function indexesOf(log: RequestLog, label: string): number[] {
  return log.events.flatMap((event, index) => (event.label === label ? [index] : []));
}

/**
 * sign-out 요청을 서버에 보내지 않고 200 으로 끝낸다 — 공유 storageState 세션을 그대로 쓴다.
 * ★실 로그아웃은 병렬 spec 들이 쓰는 공유 세션을 지우고, 새 세션을 만들려면 실 로그인이 필요한데
 *   Better Auth 기본 rate limit(`/sign-in*` 10초 3회 · prod 에서 켜짐 — better-auth 1.6.29
 *   `dist/api/rate-limiter` getDefaultSpecialRules, `context/create-context` enabled=isProduction)에 걸려
 *   T-PWA-49 가 flaky 했다 (로그인 폼 "요청이 너무 많습니다").
 * ★판정 대상은 sign-out **요청**의 시점이다 — route 가 가로채도 `request` 이벤트는 남으므로 요청 로그로 충분하다.
 */
async function stubSignOut(page: Page) {
  await page.route(
    (url) => url.pathname === SIGN_OUT_PATH,
    (route) => route.fulfill({ json: { success: true } }),
  );
}

/**
 * `/settings` 에서 로그아웃 → `/` 로 이동할 때까지.
 * ★sign-out 을 stub 해서 세션 쿠키가 살아 있다 → header.tsx 의 `router.push("/")` 뒤 랜딩이 서버에서
 *   `/dashboard` 로 리다이렉트한다 (pwa.md C-12, `app/(landing)/page.tsx`). 그래서 "/ 도착" 대신
 *   "`/settings` 에서 `/`(→ `/dashboard`) 로의 이동" 을 판정한다 — 시작 페이지를 `/settings` 로 두는 이유다.
 *   앱 셸에는 `/` 링크가 없어(prefetch 0) 이 이동은 로그아웃 핸들러의 push 로만 생긴다.
 */
async function logoutVia(page: Page, log: RequestLog) {
  expect(new URL(page.url()).pathname, "로그아웃은 /settings 에서 시작한다").toBe("/settings");
  await page.getByRole("button", { name: "계정 메뉴" }).click();
  const logoutItem = page.getByRole("menuitem", { name: "로그아웃" });
  await expect(logoutItem).toBeVisible();
  log.mark(CLICK_LOGOUT);
  await logoutItem.click();
  await page.waitForURL((url) => url.pathname === "/" || url.pathname === "/dashboard", {
    timeout: 15_000,
  });
}

function expectDeleteBetweenClickAndSignOut(log: RequestLog) {
  const clickIndex = indexesOf(log, CLICK_LOGOUT)[0];
  const deleteIndexes = indexesOf(log, `DELETE ${PUSH_SUBSCRIPTIONS_PATH}/${STUB_SUBSCRIPTION_ID}`);
  const signOutIndex = indexesOf(log, `POST ${SIGN_OUT_PATH}`)[0];
  expect(deleteIndexes, "DELETE 정확히 1회").toHaveLength(1);
  expect(signOutIndex, "sign-out POST 가 나갔다").toBeDefined();
  expect(clickIndex < deleteIndexes[0], "DELETE 는 로그아웃 클릭 이후").toBe(true);
  expect(deleteIndexes[0] < signOutIndex, "DELETE 는 sign-out POST 이전").toBe(true);
}

function logoutDelayMs(log: RequestLog): number {
  const click = log.events[indexesOf(log, CLICK_LOGOUT)[0]];
  const signOut = log.events[indexesOf(log, `POST ${SIGN_OUT_PATH}`)[0]];
  return signOut.at - click.at;
}

// ---------------------------------------------------------------- T-PWA-48 설정 탭 (SCR-002)

test.describe("T-PWA-48 알림 설정 탭", () => {
  test("페이지 로드 시 권한 요청 0 → 토글 클릭 → PUT {endpoint, keys} · 표식 저장 · 켜짐", async ({
    page,
    context,
  }) => {
    await context.grantPermissions(["notifications"]);
    await installPushStub(page, "granted");
    const pushApi = await stubPushApi(page, { isEnabled: true });

    await page.goto("/dashboard");
    await requireServiceWorkerRegistration(page);
    const me = await getMe(page);

    await page.goto("/settings?tab=notifications");
    await expect(page.getByTestId("notifications-tab-trigger")).toBeVisible();
    await expect(page.getByTestId("push-settings")).toBeVisible();
    await expect(page.getByTestId("push-status")).toHaveAttribute("data-state", "off");
    expect((await readStubState(page)).requestPermission, "페이지 로드 시 권한 요청 0").toBe(0);

    await page.getByTestId("push-toggle").click();

    await expect(page.getByTestId("push-status")).toHaveAttribute("data-state", "on");
    await expect(page.getByTestId("push-toggle")).toHaveAttribute("aria-checked", "true");
    const stub = await readStubState(page);
    expect(stub.requestPermission).toBe(1);
    expect(stub.subscribe).toBe(1);
    expect(pushApi.putBodies).toEqual([{ endpoint: STUB_ENDPOINT, keys: STUB_KEYS }]);
    expect(await readMarker(page)).toEqual({ userId: me.id, subscriptionId: STUB_SUBSCRIPTION_ID });
  });

  test("권한 denied → 안내 문구 · 토글 disabled", async ({ page }) => {
    await installPushStub(page, "denied");
    await stubPushApi(page, { isEnabled: true });

    await page.goto("/dashboard");
    await requireServiceWorkerRegistration(page);
    await page.goto("/settings?tab=notifications");

    const status = page.getByTestId("push-status");
    await expect(status).toHaveAttribute("data-state", "denied");
    await expect(status).toHaveText("브라우저 설정에서 이 사이트의 알림을 허용해 주세요");
    await expect(page.getByTestId("push-toggle")).toBeDisabled();
    expect((await readStubState(page)).requestPermission).toBe(0);
  });

  test("isEnabled=false → 알림 탭 미노출", async ({ page }) => {
    await stubPushApi(page, { isEnabled: false });
    const configResponse = page.waitForResponse((response) =>
      new URL(response.url()).pathname === PUSH_CONFIG_PATH,
    );
    await page.goto("/settings?tab=notifications");
    await configResponse;
    await page.waitForLoadState("networkidle");

    await expect(page.getByTestId("notifications-tab-trigger")).toHaveCount(0);
    await expect(page.getByTestId("push-settings")).toHaveCount(0);
  });

  test.describe("SW 등록 없음", () => {
    // 새 컨텍스트에서 getRegistration()===undefined · ready pending · register() 는 undefined 로 resolve (pwa.md C-26).
    // registrar 의 경고 1줄은 허용한다.
    test.use({ serviceWorkers: "block" });

    test("'사용 불가' · 토글 disabled · 권한 요청 0 · 화면 멈춤 없음", async ({ page }) => {
      await installPushStub(page, "granted");
      await stubPushApi(page, { isEnabled: true });
      await page.goto("/settings?tab=notifications");
      expect(await hasRegistration(page), "SW 등록 없음 전제").toBe(false);

      const status = page.getByTestId("push-status");
      await expect(status).toHaveAttribute("data-state", "unavailable", { timeout: 10_000 });
      await expect(status).toHaveText("이 브라우저·환경에서는 알림을 켤 수 없어요");
      await expect(page.getByTestId("push-toggle")).toBeDisabled();
      expect((await readStubState(page)).requestPermission).toBe(0);
    });
  });
});

// ---------------------------------------------------------------- T-PWA-49 로그아웃 순서

test.describe("T-PWA-49 로그아웃 — 푸시 정리가 sign-out 앞", () => {
  // 실 로그인 0 — 공유 storageState 세션 + sign-out stub (stubSignOut 주석 참고). 서버 세션을 건드리지 않아
  // 병렬로 도는 다른 spec 과 rate limit 에 무관하다.

  test("SW 등록 있음 — DELETE 가 클릭 이후·sign-out 이전 · unsubscribe 1 · 표식 삭제 · / 로 이동", async ({
    page,
  }) => {
    await installPushStub(page, "granted");
    await stubPushApi(page, { isEnabled: true });
    await stubSignOut(page);
    const log = recordRequests(page);

    await page.goto("/settings");
    await requireServiceWorkerRegistration(page);
    const me = await getMe(page);
    await seedPushOwner(page, me.id, { withSubscription: true });
    // 표식 일치 상태로 앱 로드 동기화가 돈다 (PUT 재전송 — DELETE 는 내지 않는다)
    await page.reload();
    await page.waitForLoadState("networkidle");

    await logoutVia(page, log);

    expectDeleteBetweenClickAndSignOut(log);
    expect((await readStubState(page)).unsubscribe, "unsubscribe 1회").toBe(1);
    expect(await readMarker(page)).toBeNull();
  });

  test("SW 등록 있음 — DELETE 가 응답하지 않아도 로그아웃 완료 (추가 지연 ≤ 3초)", async ({ page }) => {
    await installPushStub(page, "granted");
    await stubPushApi(page, { isEnabled: true, deleteMode: "hang" });
    await stubSignOut(page);
    const log = recordRequests(page);

    await page.goto("/settings");
    await requireServiceWorkerRegistration(page);
    const me = await getMe(page);
    await seedPushOwner(page, me.id, { withSubscription: true });
    await page.reload();
    await page.waitForLoadState("networkidle");

    await logoutVia(page, log);

    expectDeleteBetweenClickAndSignOut(log);
    expect(logoutDelayMs(log)).toBeLessThan(LOGOUT_DELAY_BUDGET_MS);
    expect(await readMarker(page)).toBeNull();
  });

  test.describe("SW 등록 없음", () => {
    test.use({ serviceWorkers: "block" });

    test("대기 없이 로그아웃 · 동기화+로그아웃 전체에서 DELETE 정확히 1회 · 표식 삭제", async ({ page }) => {
      await installPushStub(page, "granted");
      await stubPushApi(page, { isEnabled: true });
      await stubSignOut(page);
      const log = recordRequests(page);

      await page.goto("/settings");
      expect(await hasRegistration(page), "SW 등록 없음 전제").toBe(false);
      // 표식은 앱 로드 동기화가 끝난 뒤에 심는다 — 먼저 심으면 동기화가 DELETE·삭제를 해 버려
      // 로그아웃 ① 을 검증하지 못한다 (test-matrix T-PWA-49).
      await page.waitForLoadState("networkidle");
      const me = await getMe(page);
      await seedPushOwner(page, me.id, { withSubscription: false });

      await logoutVia(page, log);

      expectDeleteBetweenClickAndSignOut(log);
      expect(logoutDelayMs(log)).toBeLessThan(3_000);
      expect(await readMarker(page)).toBeNull();
    });
  });
});

// ---------------------------------------------------------------- T-PWA-59 워크스페이스 딥링크

interface WorkspaceSummary {
  readonly id: string;
  readonly name: string;
}

/** discover-or-create — 고정 이름·제목으로 멱등 (로컬 공유 DB 누적 방지). */
async function ensureDeepLinkFixture(page: Page) {
  const listResponse = await api(page, "GET", "/api/v1/workspaces");
  expect(listResponse.ok(), "GET /workspaces").toBe(true);
  const workspaces = (await listResponse.json()) as WorkspaceSummary[];

  let workspaceB = workspaces.find((workspace) => workspace.name === DEEPLINK_WORKSPACE_NAME);
  if (!workspaceB) {
    const created = await api(page, "POST", "/api/v1/workspaces", { name: DEEPLINK_WORKSPACE_NAME });
    expect(created.ok(), "POST /workspaces").toBe(true);
    workspaceB = (await created.json()) as WorkspaceSummary;
  }
  const workspaceBId = workspaceB.id;
  const workspaceA = workspaces.find((workspace) => workspace.id !== workspaceBId);
  if (!workspaceA) throw new Error("활성으로 둘 워크스페이스 A 가 없다 (auth.setup 이 1개를 보장한다)");

  const meetingsResponse = await api(
    page,
    "GET",
    `/api/v1/workspaces/${workspaceBId}/meetings?pageSize=100`,
  );
  expect(meetingsResponse.ok(), "GET meetings").toBe(true);
  const { items } = (await meetingsResponse.json()) as { items: { id: string; title: string }[] };
  let meetingId = items.find((meeting) => meeting.title === DEEPLINK_MEETING_TITLE)?.id;
  if (!meetingId) {
    const captured = await api(page, "POST", `/api/v1/workspaces/${workspaceBId}/meetings/capture`, {
      title: DEEPLINK_MEETING_TITLE,
      transcriptText: DEEPLINK_TRANSCRIPT,
    });
    expect(captured.status(), "POST capture").toBe(202);
    meetingId = ((await captured.json()) as { id: string }).id;
  }
  return { workspaceA, workspaceB, meetingId };
}

async function readActiveWorkspaceId(page: Page): Promise<string | null> {
  return page.evaluate(
    () => JSON.parse(localStorage.getItem("kairos-workspace") ?? "{}").state?.activeWorkspaceId ?? null,
  );
}

/** 진입~본문 표시 동안 오류 블록이 한 번이라도 그려졌는지 — 파서 삽입까지 본다. */
async function watchMeetingDetailError(page: Page) {
  await page.addInitScript(() => {
    const check = () => {
      if (document.querySelector('[data-testid="meeting-detail-error"]')) {
        window.__meetingDetailErrorSeen = true;
      }
    };
    new MutationObserver(check).observe(document, { childList: true, subtree: true });
  });
}

/** 활성 = A 로 앱에 정착시킨다. 반환값 = 그때의 history.length */
async function settleOnWorkspaceA(page: Page) {
  await page.goto("/dashboard");
  await page.waitForLoadState("networkidle");
  const me = await getMe(page);
  const fixture = await ensureDeepLinkFixture(page);
  await injectActiveWorkspace(page, fixture.workspaceA.id, me.id);
  await page.reload();
  await page.waitForLoadState("networkidle");
  expect(await readActiveWorkspaceId(page)).toBe(fixture.workspaceA.id);
  const historyLength = await page.evaluate(() => history.length);
  return { ...fixture, historyLength };
}

test.describe("T-PWA-59 알림 딥링크 워크스페이스 전환", () => {
  // 같은 이름의 워크스페이스 B 를 두 워커가 동시에 만들지 않게 직렬로 돈다.
  test.describe.configure({ mode: "serial" });

  test("멤버 B → 1회 전환 · 쿼리 제거 · replace · toast 1 · 오류 블록 미출현 · console.error 0", async ({
    page,
  }) => {
    await watchMeetingDetailError(page);
    const { workspaceB, meetingId, historyLength } = await settleOnWorkspaceA(page);
    const consoleErrors = collectConsoleErrors(page);

    await page.goto(`/meetings/${meetingId}?workspace=${workspaceB.id}`);

    // toast 는 sonner 기본 수명 뒤 사라진다 — 가장 먼저 단언한다
    await expect(page.getByText(`“${workspaceB.name}” 워크스페이스로 전환했습니다`)).toHaveCount(1);
    await expect(page.getByTestId("meeting-status")).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`/meetings/${meetingId}$`));
    await expect(page.getByTestId("workspace-switcher")).toContainText(workspaceB.name);
    expect(await readActiveWorkspaceId(page)).toBe(workspaceB.id);
    expect(await page.evaluate(() => history.length), "replace — 히스토리 추가 0").toBe(historyLength + 1);
    expect(await page.evaluate(() => window.__meetingDetailErrorSeen === true), "오류 블록 미출현").toBe(false);
    await expect(page.getByTestId("meeting-detail-error")).toHaveCount(0);
    expect(consoleErrors()).toEqual([]);
  });

  test("비멤버 C → 활성 A 유지 · 쿼리 제거 · toast 0 · 오류 블록", async ({ page }) => {
    const { workspaceA, meetingId } = await settleOnWorkspaceA(page);

    await page.goto(`/meetings/${meetingId}?workspace=${NON_MEMBER_WORKSPACE_ID}`);

    await expect(page.getByTestId("meeting-detail-error")).toBeVisible();
    await expect(page.getByTestId("meeting-detail-error")).toContainText("회의 데이터를 불러올 수 없습니다");
    await expect(page).toHaveURL(new RegExp(`/meetings/${meetingId}$`));
    expect(await readActiveWorkspaceId(page)).toBe(workspaceA.id);
    await expect(page.getByText("워크스페이스로 전환했습니다")).toHaveCount(0);
  });
});
