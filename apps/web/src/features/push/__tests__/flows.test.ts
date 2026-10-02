// T-PWA-45 (등록 없음 판정 · 로그아웃 즉시 resolve · 표식 파싱 실패) · T-PWA-50 (계정 전환·등록 없음 분기 ·
// compare-and-delete · promise 공유) · T-PWA-51 (표식 일치 → PUT 1회) — test-matrix.md, pwa.md §5.5
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ApiClient } from "@/lib/api-client";
import {
  PUSH_CLEANUP_TIMEOUT_MS,
  createBrowserPushDeps,
  deletePushSubscriptionShared,
  disablePushOnDevice,
  enablePush,
  resolvePushDeviceState,
  syncPushOnAppLoad,
  type PushDeviceDeps,
  type PushRegistrationLike,
  type PushSubscriptionLike,
} from "../flows";
import { PUSH_OWNER_MARKER_KEY, readOwnerMarker } from "../marker";
import { base64UrlToUint8Array, type PushEnvironment } from "../utils";

const ME = "11111111-1111-4111-8111-111111111111";
const OTHER_USER = "22222222-2222-4222-8222-222222222222";
const SUBSCRIPTION_ID = "33333333-3333-4333-8333-333333333333";
const NEW_SUBSCRIPTION_ID = "44444444-4444-4444-8444-444444444444";
const VAPID_PUBLIC_KEY =
  "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U";
const ENDPOINT = "https://fcm.googleapis.com/fcm/send/device-token";

const DESKTOP_ENV: PushEnvironment = {
  hasServiceWorker: true,
  hasPushManager: true,
  hasNotification: true,
  isSecureContext: true,
  userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141.0 Safari/537.36",
  platform: "Linux x86_64",
  maxTouchPoints: 0,
  isNavigatorStandalone: false,
  isDisplayModeStandalone: false,
  notificationPermission: "granted",
};

type FetchImpl = (path: string, init?: RequestInit) => Promise<unknown>;

function createApi(impl: FetchImpl = () => Promise.resolve(undefined)) {
  const fetch = vi.fn(impl);
  const api: ApiClient = {
    fetch: <T>(path: string, init?: RequestInit) => fetch(path, init) as Promise<T>,
    fetchRaw: () => Promise.reject(new Error("unused")),
    getToken: () => Promise.resolve("token"),
  };
  const callsOf = (method: string) =>
    fetch.mock.calls.filter(([, init]) => (init?.method ?? "GET") === method);
  return { api, fetch, callsOf };
}

function createSubscription(keyBytes = base64UrlToUint8Array(VAPID_PUBLIC_KEY)) {
  const unsubscribe = vi.fn(() => Promise.resolve(true));
  const subscription: PushSubscriptionLike = {
    options: { applicationServerKey: keyBytes.slice().buffer },
    toJSON: () => ({ endpoint: ENDPOINT, expirationTime: null, keys: { p256dh: "p256dh-key", auth: "auth-key" } }),
    unsubscribe,
  };
  return { subscription, unsubscribe };
}

function createRegistration(initial: PushSubscriptionLike | null) {
  let current = initial;
  const fresh = createSubscription();
  const subscribe = vi.fn<(options: PushSubscriptionOptionsInit) => Promise<PushSubscriptionLike>>(() => {
    current = fresh.subscription;
    return Promise.resolve(fresh.subscription);
  });
  const registration: PushRegistrationLike = {
    pushManager: { getSubscription: () => Promise.resolve(current), subscribe },
  };
  return { registration, subscribe, freshUnsubscribe: fresh.unsubscribe };
}

function setMarker(userId: string, subscriptionId: string) {
  localStorage.setItem(PUSH_OWNER_MARKER_KEY, JSON.stringify({ userId, subscriptionId }));
}

function deps(registration: PushRegistrationLike | undefined): PushDeviceDeps {
  return { getRegistration: () => Promise.resolve(registration), storage: localStorage };
}

/** `navigator.serviceWorker` 를 설치한다 — `ready` 는 getter spy (접근 0 단언용, 영원히 pending) */
function installServiceWorkerContainer(registration: PushRegistrationLike | undefined) {
  const readyGetter = vi.fn(() => new Promise<never>(() => {}));
  const getRegistration = vi.fn(() => Promise.resolve(registration));
  const container = {
    getRegistration,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  };
  Object.defineProperty(container, "ready", { get: readyGetter, configurable: true });
  Object.defineProperty(navigator, "serviceWorker", { value: container, configurable: true });
  return { readyGetter, getRegistration };
}

/** promise 가 이미 settle 됐는지 — 타이머를 진행하지 않고 마이크로태스크만 비운다 */
async function isSettled(promise: Promise<unknown>): Promise<boolean> {
  let settled = false;
  void promise.then(
    () => (settled = true),
    () => (settled = true),
  );
  await vi.advanceTimersByTimeAsync(0);
  return settled;
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
  Reflect.deleteProperty(navigator, "serviceWorker");
});

describe("T-PWA-45 등록 없음 (getRegistration → undefined)", () => {
  it("'사용 불가' 로 판정하고 serviceWorker.ready 에 접근하지 않는다", async () => {
    const { readyGetter, getRegistration } = installServiceWorkerContainer(undefined);
    const state = await resolvePushDeviceState(ME, VAPID_PUBLIC_KEY, DESKTOP_ENV, createBrowserPushDeps());
    expect(state).toBe("unavailable");
    expect(getRegistration).toHaveBeenCalledTimes(1);
    expect(readyGetter).not.toHaveBeenCalled();
  });

  it("로그아웃 정리가 즉시 resolve 한다 (3초 타이머 대기 0, ready 접근 0)", async () => {
    vi.useFakeTimers();
    const { readyGetter } = installServiceWorkerContainer(undefined);
    const { api, fetch } = createApi();
    const cleanup = disablePushOnDevice(api, createBrowserPushDeps());
    expect(await isSettled(cleanup)).toBe(true);
    expect(readyGetter).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("표식이 있으면 등록이 없어도 API-003 1회 후 표식을 지운다 — 대기 없이", async () => {
    vi.useFakeTimers();
    const { readyGetter } = installServiceWorkerContainer(undefined);
    setMarker(ME, SUBSCRIPTION_ID);
    const { api, callsOf } = createApi();
    expect(await isSettled(disablePushOnDevice(api, createBrowserPushDeps()))).toBe(true);
    expect(callsOf("DELETE").map(([path]) => path)).toEqual([
      `/users/me/push-subscriptions/${SUBSCRIPTION_ID}`,
    ]);
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();
    expect(readyGetter).not.toHaveBeenCalled();
  });

  it("navigator.serviceWorker 가 아예 없어도 판정·정리가 throw 하지 않는다", async () => {
    const { api } = createApi();
    await expect(
      resolvePushDeviceState(ME, VAPID_PUBLIC_KEY, { ...DESKTOP_ENV, hasServiceWorker: false }, createBrowserPushDeps()),
    ).resolves.toBe("unavailable");
    await expect(disablePushOnDevice(api, createBrowserPushDeps())).resolves.toBeUndefined();
  });
});

describe("T-PWA-45 표식 파싱", () => {
  it.each([
    ["깨진 JSON", "{not json"],
    ["uuid 아닌 userId", JSON.stringify({ userId: "me", subscriptionId: SUBSCRIPTION_ID })],
    ["필드 누락", JSON.stringify({ userId: ME })],
    ["배열", JSON.stringify([ME, SUBSCRIPTION_ID])],
  ])("%s → 없음", (_label, raw) => {
    localStorage.setItem(PUSH_OWNER_MARKER_KEY, raw);
    expect(readOwnerMarker(localStorage)).toBeNull();
  });

  it("파싱 실패 표식은 '켜짐' 근거가 되지 않는다", async () => {
    localStorage.setItem(PUSH_OWNER_MARKER_KEY, "{not json");
    const { subscription } = createSubscription();
    const { registration } = createRegistration(subscription);
    await expect(resolvePushDeviceState(ME, VAPID_PUBLIC_KEY, DESKTOP_ENV, deps(registration))).resolves.toBe("off");
  });
});

describe("SCR-002 상태 판정", () => {
  it("구독 + 표식 userId == me → on, 다른 계정 표식 → off, 권한 denied → denied", async () => {
    const { subscription } = createSubscription();
    const { registration } = createRegistration(subscription);
    setMarker(ME, SUBSCRIPTION_ID);
    await expect(resolvePushDeviceState(ME, VAPID_PUBLIC_KEY, DESKTOP_ENV, deps(registration))).resolves.toBe("on");
    await expect(resolvePushDeviceState(OTHER_USER, VAPID_PUBLIC_KEY, DESKTOP_ENV, deps(registration))).resolves.toBe("off");
    await expect(
      resolvePushDeviceState(ME, VAPID_PUBLIC_KEY, { ...DESKTOP_ENV, notificationPermission: "denied" }, deps(registration)),
    ).resolves.toBe("denied");
  });
});

describe("켜기 (토글 클릭)", () => {
  it("권한 요청 → subscribe(userVisibleOnly) → PUT {endpoint, keys} → 표식 저장", async () => {
    const { registration, subscribe } = createRegistration(null);
    const requestPermission = vi.fn(() => Promise.resolve<NotificationPermission>("granted"));
    const { api, callsOf } = createApi(() => Promise.resolve({ id: SUBSCRIPTION_ID }));

    await expect(
      enablePush(api, { meId: ME, vapidPublicKey: VAPID_PUBLIC_KEY }, { ...deps(registration), requestPermission }),
    ).resolves.toBe("on");

    expect(requestPermission).toHaveBeenCalledTimes(1);
    expect(subscribe).toHaveBeenCalledWith({
      userVisibleOnly: true,
      applicationServerKey: base64UrlToUint8Array(VAPID_PUBLIC_KEY),
    });
    const puts = callsOf("PUT");
    expect(puts).toHaveLength(1);
    expect(puts[0][0]).toBe("/users/me/push-subscriptions");
    expect(JSON.parse(String(puts[0][1]?.body))).toEqual({
      endpoint: ENDPOINT,
      keys: { p256dh: "p256dh-key", auth: "auth-key" },
    });
    expect(readOwnerMarker(localStorage)).toEqual({ userId: ME, subscriptionId: SUBSCRIPTION_ID });
  });

  it("권한 거부·닫음 → 구독·네트워크 0", async () => {
    for (const permission of ["denied", "default"] as const) {
      const { registration, subscribe } = createRegistration(null);
      const { api, fetch } = createApi();
      const outcome = await enablePush(
        api,
        { meId: ME, vapidPublicKey: VAPID_PUBLIC_KEY },
        { ...deps(registration), requestPermission: () => Promise.resolve(permission) },
      );
      expect(outcome).toBe(permission === "denied" ? "denied" : "dismissed");
      expect(subscribe).not.toHaveBeenCalled();
      expect(fetch).not.toHaveBeenCalled();
    }
  });

  it("PUT 실패 → 방금 만든 구독을 끊고 throw, 표식 없음 (fail-closed)", async () => {
    const { registration, freshUnsubscribe } = createRegistration(null);
    const { api } = createApi(() => Promise.reject(new Error("500")));
    await expect(
      enablePush(
        api,
        { meId: ME, vapidPublicKey: VAPID_PUBLIC_KEY },
        { ...deps(registration), requestPermission: () => Promise.resolve("granted") },
      ),
    ).rejects.toThrow("500");
    expect(freshUnsubscribe).toHaveBeenCalledTimes(1);
    expect(readOwnerMarker(localStorage)).toBeNull();
  });

  it("기존 구독의 공개키가 다르면 먼저 unsubscribe 하고 새로 구독한다", async () => {
    const stale = createSubscription(new Uint8Array(65).fill(7));
    const { registration, subscribe } = createRegistration(stale.subscription);
    const { api } = createApi(() => Promise.resolve({ id: SUBSCRIPTION_ID }));
    await enablePush(
      api,
      { meId: ME, vapidPublicKey: VAPID_PUBLIC_KEY },
      { ...deps(registration), requestPermission: () => Promise.resolve("granted") },
    );
    expect(stale.unsubscribe).toHaveBeenCalledTimes(1);
    expect(subscribe).toHaveBeenCalledTimes(1);
  });
});

describe("끄기 = 로그아웃 정리", () => {
  it("① 표식 id 로 DELETE ② unsubscribe ③ 표식 삭제 — 요청은 DELETE 가 먼저", async () => {
    const { subscription, unsubscribe } = createSubscription();
    const { registration } = createRegistration(subscription);
    setMarker(ME, SUBSCRIPTION_ID);
    const order: string[] = [];
    const { api } = createApi((_path, init) => {
      order.push(init?.method ?? "GET");
      return Promise.resolve(undefined);
    });
    unsubscribe.mockImplementation(() => {
      order.push("unsubscribe");
      return Promise.resolve(true);
    });
    await disablePushOnDevice(api, deps(registration));
    expect(order).toEqual(["DELETE", "unsubscribe"]);
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();
  });

  it("DELETE 가 응답하지 않아도 3초에 끝나고, unsubscribe 는 DELETE 를 기다리지 않는다", async () => {
    vi.useFakeTimers();
    const { subscription, unsubscribe } = createSubscription();
    const { registration } = createRegistration(subscription);
    setMarker(ME, SUBSCRIPTION_ID);
    const { api } = createApi(() => new Promise(() => {}));
    let isDone = false;
    void disablePushOnDevice(api, deps(registration)).then(() => (isDone = true));
    await vi.advanceTimersByTimeAsync(0);
    // 느린 네트워크가 로컬 unsubscribe 예산을 잡아먹으면 로그아웃 뒤에도 이 기기가 푸시를 받는다
    expect(unsubscribe).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(PUSH_CLEANUP_TIMEOUT_MS - 1);
    expect(isDone).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    expect(isDone).toBe(true);
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();
  });
});

describe("T-PWA-50 앱 로드 동기화 — 등록 있음", () => {
  it("구독 + 표식 userId ≠ me → unsubscribe 1회, 네트워크 0", async () => {
    const { subscription, unsubscribe } = createSubscription();
    const { registration } = createRegistration(subscription);
    setMarker(OTHER_USER, SUBSCRIPTION_ID);
    const { api, fetch } = createApi();
    await syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, deps(registration));
    expect(unsubscribe).toHaveBeenCalledTimes(1);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("구독 + 표식 없음 → unsubscribe 1회, 네트워크 0", async () => {
    const { subscription, unsubscribe } = createSubscription();
    const { registration } = createRegistration(subscription);
    const { api, fetch } = createApi();
    await syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, deps(registration));
    expect(unsubscribe).toHaveBeenCalledTimes(1);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("구독 없음 → 표식 삭제, 네트워크 0", async () => {
    const { registration } = createRegistration(null);
    setMarker(ME, SUBSCRIPTION_ID);
    const { api, fetch } = createApi();
    await syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, deps(registration));
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });
});

describe("T-PWA-50 앱 로드 동기화 — 등록 없음 (ready 접근 0)", () => {
  it("표식 userId == me → DELETE 1회 후 표식 삭제", async () => {
    const { readyGetter } = installServiceWorkerContainer(undefined);
    setMarker(ME, SUBSCRIPTION_ID);
    const { api, callsOf, fetch } = createApi();
    await syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, createBrowserPushDeps());
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(callsOf("DELETE")[0][0]).toBe(`/users/me/push-subscriptions/${SUBSCRIPTION_ID}`);
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();
    expect(readyGetter).not.toHaveBeenCalled();
  });

  it("DELETE 실패여도, 3초 타임아웃이어도 표식을 지운다", async () => {
    installServiceWorkerContainer(undefined);
    setMarker(ME, SUBSCRIPTION_ID);
    await syncPushOnAppLoad(createApi(() => Promise.reject(new Error("offline"))).api, ME, VAPID_PUBLIC_KEY, createBrowserPushDeps());
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();

    vi.useFakeTimers();
    setMarker(ME, NEW_SUBSCRIPTION_ID);
    const sync = syncPushOnAppLoad(createApi(() => new Promise(() => {})).api, ME, VAPID_PUBLIC_KEY, createBrowserPushDeps());
    await vi.advanceTimersByTimeAsync(PUSH_CLEANUP_TIMEOUT_MS);
    await sync;
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();
  });

  it("표식 불일치 → 네트워크 0 + 표식 삭제", async () => {
    const { readyGetter } = installServiceWorkerContainer(undefined);
    setMarker(OTHER_USER, SUBSCRIPTION_ID);
    const { api, fetch } = createApi();
    await syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, createBrowserPushDeps());
    expect(fetch).not.toHaveBeenCalled();
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();
    expect(readyGetter).not.toHaveBeenCalled();
  });

  it("표식 없음 → 네트워크 0", async () => {
    const { readyGetter } = installServiceWorkerContainer(undefined);
    const { api, fetch } = createApi();
    await syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, createBrowserPushDeps());
    expect(fetch).not.toHaveBeenCalled();
    expect(readyGetter).not.toHaveBeenCalled();
  });
});

describe("T-PWA-50 compare-and-delete · promise 공유", () => {
  it("DELETE 대기 중 표식이 다른 subscriptionId 로 바뀌면 지우지 않는다", async () => {
    setMarker(ME, SUBSCRIPTION_ID);
    let resolveDelete: () => void = () => {};
    const { api, fetch } = createApi(
      () => new Promise<undefined>((resolve) => (resolveDelete = () => resolve(undefined))),
    );
    const sync = syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, deps(undefined));
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    setMarker(ME, NEW_SUBSCRIPTION_ID);
    resolveDelete();
    await sync;
    expect(readOwnerMarker(localStorage)).toEqual({ userId: ME, subscriptionId: NEW_SUBSCRIPTION_ID });
  });

  it("같은 id 의 DELETE 는 진행 중이면 같은 promise 를 돌려주고 요청은 1번", async () => {
    let resolveDelete: () => void = () => {};
    const { api, fetch } = createApi(
      () => new Promise<undefined>((resolve) => (resolveDelete = () => resolve(undefined))),
    );
    const first = deletePushSubscriptionShared(api, SUBSCRIPTION_ID);
    const second = deletePushSubscriptionShared(api, SUBSCRIPTION_ID);
    expect(second).toBe(first);
    resolveDelete();
    await first;
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("동기화 DELETE 진행 중 로그아웃 정리 → DELETE 1회, 둘 다 끝난다", async () => {
    setMarker(ME, SUBSCRIPTION_ID);
    let resolveDelete: () => void = () => {};
    const { api, fetch, callsOf } = createApi(
      () => new Promise<undefined>((resolve) => (resolveDelete = () => resolve(undefined))),
    );
    const sync = syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, deps(undefined));
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    const logout = disablePushOnDevice(api, deps(undefined));
    resolveDelete();
    await Promise.all([sync, logout]);
    expect(callsOf("DELETE")).toHaveLength(1);
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();
  });
});

describe("T-PWA-51 앱 로드 동기화 — 표식 일치", () => {
  it("PUT 정확히 1회 (endpoint 교체·서버 행 유실 복구)", async () => {
    const { subscription, unsubscribe } = createSubscription();
    const { registration } = createRegistration(subscription);
    setMarker(ME, SUBSCRIPTION_ID);
    const { api, fetch, callsOf } = createApi(() => Promise.resolve({ id: SUBSCRIPTION_ID }));
    await syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, deps(registration));
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(callsOf("PUT")).toHaveLength(1);
    expect(unsubscribe).not.toHaveBeenCalled();
    expect(readOwnerMarker(localStorage)).toEqual({ userId: ME, subscriptionId: SUBSCRIPTION_ID });
  });

  it("서버가 새 id 를 주면 표식을 새 id 로 바꾼다 (로그아웃 ① 이 새 행을 지우도록)", async () => {
    const { subscription } = createSubscription();
    const { registration } = createRegistration(subscription);
    setMarker(ME, SUBSCRIPTION_ID);
    const { api } = createApi(() => Promise.resolve({ id: NEW_SUBSCRIPTION_ID }));
    await syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, deps(registration));
    expect(readOwnerMarker(localStorage)).toEqual({ userId: ME, subscriptionId: NEW_SUBSCRIPTION_ID });
  });

  it("PUT 실패는 삼킨다 (best-effort)", async () => {
    const { subscription } = createSubscription();
    const { registration } = createRegistration(subscription);
    setMarker(ME, SUBSCRIPTION_ID);
    const { api } = createApi(() => Promise.reject(new Error("offline")));
    await expect(syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, deps(registration))).resolves.toBeUndefined();
  });
});

describe("VAPID 키 교체 — 구독의 applicationServerKey ≠ API-001 공개키 (pwa.md §5.5)", () => {
  const STALE_KEY_BYTES = new Uint8Array(65).fill(7);

  it("표식 일치 → DELETE(표식 id) + unsubscribe + 표식 삭제, PUT 0", async () => {
    const stale = createSubscription(STALE_KEY_BYTES);
    const { registration } = createRegistration(stale.subscription);
    setMarker(ME, SUBSCRIPTION_ID);
    const { api, fetch, callsOf } = createApi();
    await syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, deps(registration));
    expect(callsOf("DELETE").map(([path]) => path)).toEqual([
      `/users/me/push-subscriptions/${SUBSCRIPTION_ID}`,
    ]);
    expect(callsOf("PUT")).toHaveLength(0);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(stale.unsubscribe).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();
  });

  it("표식 불일치 → unsubscribe 만, 네트워크 0 (다른 계정 표식은 건드리지 않는다)", async () => {
    const stale = createSubscription(STALE_KEY_BYTES);
    const { registration } = createRegistration(stale.subscription);
    setMarker(OTHER_USER, SUBSCRIPTION_ID);
    const { api, fetch } = createApi();
    await syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, deps(registration));
    expect(stale.unsubscribe).toHaveBeenCalledTimes(1);
    expect(fetch).not.toHaveBeenCalled();
    expect(readOwnerMarker(localStorage)).toEqual({ userId: OTHER_USER, subscriptionId: SUBSCRIPTION_ID });
  });

  it("DELETE 가 응답하지 않아도 unsubscribe 는 기다리지 않고, 3초 뒤 표식을 지운다", async () => {
    vi.useFakeTimers();
    const stale = createSubscription(STALE_KEY_BYTES);
    const { registration } = createRegistration(stale.subscription);
    setMarker(ME, SUBSCRIPTION_ID);
    const { api } = createApi(() => new Promise(() => {}));
    const sync = syncPushOnAppLoad(api, ME, VAPID_PUBLIC_KEY, deps(registration));
    await vi.advanceTimersByTimeAsync(0);
    expect(stale.unsubscribe).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(PUSH_CLEANUP_TIMEOUT_MS);
    await sync;
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();
  });

  it("공개키를 모르면(null) 비교하지 않는다 — 표식 일치면 기존대로 PUT 1회", async () => {
    const stale = createSubscription(STALE_KEY_BYTES);
    const { registration } = createRegistration(stale.subscription);
    setMarker(ME, SUBSCRIPTION_ID);
    const { api, callsOf } = createApi(() => Promise.resolve({ id: SUBSCRIPTION_ID }));
    await syncPushOnAppLoad(api, ME, null, deps(registration));
    expect(callsOf("PUT")).toHaveLength(1);
    expect(callsOf("DELETE")).toHaveLength(0);
    expect(stale.unsubscribe).not.toHaveBeenCalled();
    expect(readOwnerMarker(localStorage)).toEqual({ userId: ME, subscriptionId: SUBSCRIPTION_ID });
  });

  it("SCR-002 상태: 옛 키 구독 + 표식 일치 → off, 키 null → on", async () => {
    const stale = createSubscription(STALE_KEY_BYTES);
    const { registration } = createRegistration(stale.subscription);
    setMarker(ME, SUBSCRIPTION_ID);
    await expect(
      resolvePushDeviceState(ME, VAPID_PUBLIC_KEY, DESKTOP_ENV, deps(registration)),
    ).resolves.toBe("off");
    await expect(resolvePushDeviceState(ME, null, DESKTOP_ENV, deps(registration))).resolves.toBe("on");
    expect(stale.unsubscribe).not.toHaveBeenCalled();
  });
});
